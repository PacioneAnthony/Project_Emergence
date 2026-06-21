"""Train and evaluate explicit future-collision risk heads."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import numpy as np

from learning.datasets import build_context_transitions, load_simulation_csv
from learning.jepa import MLP
from learning.jepa_lnn_features import (
    encode_contexts,
    latest_observation_from_context,
    load_context_action_array,
    load_jepa_bundle,
)
from learning.train_lnn import resolve_device, set_training_seed

try:
    import torch
    import torch.nn.functional as F
except ModuleNotFoundError:
    torch = None
    F = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train explicit future-collision risk heads.")
    parser.add_argument("--logs", type=Path, nargs="+", required=True)
    parser.add_argument("--jepa-checkpoint", type=Path, required=True)
    parser.add_argument("--horizon", type=int, default=25)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=5101)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--output", type=Path, default=Path("models/jepa_collision_risk_001.pth"))
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("data/processed/experiments/jepa_collision_risk_001/metrics.json"),
    )
    return parser


def main() -> None:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required to train collision-risk heads.")
    args = build_parser().parse_args()
    validate_args(args)
    set_training_seed(args.seed)
    device = resolve_device(args.device)
    bundle = load_jepa_bundle(args.jepa_checkpoint, device)
    dataset = build_risk_dataset(
        args.logs, bundle.context_steps, args.horizon, args.val_fraction, args.test_fraction
    )
    latents = encode_contexts(bundle, dataset["context"], device=device, batch_size=args.batch_size)
    raw_features = np.concatenate([dataset["context"], dataset["action"]], axis=1).astype(np.float32)
    latent_features = np.concatenate([latents, dataset["action"]], axis=1).astype(np.float32)

    print(
        f"[risk] device={device} samples={len(dataset['label'])} train={int(dataset['train_mask'].sum())} "
        f"val={int(dataset['val_mask'].sum())} test={int(dataset['test_mask'].sum())} "
        f"positives={dataset['label'].mean():.3%} "
        f"horizon={args.horizon} context_steps={bundle.context_steps}",
        flush=True,
    )
    trained = {}
    reports = {}
    for name, features in (("jepa_latent_action", latent_features), ("raw_context_action", raw_features)):
        result = train_head(
            name,
            features,
            dataset["label"],
            dataset["train_mask"],
            dataset["val_mask"],
            dataset["test_mask"],
            hidden_dim=args.hidden_dim,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            weight_decay=args.weight_decay,
            patience=args.patience,
            device=device,
        )
        trained[name] = result
        reports[name] = result["metrics"]

    labels_val = dataset["label"][dataset["val_mask"]]
    labels_test = dataset["label"][dataset["test_mask"]]
    distance_val_scores = -dataset["distance"][dataset["val_mask"]]
    distance_test_scores = -dataset["distance"][dataset["test_mask"]]
    baseline_scale, baseline_bias = fit_score_calibration(distance_val_scores, labels_val)
    baseline_probabilities = sigmoid(baseline_scale * distance_test_scores + baseline_bias)
    reports["ultrasonic_distance"] = binary_metrics(
        labels_test,
        distance_test_scores,
        scores_are_logits=False,
        probabilities=baseline_probabilities,
    )
    reports["ultrasonic_distance"]["calibration_scale"] = float(baseline_scale)
    reports["ultrasonic_distance"]["calibration_bias"] = float(baseline_bias)
    winner = max(reports, key=lambda name: reports[name]["average_precision"])
    metrics = {
        "logs": [str(path) for path in args.logs],
        "jepa_checkpoint": str(args.jepa_checkpoint),
        "horizon_steps": int(args.horizon),
        "horizon_seconds": float(args.horizon * 0.02),
        "context_steps": int(bundle.context_steps),
        "n_samples": int(len(dataset["label"])),
        "n_train": int(dataset["train_mask"].sum()),
        "n_validation": int(dataset["val_mask"].sum()),
        "n_test": int(dataset["test_mask"].sum()),
        "train_positive_rate": float(dataset["label"][dataset["train_mask"]].mean()),
        "validation_positive_rate": float(labels_val.mean()),
        "test_positive_rate": float(labels_test.mean()),
        "models": reports,
        "best_average_precision_model": winner,
    }
    checkpoint = {
        "jepa_checkpoint": str(args.jepa_checkpoint),
        "context_steps": int(bundle.context_steps),
        "horizon_steps": int(args.horizon),
        "hidden_dim": int(args.hidden_dim),
        "heads": {
            name: {
                "input_dim": int(result["input_dim"]),
                "state_dict": result["state_dict"],
                "feature_mean": result["feature_mean"],
                "feature_std": result["feature_std"],
                "best_epoch": int(result["best_epoch"]),
                "calibration_scale": float(result["calibration_scale"]),
                "calibration_bias": float(result["calibration_bias"]),
            }
            for name, result in trained.items()
        },
        "metrics": metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, args.output)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"[risk] saved={args.output} winner={winner} "
        f"AP={reports[winner]['average_precision']:.4f} metrics={args.metrics_output}",
        flush=True,
    )


def validate_args(args: argparse.Namespace) -> None:
    if args.horizon <= 0 or args.epochs <= 0 or args.batch_size <= 0 or args.hidden_dim <= 0:
        raise ValueError("Horizon and training dimensions must be positive.")
    if not 0.0 < args.val_fraction < 1.0 or not 0.0 < args.test_fraction < 1.0:
        raise ValueError("Validation and test fractions must be in (0, 1).")
    if args.val_fraction + args.test_fraction >= 1.0:
        raise ValueError("Validation and test fractions must leave training episodes.")
    if args.patience < 0:
        raise ValueError("--patience must be >= 0.")
    missing = [path for path in [*args.logs, args.jepa_checkpoint] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing risk-training inputs: {missing}")


def build_risk_dataset(
    logs: list[Path],
    context_steps: int,
    horizon: int,
    val_fraction: float = 0.2,
    test_fraction: float = 0.2,
) -> dict[str, np.ndarray]:
    parts: dict[str, list[np.ndarray]] = {
        "context": [],
        "action": [],
        "distance": [],
        "label": [],
        "train_mask": [],
        "val_mask": [],
        "test_mask": [],
    }
    for path in logs:
        arrays = load_simulation_csv(path)
        arrays["action"] = load_context_action_array(path)
        arrays["risk_label"] = future_collision_labels_by_episode(
            arrays["collision"], arrays["episode"], horizon
        )
        arrays["risk_eligible"] = (arrays["collision"] == 0).astype(np.int64)
        contexts = build_context_transitions(arrays, context_steps=context_steps)
        eligible = contexts["risk_eligible"].astype(bool)
        episodes = contexts["episode"].astype(int)
        train_eps, val_eps, test_eps = split_episode_ids_three_way(
            episodes, val_fraction, test_fraction
        )
        parts["context"].append(contexts["obs"][eligible].astype(np.float32))
        parts["action"].append(contexts["action"][eligible].astype(np.float32))
        parts["distance"].append(
            latest_observation_from_context(contexts["obs"], context_steps)[eligible, 0].astype(np.float32)
        )
        parts["label"].append(contexts["risk_label"][eligible].astype(np.float32))
        eligible_episodes = episodes[eligible]
        parts["train_mask"].append(np.isin(eligible_episodes, list(train_eps)))
        parts["val_mask"].append(np.isin(eligible_episodes, list(val_eps)))
        parts["test_mask"].append(np.isin(eligible_episodes, list(test_eps)))
    return {key: np.concatenate(values, axis=0) for key, values in parts.items()}


def future_collision_labels_by_episode(collisions: np.ndarray, episodes: np.ndarray, horizon: int) -> np.ndarray:
    labels = np.zeros(len(collisions), dtype=np.float32)
    for episode in np.unique(episodes.astype(int)):
        indices = np.flatnonzero(episodes.astype(int) == episode)
        labels[indices] = future_collision_labels(collisions[indices], horizon)
    return labels


def future_collision_labels(collisions: np.ndarray, horizon: int) -> np.ndarray:
    collisions = np.asarray(collisions, dtype=bool)
    labels = np.zeros(len(collisions), dtype=np.float32)
    next_collision = len(collisions) + horizon + 1
    for index in range(len(collisions) - 1, -1, -1):
        if index + 1 < len(collisions) and collisions[index + 1]:
            next_collision = index + 1
        labels[index] = float(next_collision <= index + horizon)
    return labels


def split_episode_ids(episodes: np.ndarray, val_fraction: float) -> tuple[set[int], set[int]]:
    unique = sorted(int(value) for value in np.unique(episodes))
    if len(unique) < 2:
        raise ValueError("Risk training requires at least two episodes per log.")
    n_val = max(1, int(round(len(unique) * val_fraction)))
    n_val = min(n_val, len(unique) - 1)
    return set(unique[:-n_val]), set(unique[-n_val:])


def split_episode_ids_three_way(
    episodes: np.ndarray, val_fraction: float, test_fraction: float
) -> tuple[set[int], set[int], set[int]]:
    unique = sorted(int(value) for value in np.unique(episodes))
    if len(unique) < 3:
        raise ValueError("Risk evaluation requires at least three episodes per log.")
    n_val = max(1, int(round(len(unique) * val_fraction)))
    n_test = max(1, int(round(len(unique) * test_fraction)))
    while n_val + n_test >= len(unique):
        if n_val >= n_test and n_val > 1:
            n_val -= 1
        elif n_test > 1:
            n_test -= 1
        else:
            raise ValueError("Not enough episodes for train/validation/test split.")
    train_end = len(unique) - n_val - n_test
    val_end = len(unique) - n_test
    return set(unique[:train_end]), set(unique[train_end:val_end]), set(unique[val_end:])


def train_head(
    name: str,
    features: np.ndarray,
    labels: np.ndarray,
    train_mask: np.ndarray,
    val_mask: np.ndarray,
    test_mask: np.ndarray,
    *,
    hidden_dim: int,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    patience: int,
    device,
) -> dict[str, Any]:
    mean = features[train_mask].mean(axis=0).astype(np.float32)
    std = np.maximum(features[train_mask].std(axis=0), 1e-4).astype(np.float32)
    normalized = ((features - mean) / std).astype(np.float32)
    x = torch.from_numpy(normalized).to(device)
    y = torch.from_numpy(labels.astype(np.float32)).to(device)
    train_idx = torch.from_numpy(np.flatnonzero(train_mask)).long().to(device)
    val_idx = torch.from_numpy(np.flatnonzero(val_mask)).long().to(device)
    test_idx = torch.from_numpy(np.flatnonzero(test_mask)).long().to(device)
    model = MLP(features.shape[1], 1, hidden_dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    train_positive = float(labels[train_mask].sum())
    train_negative = float(train_mask.sum() - train_positive)
    pos_weight = torch.tensor(train_negative / max(1.0, train_positive), device=device)
    best_ap = -1.0
    best_epoch = 0
    best_state = None
    wait = 0
    for epoch in range(1, epochs + 1):
        model.train()
        permutation = train_idx[torch.randperm(len(train_idx), device=device)]
        total_loss = 0.0
        for start in range(0, len(permutation), batch_size):
            idx = permutation[start : start + batch_size]
            logits = model(x[idx]).squeeze(-1)
            loss = F.binary_cross_entropy_with_logits(logits, y[idx], pos_weight=pos_weight)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.item()) * len(idx)
        model.eval()
        with torch.no_grad():
            val_logits = model(x[val_idx]).squeeze(-1).detach().cpu().numpy()
        metrics = binary_metrics(labels[val_mask], val_logits, scores_are_logits=True)
        improved = metrics["average_precision"] > best_ap + 1e-5
        if improved:
            best_ap = metrics["average_precision"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
        if epoch == 1 or epoch % 5 == 0 or improved:
            print(
                f"[risk:{name}] epoch={epoch:03d} loss={total_loss / len(train_idx):.5f} "
                f"val_AP={metrics['average_precision']:.4f} val_AUROC={metrics['auroc']:.4f} "
                f"best={best_ap:.4f}@{best_epoch} wait={wait}/{patience}",
                flush=True,
            )
        if patience > 0 and wait >= patience:
            break
    if best_state is None:
        raise RuntimeError(f"Risk head {name} did not produce a checkpoint.")
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_logits = model(x[val_idx]).squeeze(-1).detach().cpu().numpy()
        test_logits = model(x[test_idx]).squeeze(-1).detach().cpu().numpy()
    calibration_scale, calibration_bias = fit_score_calibration(val_logits, labels[val_mask])
    test_probabilities = sigmoid(calibration_scale * test_logits + calibration_bias)
    return {
        "input_dim": int(features.shape[1]),
        "state_dict": {key: value.detach().cpu() for key, value in model.state_dict().items()},
        "feature_mean": mean,
        "feature_std": std,
        "best_epoch": int(best_epoch),
        "calibration_scale": float(calibration_scale),
        "calibration_bias": float(calibration_bias),
        "metrics": {
            **binary_metrics(
                labels[test_mask],
                test_logits,
                scores_are_logits=True,
                probabilities=test_probabilities,
            ),
            "selection_validation_average_precision": float(best_ap),
        },
    }


def binary_metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    *,
    scores_are_logits: bool,
    probabilities: np.ndarray | None = None,
) -> dict[str, float]:
    labels = np.asarray(labels, dtype=np.float64)
    scores = np.asarray(scores, dtype=np.float64)
    if probabilities is None:
        probabilities = sigmoid(scores) if scores_are_logits else minmax_probability(scores)
    operating = recall_at_fpr(labels, scores, max_fpr=0.05)
    return {
        "positive_rate": float(labels.mean()),
        "average_precision": float(average_precision(labels, scores)),
        "auroc": float(auroc(labels, scores)),
        "brier": float(np.mean((probabilities - labels) ** 2)),
        "ece_10_bins": float(expected_calibration_error(labels, probabilities, bins=10)),
        **operating,
    }


def average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=np.int64)
    positives = int(labels.sum())
    if positives == 0:
        return 0.0
    order = np.argsort(-scores, kind="mergesort")
    ranked = labels[order]
    precision = np.cumsum(ranked) / np.arange(1, len(ranked) + 1)
    return float(np.sum(precision * ranked) / positives)


def auroc(labels: np.ndarray, scores: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=np.int64)
    positives = int(labels.sum())
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return 0.5
    order = np.argsort(-scores, kind="mergesort")
    ranked = labels[order]
    tpr = np.concatenate([[0.0], np.cumsum(ranked) / positives, [1.0]])
    fpr = np.concatenate([[0.0], np.cumsum(1 - ranked) / negatives, [1.0]])
    return float(np.trapezoid(tpr, fpr))


def recall_at_fpr(labels: np.ndarray, scores: np.ndarray, max_fpr: float) -> dict[str, float]:
    labels = np.asarray(labels, dtype=np.int64)
    positives = max(1, int(labels.sum()))
    negatives = max(1, len(labels) - int(labels.sum()))
    order = np.argsort(-scores, kind="mergesort")
    ranked = labels[order]
    tp = np.cumsum(ranked)
    fp = np.cumsum(1 - ranked)
    valid = np.flatnonzero(fp / negatives <= max_fpr)
    index = int(valid[-1]) if len(valid) else 0
    return {
        "recall_at_5pct_fpr": float(tp[index] / positives),
        "precision_at_5pct_fpr": float(tp[index] / max(1, tp[index] + fp[index])),
        "threshold_at_5pct_fpr": float(scores[order[index]]),
        "actual_fpr": float(fp[index] / negatives),
    }


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def fit_score_calibration(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    score_t = torch.from_numpy(np.asarray(scores, dtype=np.float32))
    label_t = torch.from_numpy(np.asarray(labels, dtype=np.float32))
    log_scale = torch.zeros((), requires_grad=True)
    bias = torch.zeros((), requires_grad=True)
    optimizer = torch.optim.LBFGS([log_scale, bias], lr=0.25, max_iter=100, line_search_fn="strong_wolfe")

    def closure():
        optimizer.zero_grad()
        calibrated = torch.exp(log_scale) * score_t + bias
        loss = F.binary_cross_entropy_with_logits(calibrated, label_t)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(torch.exp(log_scale).detach().item()), float(bias.detach().item())


def minmax_probability(scores: np.ndarray) -> np.ndarray:
    low = float(np.min(scores))
    high = float(np.max(scores))
    if high <= low:
        return np.full_like(scores, 0.5, dtype=np.float64)
    return (scores - low) / (high - low)


def expected_calibration_error(labels: np.ndarray, probabilities: np.ndarray, bins: int) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(labels)
    error = 0.0
    for index in range(bins):
        upper_inclusive = index == bins - 1
        mask = (probabilities >= edges[index]) & (
            probabilities <= edges[index + 1] if upper_inclusive else probabilities < edges[index + 1]
        )
        if np.any(mask):
            error += float(mask.mean()) * abs(float(probabilities[mask].mean()) - float(labels[mask].mean()))
    return error


if __name__ == "__main__":
    main()
