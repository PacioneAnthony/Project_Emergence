"""Evaluate a trained SensorJEPA checkpoint on sim2d logs."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import numpy as np

from learning.datasets import build_context_transitions, load_simulation_csv
from learning.jepa import SensorJEPA


OBS_FIELD_NAMES = ("distance", "servo_angle", "gyro_z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a minimal JEPA checkpoint on sim2d logs.")
    parser.add_argument("--log", type=Path, default=Path("data/raw/sim2d_bootstrap.csv"))
    parser.add_argument("--checkpoint", type=Path, default=Path("models/sensor_jepa.pth"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/jepa_eval"))
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--ridge", type=float, default=1e-3)
    parser.add_argument("--context-steps", type=int, default=None)
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--max-plot-points", type=int, default=600)
    return parser


def main() -> None:
    try:
        import torch
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("PyTorch is required to evaluate JEPA. Use the .venv or WSL/GPU environment.") from exc

    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    state_dict, target_encoder_state_dict, checkpoint_meta = load_checkpoint(args.checkpoint, torch)
    dims = infer_checkpoint_dims(state_dict)
    dims.update({key: int(value) for key, value in checkpoint_meta.items() if key in dims and value is not None})
    context_steps = args.context_steps or int(checkpoint_meta.get("context_steps") or infer_context_steps(dims["obs_dim"], dims["action_dim"]))
    arrays = build_context_transitions(load_simulation_csv(args.log), context_steps=context_steps)

    model = SensorJEPA(
        obs_dim=dims["obs_dim"],
        action_dim=dims["action_dim"],
        latent_dim=dims["latent_dim"],
        hidden_dim=dims["hidden_dim"],
        decoded_obs_dim=dims.get("decoded_obs_dim"),
    )
    model.load_state_dict(state_dict)
    model.eval()
    target_encoder = None
    if target_encoder_state_dict is not None:
        target_encoder = copy.deepcopy(model.encoder)
        target_encoder.load_state_dict(target_encoder_state_dict)
        target_encoder.eval()

    obs = arrays["obs"]
    actions = arrays["action"]
    next_obs = arrays["next_obs"]
    target_obs = arrays.get("target_obs", next_obs)
    persistence_obs = latest_observation_from_context(obs, context_steps)
    train_idx, test_idx = split_indices(arrays, args.val_fraction)

    s_t, pred_s_next, target_s_next = predict_latents(
        model,
        obs,
        actions,
        next_obs,
        torch,
        args.batch_size,
        target_encoder=target_encoder,
    )

    latent_metrics = latent_prediction_metrics(
        s_t[test_idx],
        pred_s_next[test_idx],
        target_s_next[test_idx],
        target_s_next[train_idx],
    )

    probe = fit_ridge_probe(pred_s_next[train_idx], target_obs[train_idx], alpha=args.ridge)
    probe_next_obs = apply_linear_probe(pred_s_next[test_idx], probe)
    observation_probe_metrics_value = observation_probe_metrics(
        probe_next_obs,
        target_obs[test_idx],
        persistence_prediction=persistence_obs[test_idx],
        mean_prediction=np.repeat(target_obs[train_idx].mean(axis=0, keepdims=True), len(test_idx), axis=0),
    )
    observation_decoder_metrics_value = None
    decoder_next_obs = None
    if model.obs_decoder is not None:
        decoder_next_obs = decode_observations(model, pred_s_next[test_idx], torch, args.batch_size)
        observation_decoder_metrics_value = observation_probe_metrics(
            decoder_next_obs,
            target_obs[test_idx],
            persistence_prediction=persistence_obs[test_idx],
            mean_prediction=np.repeat(target_obs[train_idx].mean(axis=0, keepdims=True), len(test_idx), axis=0),
        )

    collapse_metrics = latent_health_metrics(target_s_next[test_idx])
    metrics = {
        "log": str(args.log),
        "checkpoint": str(args.checkpoint),
        "n_samples": int(len(obs)),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "checkpoint_dims": dims,
        "context_steps": int(context_steps),
        "latent_prediction": latent_metrics,
        "observation_probe": observation_probe_metrics_value,
        "observation_decoder": observation_decoder_metrics_value,
        "latent_health": collapse_metrics,
    }

    metrics_path = args.output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    if not args.no_plots:
        plot_prediction = decoder_next_obs if decoder_next_obs is not None else probe_next_obs
        plot_label = "JEPA+decoder" if decoder_next_obs is not None else "JEPA+probe"
        write_plots(
            output_dir=args.output_dir,
            obs_target=target_obs[test_idx],
            obs_pred=plot_prediction,
            obs_persistence=persistence_obs[test_idx],
            pred_label=plot_label,
            pred_latent=pred_s_next[test_idx],
            target_latent=target_s_next[test_idx],
            max_points=args.max_plot_points,
        )

    print_summary(metrics, metrics_path)


def load_checkpoint(path: Path, torch_module):
    try:
        checkpoint = torch_module.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        checkpoint = torch_module.load(path, map_location="cpu")

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        meta = {
            "obs_dim": checkpoint.get("obs_dim"),
            "action_dim": checkpoint.get("action_dim"),
            "latent_dim": checkpoint.get("latent_dim"),
            "hidden_dim": checkpoint.get("hidden_dim"),
            "decoded_obs_dim": checkpoint.get("decoded_obs_dim"),
            "context_steps": checkpoint.get("context_steps"),
        }
        return checkpoint["model_state_dict"], checkpoint.get("target_encoder_state_dict"), meta

    return checkpoint, None, {}


def infer_context_steps(obs_dim: int, action_dim: int) -> int:
    base_obs_dim = 3
    if obs_dim == base_obs_dim:
        return 1
    numerator = obs_dim + action_dim
    denominator = base_obs_dim + action_dim
    if numerator % denominator == 0:
        return max(1, int(numerator // denominator))
    return 1


def latest_observation_from_context(context_obs: np.ndarray, context_steps: int, base_obs_dim: int = 3) -> np.ndarray:
    if context_steps <= 1:
        return context_obs[:, :base_obs_dim]
    start = (context_steps - 1) * base_obs_dim
    end = context_steps * base_obs_dim
    return context_obs[:, start:end]


def infer_checkpoint_dims(state_dict: dict[str, Any]) -> dict[str, int]:
    encoder_in = state_dict["encoder.net.0.weight"]
    encoder_hidden = state_dict["encoder.net.0.bias"]
    encoder_out = state_dict["encoder.net.4.bias"]
    predictor_in = state_dict["predictor.net.0.weight"]

    obs_dim = int(encoder_in.shape[1])
    hidden_dim = int(encoder_hidden.shape[0])
    latent_dim = int(encoder_out.shape[0])
    action_dim = int(predictor_in.shape[1] - latent_dim)
    return {
        "obs_dim": obs_dim,
        "action_dim": action_dim,
        "latent_dim": latent_dim,
        "hidden_dim": hidden_dim,
        "decoded_obs_dim": infer_decoded_obs_dim(state_dict),
    }


def infer_decoded_obs_dim(state_dict: dict[str, Any]) -> int | None:
    key = "obs_decoder.net.4.bias"
    if key in state_dict:
        return int(state_dict[key].shape[0])
    return None


def split_indices(arrays: dict[str, np.ndarray], val_fraction: float) -> tuple[np.ndarray, np.ndarray]:
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


def predict_latents(
    model,
    obs: np.ndarray,
    actions: np.ndarray,
    next_obs: np.ndarray,
    torch_module,
    batch_size: int,
    target_encoder=None,
):
    pred_batches = []
    s_batches = []
    target_batches = []
    with torch_module.no_grad():
        for start in range(0, len(obs), batch_size):
            end = min(start + batch_size, len(obs))
            obs_t = torch_module.from_numpy(obs[start:end]).float()
            action_t = torch_module.from_numpy(actions[start:end]).float()
            next_obs_t = torch_module.from_numpy(next_obs[start:end]).float()
            s_t, pred_s_next = model(obs_t, action_t)
            if target_encoder is not None:
                target_s_next = target_encoder(next_obs_t)
            else:
                target_s_next = model.encode(next_obs_t)
            s_batches.append(s_t.cpu().numpy())
            pred_batches.append(pred_s_next.cpu().numpy())
            target_batches.append(target_s_next.cpu().numpy())

    return np.vstack(s_batches), np.vstack(pred_batches), np.vstack(target_batches)


def decode_observations(model, latents: np.ndarray, torch_module, batch_size: int) -> np.ndarray:
    batches = []
    with torch_module.no_grad():
        for start in range(0, len(latents), batch_size):
            end = min(start + batch_size, len(latents))
            latent_t = torch_module.from_numpy(latents[start:end]).float()
            obs_t = model.decode_observation(latent_t)
            batches.append(obs_t.cpu().numpy())
    return np.vstack(batches)


def latent_prediction_metrics(
    s_t: np.ndarray,
    pred_s_next: np.ndarray,
    target_s_next: np.ndarray,
    train_target_s_next: np.ndarray,
) -> dict[str, float]:
    model_mse = mse(pred_s_next, target_s_next)
    persistence_mse = mse(s_t, target_s_next)
    mean_baseline = np.repeat(train_target_s_next.mean(axis=0, keepdims=True), len(target_s_next), axis=0)
    mean_mse = mse(mean_baseline, target_s_next)
    return {
        "mse": model_mse,
        "mae": mae(pred_s_next, target_s_next),
        "persistence_mse": persistence_mse,
        "mean_baseline_mse": mean_mse,
        "improvement_vs_persistence": safe_improvement(model_mse, persistence_mse),
        "r2_vs_train_mean": safe_improvement(model_mse, mean_mse),
    }


def fit_ridge_probe(features: np.ndarray, targets: np.ndarray, alpha: float = 1e-3) -> np.ndarray:
    x = np.concatenate([features, np.ones((features.shape[0], 1), dtype=features.dtype)], axis=1)
    xtx = x.T @ x
    reg = np.eye(xtx.shape[0], dtype=np.float64) * float(alpha)
    reg[-1, -1] = 0.0
    xty = x.T @ targets
    return np.linalg.solve(xtx.astype(np.float64) + reg, xty.astype(np.float64))


def apply_linear_probe(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    x = np.concatenate([features, np.ones((features.shape[0], 1), dtype=features.dtype)], axis=1)
    return (x @ weights).astype(np.float32)


def observation_probe_metrics(
    decoded_prediction: np.ndarray,
    target: np.ndarray,
    persistence_prediction: np.ndarray,
    mean_prediction: np.ndarray,
) -> dict[str, Any]:
    model_rmse = rmse_by_field(decoded_prediction, target)
    persistence_rmse = rmse_by_field(persistence_prediction, target)
    mean_rmse = rmse_by_field(mean_prediction, target)
    model_mae = mae_by_field(decoded_prediction, target)

    per_field = {}
    for i, name in enumerate(OBS_FIELD_NAMES):
        per_field[name] = {
            "rmse": float(model_rmse[i]),
            "mae": float(model_mae[i]),
            "persistence_rmse": float(persistence_rmse[i]),
            "mean_baseline_rmse": float(mean_rmse[i]),
            "improvement_vs_persistence": safe_improvement(float(model_rmse[i] ** 2), float(persistence_rmse[i] ** 2)),
        }

    return {
        "rmse_mean": float(np.mean(model_rmse)),
        "mae_mean": float(np.mean(model_mae)),
        "persistence_rmse_mean": float(np.mean(persistence_rmse)),
        "mean_baseline_rmse_mean": float(np.mean(mean_rmse)),
        "per_field": per_field,
    }


def latent_health_metrics(latents: np.ndarray) -> dict[str, float]:
    std = latents.std(axis=0)
    cov = np.cov(latents, rowvar=False)
    off_diag = cov - np.diag(np.diag(cov))
    sign, logdet = np.linalg.slogdet(cov + np.eye(cov.shape[0]) * 1e-6)
    return {
        "std_min": float(std.min()),
        "std_mean": float(std.mean()),
        "std_max": float(std.max()),
        "cov_offdiag_mean_abs": float(np.mean(np.abs(off_diag))),
        "cov_logdet_eps": float(logdet if sign > 0 else -np.inf),
    }


def write_plots(
    output_dir: Path,
    obs_target: np.ndarray,
    obs_pred: np.ndarray,
    obs_persistence: np.ndarray,
    pred_label: str,
    pred_latent: np.ndarray,
    target_latent: np.ndarray,
    max_points: int,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError:
        print("matplotlib not available; skipping plots.")
        return

    count = min(max_points, len(obs_target))
    x_axis = np.arange(count)
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for i, name in enumerate(OBS_FIELD_NAMES):
        axes[i].plot(x_axis, obs_target[:count, i], label="target", linewidth=1.6)
        axes[i].plot(x_axis, obs_pred[:count, i], label=pred_label, linewidth=1.2)
        axes[i].plot(x_axis, obs_persistence[:count, i], label="persistence", linewidth=1.0, alpha=0.65)
        axes[i].set_ylabel(name)
        axes[i].grid(alpha=0.25)
    axes[-1].set_xlabel("test sample")
    axes[0].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_dir / "next_observation_probe.png", dpi=140)
    plt.close(fig)

    pca_points = min(max_points, len(target_latent))
    combined = np.vstack([target_latent[:pca_points], pred_latent[:pca_points]])
    centered = combined - combined.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    coords = centered @ vt[:2].T
    target_coords = coords[:pca_points]
    pred_coords = coords[pca_points:]

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(target_coords[:, 0], target_coords[:, 1], s=8, alpha=0.65, label="target latent")
    ax.scatter(pred_coords[:, 0], pred_coords[:, 1], s=8, alpha=0.65, label="predicted latent")
    ax.set_title("Latent PCA: predicted vs target")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_dir / "latent_pca.png", dpi=140)
    plt.close(fig)


def print_summary(metrics: dict[str, Any], metrics_path: Path) -> None:
    latent = metrics["latent_prediction"]
    obs = metrics["observation_decoder"] or metrics["observation_probe"]
    obs_name = "decoder" if metrics["observation_decoder"] is not None else "probe"
    health = metrics["latent_health"]
    print("JEPA evaluation complete")
    print(f"  samples: train={metrics['n_train']} test={metrics['n_test']}")
    print(f"  latent mse: {latent['mse']:.6f}")
    print(f"  persistence latent mse: {latent['persistence_mse']:.6f}")
    print(f"  improvement vs persistence: {latent['improvement_vs_persistence'] * 100.0:.2f}%")
    print(f"  obs {obs_name} rmse mean: {obs['rmse_mean']:.6f}")
    print(f"  obs persistence rmse mean: {obs['persistence_rmse_mean']:.6f}")
    print(f"  latent std min/mean/max: {health['std_min']:.4f}/{health['std_mean']:.4f}/{health['std_max']:.4f}")
    print(f"  metrics: {metrics_path}")


def mse(prediction: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean((prediction - target) ** 2))


def mae(prediction: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean(np.abs(prediction - target)))


def rmse_by_field(prediction: np.ndarray, target: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean((prediction - target) ** 2, axis=0))


def mae_by_field(prediction: np.ndarray, target: np.ndarray) -> np.ndarray:
    return np.mean(np.abs(prediction - target), axis=0)


def safe_improvement(model_error: float, baseline_error: float) -> float:
    if baseline_error <= 1e-12:
        return 0.0
    return float(1.0 - (model_error / baseline_error))


if __name__ == "__main__":
    main()
