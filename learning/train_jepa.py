"""Train the minimal JEPA on simulator CSV logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import copy

from learning.datasets import build_context_transitions, load_simulation_csv
from learning.jepa import SensorJEPA, covariance_loss, jepa_loss, variance_loss, weighted_observation_loss

try:
    import torch
except ModuleNotFoundError:
    torch = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a minimal JEPA from sim2d logs.")
    parser.add_argument("--log", type=Path, default=Path("data/raw/sim2d_log.csv"))
    parser.add_argument("--epochs", type=int, default=2000)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--latent-dim", type=int, default=32)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--context-steps", type=int, default=4)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--ema-decay", type=float, default=0.99)
    parser.add_argument("--obs-loss-weight", type=float, default=1.0)
    parser.add_argument("--distance-loss-weight", type=float, default=3.0)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--eval-every", type=int, default=500)
    parser.add_argument("--eval-samples", type=int, default=65536)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=0,
        help="Stop after this many validation checks without improvement. 0 disables early stopping.",
    )
    parser.add_argument(
        "--early-stopping-min-delta",
        type=float,
        default=0.0,
        help="Minimum validation-score decrease required to reset early-stopping patience.",
    )
    parser.add_argument("--output", type=Path, default=Path("models/sensor_jepa.pth"))
    return parser


def main() -> None:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required to train JEPA. Run this in the WSL/GPU environment.")

    args = build_parser().parse_args()
    if args.early_stopping_patience < 0:
        raise ValueError("--early-stopping-patience must be >= 0.")
    if args.early_stopping_min_delta < 0.0:
        raise ValueError("--early-stopping-min-delta must be >= 0.")
    if args.early_stopping_patience > 0 and args.eval_every <= 0:
        raise ValueError("--early-stopping-patience requires --eval-every > 0.")

    arrays = build_context_transitions(load_simulation_csv(args.log), context_steps=args.context_steps)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is False.")
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    obs = torch.from_numpy(arrays["obs"]).float().to(device)
    actions = torch.from_numpy(arrays["action"]).float().to(device)
    next_obs = torch.from_numpy(arrays["next_obs"]).float().to(device)
    target_obs = torch.from_numpy(arrays["target_obs"]).float().to(device)
    train_idx_np, val_idx_np = split_indices(arrays, args.val_fraction)
    train_idx = torch.from_numpy(train_idx_np).long().to(device)
    val_idx = torch.from_numpy(val_idx_np).long().to(device)

    decoded_obs_dim = target_obs.shape[-1] if args.obs_loss_weight > 0.0 else None
    model = SensorJEPA(
        obs_dim=obs.shape[-1],
        action_dim=actions.shape[-1],
        latent_dim=args.latent_dim,
        hidden_dim=args.hidden_dim,
        decoded_obs_dim=decoded_obs_dim,
    ).to(device)
    target_encoder = copy.deepcopy(model.encoder)
    target_encoder.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    print(
        f"[i] device={device} samples={len(obs)} train={len(train_idx)} val={len(val_idx)} "
        f"obs_dim={obs.shape[-1]} aux_obs={decoded_obs_dim is not None}",
        flush=True,
    )
    best_score = float("inf")
    best_epoch = 0
    best_model_state = None
    best_target_state = None
    checks_since_improvement = 0
    stopped_epoch = 0
    early_stopped = False
    for epoch in range(1, args.epochs + 1):
        stopped_epoch = epoch
        local_idx = torch.randint(0, len(train_idx), (min(args.batch_size, len(train_idx)),), device=device)
        idx = train_idx[local_idx]
        obs_b = obs[idx]
        action_b = actions[idx]
        next_obs_b = next_obs[idx]
        target_obs_b = target_obs[idx]

        loss, loss_pred, loss_obs, loss_var, loss_cov = compute_losses(
            model,
            target_encoder,
            obs_b,
            action_b,
            next_obs_b,
            target_obs_b,
            obs_loss_weight=args.obs_loss_weight,
            distance_loss_weight=args.distance_loss_weight,
            include_regularizers=True,
        )

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        for online, target_param in zip(model.encoder.parameters(), target_encoder.parameters()):
            target_param.data.mul_(args.ema_decay).add_(online.data, alpha=1.0 - args.ema_decay)

        val_score = None
        if epoch == 1 or (args.eval_every > 0 and epoch % args.eval_every == 0):
            val_score, val_pred, val_obs = evaluate_validation(
                model,
                target_encoder,
                obs,
                actions,
                next_obs,
                target_obs,
                val_idx,
                eval_samples=args.eval_samples,
                batch_size=args.batch_size,
                obs_loss_weight=args.obs_loss_weight,
                distance_loss_weight=args.distance_loss_weight,
            )
            if validation_improved(val_score, best_score, args.early_stopping_min_delta):
                best_score = val_score
                best_epoch = epoch
                best_model_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                best_target_state = {key: value.detach().cpu().clone() for key, value in target_encoder.state_dict().items()}
                checks_since_improvement = 0
            else:
                checks_since_improvement += 1
            early_stopping_status = ""
            if args.early_stopping_patience > 0:
                early_stopping_status = f" early_stop_wait={checks_since_improvement}/{args.early_stopping_patience}"
            print(
                f"epoch={epoch:04d} loss={loss.item():.5f} pred={loss_pred.item():.5f} "
                f"obs={loss_obs.item():.5f} var={loss_var.item():.5f} cov={loss_cov.item():.5f} "
                f"val={val_score:.5f} val_pred={val_pred:.5f} val_obs={val_obs:.5f} best={best_score:.5f}@{best_epoch}"
                f"{early_stopping_status}",
                flush=True,
            )
            if (
                args.early_stopping_patience > 0
                and checks_since_improvement >= args.early_stopping_patience
            ):
                early_stopped = True
                print(
                    f"Early stopping at epoch={epoch} best={best_score:.6f}@{best_epoch} "
                    f"patience={args.early_stopping_patience} min_delta={args.early_stopping_min_delta}",
                    flush=True,
                )
                break
        elif args.log_every > 0 and epoch % args.log_every == 0:
            print(
                f"epoch={epoch:04d} loss={loss.item():.5f} pred={loss_pred.item():.5f} "
                f"obs={loss_obs.item():.5f} var={loss_var.item():.5f} cov={loss_cov.item():.5f} "
                f"best={best_score:.5f}@{best_epoch}",
                flush=True,
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    model_state = best_model_state or {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    target_state = best_target_state or {key: value.detach().cpu().clone() for key, value in target_encoder.state_dict().items()}
    torch.save(
        {
            "model_state_dict": model_state,
            "target_encoder_state_dict": target_state,
            "obs_dim": int(obs.shape[-1]),
            "action_dim": int(actions.shape[-1]),
            "latent_dim": int(args.latent_dim),
            "hidden_dim": int(args.hidden_dim),
            "decoded_obs_dim": int(decoded_obs_dim) if decoded_obs_dim is not None else None,
            "context_steps": int(args.context_steps),
            "ema_decay": float(args.ema_decay),
            "obs_loss_weight": float(args.obs_loss_weight),
            "distance_loss_weight": float(args.distance_loss_weight),
            "best_epoch": int(best_epoch),
            "best_validation_score": float(best_score),
            "stopped_epoch": int(stopped_epoch),
            "early_stopped": bool(early_stopped),
            "early_stopping_patience": int(args.early_stopping_patience),
            "early_stopping_min_delta": float(args.early_stopping_min_delta),
        },
        args.output,
    )
    print(
        f"Saved JEPA checkpoint to {args.output} "
        f"(best_epoch={best_epoch}, best_validation_score={best_score:.6f}, "
        f"stopped_epoch={stopped_epoch}, early_stopped={early_stopped})",
        flush=True,
    )


def compute_losses(
    model,
    target_encoder,
    obs_b,
    action_b,
    next_obs_b,
    target_obs_b,
    obs_loss_weight: float,
    distance_loss_weight: float,
    include_regularizers: bool,
):
    s_t, pred = model(obs_b, action_b)
    with torch.no_grad():
        target = target_encoder(next_obs_b)

    loss_pred = jepa_loss(pred, target)
    if model.obs_decoder is not None:
        pred_obs = model.decode_observation(pred)
        loss_obs = weighted_observation_loss(pred_obs, target_obs_b, distance_weight=distance_loss_weight)
    else:
        loss_obs = pred.new_tensor(0.0)

    if include_regularizers:
        loss_var = variance_loss(s_t)
        loss_cov = covariance_loss(s_t)
    else:
        loss_var = pred.new_tensor(0.0)
        loss_cov = pred.new_tensor(0.0)

    loss = loss_pred + obs_loss_weight * loss_obs + 0.05 * loss_var + 0.01 * loss_cov
    return loss, loss_pred, loss_obs, loss_var, loss_cov


def evaluate_validation(
    model,
    target_encoder,
    obs,
    actions,
    next_obs,
    target_obs,
    val_idx,
    eval_samples: int,
    batch_size: int,
    obs_loss_weight: float,
    distance_loss_weight: float,
):
    model.eval()
    if len(val_idx) > eval_samples:
        choice = torch.randperm(len(val_idx), device=val_idx.device)[:eval_samples]
        eval_idx = val_idx[choice]
    else:
        eval_idx = val_idx

    total = 0.0
    total_pred = 0.0
    total_obs = 0.0
    count = 0
    with torch.no_grad():
        for start in range(0, len(eval_idx), batch_size):
            idx = eval_idx[start : start + batch_size]
            loss, loss_pred, loss_obs, _, _ = compute_losses(
                model,
                target_encoder,
                obs[idx],
                actions[idx],
                next_obs[idx],
                target_obs[idx],
                obs_loss_weight=obs_loss_weight,
                distance_loss_weight=distance_loss_weight,
                include_regularizers=False,
            )
            n = len(idx)
            total += float(loss.item()) * n
            total_pred += float(loss_pred.item()) * n
            total_obs += float(loss_obs.item()) * n
            count += n
    model.train()
    return total / count, total_pred / count, total_obs / count


def validation_improved(score: float, best_score: float, min_delta: float) -> bool:
    return score < best_score - min_delta


def split_indices(arrays: dict, val_fraction: float):
    import numpy as np

    n = len(arrays["obs"])
    val_fraction = float(np.clip(val_fraction, 0.05, 0.95))
    if "episode" in arrays:
        episodes = np.unique(arrays["episode"].astype(int))
        if len(episodes) > 1:
            split = max(1, int(round(len(episodes) * (1.0 - val_fraction))))
            split = min(split, len(episodes) - 1)
            train_eps = set(int(x) for x in episodes[:split])
            mask = np.array([int(ep) in train_eps for ep in arrays["episode"]], dtype=bool)
            return np.flatnonzero(mask), np.flatnonzero(~mask)
    split = max(1, int(round(n * (1.0 - val_fraction))))
    split = min(split, n - 1)
    return np.arange(split), np.arange(split, n)


if __name__ == "__main__":
    main()
