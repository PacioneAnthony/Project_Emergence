"""TV-001: active visual exploration with a real JEPA learner.

The frozen protocol lives in
``docs/research/tv_real_jepa_001_preregistration.md``.  This module is additive:
the DC-001..005 schedulers and the validated visual-JEPA implementation are not
modified.  It supplies the unlearnable visual source, held-out regional anchors,
the robust regional-gain scheduler, calibration, and one campaign run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from learning.active_exploration import (
    CAPTURE_HZ,
    DECISION_FRAMES,
    ExperienceBuffer,
    coverage_entropy,
    train_round,
)
from learning.train_visual_jepa import ProbeHeads, normalize_action, resolve_device
from learning.visual_jepa import VisualJEPA

try:
    import torch
except ModuleNotFoundError:
    torch = None


TV_LOW_DEG = 130.0
TV_HIGH_DEG = 170.0
ANGLE_BINS = 8
CONTEXT_BINS = 2
PROBE_BATCH_SIZE = 16
ANCHORS_PER_CELL = 64
GAIN_HISTORY = 4
MIN_GAIN_HISTORY = 2


def angle_bin(angle_deg: float, min_deg: float = 10.0, max_deg: float = 170.0) -> int:
    span = max_deg - min_deg
    index = int((float(angle_deg) - min_deg) / span * ANGLE_BINS)
    return min(max(index, 0), ANGLE_BINS - 1)


def visual_context_id(frame: np.ndarray) -> int:
    """Two-way visual context derived only from a neutral camera image."""

    height, width = frame.shape[:2]
    if height % 8 or width % 8:
        raise ValueError("visual context requires image dimensions divisible by 8")
    gray = (
        0.299 * frame[..., 0].astype(np.float32)
        + 0.587 * frame[..., 1].astype(np.float32)
        + 0.114 * frame[..., 2].astype(np.float32)
    )
    thumb = gray.reshape(8, height // 8, 8, width // 8).mean(axis=(1, 3))
    quantized = np.clip(np.round(thumb / 16.0), 0, 15).astype(np.uint8)
    return int(hashlib.sha256(quantized.tobytes()).digest()[0] & 1)


def television_rectangle(frame: np.ndarray) -> tuple[slice, slice]:
    height, width = frame.shape[:2]
    return slice(height // 8, height - height // 8), slice(width // 8, width - width // 8)


def apply_television(frame: np.ndarray, angle_deg: float, rng: np.random.Generator) -> np.ndarray:
    """Overlay independent RGB television noise in the frozen angular sector."""

    output = np.array(frame, copy=True)
    if not (TV_LOW_DEG <= float(angle_deg) <= TV_HIGH_DEG):
        return output
    ys, xs = television_rectangle(output)
    output[ys, xs] = rng.integers(0, 256, size=output[ys, xs].shape, dtype=np.uint8)
    # A fixed dark bezel makes the source look like a screen without making its
    # content predictable.
    y0, y1 = ys.start, ys.stop
    x0, x1 = xs.start, xs.stop
    output[max(0, y0 - 2) : y0, max(0, x0 - 2) : min(output.shape[1], x1 + 2)] = 8
    output[y1 : min(output.shape[0], y1 + 2), max(0, x0 - 2) : min(output.shape[1], x1 + 2)] = 8
    output[y0:y1, max(0, x0 - 2) : x0] = 8
    output[y0:y1, x1 : min(output.shape[1], x1 + 2)] = 8
    return output


def television_lag_correlation(seed: int, image_size: int = 64, pairs: int = 64) -> float:
    """Mean correlation of independent television contents (construction check)."""

    rng = np.random.default_rng(seed)
    base = np.zeros((image_size, image_size, 3), dtype=np.uint8)
    correlations = []
    previous = apply_television(base, 150.0, rng)
    ys, xs = television_rectangle(previous)
    for _ in range(pairs):
        current = apply_television(base, 150.0, rng)
        a = previous[ys, xs].astype(np.float64).ravel()
        b = current[ys, xs].astype(np.float64).ravel()
        correlations.append(float(np.corrcoef(a, b)[0, 1]))
        previous = current
    return float(np.mean(correlations))


@dataclass
class AnchorBank:
    frames_start: np.ndarray
    frames_end: np.ndarray
    actions: np.ndarray
    angle_bins: np.ndarray
    contexts: np.ndarray
    target_deg: np.ndarray

    def __len__(self) -> int:
        return int(self.frames_start.shape[0])

    def cell_indices(self, cell: tuple[int, int]) -> np.ndarray:
        angle, context = cell
        return np.flatnonzero((self.angle_bins == angle) & (self.contexts == context)).astype(np.int64)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            frames_start=self.frames_start,
            frames_end=self.frames_end,
            actions=self.actions,
            angle_bins=self.angle_bins,
            contexts=self.contexts,
            target_deg=self.target_deg,
        )

    @classmethod
    def load(cls, path: Path) -> "AnchorBank":
        with np.load(path) as data:
            return cls(**{name: np.array(data[name]) for name in cls.__annotations__})


def _settle(env, target: float, steps: int) -> None:
    for _ in range(steps):
        env.step(target)


def generate_anchor_bank(
    seed: int,
    path: Path,
    image_size: int = 64,
    anchors_per_cell: int = ANCHORS_PER_CELL,
) -> AnchorBank:
    """Generate or load a held-out bank balanced by angle and pixel context."""

    if path.exists():
        bank = AnchorBank.load(path)
        expected = ANGLE_BINS * CONTEXT_BINS * anchors_per_cell
        if len(bank) != expected:
            raise ValueError(f"anchor bank {path} contains {len(bank)} pairs, expected {expected}")
        return bank

    from sim3d.bench_env import BenchHeadEnv
    from sim3d.bench_model import BenchConfig

    env = BenchHeadEnv(BenchConfig(seed=seed))
    rng = np.random.default_rng(seed + 610_000)
    frames_start: list[np.ndarray] = []
    frames_end: list[np.ndarray] = []
    actions: list[np.ndarray] = []
    bins: list[int] = []
    contexts: list[int] = []
    targets: list[float] = []
    counts = np.zeros((ANGLE_BINS, CONTEXT_BINS), dtype=int)
    candidate = 0
    try:
        while np.any(counts < anchors_per_cell):
            if candidate >= 512:
                raise RuntimeError("could not balance held-out visual contexts after 512 rooms")
            room_seed = 41_000_000 + seed * 1000 + candidate
            candidate += 1
            env.reset(seed=room_seed)
            _settle(env, 90.0, 20)
            neutral = env.render_camera(image_size, image_size)
            context = visual_context_id(neutral)
            needed = [index for index in range(ANGLE_BINS) if counts[index, context] < anchors_per_cell]
            if not needed:
                continue
            tv_rng = np.random.default_rng(room_seed + 710_000)
            for index in needed:
                remaining = anchors_per_cell - counts[index, context]
                repeats = min(8, remaining)
                low = 10.0 + index * 20.0
                high = low + 20.0
                for _ in range(repeats):
                    _settle(env, 90.0, 20)
                    obs_start = env.step(90.0)
                    start = apply_television(
                        env.render_camera(image_size, image_size), obs_start.as5600_deg, tv_rng
                    )
                    target = float(rng.uniform(low + 0.25, high - 0.25))
                    _settle(env, target, 15)  # 0.3 s, the strongest validated v3 horizon
                    obs_end = env.step(target)
                    end = apply_television(
                        env.render_camera(image_size, image_size), obs_end.as5600_deg, tv_rng
                    )
                    action = np.zeros(5, dtype=np.float32)
                    action[:3] = normalize_action(np.full(3, target, dtype=np.float32))
                    frames_start.append(start)
                    frames_end.append(end)
                    actions.append(action)
                    bins.append(index)
                    contexts.append(context)
                    targets.append(float(obs_end.as5600_deg))
                    counts[index, context] += 1
    finally:
        env.close()

    bank = AnchorBank(
        frames_start=np.stack(frames_start).astype(np.uint8),
        frames_end=np.stack(frames_end).astype(np.uint8),
        actions=np.stack(actions).astype(np.float32),
        angle_bins=np.asarray(bins, dtype=np.int8),
        contexts=np.asarray(contexts, dtype=np.int8),
        target_deg=np.asarray(targets, dtype=np.float32),
    )
    bank.save(path)
    return bank


def anchor_errors(model, bank: AnchorBank, indices: np.ndarray, device, batch_size: int = 256) -> np.ndarray:
    """Per-anchor bounded latent prediction error."""

    model.eval()
    values: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(indices), batch_size):
            selected = indices[start : start + batch_size]
            frame_t = (
                torch.from_numpy(bank.frames_start[selected]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            )
            frame_next = (
                torch.from_numpy(bank.frames_end[selected]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            )
            action = torch.from_numpy(bank.actions[selected]).to(device)
            horizon = torch.full((len(selected), 1), 3.0 / 5.0, device=device)
            latent_t = model.encode(frame_t)
            latent_next = model.encode(frame_next)
            prediction = model.predict_next(latent_t, action, horizon)
            pred = torch.mean((prediction - latent_next) ** 2, dim=1)
            copy = torch.mean((latent_t - latent_next) ** 2, dim=1)
            bounded = pred / torch.clamp(pred + copy, min=1e-8)
            values.append(bounded.float().cpu().numpy())
    return np.concatenate(values) if values else np.empty(0, dtype=np.float32)


def sample_cell_error(
    model,
    bank: AnchorBank,
    cell: tuple[int, int],
    device,
    batches: int,
    seed: int,
) -> tuple[float, list[float]]:
    pool = bank.cell_indices(cell)
    if len(pool) < PROBE_BATCH_SIZE:
        raise ValueError(f"cell {cell} has only {len(pool)} anchors")
    rng = np.random.default_rng(seed)
    batch_means = []
    for _ in range(batches):
        selected = rng.choice(pool, size=PROBE_BATCH_SIZE, replace=False)
        batch_means.append(float(np.mean(anchor_errors(model, bank, selected, device))))
    return float(np.mean(batch_means)), batch_means


def full_anchor_metrics(model, bank: AnchorBank, device) -> dict[str, float]:
    indices = np.arange(len(bank), dtype=np.int64)
    errors = anchor_errors(model, bank, indices, device)
    structured = bank.target_deg < TV_LOW_DEG
    television = ~structured
    return {
        "structured_error": float(np.mean(errors[structured])),
        "television_error": float(np.mean(errors[television])),
        "all_error": float(np.mean(errors)),
        "anchors": int(len(bank)),
        "structured_anchors": int(np.sum(structured)),
        "television_anchors": int(np.sum(television)),
    }


class UniformTelevisionPolicy:
    def __init__(self, min_deg: float = 10.0, max_deg: float = 170.0):
        self.min_deg = min_deg
        self.max_deg = max_deg

    def choose(self, context: int, rng: np.random.Generator) -> tuple[float, tuple[int, int]]:
        target = float(rng.uniform(self.min_deg, self.max_deg))
        return target, (angle_bin(target, self.min_deg, self.max_deg), int(context))

    def update(self, cell: tuple[int, int], gain: float) -> None:
        return None

    def diagnostics(self) -> dict:
        return {}


class RegionalGainTelevisionPolicy:
    """Windowed signed regional learning progress; aggregate, then clip."""

    def __init__(self, epsilon: float = 0.10):
        self.epsilon = float(epsilon)
        self.histories = {
            (angle, context): deque(maxlen=GAIN_HISTORY)
            for angle in range(ANGLE_BINS)
            for context in range(CONTEXT_BINS)
        }

    def score(self, cell: tuple[int, int]) -> float:
        history = self.histories[cell]
        if len(history) < MIN_GAIN_HISTORY:
            return math.inf
        return max(float(np.mean(history)), 0.0)

    def choose(self, context: int, rng: np.random.Generator) -> tuple[float, tuple[int, int]]:
        cells = [(angle, int(context)) for angle in range(ANGLE_BINS)]
        if rng.random() < self.epsilon:
            cell = cells[int(rng.integers(0, len(cells)))]
        else:
            scores = np.asarray([self.score(cell) for cell in cells])
            best = float(np.max(scores))
            candidates = np.flatnonzero(scores == best)
            cell = cells[int(rng.choice(candidates))]
        low = 10.0 + cell[0] * 20.0
        target = float(rng.uniform(low, low + 20.0))
        return target, cell

    def update(self, cell: tuple[int, int], gain: float) -> None:
        self.histories[cell].append(float(gain))

    def diagnostics(self) -> dict:
        return {
            f"angle{angle}_context{context}": {
                "gains": list(self.histories[(angle, context)]),
                "score": self.score((angle, context)),
            }
            for angle in range(ANGLE_BINS)
            for context in range(CONTEXT_BINS)
        }


def collect_tv_episode(
    env,
    policy,
    rng: np.random.Generator,
    frames_per_episode: int,
    image_size: int,
    room_seed: int,
) -> tuple[list[np.ndarray], list[float], list[float], list[float], list[tuple[int, int]], list[float]]:
    env.reset(seed=room_seed)
    neutral = env.render_camera(image_size, image_size)
    context = visual_context_id(neutral)
    tv_rng = np.random.default_rng(room_seed + 710_000)
    capture_every = max(1, round(1.0 / (CAPTURE_HZ * env.config.control_dt)))
    frames: list[np.ndarray] = []
    requested: list[float] = []
    as5600: list[float] = []
    distance: list[float] = []
    decision_cells: list[tuple[int, int]] = []
    decision_targets: list[float] = []
    target = 90.0

    for frame_index in range(frames_per_episode):
        if frame_index % DECISION_FRAMES == 0:
            target, cell = policy.choose(context, rng)
            decision_cells.append(cell)
            decision_targets.append(target)
        obs = None
        for _ in range(capture_every):
            obs = env.step(target)
        clean = env.render_camera(image_size, image_size)
        frames.append(apply_television(clean, obs.as5600_deg, tv_rng))
        requested.append(obs.requested_deg)
        as5600.append(obs.as5600_deg)
        distance.append(obs.distance_m)
    return frames, requested, as5600, distance, decision_cells, decision_targets


def select_probe_batches(differences: np.ndarray, median_error: float) -> tuple[int | None, dict]:
    """Apply the frozen calibration rule to null gain observations."""

    values = np.asarray(differences, dtype=np.float64)
    if values.size < 32 or not np.all(np.isfinite(values)):
        raise ValueError("at least 32 finite null differences are required")
    if not math.isfinite(median_error) or median_error <= 0:
        raise ValueError("median_error must be positive and finite")
    sigma = float(np.std(values, ddof=1))
    threshold = 0.02 * float(median_error)
    candidates: dict[str, dict[str, float | int | bool]] = {}
    selected = None
    for batches in (4, 8, 16, 32):
        usable = len(values) // batches * batches
        aggregates = values[:usable].reshape(-1, batches).mean(axis=1)
        half_width = float(1.96 * sigma / math.sqrt(batches))
        false_positive_rate = float(np.mean(aggregates > threshold))
        passed = half_width <= threshold and false_positive_rate <= 0.05
        candidates[str(batches)] = {
            "half_width_95": half_width,
            "false_positive_rate": false_positive_rate,
            "aggregates": int(len(aggregates)),
            "passed": bool(passed),
        }
        if selected is None and passed:
            selected = batches
    return selected, {"sigma": sigma, "threshold": threshold, "candidates": candidates}


def calibrate_noise(
    seeds: tuple[int, ...],
    anchor_dir: Path,
    device,
    image_size: int = 64,
    output: Path | None = None,
) -> dict:
    """Execute the frozen null-gain calibration and select B."""

    null_differences: list[float] = []
    base_errors: list[float] = []
    lag_correlations: list[float] = []
    for seed in seeds:
        torch.manual_seed(seed)
        model = VisualJEPA(
            latent_dim=128,
            action_dim=5,
            hidden_dim=512,
            encoder_width=32,
            use_action=True,
            horizon_dim=1,
        ).to(device)
        bank = generate_anchor_bank(seed, anchor_dir / f"anchors_seed{seed}.npz", image_size=image_size)
        lag_correlations.append(television_lag_correlation(seed))
        for angle in range(ANGLE_BINS):
            for context in range(CONTEXT_BINS):
                cell = (angle, context)
                before, before_values = sample_cell_error(
                    model, bank, cell, device, 64, seed + 810_000 + angle * 10 + context
                )
                after, after_values = sample_cell_error(
                    model, bank, cell, device, 64, seed + 820_000 + angle * 10 + context
                )
                # Preserve the 64 paired null observations; the aggregate means are
                # reported only as a cross-check.
                null_differences.extend((np.asarray(before_values) - np.asarray(after_values)).tolist())
                base_errors.extend(before_values)
                if not math.isfinite(before - after):
                    raise RuntimeError("non-finite calibration gain")

    differences = np.asarray(null_differences, dtype=np.float64)
    median_error = float(np.median(base_errors))
    selected, selection = select_probe_batches(differences, median_error)
    sigma = float(selection["sigma"])
    threshold = float(selection["threshold"])
    candidates = selection["candidates"]

    lag_max = float(max(abs(value) for value in lag_correlations))
    report = {
        "status": "passed" if selected is not None and lag_max <= 0.02 else "failed",
        "protocol": "docs/research/tv_real_jepa_001_preregistration.md",
        "seeds": list(seeds),
        "null_differences": int(len(differences)),
        "sigma": sigma,
        "median_error": median_error,
        "relative_threshold": threshold,
        "candidates": candidates,
        "selected_probe_batches": selected,
        "television_lag_correlations": lag_correlations,
        "television_lag_abs_max": lag_max,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def run_condition(args: argparse.Namespace) -> dict:
    if torch is None:
        raise ModuleNotFoundError("tv_exploration requires PyTorch")
    device = resolve_device(args.device)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed + 400_000)

    from sim3d.bench_env import BenchHeadEnv
    from sim3d.bench_model import BenchConfig

    bank = generate_anchor_bank(
        args.seed,
        args.anchor_dir / f"anchors_seed{args.seed}.npz",
        image_size=args.image_size,
    )
    model = VisualJEPA(
        latent_dim=128,
        action_dim=5,
        hidden_dim=512,
        encoder_width=32,
        use_action=True,
        horizon_dim=1,
    ).to(device)
    probes = ProbeHeads(128).to(device)
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(probes.parameters()), lr=3e-4, weight_decay=1e-4
    )
    policy = (
        RegionalGainTelevisionPolicy()
        if args.condition == "regional_lp_gain"
        else UniformTelevisionPolicy()
    )
    env = BenchHeadEnv(BenchConfig(seed=args.seed))
    buffer = ExperienceBuffer()
    rounds_report = []
    all_decision_targets: list[float] = []
    all_decision_cells: list[tuple[int, int]] = []
    frames_per_episode = args.frames_per_round // args.episodes_per_round
    initial = full_anchor_metrics(model, bank, device)
    started = time.perf_counter()

    try:
        for round_index in range(args.rounds):
            visited: set[tuple[int, int]] = set()
            round_targets: list[float] = []
            round_angles: list[float] = []
            for episode_index in range(args.episodes_per_round):
                global_episode = round_index * args.episodes_per_round + episode_index
                room_seed = 51_000_000 + args.seed * 1000 + global_episode
                frames, requested, as5600, distance, cells, targets = collect_tv_episode(
                    env,
                    policy,
                    rng,
                    frames_per_episode,
                    args.image_size,
                    room_seed,
                )
                buffer.add_episode(frames, requested, as5600, distance)
                visited.update(cells)
                round_targets.extend(targets)
                round_angles.extend(as5600)
                all_decision_targets.extend(targets)
                all_decision_cells.extend(cells)

            before: dict[tuple[int, int], tuple[float, list[float]]] = {}
            for cell in sorted(visited):
                before[cell] = sample_cell_error(
                    model,
                    bank,
                    cell,
                    device,
                    args.probe_batches,
                    args.seed + 1_000_000 + round_index * 1000 + cell[0] * 10 + cell[1],
                )

            data = buffer.to_data()
            train_loss = train_round(
                model,
                probes,
                optimizer,
                data,
                args.epochs_per_round,
                256,
                rng,
                device,
                5,
                1.0,
                0.1,
            )

            gains = {}
            for cell in sorted(visited):
                after = sample_cell_error(
                    model,
                    bank,
                    cell,
                    device,
                    args.probe_batches,
                    args.seed + 2_000_000 + round_index * 1000 + cell[0] * 10 + cell[1],
                )
                gain = float(before[cell][0] - after[0])
                gains[f"{cell[0]}:{cell[1]}"] = {
                    "before": before[cell][0],
                    "after": after[0],
                    "gain": gain,
                }
                policy.update(cell, gain)

            external = full_anchor_metrics(model, bank, device)
            round_tv_fraction = float(np.mean(np.asarray(round_targets) >= TV_LOW_DEG))
            rounds_report.append(
                {
                    "round": round_index + 1,
                    "frames_total": buffer.total_frames(),
                    "decisions": len(round_targets),
                    "train_loss": train_loss,
                    "television_fraction": round_tv_fraction,
                    "angle_coverage_entropy": coverage_entropy(np.asarray(round_angles), 10.0, 170.0),
                    "visited_cells": [list(cell) for cell in sorted(visited)],
                    "regional_gains": gains,
                    "external": external,
                }
            )
            print(
                f"round {round_index + 1}/{args.rounds}: frames={buffer.total_frames()} "
                f"structured={external['structured_error']:.4f} tv={round_tv_fraction:.3f}",
                flush=True,
            )
    finally:
        env.close()

    final = full_anchor_metrics(model, bank, device)
    elapsed = time.perf_counter() - started
    targets_array = np.asarray(all_decision_targets, dtype=np.float64)
    target_bins = np.asarray([cell[0] for cell in all_decision_cells], dtype=np.int64)
    structured_counts = np.bincount(target_bins[target_bins < 6], minlength=6)
    structured_total = int(structured_counts.sum())
    if structured_total:
        p = structured_counts[structured_counts > 0] / structured_total
        structured_entropy = float(-(p * np.log(p)).sum() / math.log(6))
        structured_min_share = float(structured_counts.min() / len(targets_array))
    else:
        structured_entropy = 0.0
        structured_min_share = 0.0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": {name: value.detach().cpu() for name, value in model.state_dict().items()},
            "probes_state_dict": {name: value.detach().cpu() for name, value in probes.state_dict().items()},
            "condition": args.condition,
            "seed": args.seed,
            "protocol": "tv_real_jepa_001",
        },
        args.output,
    )
    report = {
        "status": "complete",
        "protocol": "docs/research/tv_real_jepa_001_preregistration.md",
        "condition": args.condition,
        "seed": int(args.seed),
        "device": str(device),
        "probe_batches": int(args.probe_batches),
        "frames_budget": int(buffer.total_frames()),
        "decision_budget": int(len(targets_array)),
        "optimizer_steps_budget": int(
            sum(args.epochs_per_round * max(1, ((index + 1) * args.frames_per_round - (index + 1) * args.episodes_per_round) // 256)
                for index in range(args.rounds))
        ),
        "initial_external": initial,
        "final_external": final,
        "structured_improvement": float((initial["structured_error"] - final["structured_error"]) / initial["structured_error"]),
        "television_fraction": float(np.mean(targets_array >= TV_LOW_DEG)),
        "structured_coverage_entropy": structured_entropy,
        "structured_bin_min_decision_share": structured_min_share,
        "structured_bin_counts": structured_counts.astype(int).tolist(),
        "policy": policy.diagnostics(),
        "rounds": rounds_report,
        "wall_seconds": float(elapsed),
        "checkpoint": str(args.output),
    }
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TV-001 real-JEPA exploration run")
    parser.add_argument("--condition", choices=("babbling", "regional_lp_gain"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--probe-batches", type=int, required=True)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--frames-per-round", type=int, default=800)
    parser.add_argument("--episodes-per-round", type=int, default=4)
    parser.add_argument("--epochs-per-round", type=int, default=20)
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--anchor-dir", type=Path, default=Path("data/raw/tv_real_jepa_001"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metrics-output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.frames_per_round % args.episodes_per_round:
        raise ValueError("frames-per-round must be divisible by episodes-per-round")
    report = run_condition(args)
    print(
        f"TV-001 run complete: {args.condition} seed={args.seed} "
        f"structured={report['final_external']['structured_error']:.4f} "
        f"tv_fraction={report['television_fraction']:.3f} ({report['wall_seconds']:.0f}s)",
        flush=True,
    )


if __name__ == "__main__":
    main()
