"""Measure direct JEPA-LNN action sensitivity to raw observations versus latent input."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from learning.jepa_lnn_features import build_jepa_lnn_arrays
from learning.lnn import SimpleLNN
from learning.train_lnn import action_scales_from_config, resolve_device, sequence_start_indices
from sim2d.config import RobotConfig

try:
    import torch
except ModuleNotFoundError:
    torch = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare JEPA-LNN action gradients for obs and latent inputs.")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--jepa-checkpoint", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--burn-in", type=int, default=64)
    parser.add_argument("--jepa-batch-size", type=int, default=4096)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required for JEPA-LNN sensitivity diagnostics.")

    args = build_parser().parse_args()
    validate_args(args)
    device = resolve_device(args.device)
    checkpoint = load_checkpoint(args.checkpoint)
    jepa_checkpoint = args.jepa_checkpoint or Path(checkpoint["jepa_checkpoint"])
    arrays, feature_meta = build_jepa_lnn_arrays(args.log, jepa_checkpoint, device, args.jepa_batch_size)

    episodes = arrays.get("episode", np.zeros(len(arrays["obs"]), dtype=np.int64)).astype(np.int64)
    starts = sequence_start_indices(episodes, args.burn_in + 1, set(int(value) for value in np.unique(episodes)))
    starts = evenly_subsample(starts, args.samples)
    obs = torch.from_numpy(arrays["obs"]).float().to(device)

    model = SimpleLNN(
        state_dim=int(checkpoint["state_dim"]),
        input_dim=int(checkpoint["input_dim"]),
        action_dim=int(checkpoint["action_dim"]),
        hidden_dim=int(checkpoint["hidden_dim"]),
        tau_min=float(checkpoint.get("tau_min", 0.05)),
        tau_max=float(checkpoint.get("tau_max", 1.5)),
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    obs_norm, latent_norm = action_input_gradient_norms(
        model,
        obs,
        starts,
        burn_in=args.burn_in,
        dt=float(checkpoint.get("dt", 0.02)),
        action_scales=np.array(
            checkpoint.get("action_scales") or action_scales_from_config(RobotConfig()).tolist(), dtype=np.float32
        ),
    )
    metrics = sensitivity_metrics(obs_norm, latent_norm, obs_dim=3, latent_dim=int(feature_meta["jepa_latent_dim"]))
    metrics.update(
        {
            "log": str(args.log),
            "checkpoint": str(args.checkpoint),
            "jepa_checkpoint": str(jepa_checkpoint),
            "samples": int(len(starts)),
            "burn_in": int(args.burn_in),
            "feature_meta": feature_meta,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"JEPA-LNN sensitivity: total_ratio={metrics['latent_vs_obs_total_norm_ratio']:.3f} "
        f"per_dim_ratio={metrics['latent_vs_obs_per_dim_rms_ratio']:.3f} output={args.output}",
        flush=True,
    )


def validate_args(args: argparse.Namespace) -> None:
    for path in (args.log, args.checkpoint):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.jepa_checkpoint is not None and not args.jepa_checkpoint.exists():
        raise FileNotFoundError(args.jepa_checkpoint)
    if args.samples <= 0 or args.burn_in <= 0 or args.jepa_batch_size <= 0:
        raise ValueError("Samples, burn-in and JEPA batch size must be > 0.")


def load_checkpoint(path: Path) -> dict[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def evenly_subsample(indices: np.ndarray, limit: int) -> np.ndarray:
    if len(indices) <= limit:
        return indices
    positions = np.linspace(0, len(indices) - 1, limit).astype(np.int64)
    return indices[positions]


def action_input_gradient_norms(model, obs, starts, burn_in: int, dt: float, action_scales: np.ndarray):
    starts_t = torch.from_numpy(starts).long().to(obs.device)
    offsets = torch.arange(burn_in, device=obs.device).long()
    history = obs[starts_t[:, None] + offsets[None, :]]
    current = obs[starts_t + burn_in].detach().clone().requires_grad_(True)
    x = obs.new_zeros((len(starts), model.state_dim))
    with torch.no_grad():
        for step in range(burn_in):
            x = model.step(x, history[:, step, :], dt)
    scales = torch.from_numpy(action_scales).float().to(obs.device)
    physical_action = model.act(x.detach(), current) * scales
    gradients = []
    for action_index in range(physical_action.shape[-1]):
        gradient = torch.autograd.grad(
            physical_action[:, action_index].sum(),
            current,
            retain_graph=action_index < physical_action.shape[-1] - 1,
        )[0]
        gradients.append(gradient)
    jacobian = torch.stack(gradients, dim=1)
    obs_norm = torch.linalg.vector_norm(jacobian[:, :, :3], dim=(1, 2))
    latent_norm = torch.linalg.vector_norm(jacobian[:, :, 3:], dim=(1, 2))
    return obs_norm.detach().cpu().numpy(), latent_norm.detach().cpu().numpy()


def sensitivity_metrics(obs_norm: np.ndarray, latent_norm: np.ndarray, obs_dim: int, latent_dim: int) -> dict[str, Any]:
    obs_per_dim = obs_norm / np.sqrt(obs_dim)
    latent_per_dim = latent_norm / np.sqrt(latent_dim)
    return {
        "obs_gradient_norm": value_summary(obs_norm),
        "latent_gradient_norm": value_summary(latent_norm),
        "obs_gradient_rms_per_input_dim": value_summary(obs_per_dim),
        "latent_gradient_rms_per_input_dim": value_summary(latent_per_dim),
        "latent_vs_obs_total_norm_ratio": safe_ratio(float(np.mean(latent_norm)), float(np.mean(obs_norm))),
        "latent_vs_obs_per_dim_rms_ratio": safe_ratio(float(np.mean(latent_per_dim)), float(np.mean(obs_per_dim))),
    }


def value_summary(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "max": float(np.max(values)),
    }


def safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-12:
        return 0.0
    return float(numerator / denominator)


if __name__ == "__main__":
    main()
