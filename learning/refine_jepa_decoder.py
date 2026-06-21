"""Refine only the observation decoder of a trained SensorJEPA checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from learning.datasets import build_context_transitions, load_simulation_csv
from learning.evaluate_jepa import infer_checkpoint_dims, infer_context_steps, split_indices
from learning.jepa import SensorJEPA, weighted_observation_loss

try:
    import torch
except ModuleNotFoundError:
    torch = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fine-tune only the JEPA observation decoder.")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=16384)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--distance-loss-weight", type=float, default=1.0)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--eval-every", type=int, default=50)
    parser.add_argument("--early-stopping-patience", type=int, default=20)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required to refine the JEPA decoder.")

    args = build_parser().parse_args()
    if args.epochs <= 0:
        raise ValueError("--epochs must be > 0.")
    if args.eval_every <= 0:
        raise ValueError("--eval-every must be > 0.")
    if args.early_stopping_patience < 0:
        raise ValueError("--early-stopping-patience must be >= 0.")

    device = resolve_device(args.device)
    checkpoint = load_full_checkpoint(args.checkpoint)
    state_dict = checkpoint["model_state_dict"] if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint
    dims = infer_checkpoint_dims(state_dict)
    if dims.get("decoded_obs_dim") is None:
        dims["decoded_obs_dim"] = 3
    if isinstance(checkpoint, dict):
        for key in ("obs_dim", "action_dim", "latent_dim", "hidden_dim", "decoded_obs_dim"):
            if checkpoint.get(key) is not None:
                dims[key] = int(checkpoint[key])
    context_steps = int(checkpoint.get("context_steps") if isinstance(checkpoint, dict) and checkpoint.get("context_steps") else infer_context_steps(dims["obs_dim"], dims["action_dim"]))

    arrays = build_context_transitions(load_simulation_csv(args.log), context_steps=context_steps)
    train_idx_np, val_idx_np = split_indices(arrays, args.val_fraction)

    model = SensorJEPA(
        obs_dim=dims["obs_dim"],
        action_dim=dims["action_dim"],
        latent_dim=dims["latent_dim"],
        hidden_dim=dims["hidden_dim"],
        decoded_obs_dim=dims["decoded_obs_dim"],
    ).to(device)
    model.load_state_dict(state_dict)
    model.train()
    freeze_except_decoder(model)

    obs = torch.from_numpy(arrays["obs"]).float().to(device)
    actions = torch.from_numpy(arrays["action"]).float().to(device)
    target_obs = torch.from_numpy(arrays["target_obs"]).float().to(device)
    train_idx = torch.from_numpy(train_idx_np).long().to(device)
    val_idx = torch.from_numpy(val_idx_np).long().to(device)

    optimizer = torch.optim.AdamW(
        model.obs_decoder.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )

    print(
        f"[i] refine decoder device={device} samples={len(obs)} train={len(train_idx)} val={len(val_idx)} "
        f"context_steps={context_steps} decoded_obs_dim={dims['decoded_obs_dim']}",
        flush=True,
    )

    best_val = float("inf")
    best_epoch = 0
    best_decoder_state = None
    checks_since_improvement = 0
    stopped_epoch = 0
    early_stopped = False
    for epoch in range(1, args.epochs + 1):
        stopped_epoch = epoch
        model.train()
        local_idx = torch.randint(0, len(train_idx), (min(args.batch_size, len(train_idx)),), device=device)
        idx = train_idx[local_idx]
        loss = decoder_loss(model, obs[idx], actions[idx], target_obs[idx], args.distance_loss_weight)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.obs_decoder.parameters(), 1.0)
        optimizer.step()

        if epoch == 1 or epoch % args.eval_every == 0:
            val_loss, val_rmse = evaluate_decoder(
                model,
                obs,
                actions,
                target_obs,
                val_idx,
                args.batch_size,
                args.distance_loss_weight,
            )
            improved = val_rmse < best_val
            if improved:
                best_val = val_rmse
                best_epoch = epoch
                best_decoder_state = {key: value.detach().cpu().clone() for key, value in model.obs_decoder.state_dict().items()}
                checks_since_improvement = 0
            else:
                checks_since_improvement += 1
            print(
                f"epoch={epoch:04d} loss={loss.item():.6f} val_loss={val_loss:.6f} "
                f"val_rmse={val_rmse:.6f} best_rmse={best_val:.6f}@{best_epoch} "
                f"early_stop_wait={checks_since_improvement}/{args.early_stopping_patience}",
                flush=True,
            )
            if args.early_stopping_patience > 0 and checks_since_improvement >= args.early_stopping_patience:
                early_stopped = True
                print(
                    f"Early stopping decoder refinement at epoch={epoch} "
                    f"best_rmse={best_val:.6f}@{best_epoch}",
                    flush=True,
                )
                break

    if best_decoder_state is not None:
        model.obs_decoder.load_state_dict(best_decoder_state)

    output_checkpoint = checkpoint if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else {}
    output_checkpoint = dict(output_checkpoint)
    output_checkpoint.update(
        {
            "model_state_dict": {key: value.detach().cpu().clone() for key, value in model.state_dict().items()},
            "obs_dim": int(dims["obs_dim"]),
            "action_dim": int(dims["action_dim"]),
            "latent_dim": int(dims["latent_dim"]),
            "hidden_dim": int(dims["hidden_dim"]),
            "decoded_obs_dim": int(dims["decoded_obs_dim"]),
            "context_steps": int(context_steps),
            "decoder_refined": True,
            "decoder_refine_best_epoch": int(best_epoch),
            "decoder_refine_best_val_rmse": float(best_val),
            "decoder_refine_stopped_epoch": int(stopped_epoch),
            "decoder_refine_early_stopped": bool(early_stopped),
            "decoder_refine_distance_loss_weight": float(args.distance_loss_weight),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(output_checkpoint, args.output)
    print(
        f"Saved refined checkpoint to {args.output} "
        f"(best_epoch={best_epoch}, best_val_rmse={best_val:.6f})",
        flush=True,
    )


def resolve_device(name: str):
    if name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is False.")
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def load_full_checkpoint(path: Path) -> Any:
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def freeze_except_decoder(model) -> None:
    if model.obs_decoder is None:
        raise RuntimeError("Checkpoint has no observation decoder to refine.")
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    for parameter in model.obs_decoder.parameters():
        parameter.requires_grad_(True)


def decoder_loss(model, obs, actions, target_obs, distance_loss_weight: float):
    with torch.no_grad():
        _, pred = model(obs, actions)
    decoded = model.decode_observation(pred.detach())
    return weighted_observation_loss(decoded, target_obs, distance_weight=distance_loss_weight)


def evaluate_decoder(model, obs, actions, target_obs, val_idx, batch_size: int, distance_loss_weight: float) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    total_squared = 0.0
    total_values = 0
    with torch.no_grad():
        for start in range(0, len(val_idx), batch_size):
            idx = val_idx[start : start + batch_size]
            _, pred = model(obs[idx], actions[idx])
            decoded = model.decode_observation(pred)
            loss = weighted_observation_loss(decoded, target_obs[idx], distance_weight=distance_loss_weight)
            error = decoded - target_obs[idx]
            n = len(idx)
            total_loss += float(loss.item()) * n
            total_squared += float(error.pow(2).sum().item())
            total_values += int(error.numel())
    model.train()
    return total_loss / len(val_idx), (total_squared / total_values) ** 0.5


if __name__ == "__main__":
    main()
