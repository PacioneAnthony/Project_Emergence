"""Measure JEPA latent distribution shift between expert replay and policy rollout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from learning.datasets import build_context_transitions, load_simulation_csv
from learning.jepa_lnn_features import encode_contexts, load_context_action_array, load_jepa_bundle
from learning.train_lnn import resolve_device


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose JEPA latent shift with regularized Mahalanobis distance.")
    parser.add_argument("--reference-log", type=Path, required=True)
    parser.add_argument("--rollout-log", type=Path, required=True)
    parser.add_argument("--jepa-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fit-fraction", type=float, default=0.8)
    parser.add_argument("--max-fit-samples", type=int, default=100000)
    parser.add_argument("--max-reference-eval-samples", type=int, default=50000)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--shrinkage", type=float, default=0.05)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)
    device = resolve_device(args.device)
    bundle = load_jepa_bundle(args.jepa_checkpoint, device)

    reference = build_latent_context_arrays(args.reference_log, bundle.context_steps)
    rollout = build_latent_context_arrays(args.rollout_log, bundle.context_steps)
    fit_idx, eval_idx = split_reference_indices(reference, args.fit_fraction)
    fit_idx = evenly_subsample(fit_idx, args.max_fit_samples)
    eval_idx = evenly_subsample(eval_idx, args.max_reference_eval_samples)

    fit_latents = encode_contexts(bundle, reference["obs"][fit_idx], device, args.batch_size)
    eval_latents = encode_contexts(bundle, reference["obs"][eval_idx], device, args.batch_size)
    rollout_latents = encode_contexts(bundle, rollout["obs"], device, args.batch_size)

    mean, precision = fit_regularized_gaussian(fit_latents, args.shrinkage)
    reference_distance = mahalanobis_distance(eval_latents, mean, precision)
    rollout_distance = mahalanobis_distance(rollout_latents, mean, precision)
    collision = rollout.get("collision", np.zeros(len(rollout_distance), dtype=np.int64)).astype(bool)

    metrics = {
        "reference_log": str(args.reference_log),
        "rollout_log": str(args.rollout_log),
        "jepa_checkpoint": str(args.jepa_checkpoint),
        "context_steps": int(bundle.context_steps),
        "latent_dim": int(bundle.latent_dim),
        "fit_samples": int(len(fit_latents)),
        "reference_eval_samples": int(len(eval_latents)),
        "rollout_samples": int(len(rollout_latents)),
        "shrinkage": float(args.shrinkage),
        "reference_distance": distance_summary(reference_distance),
        "rollout_distance": distance_summary(rollout_distance),
        "shift_ratio_p95": safe_ratio(np.percentile(rollout_distance, 95), np.percentile(reference_distance, 95)),
        "collision_conditioned": collision_conditioned_summary(rollout_distance, collision),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"JEPA latent shift: reference_p95={metrics['reference_distance']['p95']:.3f} "
        f"rollout_p95={metrics['rollout_distance']['p95']:.3f} "
        f"ratio={metrics['shift_ratio_p95']:.2f} output={args.output}",
        flush=True,
    )


def validate_args(args: argparse.Namespace) -> None:
    for path in (args.reference_log, args.rollout_log, args.jepa_checkpoint):
        if not path.exists():
            raise FileNotFoundError(path)
    if not 0.0 < args.fit_fraction < 1.0:
        raise ValueError("--fit-fraction must be between 0 and 1.")
    if args.max_fit_samples <= 0 or args.max_reference_eval_samples <= 0 or args.batch_size <= 0:
        raise ValueError("Sample limits and batch size must be > 0.")
    if not 0.0 <= args.shrinkage <= 1.0:
        raise ValueError("--shrinkage must be between 0 and 1.")


def build_latent_context_arrays(path: Path, context_steps: int) -> dict[str, np.ndarray]:
    arrays = load_simulation_csv(path)
    arrays["action"] = load_context_action_array(path)
    return build_context_transitions(arrays, context_steps=context_steps)


def split_reference_indices(arrays: dict[str, np.ndarray], fit_fraction: float) -> tuple[np.ndarray, np.ndarray]:
    episodes = arrays.get("episode")
    if episodes is not None:
        unique = np.unique(episodes.astype(np.int64))
        if len(unique) > 1:
            split = min(len(unique) - 1, max(1, int(round(len(unique) * fit_fraction))))
            fit_episodes = set(int(value) for value in unique[:split])
            fit_mask = np.array([int(value) in fit_episodes for value in episodes], dtype=bool)
            return np.flatnonzero(fit_mask), np.flatnonzero(~fit_mask)
    split = min(len(arrays["obs"]) - 1, max(1, int(round(len(arrays["obs"]) * fit_fraction))))
    return np.arange(split), np.arange(split, len(arrays["obs"]))


def evenly_subsample(indices: np.ndarray, limit: int) -> np.ndarray:
    if len(indices) <= limit:
        return indices
    positions = np.linspace(0, len(indices) - 1, limit).astype(np.int64)
    return indices[positions]


def fit_regularized_gaussian(latents: np.ndarray, shrinkage: float) -> tuple[np.ndarray, np.ndarray]:
    mean = latents.mean(axis=0).astype(np.float64)
    centered = latents.astype(np.float64) - mean
    covariance = centered.T @ centered / max(1, len(centered) - 1)
    diagonal = np.diag(np.diag(covariance))
    covariance = (1.0 - shrinkage) * covariance + shrinkage * diagonal
    scale = max(float(np.trace(covariance) / covariance.shape[0]), 1e-8)
    covariance += np.eye(covariance.shape[0], dtype=np.float64) * scale * 1e-6
    return mean, np.linalg.pinv(covariance, hermitian=True)


def mahalanobis_distance(latents: np.ndarray, mean: np.ndarray, precision: np.ndarray) -> np.ndarray:
    centered = latents.astype(np.float64) - mean
    squared = np.einsum("bi,ij,bj->b", centered, precision, centered)
    return np.sqrt(np.maximum(squared, 0.0))


def distance_summary(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
    }


def collision_conditioned_summary(distance: np.ndarray, collision: np.ndarray) -> dict[str, Any]:
    result: dict[str, Any] = {
        "collision_samples": int(np.sum(collision)),
        "non_collision_samples": int(np.sum(~collision)),
    }
    result["collision"] = distance_summary(distance[collision]) if np.any(collision) else None
    result["non_collision"] = distance_summary(distance[~collision]) if np.any(~collision) else None
    if result["collision"] is not None and result["non_collision"] is not None:
        result["mean_ratio_collision_vs_non_collision"] = safe_ratio(
            result["collision"]["mean"], result["non_collision"]["mean"]
        )
    return result


def safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-12:
        return 0.0
    return float(numerator / denominator)


if __name__ == "__main__":
    main()
