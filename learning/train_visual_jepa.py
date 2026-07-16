"""Train the action-conditioned visual JEPA on a bench camera corpus.

Pre-registered probe (docs/research/visual_bench_probe.md): does knowing the
motor command improve next-frame latent prediction (sensorimotor contingency)?
The control variant (--no-action) has identical capacity with a zeroed action
input. The copy baseline (z_t as prediction of z_{t+1}) is computed on the
same latents, so the reported ratio is scale-invariant.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np

from learning.jepa import covariance_loss, variance_loss
from learning.visual_jepa import VisualJEPA

try:
    import torch
except ModuleNotFoundError:
    torch = None

SERVO_NEUTRAL_DEG = 90.0
SERVO_SPAN_DEG = 80.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a visual JEPA on bench head camera shards.")
    parser.add_argument("--corpus", type=Path, default=Path("data/raw/bench_visual_corpus"))
    parser.add_argument("--image-size", type=int, default=64, help="Training resolution (stored frames are box-downsampled).")
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--encoder-width", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--variance-weight", type=float, default=1.0)
    parser.add_argument("--covariance-weight", type=float, default=0.1)
    parser.add_argument("--val-episode-fraction", type=float, default=0.15)
    parser.add_argument("--eval-every", type=int, default=2, help="Epochs between validations.")
    parser.add_argument("--early-stopping-patience", type=int, default=15, help="Validations without improvement (0 disables).")
    parser.add_argument("--seed", type=int, default=4301)
    parser.add_argument("--no-action", action="store_true", help="Control variant: zeroed action input.")
    parser.add_argument("--select", choices=("ratio", "final"), default="ratio", help="Checkpoint selection: best val ratio or final epoch.")
    parser.add_argument("--eval-motion-threshold-deg", type=float, default=5.0, help="Pairs with |delta as5600| above this are 'moving' at eval.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--output", type=Path, default=Path("models/visual_jepa_001.pth"))
    parser.add_argument("--metrics-output", type=Path, default=Path("data/processed/experiments/visual_jepa_001/metrics.json"))
    return parser


def resolve_device(name: str) -> "torch.device":
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def downsample_frames(frames: np.ndarray, target: int) -> np.ndarray:
    """Box-downsample (N, S, S, 3) uint8 frames to (N, target, target, 3)."""

    size = frames.shape[1]
    if size == target:
        return frames
    if size % target != 0:
        raise ValueError(f"Stored size {size} is not a multiple of training size {target}.")
    factor = size // target
    reduced = frames.reshape(frames.shape[0], target, factor, target, factor, 3).mean(axis=(2, 4))
    return reduced.astype(np.uint8)


def load_corpus(corpus_dir: Path, image_size: int) -> dict[str, np.ndarray | list]:
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    cache_path = corpus_dir / f"cache_train_{image_size}_{manifest['episodes']}ep.npz"
    if cache_path.exists():
        cached = np.load(cache_path)
        return {key: cached[key] for key in ("frames", "requested_deg", "as5600_deg", "distance_m", "episode")}

    frames_list = []
    requested = []
    as5600 = []
    distance = []
    episode_ids = []
    for item in manifest["episodes_detail"]:
        shard = np.load(corpus_dir / item["shard"])
        frames_list.append(downsample_frames(shard["frames"], image_size))
        requested.append(shard["requested_deg"])
        as5600.append(shard["as5600_deg"])
        distance.append(shard["distance_m"])
        episode_ids.append(np.full(shard["frames"].shape[0], int(item["episode"]), dtype=np.int32))

    data = {
        "frames": np.concatenate(frames_list, axis=0),
        "requested_deg": np.concatenate(requested, axis=0).astype(np.float32),
        "as5600_deg": np.concatenate(as5600, axis=0).astype(np.float32),
        "distance_m": np.concatenate(distance, axis=0).astype(np.float32),
        "episode": np.concatenate(episode_ids, axis=0),
    }
    np.savez(cache_path, **data)
    return data


def build_pairs(episode_ids: np.ndarray) -> np.ndarray:
    """Indices i such that i and i+1 belong to the same episode."""

    same = episode_ids[:-1] == episode_ids[1:]
    return np.nonzero(same)[0].astype(np.int64)


def normalize_action(requested_deg: np.ndarray) -> np.ndarray:
    return ((requested_deg - SERVO_NEUTRAL_DEG) / SERVO_SPAN_DEG).astype(np.float32)


class ProbeHeads(torch.nn.Module if torch is not None else object):
    def __init__(self, latent_dim: int):
        super().__init__()
        self.angle = torch.nn.Linear(latent_dim, 2)  # sin, cos
        self.distance = torch.nn.Linear(latent_dim, 1)


def evaluate(
    model,
    probes,
    data,
    pairs,
    action_norm,
    device,
    batch_size: int,
    motion_threshold_deg: float = 5.0,
) -> dict[str, float]:
    model.eval()
    probes.eval()
    moving_mask = np.abs(data["as5600_deg"][pairs + 1] - data["as5600_deg"][pairs]) > motion_threshold_deg
    sums = {"all": [0.0, 0.0, 0], "moving": [0.0, 0.0, 0], "static": [0.0, 0.0, 0]}
    angle_err_deg = []
    distance_true = []
    distance_pred = []

    with torch.no_grad():
        for start in range(0, len(pairs), batch_size):
            index = pairs[start : start + batch_size]
            frames_t = torch.from_numpy(data["frames"][index]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            frames_next = torch.from_numpy(data["frames"][index + 1]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            action = torch.from_numpy(action_norm[index]).to(device).unsqueeze(-1)

            latent_t = model.encode(frames_t)
            latent_next = model.encode(frames_next)
            prediction = model.predict_next(latent_t, action)

            pred_per_sample = torch.sum((prediction - latent_next) ** 2, dim=1)
            copy_per_sample = torch.sum((latent_t - latent_next) ** 2, dim=1)
            batch_moving = torch.from_numpy(moving_mask[start : start + batch_size]).to(device)
            for name, mask in (("all", None), ("moving", batch_moving), ("static", ~batch_moving)):
                selected_pred = pred_per_sample if mask is None else pred_per_sample[mask]
                selected_copy = copy_per_sample if mask is None else copy_per_sample[mask]
                sums[name][0] += float(selected_pred.sum().item())
                sums[name][1] += float(selected_copy.sum().item())
                sums[name][2] += int(selected_pred.shape[0]) * latent_t.shape[1]

            angle_out = probes.angle(latent_next)
            angle_pred = torch.atan2(angle_out[:, 0], angle_out[:, 1])
            angle_true = torch.from_numpy(np.radians(data["as5600_deg"][index + 1])).to(device)
            wrapped = torch.remainder(angle_pred - angle_true + math.pi, 2.0 * math.pi) - math.pi
            angle_err_deg.extend(torch.abs(torch.rad2deg(wrapped)).cpu().numpy().tolist())

            distance_pred.extend(probes.distance(latent_next).squeeze(-1).cpu().numpy().tolist())
            distance_true.extend(data["distance_m"][index + 1].tolist())

    def ratio_of(name: str) -> float:
        pred_sum, copy_sum, count = sums[name]
        if count == 0 or copy_sum <= 0:
            return float("nan")
        return float(pred_sum / copy_sum)

    pred_mse = sums["all"][0] / max(1, sums["all"][2])
    copy_mse = sums["all"][1] / max(1, sums["all"][2])
    distance_true_arr = np.asarray(distance_true)
    distance_pred_arr = np.asarray(distance_pred)
    ss_res = float(np.sum((distance_true_arr - distance_pred_arr) ** 2))
    ss_tot = float(np.sum((distance_true_arr - distance_true_arr.mean()) ** 2))
    return {
        "pred_mse": float(pred_mse),
        "copy_mse": float(copy_mse),
        "pred_to_copy_ratio": float(pred_mse / copy_mse) if copy_mse > 0 else float("inf"),
        "pred_to_copy_ratio_moving": ratio_of("moving"),
        "pred_to_copy_ratio_static": ratio_of("static"),
        "moving_pair_fraction": float(np.mean(moving_mask)) if len(pairs) else float("nan"),
        "angle_probe_mae_deg": float(np.mean(angle_err_deg)) if angle_err_deg else float("nan"),
        "distance_probe_r2": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
    }


def main() -> None:
    if torch is None:
        raise ModuleNotFoundError("train_visual_jepa requires PyTorch.")
    args = build_parser().parse_args()
    device = resolve_device(args.device)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    data = load_corpus(args.corpus, args.image_size)
    episodes = np.unique(data["episode"])
    val_count = max(1, int(round(len(episodes) * args.val_episode_fraction)))
    val_episodes = set(episodes[-val_count:].tolist())
    pairs = build_pairs(data["episode"])
    is_val = np.isin(data["episode"][pairs], list(val_episodes))
    train_pairs = pairs[~is_val]
    val_pairs = pairs[is_val]
    action_norm = normalize_action(data["requested_deg"])

    model = VisualJEPA(
        latent_dim=args.latent_dim,
        action_dim=1,
        hidden_dim=args.hidden_dim,
        encoder_width=args.encoder_width,
        use_action=not args.no_action,
    ).to(device)
    probes = ProbeHeads(args.latent_dim).to(device)
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(probes.parameters()), lr=args.lr, weight_decay=args.weight_decay
    )
    autocast_dtype = torch.bfloat16 if device.type == "cuda" else torch.float32

    history = []
    best_ratio = float("inf")
    best_state = None
    evals_without_improvement = 0
    started = time.perf_counter()
    steps_per_epoch = max(1, len(train_pairs) // args.batch_size)

    for epoch in range(args.epochs):
        model.train()
        probes.train()
        order = rng.permutation(len(train_pairs))
        epoch_loss = 0.0
        for step in range(steps_per_epoch):
            index = train_pairs[order[step * args.batch_size : (step + 1) * args.batch_size]]
            frames_t = torch.from_numpy(data["frames"][index]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            frames_next = torch.from_numpy(data["frames"][index + 1]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            action = torch.from_numpy(action_norm[index]).to(device).unsqueeze(-1)

            with torch.autocast(device_type=device.type, dtype=autocast_dtype, enabled=device.type == "cuda"):
                latent_t = model.encode(frames_t)
                latent_next = model.encode(frames_next)
                prediction = model.predict_next(latent_t, action)

                pred_loss = torch.mean((prediction - latent_next.detach()) ** 2)
                reg = args.variance_weight * 0.5 * (variance_loss(latent_t) + variance_loss(latent_next))
                reg = reg + args.covariance_weight * 0.5 * (covariance_loss(latent_t) + covariance_loss(latent_next))

                detached = latent_next.detach()
                angle_out = probes.angle(detached)
                angle_true = torch.from_numpy(np.radians(data["as5600_deg"][index + 1])).to(device).float()
                probe_loss = torch.mean((angle_out[:, 0] - torch.sin(angle_true)) ** 2)
                probe_loss = probe_loss + torch.mean((angle_out[:, 1] - torch.cos(angle_true)) ** 2)
                distance_true = torch.from_numpy(data["distance_m"][index + 1]).to(device).float()
                probe_loss = probe_loss + torch.mean((probes.distance(detached).squeeze(-1) - distance_true) ** 2)

                loss = pred_loss + reg + probe_loss

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.item())

        if (epoch + 1) % args.eval_every == 0 or epoch == args.epochs - 1:
            metrics = evaluate(
                model, probes, data, val_pairs, action_norm, device, args.batch_size,
                motion_threshold_deg=args.eval_motion_threshold_deg,
            )
            metrics["epoch"] = epoch + 1
            metrics["train_loss"] = epoch_loss / steps_per_epoch
            history.append(metrics)
            print(
                f"epoch {epoch + 1}: train={metrics['train_loss']:.5f} val_ratio={metrics['pred_to_copy_ratio']:.4f} "
                f"angle_mae={metrics['angle_probe_mae_deg']:.2f}deg dist_r2={metrics['distance_probe_r2']:.3f}",
                flush=True,
            )
            if metrics["pred_to_copy_ratio"] < best_ratio - 1e-5:
                best_ratio = metrics["pred_to_copy_ratio"]
                best_state = {
                    "model_state_dict": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                    "probes_state_dict": {k: v.detach().cpu().clone() for k, v in probes.state_dict().items()},
                    "metrics": dict(metrics),
                }
                evals_without_improvement = 0
            else:
                evals_without_improvement += 1
                if args.early_stopping_patience > 0 and evals_without_improvement >= args.early_stopping_patience:
                    print(f"early stopping at epoch {epoch + 1}", flush=True)
                    break

    elapsed = time.perf_counter() - started
    final_state = {
        "model_state_dict": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
        "probes_state_dict": {k: v.detach().cpu().clone() for k, v in probes.state_dict().items()},
        "metrics": history[-1] if history else {},
    }
    if best_state is None:
        best_state = final_state
    selected_state = final_state if args.select == "final" else best_state

    checkpoint = {
        "model_state_dict": selected_state["model_state_dict"],
        "probes_state_dict": selected_state["probes_state_dict"],
        "latent_dim": args.latent_dim,
        "hidden_dim": args.hidden_dim,
        "encoder_width": args.encoder_width,
        "image_size": args.image_size,
        "use_action": not args.no_action,
        "seed": args.seed,
        "corpus": str(args.corpus),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, args.output)

    final = {
        "status": "complete",
        "variant": "no_action" if args.no_action else "action",
        "seed": int(args.seed),
        "device": str(device),
        "image_size": int(args.image_size),
        "latent_dim": int(args.latent_dim),
        "train_pairs": int(len(train_pairs)),
        "val_pairs": int(len(val_pairs)),
        "val_episodes": sorted(int(e) for e in val_episodes),
        "epochs_run": int(history[-1]["epoch"]) if history else 0,
        "wall_seconds": float(elapsed),
        "parameters": int(sum(p.numel() for p in model.parameters())),
        "select": str(args.select),
        "best": best_state["metrics"],
        "final": final_state["metrics"],
        "selected_metrics": selected_state["metrics"],
        "history": history,
        "checkpoint": str(args.output),
    }
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(
        f"Visual JEPA done: variant={final['variant']} seed={args.seed} best_ratio={best_ratio:.4f} "
        f"({elapsed:.0f}s) checkpoint={args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
