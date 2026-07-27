"""REF-002 spatial transport blocks frozen by the amended pre-registration.

This module contains models and analytic baselines only. It neither generates
reserved worlds nor launches training.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Literal

import numpy as np

from learning.jepa import covariance_loss, variance_loss
from learning.paired_stats import (
    bca_bootstrap_ci,
    cohen_dz,
    exact_sign_flip_pvalue,
    holm_correction,
    paired_sign_counts,
    rank_biserial,
)
from learning.train_visual_jepa import build_pairs_multi
from sim3d.bench_model import BenchConfig, BenchRoomConfig

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as functional
except ModuleNotFoundError:
    torch = None
    nn = None
    functional = None


Condition = Literal["transport_jepa", "concat_relative_jepa", "no_command_jepa"]
CONDITIONS: tuple[Condition, ...] = (
    "transport_jepa",
    "concat_relative_jepa",
    "no_command_jepa",
)
MAX_HORIZON = 5
ANGLE_RANGE_DEG = 160.0
RESERVED_SEEDS = tuple(range(13301, 13317))
SMOKE_SEED = 13991
STRUCTURED_CENTERS_DEG = (20.0, 40.0, 60.0, 80.0, 100.0, 120.0)
BANKS = (
    "moving_self_calibration",
    "moving_self_test",
    "micro_self_calibration",
    "micro_self_test",
    "external_only",
    "mixed",
    "learner_validation",
)
MOBILE_MATCHED_BANKS = ("moving_self_calibration", "moving_self_test", "mixed")
ANALYSIS_SEED = 2026072601


@dataclass(frozen=True)
class Ref2Spec:
    episodes: int = 20
    frames_per_episode: int = 600
    decisions_per_episode: int = 120
    optimizer_steps: int = 4_500
    batch_size: int = 256
    max_horizon: int = MAX_HORIZON
    image_size: int = 64
    encoder_width: int = 32
    motor_hidden: int = 64
    motor_channels: int = 16
    pairs_per_bin: int = 128
    lr: float = 3e-4
    weight_decay: float = 1e-4
    variance_weight: float = 1.0
    covariance_weight: float = 0.1
    version: str = "ref-002-c1-c8-v1"

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def images(self) -> int:
        return self.episodes * self.frames_per_episode

    @property
    def decisions(self) -> int:
        return self.episodes * self.decisions_per_episode


@dataclass
class Ref2Bank:
    frames_start: np.ndarray
    frames_end: np.ndarray
    current_angle_deg: np.ndarray
    command_targets_deg: np.ndarray
    motor_input: np.ndarray
    horizon: np.ndarray
    planned_signed_amplitude_deg: np.ndarray
    angle_bins: np.ndarray
    contexts: np.ndarray
    head_delta_deg: np.ndarray
    object_delta_m: np.ndarray
    labels: np.ndarray

    def __len__(self) -> int:
        return int(len(self.frames_start))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **{name: getattr(self, name) for name in self.__annotations__})

    @classmethod
    def load(cls, path: Path) -> "Ref2Bank":
        with np.load(path) as stored:
            return cls(**{name: np.array(stored[name]) for name in cls.__annotations__})


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _correlation(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation arrays must have matching non-trivial size")
    if np.std(left) == 0 or np.std(right) == 0:
        return float("nan")
    return float(np.corrcoef(left, right)[0, 1])


def _bounded_reflect(value: float, low: float, high: float) -> float:
    if value < low:
        return low + (low - value)
    if value > high:
        return high - (value - high)
    return value


def corpus_path(root: Path, seed: int) -> Path:
    return root / "corpora" / f"seed_{seed}.npz"


def bank_path(root: Path, seed: int, kind: str) -> Path:
    return root / "banks" / f"seed_{seed}" / f"{kind}.npz"


def run_path(root: Path, seed: int, condition: str) -> Path:
    return root / "runs" / f"seed_{seed}_{condition}.json"


def checkpoint_path(root: Path, seed: int, condition: str) -> Path:
    return root / "checkpoints" / f"seed_{seed}_{condition}.pt"


def evaluation_path(root: Path, seed: int) -> Path:
    return root / "evaluations" / f"seed_{seed}.json"


def ref2_bench_config(seed: int, bearing_deg: float = 82.0, context: int = 0) -> BenchConfig:
    if context not in (0, 1):
        raise ValueError("REF2 context must be 0 or 1")
    primary = (0.54, 0.70, 0.48) if context == 0 else (0.68, 0.48, 0.72)
    secondary = (0.62, 0.44, 0.30) if context == 0 else (0.32, 0.58, 0.66)
    room = BenchRoomConfig(
        width=3.3,
        depth=3.7,
        object_count=9,
        min_object_size=0.05,
        max_object_size=0.24,
        primary_light_rgb=primary,
        secondary_light_rgb=secondary,
        headlight_ambient_rgb=(0.28, 0.30, 0.26),
        headlight_diffuse_rgb=(0.62, 0.60, 0.56),
        reafference_object=True,
        reafference_bearing_deg=float(bearing_deg),
        reafference_distance_m=1.32,
        reafference_travel_m=0.40,
    )
    return BenchConfig(seed=int(seed), randomize_room=True, room=room)


def _frame_hashes(frames: np.ndarray) -> list[bytes]:
    return [hashlib.sha256(frame.tobytes()).digest() for frame in frames]


def _balanced_signed_values(values: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    unsigned = np.asarray(values, dtype=np.float32)
    if len(unsigned) % 2:
        raise ValueError("balanced signs require an even number of values")
    signs = np.ones(len(unsigned), dtype=np.float32)
    signs[: len(unsigned) // 2] = -1
    rng.shuffle(signs)
    return unsigned * signs


def _one_bin_motion(
    rng: np.random.Generator,
    center_deg: float,
    pairs: int,
    *,
    micro: bool,
) -> dict[str, np.ndarray]:
    if micro:
        if pairs != 128:
            raise ValueError("the frozen micro plan requires 128 pairs per bin")
        counts = (24, 26, 26, 26, 26)
        horizons = np.concatenate(
            [np.full(count, horizon, dtype=np.int8) for horizon, count in enumerate(counts, start=1)]
        )
        unsigned = np.full(pairs, 2.0, dtype=np.float32)
    else:
        if pairs != 128:
            raise ValueError("the frozen mobile plan requires 128 pairs per bin")
        combinations = [(amplitude, horizon) for amplitude in (4.0, 6.0, 8.0, 10.0) for horizon in range(1, 6)]
        counts = [8] * 4 + [6] * 16
        unsigned = np.concatenate(
            [np.full(count, combination[0], dtype=np.float32) for combination, count in zip(combinations, counts)]
        )
        horizons = np.concatenate(
            [np.full(count, combination[1], dtype=np.int8) for combination, count in zip(combinations, counts)]
        )
    signed = np.empty(pairs, dtype=np.float32)
    for horizon_value in range(1, MAX_HORIZON + 1):
        for amplitude_value in np.unique(unsigned[horizons == horizon_value]):
            selected = np.flatnonzero(
                (horizons == horizon_value) & (unsigned == amplitude_value)
            )
            values = _balanced_signed_values(unsigned[selected], rng)
            signed[selected] = values
    order = rng.permutation(pairs)
    unsigned = unsigned[order]
    signed = signed[order]
    horizons = horizons[order]
    current = center_deg + rng.uniform(-4.0, 4.0, size=pairs).astype(np.float32)
    targets = np.repeat((current + signed)[:, None], MAX_HORIZON, axis=1).astype(np.float32)
    return {
        "current_angle_deg": current,
        "command_targets_deg": targets,
        "horizon": horizons,
        "signed_amplitude_deg": signed,
    }


def build_matched_motion_plans(seed: int, spec: Ref2Spec | None = None) -> dict[str, dict[str, np.ndarray]]:
    """Build frozen bank plans without rendering or opening a reserved world."""

    spec = spec or Ref2Spec()
    plans: dict[str, dict[str, np.ndarray]] = {}
    mobile_parts = {name: [] for name in ("current_angle_deg", "command_targets_deg", "horizon", "signed_amplitude_deg", "angle_bin")}
    micro_parts = {name: [] for name in mobile_parts}
    rng = np.random.default_rng(141_000_000 + int(seed))
    for angle_bin, center in enumerate(STRUCTURED_CENTERS_DEG):
        mobile = _one_bin_motion(rng, center, spec.pairs_per_bin, micro=False)
        micro = _one_bin_motion(rng, center, spec.pairs_per_bin, micro=True)
        for key in mobile_parts:
            if key == "angle_bin":
                mobile_parts[key].append(np.full(spec.pairs_per_bin, angle_bin, dtype=np.int8))
                micro_parts[key].append(np.full(spec.pairs_per_bin, angle_bin, dtype=np.int8))
            else:
                mobile_parts[key].append(mobile[key])
                micro_parts[key].append(micro[key])
    mobile_base = {key: np.concatenate(value) for key, value in mobile_parts.items()}
    micro_base = {key: np.concatenate(value) for key, value in micro_parts.items()}
    size = len(mobile_base["horizon"])

    for bank_index, kind in enumerate(MOBILE_MATCHED_BANKS):
        bank_rng = np.random.default_rng(142_000_000 + seed * 10 + bank_index)
        order = bank_rng.permutation(size)
        plans[kind] = {key: value[order].copy() for key, value in mobile_base.items()}

    for bank_index, kind in enumerate(("micro_self_calibration", "micro_self_test")):
        bank_rng = np.random.default_rng(143_000_000 + seed * 10 + bank_index)
        order = bank_rng.permutation(size)
        plans[kind] = {key: value[order].copy() for key, value in micro_base.items()}

    external_rng = np.random.default_rng(144_000_000 + seed)
    external_current = np.concatenate(
        [
            center + external_rng.uniform(-4.0, 4.0, size=spec.pairs_per_bin)
            for center in STRUCTURED_CENTERS_DEG
        ]
    ).astype(np.float32)
    external_horizon = np.resize(np.arange(1, MAX_HORIZON + 1, dtype=np.int8), size)
    external_targets = np.repeat(external_current[:, None], MAX_HORIZON, axis=1)
    plans["external_only"] = {
        "current_angle_deg": external_current,
        "command_targets_deg": external_targets.astype(np.float32),
        "horizon": external_horizon,
        "signed_amplitude_deg": np.zeros(size, dtype=np.float32),
        "angle_bin": np.repeat(np.arange(6, dtype=np.int8), spec.pairs_per_bin),
    }

    validation_rng = np.random.default_rng(145_000_000 + seed)
    validation_order = validation_rng.permutation(size)
    plans["learner_validation"] = {
        key: value[validation_order].copy() for key, value in mobile_base.items()
    }
    return plans


def matched_motion_signature(plan: dict[str, np.ndarray], angle_bin: int) -> list[tuple[float, float, int]]:
    selected = np.asarray(plan["angle_bin"]) == angle_bin
    current = np.asarray(plan["current_angle_deg"])[selected]
    amplitude = np.asarray(plan["signed_amplitude_deg"])[selected]
    horizon = np.asarray(plan["horizon"])[selected]
    return sorted(
        (round(float(start), 6), round(float(delta), 6), int(span))
        for start, delta, span in zip(current, amplitude, horizon)
    )


def counterfactual_permutation(plan: dict[str, np.ndarray], *, seed: int) -> np.ndarray:
    """Opposite-sign derangement within (bin, horizon, unsigned amplitude)."""

    angle_bin = np.asarray(plan["angle_bin"])
    horizon = np.asarray(plan["horizon"])
    amplitude = np.asarray(plan["signed_amplitude_deg"])
    result = np.full(len(amplitude), -1, dtype=np.int64)
    rng = np.random.default_rng(seed)
    keys = sorted({(int(b), int(h), float(abs(a))) for b, h, a in zip(angle_bin, horizon, amplitude)})
    for key in keys:
        selected = np.flatnonzero(
            (angle_bin == key[0]) & (horizon == key[1]) & (np.abs(amplitude) == key[2])
        )
        negative = selected[amplitude[selected] < 0]
        positive = selected[amplitude[selected] > 0]
        if len(negative) != len(positive) or len(negative) == 0:
            raise ValueError(f"counterfactual stratum is not sign-balanced: {key}")
        rng.shuffle(negative)
        rng.shuffle(positive)
        result[negative] = positive
        result[positive] = negative
    if np.any(result < 0) or np.any(result == np.arange(len(result))):
        raise RuntimeError("counterfactual mapping is not a complete derangement")
    return result


def independent_corpus_plan(seed: int, spec: Ref2Spec) -> dict[str, np.ndarray]:
    action_rng = np.random.default_rng(151_000_000 + seed)
    episode_rng = np.random.default_rng(152_000_000 + seed)
    mobile_episodes = np.zeros(spec.episodes, dtype=bool)
    mobile_episodes[episode_rng.choice(spec.episodes, spec.episodes // 2, replace=False)] = True
    targets = np.empty(spec.decisions, dtype=np.float32)
    current = 90.0
    for index in range(spec.decisions):
        current = _bounded_reflect(current + float(action_rng.uniform(-18.0, 18.0)), 12.0, 168.0)
        targets[index] = current
    action_delta = np.diff(np.concatenate(([90.0], targets.astype(np.float64))))
    decision_episode = np.repeat(np.arange(spec.episodes), spec.decisions_per_episode)
    for attempt in range(10_000):
        object_rng = np.random.default_rng(153_000_000 + seed * 10_000 + attempt)
        positions = np.zeros(spec.decisions, dtype=np.float32)
        position = 0.0
        for index, episode in enumerate(decision_episode):
            if mobile_episodes[episode]:
                position = _bounded_reflect(
                    position + float(object_rng.uniform(-0.045, 0.045)),
                    -0.20,
                    0.20,
                )
            positions[index] = position
        object_delta = np.diff(np.concatenate(([0.0], positions.astype(np.float64))))
        correlation = _correlation(action_delta, object_delta)
        if abs(correlation) <= 0.045 and np.std(object_delta) > 0:
            return {
                "targets_deg": targets,
                "action_delta_deg": action_delta.astype(np.float32),
                "object_position_m": positions,
                "object_delta_m": object_delta.astype(np.float32),
                "mobile_episodes": mobile_episodes,
                "correlation": np.asarray(correlation),
            }
    raise RuntimeError("could not build independent REF2 corpus motion")


def load_corpus(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as stored:
        return {name: np.array(stored[name]) for name in stored.files}


def _validate_corpus(data: dict[str, np.ndarray], spec: Ref2Spec) -> None:
    required = {
        "frames",
        "requested_deg",
        "as5600_deg",
        "episode",
        "decision_action_delta_deg",
        "decision_object_delta_m",
        "object_displacement_m",
        "episode_object_mobile",
    }
    if not required.issubset(data):
        raise RuntimeError(f"REF2 corpus missing {sorted(required - set(data))}")
    if data["frames"].shape != (spec.images, spec.image_size, spec.image_size, 3):
        raise RuntimeError("REF2 corpus image budget diverges")
    if any(len(data[name]) != spec.images for name in ("requested_deg", "as5600_deg", "episode")):
        raise RuntimeError("REF2 corpus per-frame arrays diverge")
    correlation = _correlation(
        data["decision_action_delta_deg"],
        data["decision_object_delta_m"],
    )
    if not np.isfinite(correlation) or abs(correlation) > 0.05:
        raise RuntimeError(f"REF2 corpus independence failed: {correlation}")


def generate_corpus(seed: int, path: Path, spec: Ref2Spec) -> dict:
    if path.exists():
        data = load_corpus(path)
        _validate_corpus(data, spec)
        return {"path": str(path), "sha256": _sha256(path), "images": spec.images}
    from sim3d.bench_env import BenchHeadEnv

    plan = independent_corpus_plan(seed, spec)
    frames: list[np.ndarray] = []
    requested: list[float] = []
    actual: list[float] = []
    episodes: list[int] = []
    object_positions: list[float] = []
    decision_index = 0
    for episode in range(spec.episodes):
        env = BenchHeadEnv(
            ref2_bench_config(
                154_000_000 + seed * 100 + episode,
                bearing_deg=82.0,
                context=episode % 2,
            )
        )
        try:
            previous_object = (
                0.0
                if decision_index == 0
                else float(plan["object_position_m"][decision_index - 1])
            )
            env.set_external_object_displacement(previous_object)
            for _ in range(spec.decisions_per_episode):
                target = float(plan["targets_deg"][decision_index])
                end_object = float(plan["object_position_m"][decision_index])
                for subframe in range(5):
                    fraction = (subframe + 1) / 5.0
                    env.set_external_object_displacement(
                        previous_object + fraction * (end_object - previous_object)
                    )
                    observation = None
                    for _ in range(5):
                        observation = env.step(target)
                    frames.append(env.render_camera(spec.image_size, spec.image_size))
                    requested.append(target)
                    actual.append(float(observation.as5600_deg))
                    episodes.append(episode)
                    object_positions.append(env.external_object_displacement())
                previous_object = end_object
                decision_index += 1
        finally:
            env.close()
    data = {
        "frames": np.stack(frames).astype(np.uint8),
        "requested_deg": np.asarray(requested, dtype=np.float32),
        "as5600_deg": np.asarray(actual, dtype=np.float32),
        "episode": np.asarray(episodes, dtype=np.int16),
        "decision_action_delta_deg": plan["action_delta_deg"].astype(np.float32),
        "decision_object_delta_m": plan["object_delta_m"].astype(np.float32),
        "object_displacement_m": np.asarray(object_positions, dtype=np.float32),
        "episode_object_mobile": plan["mobile_episodes"].astype(bool),
    }
    _validate_corpus(data, spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **data)
    return {"path": str(path), "sha256": _sha256(path), "images": spec.images}


def _object_plan(seed: int, kind: str, motion: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    size = len(motion["horizon"])
    rng = np.random.default_rng(155_000_000 + seed * 10 + BANKS.index(kind))
    starts = rng.uniform(-0.13, 0.13, size=size).astype(np.float32)
    deltas = np.zeros(size, dtype=np.float32)
    if kind in {"external_only", "mixed"}:
        deltas = _balanced_signed_values(rng.uniform(0.05, 0.16, size=size), rng)
    elif kind == "learner_validation":
        selected = np.arange(size) % 3 != 0
        values = _balanced_signed_values(rng.uniform(0.05, 0.16, size=int(np.sum(selected))), rng)
        deltas[selected] = values
    ends = np.clip(starts + deltas, -0.19, 0.19)
    deltas = ends - starts
    if kind == "mixed":
        for _ in range(10_000):
            correlation = _correlation(motion["signed_amplitude_deg"], deltas)
            if abs(correlation) <= 0.045:
                break
            rng.shuffle(deltas)
            ends = np.clip(starts + deltas, -0.19, 0.19)
            deltas = ends - starts
        else:
            raise RuntimeError("could not build independent REF2 mixed object motion")
    return starts.astype(np.float32), ends.astype(np.float32)


def _validate_bank(bank: Ref2Bank, kind: str, spec: Ref2Spec) -> None:
    expected = len(STRUCTURED_CENTERS_DEG) * spec.pairs_per_bin
    if len(bank) != expected or bank.frames_start.shape[1:] != (64, 64, 3):
        raise RuntimeError(f"REF2 {kind} bank shape diverges")
    recomputed = build_motor_input(
        bank.current_angle_deg,
        bank.command_targets_deg,
        bank.horizon,
    )
    if not np.array_equal(recomputed, bank.motor_input):
        raise RuntimeError(f"REF2 {kind} motor input is not recomputable")
    for angle_bin in range(6):
        selected = bank.angle_bins == angle_bin
        if int(np.sum(selected)) != spec.pairs_per_bin:
            raise RuntimeError(f"REF2 {kind} bin {angle_bin} is unbalanced")
        contexts = [int(np.sum(selected & (bank.contexts == value))) for value in (0, 1)]
        if contexts != [spec.pairs_per_bin // 2] * 2:
            raise RuntimeError(f"REF2 {kind} context balance diverges")
    if kind in {"moving_self_calibration", "moving_self_test", "micro_self_calibration", "micro_self_test"}:
        if np.any(bank.head_delta_deg == 0) or np.any(bank.object_delta_m != 0):
            raise RuntimeError(f"REF2 {kind} violates self-motion structure")
    if kind == "external_only" and (
        np.any(bank.head_delta_deg != 0) or np.any(bank.object_delta_m == 0)
    ):
        raise RuntimeError("REF2 external_only structure diverges")


def generate_bank(seed: int, kind: str, path: Path, spec: Ref2Spec) -> Ref2Bank:
    if kind not in BANKS:
        raise ValueError(f"unknown REF2 bank: {kind}")
    if path.exists():
        bank = Ref2Bank.load(path)
        _validate_bank(bank, kind, spec)
        return bank
    from sim3d.bench_env import BenchHeadEnv

    motion = build_matched_motion_plans(seed, spec)[kind]
    object_start, object_end = _object_plan(seed, kind, motion)
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    current_angles: list[float] = []
    commands: list[np.ndarray] = []
    horizons: list[int] = []
    angle_bins: list[int] = []
    contexts: list[int] = []
    head_deltas: list[float] = []
    object_deltas: list[float] = []
    labels: list[str] = []
    planned_amplitudes: list[float] = []
    for angle_bin, center in enumerate(STRUCTURED_CENTERS_DEG):
        bin_indices = np.flatnonzero(motion["angle_bin"] == angle_bin)
        for context in (0, 1):
            chosen = bin_indices[context::2]
            room_seed = (
                156_000_000
                + seed * 10_000
                + BANKS.index(kind) * 1_000
                + angle_bin * 10
                + context
            )
            env = BenchHeadEnv(ref2_bench_config(room_seed, center + 8.0, context))
            try:
                for index in chosen:
                    start_angle = float(motion["current_angle_deg"][index])
                    target_sequence = motion["command_targets_deg"][index]
                    span = int(motion["horizon"][index])
                    env.set_external_object_displacement(float(object_start[index]))
                    for _ in range(20):
                        start_observation = env.step(start_angle)
                    start_frame = env.render_camera(64, 64)
                    for step in range(span):
                        fraction = (step + 1) / span
                        env.set_external_object_displacement(
                            float(
                                object_start[index]
                                + fraction * (object_end[index] - object_start[index])
                            )
                        )
                        for _ in range(5):
                            end_observation = env.step(float(target_sequence[step]))
                    end_frame = env.render_camera(64, 64)
                    starts.append(start_frame)
                    ends.append(end_frame)
                    current_angles.append(float(start_observation.as5600_deg))
                    commands.append(target_sequence.astype(np.float32))
                    horizons.append(span)
                    planned_amplitudes.append(float(motion["signed_amplitude_deg"][index]))
                    angle_bins.append(angle_bin)
                    contexts.append(context)
                    head_deltas.append(
                        float(end_observation.as5600_deg - start_observation.as5600_deg)
                    )
                    object_deltas.append(float(object_end[index] - object_start[index]))
                    labels.append(kind)
            finally:
                env.close()
    current_array = np.asarray(current_angles, dtype=np.float32)
    command_array = np.stack(commands).astype(np.float32)
    horizon_array = np.asarray(horizons, dtype=np.int8)
    bank = Ref2Bank(
        frames_start=np.stack(starts).astype(np.uint8),
        frames_end=np.stack(ends).astype(np.uint8),
        current_angle_deg=current_array,
        command_targets_deg=command_array,
        motor_input=build_motor_input(current_array, command_array, horizon_array),
        horizon=horizon_array,
        planned_signed_amplitude_deg=np.asarray(planned_amplitudes, dtype=np.float32),
        angle_bins=np.asarray(angle_bins, dtype=np.int8),
        contexts=np.asarray(contexts, dtype=np.int8),
        head_delta_deg=np.asarray(head_deltas, dtype=np.float32),
        object_delta_m=np.asarray(object_deltas, dtype=np.float32),
        labels=np.asarray(labels, dtype="U32"),
    )
    _validate_bank(bank, kind, spec)
    bank.save(path)
    return bank


def prepare_seed(seed: int, root: Path, spec: Ref2Spec) -> dict:
    started = time.perf_counter()
    corpus = generate_corpus(seed, corpus_path(root, seed), spec)
    banks = {}
    for kind in BANKS:
        bank = generate_bank(seed, kind, bank_path(root, seed, kind), spec)
        banks[kind] = {
            "path": str(bank_path(root, seed, kind)),
            "sha256": _sha256(bank_path(root, seed, kind)),
            "pairs": len(bank),
        }
    payload = {
        "seed": seed,
        "spec_digest": spec.digest(),
        "corpus": corpus,
        "banks": banks,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(root / "manifests" / f"seed_{seed}.json", payload)
    return payload


def _require_torch() -> None:
    if torch is None or nn is None or functional is None:
        raise ModuleNotFoundError("learning.reafference_002 requires PyTorch")


def build_motor_input(
    current_angle_deg: np.ndarray,
    command_targets_deg: np.ndarray,
    horizon: np.ndarray,
    *,
    max_horizon: int = MAX_HORIZON,
) -> np.ndarray:
    """Build the motor tensor using pre-transition fields only.

    Shapes are `(N,)`, `(N, max_horizon)`, `(N,)`. Commands after each
    sample's horizon are masked to zero. No realised/future angle is accepted
    by this function's contract.
    """

    current = np.asarray(current_angle_deg, dtype=np.float32)
    targets = np.asarray(command_targets_deg, dtype=np.float32)
    horizons = np.asarray(horizon, dtype=np.int64)
    if current.ndim != 1 or targets.shape != (len(current), max_horizon):
        raise ValueError("invalid current-angle or command-target shape")
    if horizons.shape != current.shape or np.any(horizons < 1) or np.any(horizons > max_horizon):
        raise ValueError("horizon must be in [1, max_horizon]")
    errors = (targets - current[:, None]) / np.float32(ANGLE_RANGE_DEG)
    mask = np.arange(max_horizon)[None, :] < horizons[:, None]
    errors = np.where(mask, errors, np.float32(0.0))
    current_norm = (current - np.float32(90.0)) / np.float32(80.0)
    horizon_norm = horizons.astype(np.float32) / np.float32(max_horizon)
    return np.concatenate((current_norm[:, None], errors, horizon_norm[:, None]), axis=1).astype(
        np.float32,
        copy=False,
    )


def zero_command_component(motor_input):
    """Preserve current angle and horizon while removing command errors."""

    _require_torch()
    result = motor_input.clone()
    result[:, 1 : 1 + MAX_HORIZON] = 0
    return result


if nn is not None:

    class SpatialEncoder(nn.Module):
        """64×64 RGB frame -> 8×8×128 feature map."""

        def __init__(self, width: int = 32):
            super().__init__()
            self.layers = nn.Sequential(
                nn.Conv2d(3, width, kernel_size=4, stride=2, padding=1),
                nn.GELU(),
                nn.Conv2d(width, width * 2, kernel_size=4, stride=2, padding=1),
                nn.GELU(),
                nn.Conv2d(width * 2, width * 4, kernel_size=4, stride=2, padding=1),
                nn.GELU(),
            )

        def forward(self, frames):
            return self.layers(frames)


    class SpatialReafferenceJEPA(nn.Module):
        """Equal-capacity spatial predictor under one of three frozen conditions."""

        def __init__(
            self,
            condition: Condition,
            *,
            width: int = 32,
            motor_hidden: int = 64,
            motor_channels: int = 16,
            max_horizon: int = MAX_HORIZON,
        ):
            super().__init__()
            if condition not in CONDITIONS:
                raise ValueError(f"unsupported REF-002 condition: {condition}")
            self.condition = condition
            self.max_horizon = max_horizon
            map_channels = width * 4
            motor_input_dim = max_horizon + 2
            self.encoder = SpatialEncoder(width)
            self.motor_adapter = nn.Sequential(
                nn.Linear(motor_input_dim, motor_hidden),
                nn.GELU(),
                nn.Linear(motor_hidden, motor_channels),
            )
            self.residual = nn.Sequential(
                nn.Conv2d(map_channels + motor_channels, map_channels, kernel_size=3, padding=1),
                nn.GELU(),
                nn.Conv2d(map_channels, map_channels, kernel_size=3, padding=1),
            )

        def encode_map(self, frames):
            return self.encoder(frames)

        @staticmethod
        def _identity_grid(batch: int, height: int, width: int, *, device, dtype):
            y, x = torch.meshgrid(
                torch.linspace(-1, 1, height, device=device, dtype=dtype),
                torch.linspace(-1, 1, width, device=device, dtype=dtype),
                indexing="ij",
            )
            return torch.stack((x, y), dim=-1).unsqueeze(0).expand(batch, -1, -1, -1).clone()

        def transport_map(self, feature_map, displacement_cells):
            batch, _, height, width = feature_map.shape
            grid = self._identity_grid(
                batch,
                height,
                width,
                device=feature_map.device,
                dtype=feature_map.dtype,
            )
            # align_corners=True: two normalized units span width-1 cell intervals.
            grid[..., 0] -= displacement_cells[:, None, None] * (2.0 / max(1, width - 1))
            warped = functional.grid_sample(
                feature_map,
                grid,
                mode="bilinear",
                padding_mode="zeros",
                align_corners=True,
            )
            zero = (displacement_cells == 0)[:, None, None, None]
            return torch.where(zero, feature_map, warped)

        def predictor_input(self, current_map, motor_input):
            if self.condition == "no_command_jepa":
                motor_input = zero_command_component(motor_input)
            embedding = self.motor_adapter(motor_input)
            signed_mean = motor_input[:, 1 : 1 + self.max_horizon].mean(dim=1)
            displacement = torch.tanh(embedding[:, 0]) * signed_mean * (current_map.shape[-1] - 1)
            if self.condition == "transport_jepa":
                base = self.transport_map(current_map, displacement)
            else:
                # Execute the same differentiable sampler for compute fairness,
                # while fixing the control warp to the exact identity.
                base = self.transport_map(current_map, torch.zeros_like(displacement))
            motor_fields = embedding[:, :, None, None].expand(
                -1, -1, current_map.shape[-2], current_map.shape[-1]
            )
            return torch.cat((base, motor_fields), dim=1)

        def predict_map(self, current_map, motor_input):
            predictor_input = self.predictor_input(current_map, motor_input)
            return current_map + self.residual(predictor_input)

        def forward(self, frames, motor_input):
            current_map = self.encode_map(frames)
            return current_map, self.predict_map(current_map, motor_input)


else:

    class SpatialEncoder:
        def __init__(self, *args, **kwargs):
            _require_torch()


    class SpatialReafferenceJEPA:
        def __init__(self, *args, **kwargs):
            _require_torch()


def spatial_score(predicted_map, current_map, target_map):
    _require_torch()
    prediction_error = torch.mean((predicted_map - target_map) ** 2, dim=(1, 2, 3))
    copy_error = torch.mean((current_map - target_map) ** 2, dim=(1, 2, 3))
    score = prediction_error / torch.clamp(prediction_error + copy_error, min=1e-8)
    return score, prediction_error, copy_error


def pooled_vicreg_latent(feature_map):
    """The amended common 128-vector reduction for variance/covariance."""

    _require_torch()
    return torch.mean(feature_map, dim=(2, 3))


def predicted_servo_displacement_deg(
    current_angle_deg: np.ndarray,
    command_targets_deg: np.ndarray,
    horizon: np.ndarray,
    *,
    max_speed_deg_s: float = 600.0,
    control_dt: float = 0.02,
) -> np.ndarray:
    """Frozen rate-limited yaw predictor; uses no realised future angle."""

    current = np.asarray(current_angle_deg, dtype=np.float64)
    targets = np.asarray(command_targets_deg, dtype=np.float64)
    horizons = np.asarray(horizon, dtype=np.int64)
    if current.ndim != 1 or targets.ndim != 2 or targets.shape[0] != len(current):
        raise ValueError("invalid servo predictor shapes")
    if horizons.shape != current.shape or np.any(horizons < 1) or np.any(horizons > targets.shape[1]):
        raise ValueError("invalid servo predictor horizon")
    predicted = current.copy()
    maximum_delta = float(max_speed_deg_s * control_dt)
    for step in range(targets.shape[1]):
        active = step < horizons
        delta = np.clip(targets[:, step] - predicted, -maximum_delta, maximum_delta)
        predicted = np.where(active, predicted + delta, predicted)
    return predicted - current


@dataclass(frozen=True)
class YawWarpResult:
    warped: np.ndarray
    valid_mask: np.ndarray
    predicted_delta_deg: np.ndarray


def yaw_warp(
    frames: np.ndarray,
    current_angle_deg: np.ndarray,
    command_targets_deg: np.ndarray,
    horizon: np.ndarray,
    *,
    vertical_fov_deg: float = 30.0,
) -> YawWarpResult:
    """Inverse-projective deterministic RGB yaw warp with bilinear sampling."""

    images = np.asarray(frames)
    if images.ndim != 4 or images.shape[-1] != 3 or images.shape[1] != images.shape[2]:
        raise ValueError("yaw_warp expects NHWC square RGB frames")
    batch, height, width, _ = images.shape
    if height != 64 or width != 64:
        raise ValueError("REF-002 yaw_warp is frozen for 64x64 frames")
    delta_deg = predicted_servo_displacement_deg(
        current_angle_deg,
        command_targets_deg,
        horizon,
    )
    focal = (height / 2.0) / math.tan(math.radians(vertical_fov_deg / 2.0))
    center_x = (width - 1.0) / 2.0
    center_y = (height - 1.0) / 2.0
    output = np.zeros_like(images, dtype=np.float32)
    valid = np.zeros((batch, height, width), dtype=bool)
    source = images.astype(np.float32, copy=False)
    yy, xx = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    ray_x_out = (xx - center_x) / focal
    ray_y_out = (yy - center_y) / focal

    for index in range(batch):
        if delta_deg[index] == 0:
            output[index] = source[index]
            valid[index] = True
            continue
        angle = math.radians(float(delta_deg[index]))
        cosine, sine = math.cos(angle), math.sin(angle)
        # Inverse mapping from target-camera rays to the current source frame.
        denominator = cosine - ray_x_out * sine
        ray_x_source = (ray_x_out * cosine + sine) / denominator
        ray_y_source = ray_y_out / denominator
        source_x = focal * ray_x_source + center_x
        source_y = focal * ray_y_source + center_y
        mask = (
            (denominator > 0)
            & (source_x >= 0)
            & (source_x <= width - 1)
            & (source_y >= 0)
            & (source_y <= height - 1)
        )
        x0 = np.clip(np.floor(source_x).astype(np.int64), 0, width - 1)
        y0 = np.clip(np.floor(source_y).astype(np.int64), 0, height - 1)
        x1 = np.clip(x0 + 1, 0, width - 1)
        y1 = np.clip(y0 + 1, 0, height - 1)
        wx = (source_x - x0)[..., None]
        wy = (source_y - y0)[..., None]
        interpolated = (
            source[index, y0, x0] * (1 - wx) * (1 - wy)
            + source[index, y0, x1] * wx * (1 - wy)
            + source[index, y1, x0] * (1 - wx) * wy
            + source[index, y1, x1] * wx * wy
        )
        output[index] = np.where(mask[..., None], interpolated, 0)
        valid[index] = mask
    return YawWarpResult(output, valid, delta_deg)


def yaw_warp_error(warped: np.ndarray, target: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    left = np.asarray(warped, dtype=np.float64) / 255.0
    right = np.asarray(target, dtype=np.float64) / 255.0
    mask = np.asarray(valid_mask, dtype=bool)
    if left.shape != right.shape or mask.shape != left.shape[:3]:
        raise ValueError("warp error shapes do not match")
    pixel_error = np.mean(np.abs(left - right), axis=-1)
    counts = np.sum(mask, axis=(1, 2))
    if np.any(counts == 0):
        raise ValueError("yaw warp has an empty valid mask")
    return np.sum(pixel_error * mask, axis=(1, 2)) / counts


def make_learner(seed: int, condition: Condition, spec: Ref2Spec, device):
    _require_torch()
    if condition not in CONDITIONS:
        raise ValueError(f"unknown REF2 condition: {condition}")
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
    model = SpatialReafferenceJEPA(
        condition,
        width=spec.encoder_width,
        motor_hidden=spec.motor_hidden,
        motor_channels=spec.motor_channels,
        max_horizon=spec.max_horizon,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=spec.lr,
        weight_decay=spec.weight_decay,
    )
    return model, optimizer


def state_digest(model) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def encoder_digest(model) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.encoder.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def parameter_counts(model) -> dict[str, int]:
    return {
        "total": int(sum(parameter.numel() for parameter in model.parameters())),
        "trainable": int(
            sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
        ),
    }


def _corpus_motor_input(
    data: dict[str, np.ndarray],
    indices: np.ndarray,
    horizon_value: int,
    max_horizon: int,
) -> np.ndarray:
    targets = np.zeros((len(indices), max_horizon), dtype=np.float32)
    for step in range(horizon_value):
        targets[:, step] = data["requested_deg"][indices + step + 1]
    horizons = np.full(len(indices), horizon_value, dtype=np.int64)
    return build_motor_input(
        data["as5600_deg"][indices],
        targets,
        horizons,
        max_horizon=max_horizon,
    )


def _model_scores(
    model,
    bank: Ref2Bank,
    spec: Ref2Spec,
    device,
    *,
    motor_input: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    scores: list[np.ndarray] = []
    predictions: list[np.ndarray] = []
    copies: list[np.ndarray] = []
    inputs = bank.motor_input if motor_input is None else motor_input
    model.eval()
    with torch.no_grad():
        for start in range(0, len(bank), spec.batch_size):
            selected = slice(start, start + spec.batch_size)
            frame_start = (
                torch.from_numpy(bank.frames_start[selected])
                .to(device)
                .permute(0, 3, 1, 2)
                .float()
                .div_(255.0)
            )
            frame_end = (
                torch.from_numpy(bank.frames_end[selected])
                .to(device)
                .permute(0, 3, 1, 2)
                .float()
                .div_(255.0)
            )
            motor = torch.from_numpy(inputs[selected]).to(device)
            current_map = model.encode_map(frame_start)
            target_map = model.encode_map(frame_end)
            prediction = model.predict_map(current_map, motor)
            score, prediction_error, copy_error = spatial_score(
                prediction,
                current_map,
                target_map,
            )
            scores.append(score.cpu().numpy())
            predictions.append(prediction_error.cpu().numpy())
            copies.append(copy_error.cpu().numpy())
    return (
        np.concatenate(scores).astype(np.float64),
        np.concatenate(predictions).astype(np.float64),
        np.concatenate(copies).astype(np.float64),
    )


def pixel_change(bank: Ref2Bank) -> np.ndarray:
    return (
        np.mean(
            np.abs(bank.frames_end.astype(np.float32) - bank.frames_start.astype(np.float32)),
            axis=(1, 2, 3),
            dtype=np.float64,
        )
        / 255.0
    )


def _yaw_scores(bank: Ref2Bank) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    result = yaw_warp(
        bank.frames_start,
        bank.current_angle_deg,
        bank.command_targets_deg,
        bank.horizon,
    )
    return (
        yaw_warp_error(result.warped, bank.frames_end, result.valid_mask),
        np.mean(result.valid_mask, axis=(1, 2), dtype=np.float64),
        result.predicted_delta_deg,
    )


def _counterfactual_motor_inputs(
    bank: Ref2Bank,
    *,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    plan = {
        "angle_bin": bank.angle_bins,
        "horizon": bank.horizon,
        "signed_amplitude_deg": bank.planned_signed_amplitude_deg,
    }
    mapping = counterfactual_permutation(plan, seed=seed)
    permuted_targets = bank.command_targets_deg[mapping]
    permuted = build_motor_input(
        bank.current_angle_deg,
        permuted_targets,
        bank.horizon,
    )
    inverted_targets = (
        2.0 * bank.current_angle_deg[:, None] - bank.command_targets_deg
    ).astype(np.float32)
    inverted = build_motor_input(
        bank.current_angle_deg,
        inverted_targets,
        bank.horizon,
    )
    return permuted, inverted, mapping


def _raw_scores_and_h5(model, banks: dict[str, Ref2Bank], spec: Ref2Spec, device, seed: int):
    scoring_started = time.perf_counter()
    raw = {}
    for kind, bank in banks.items():
        score, prediction_error, copy_error = _model_scores(model, bank, spec, device)
        raw[kind] = {
            "score": score.tolist(),
            "prediction_mse": prediction_error.tolist(),
            "copy_mse": copy_error.tolist(),
        }
    scoring_seconds = time.perf_counter() - scoring_started
    h5_started = time.perf_counter()
    bank = banks["moving_self_test"]
    permuted, inverted, mapping = _counterfactual_motor_inputs(
        bank,
        seed=202_607_2601 + seed,
    )
    normal = np.asarray(raw["moving_self_test"]["score"], dtype=np.float64)
    permuted_score, _, _ = _model_scores(
        model,
        bank,
        spec,
        device,
        motor_input=permuted,
    )
    inverted_score, _, _ = _model_scores(
        model,
        bank,
        spec,
        device,
        motor_input=inverted,
    )
    h5_seconds = time.perf_counter() - h5_started
    return raw, {
        "normal": normal.tolist(),
        "permuted": permuted_score.tolist(),
        "inverted": inverted_score.tolist(),
        "mapping_sha256": hashlib.sha256(mapping.tobytes()).hexdigest(),
    }, scoring_seconds, h5_seconds


def train_condition(
    seed: int,
    condition: Condition,
    root: Path,
    spec: Ref2Spec,
    device,
    deadline: float | None = None,
) -> dict:
    result_file = run_path(root, seed, condition)
    checkpoint_file = checkpoint_path(root, seed, condition)
    if result_file.exists() and checkpoint_file.exists():
        result = json.loads(result_file.read_text(encoding="utf-8"))
        if result.get("status") == "complete" and result.get("spec_digest") == spec.digest():
            return result
    data = load_corpus(corpus_path(root, seed))
    banks = {kind: Ref2Bank.load(bank_path(root, seed, kind)) for kind in BANKS}
    model, optimizer = make_learner(seed, condition, spec, device)
    initial_state = state_digest(model)
    initial_encoder = encoder_digest(model)
    initial_validation = float(
        np.mean(_model_scores(model, banks["learner_validation"], spec, device)[0])
    )
    pairs_by_horizon = build_pairs_multi(data["episode"], spec.max_horizon)
    rng = np.random.default_rng(161_000_000 + seed)
    batch_digest = hashlib.sha256()
    autocast_dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    training_started = time.perf_counter()
    loss_sum = 0.0
    nonzero_gradient_parameters = None
    for step in range(spec.optimizer_steps):
        if deadline is not None and time.perf_counter() >= deadline:
            raise TimeoutError("REF-002 wall-time cap reached during training")
        horizon_value = int(rng.integers(1, spec.max_horizon + 1))
        pool = pairs_by_horizon[horizon_value]
        indices = pool[rng.integers(0, len(pool), size=spec.batch_size)]
        batch_digest.update(np.asarray([horizon_value], dtype=np.int8).tobytes())
        batch_digest.update(indices.astype(np.int32).tobytes())
        frame_start = (
            torch.from_numpy(data["frames"][indices])
            .to(device)
            .permute(0, 3, 1, 2)
            .float()
            .div_(255.0)
        )
        frame_end = (
            torch.from_numpy(data["frames"][indices + horizon_value])
            .to(device)
            .permute(0, 3, 1, 2)
            .float()
            .div_(255.0)
        )
        motor = torch.from_numpy(
            _corpus_motor_input(data, indices, horizon_value, spec.max_horizon)
        ).to(device)
        with torch.autocast(
            device_type=device.type,
            dtype=autocast_dtype,
            enabled=device.type == "cuda",
        ):
            current_map = model.encode_map(frame_start)
            target_map = model.encode_map(frame_end)
            prediction = model.predict_map(current_map, motor)
            prediction_loss = torch.mean((prediction - target_map.detach()) ** 2)
            current_pooled = pooled_vicreg_latent(current_map)
            target_pooled = pooled_vicreg_latent(target_map)
            regularizer = spec.variance_weight * 0.5 * (
                variance_loss(current_pooled) + variance_loss(target_pooled)
            )
            regularizer = regularizer + spec.covariance_weight * 0.5 * (
                covariance_loss(current_pooled) + covariance_loss(target_pooled)
            )
            loss = prediction_loss + regularizer
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if step == 0:
            nonzero_gradient_parameters = int(
                sum(
                    parameter.numel()
                    for parameter in model.parameters()
                    if parameter.grad is not None and torch.any(parameter.grad != 0)
                )
            )
        optimizer.step()
        loss_sum += float(loss.item())
    training_seconds = time.perf_counter() - training_started
    final_validation = float(
        np.mean(_model_scores(model, banks["learner_validation"], spec, device)[0])
    )
    raw, h5, scoring_seconds, h5_seconds = _raw_scores_and_h5(
        model,
        banks,
        spec,
        device,
        seed,
    )
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": {
                name: value.detach().cpu() for name, value in model.state_dict().items()
            },
            "seed": seed,
            "condition": condition,
            "spec": asdict(spec),
        },
        checkpoint_file,
    )
    counts = parameter_counts(model)
    result = {
        "status": "complete",
        "seed": seed,
        "condition": condition,
        "spec_digest": spec.digest(),
        "corpus_sha256": _sha256(corpus_path(root, seed)),
        "bank_sha256": {kind: _sha256(bank_path(root, seed, kind)) for kind in BANKS},
        "initial_state_digest": initial_state,
        "initial_encoder_digest": initial_encoder,
        "batch_order_digest": batch_digest.hexdigest(),
        "parameter_count": counts["total"],
        "trainable_parameter_count": counts["trainable"],
        "nonzero_gradient_parameter_count": nonzero_gradient_parameters,
        "optimizer_steps": spec.optimizer_steps,
        "batch_size": spec.batch_size,
        "examples_gradient": spec.optimizer_steps * spec.batch_size,
        "mean_train_loss": loss_sum / spec.optimizer_steps,
        "learner_validation_initial": initial_validation,
        "learner_validation_final": final_validation,
        "learner_relative_reduction": (
            (initial_validation - final_validation) / max(initial_validation, 1e-12)
        ),
        "scores": raw,
        "h5": h5,
        "timing": {
            "training_seconds": training_seconds,
            "scoring_seconds": scoring_seconds,
            "h5_seconds": h5_seconds,
            "complete_condition_seconds": training_seconds + scoring_seconds + h5_seconds,
        },
        "checkpoint": str(checkpoint_file),
    }
    _write_json(result_file, result)
    return result


def calibration_threshold(scores: np.ndarray) -> float:
    values = np.sort(np.asarray(scores, dtype=np.float64))
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("calibration scores must be non-empty and finite")
    allowed_above = int(math.floor(0.05 * values.size))
    return float(values[max(0, values.size - allowed_above - 1)])


def evaluate_seed(seed: int, root: Path, spec: Ref2Spec) -> dict:
    evaluation_started = time.perf_counter()
    results = {
        condition: json.loads(run_path(root, seed, condition).read_text(encoding="utf-8"))
        for condition in CONDITIONS
    }
    banks = {kind: Ref2Bank.load(bank_path(root, seed, kind)) for kind in BANKS}
    methods = CONDITIONS + ("pixel_change", "yaw_warp")
    scores: dict[str, dict[str, np.ndarray]] = {method: {} for method in methods}
    copies: dict[str, dict[str, np.ndarray]] = {condition: {} for condition in CONDITIONS}
    predictions: dict[str, dict[str, np.ndarray]] = {
        condition: {} for condition in CONDITIONS
    }
    for condition in CONDITIONS:
        for kind in BANKS:
            exported = results[condition]["scores"][kind]
            scores[condition][kind] = np.asarray(exported["score"], dtype=np.float64)
            copies[condition][kind] = np.asarray(exported["copy_mse"], dtype=np.float64)
            predictions[condition][kind] = np.asarray(
                exported["prediction_mse"],
                dtype=np.float64,
            )
    valid_fractions = {}
    predicted_deltas = {}
    for kind, bank in banks.items():
        scores["pixel_change"][kind] = pixel_change(bank)
        yaw_score, valid_fraction, predicted_delta = _yaw_scores(bank)
        scores["yaw_warp"][kind] = yaw_score
        valid_fractions[kind] = valid_fraction
        predicted_deltas[kind] = predicted_delta
    thresholds = {method: {"moving": [], "micro": []} for method in methods}
    for method in methods:
        for angle_bin in range(6):
            moving = banks["moving_self_calibration"].angle_bins == angle_bin
            micro = banks["micro_self_calibration"].angle_bins == angle_bin
            thresholds[method]["moving"].append(
                calibration_threshold(scores[method]["moving_self_calibration"][moving])
            )
            thresholds[method]["micro"].append(
                calibration_threshold(scores[method]["micro_self_calibration"][micro])
            )
    rates = {method: {} for method in methods}
    for method in methods:
        for kind, threshold_kind in (
            ("moving_self_test", "moving"),
            ("mixed", "moving"),
            ("micro_self_test", "micro"),
            ("external_only", "micro"),
        ):
            by_bin = []
            for angle_bin in range(6):
                selected = banks[kind].angle_bins == angle_bin
                by_bin.append(
                    float(
                        np.mean(
                            scores[method][kind][selected]
                            > thresholds[method][threshold_kind][angle_bin]
                        )
                    )
                )
            rates[method][kind] = by_bin
    h5 = {}
    for condition in CONDITIONS:
        normal = np.asarray(results[condition]["h5"]["normal"], dtype=np.float64)
        permuted = np.asarray(results[condition]["h5"]["permuted"], dtype=np.float64)
        inverted = np.asarray(results[condition]["h5"]["inverted"], dtype=np.float64)
        h5[condition] = {
            "permuted_minus_normal_by_bin": [
                float(np.mean((permuted - normal)[banks["moving_self_test"].angle_bins == angle_bin]))
                for angle_bin in range(6)
            ],
            "inverted_minus_normal_by_bin": [
                float(np.mean((inverted - normal)[banks["moving_self_test"].angle_bins == angle_bin]))
                for angle_bin in range(6)
            ],
            "mapping_sha256": results[condition]["h5"]["mapping_sha256"],
        }
    payload = {
        "seed": seed,
        "spec_digest": spec.digest(),
        "thresholds": thresholds,
        "rates_by_bin": rates,
        "self_error_by_bin": {
            condition: [
                float(
                    np.mean(
                        scores[condition]["moving_self_test"][
                            banks["moving_self_test"].angle_bins == angle_bin
                        ]
                    )
                )
                for angle_bin in range(6)
            ]
            for condition in CONDITIONS
        },
        "h5": h5,
        "learner_guard": {
            condition: {
                "initial": results[condition]["learner_validation_initial"],
                "final": results[condition]["learner_validation_final"],
                "relative_reduction": results[condition]["learner_relative_reduction"],
                "passed": results[condition]["learner_relative_reduction"] >= 0.20,
            }
            for condition in CONDITIONS
        },
        "copy_diagnostics": {
            condition: {
                kind: {
                    "minimum": float(np.min(copies[condition][kind])),
                    "median": float(np.median(copies[condition][kind])),
                    "maximum": float(np.max(copies[condition][kind])),
                }
                for kind in BANKS
            }
            for condition in CONDITIONS
        },
        "prediction_diagnostics": {
            condition: {
                kind: {
                    "minimum": float(np.min(predictions[condition][kind])),
                    "median": float(np.median(predictions[condition][kind])),
                    "maximum": float(np.max(predictions[condition][kind])),
                }
                for kind in BANKS
            }
            for condition in CONDITIONS
        },
        "warp": {
            "valid_fraction_by_bank": {
                kind: valid_fractions[kind].tolist() for kind in BANKS
            },
            "predicted_delta_by_bank": {
                kind: predicted_deltas[kind].tolist() for kind in BANKS
            },
        },
        "elapsed_seconds": time.perf_counter() - evaluation_started,
    }
    _write_json(evaluation_path(root, seed), payload)
    return payload


def _paired_summary(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=np.float64)
    low, high = bca_bootstrap_ci(values, n_boot=10_000, seed=ANALYSIS_SEED)
    return {
        "values": values.tolist(),
        "mean": float(np.mean(values)),
        "ci_bca_95": [low, high],
        "p_exact_greater": exact_sign_flip_pvalue(values, "greater"),
        "signs": paired_sign_counts(values),
        "cohen_dz": cohen_dz(values),
        "rank_biserial": rank_biserial(values),
    }


def analyze_evaluations(evaluations: list[dict]) -> dict:
    if len(evaluations) != 16 or sorted(item["seed"] for item in evaluations) != list(
        RESERVED_SEEDS
    ):
        raise RuntimeError("REF2 analysis requires exactly 16 reserved paired seeds")
    tests: dict[str, dict] = {}
    raw_p: list[float] = []
    ordered_keys: list[str] = []

    for control in ("concat_relative_jepa", "no_command_jepa"):
        per_seed = []
        bin_sum = np.zeros(6, dtype=np.float64)
        for item in evaluations:
            transport = np.asarray(item["self_error_by_bin"]["transport_jepa"])
            baseline = np.asarray(item["self_error_by_bin"][control])
            difference = baseline - transport
            per_seed.append(float(np.mean(difference)))
            bin_sum += difference
        bin_mean = bin_sum / len(evaluations)
        summary = _paired_summary(np.asarray(per_seed))
        summary["bin_mean_differences"] = bin_mean.tolist()
        summary["favorable_bins"] = int(np.sum(bin_mean > 0))
        key = f"h1_vs_{control}"
        tests[key] = summary
        ordered_keys.append(key)
        raw_p.append(summary["p_exact_greater"])

    for baseline in (
        "concat_relative_jepa",
        "no_command_jepa",
        "pixel_change",
        "yaw_warp",
    ):
        per_seed = []
        bin_sum = np.zeros(6, dtype=np.float64)
        for item in evaluations:
            transport = np.asarray(item["rates_by_bin"]["transport_jepa"]["mixed"])
            control = np.asarray(item["rates_by_bin"][baseline]["mixed"])
            difference = transport - control
            per_seed.append(float(np.mean(difference)))
            bin_sum += difference
        bin_mean = bin_sum / len(evaluations)
        summary = _paired_summary(np.asarray(per_seed))
        summary["bin_mean_differences"] = bin_mean.tolist()
        summary["favorable_bins"] = int(np.sum(bin_mean > 0))
        key = f"h3_vs_{baseline}"
        tests[key] = summary
        ordered_keys.append(key)
        raw_p.append(summary["p_exact_greater"])

    for perturbation in ("permuted", "inverted"):
        field = f"{perturbation}_minus_normal_by_bin"
        per_seed = []
        bin_sum = np.zeros(6, dtype=np.float64)
        for item in evaluations:
            difference = np.asarray(item["h5"]["transport_jepa"][field])
            per_seed.append(float(np.mean(difference)))
            bin_sum += difference
        bin_mean = bin_sum / len(evaluations)
        summary = _paired_summary(np.asarray(per_seed))
        summary["bin_mean_differences"] = bin_mean.tolist()
        summary["favorable_bins"] = int(np.sum(bin_mean > 0))
        key = f"h5_{perturbation}"
        tests[key] = summary
        ordered_keys.append(key)
        raw_p.append(summary["p_exact_greater"])

    adjusted = holm_correction(raw_p)
    for key, adjusted_p in zip(ordered_keys, adjusted):
        tests[key]["p_holm"] = float(adjusted_p)
        margin = 0.10 if key.startswith("h3_") else 0.03
        tests[key]["minimum_effect"] = margin
        tests[key]["passed"] = bool(
            tests[key]["mean"] >= margin
            and tests[key]["ci_bca_95"][0] > 0
            and tests[key]["p_holm"] <= 0.05
            and tests[key]["favorable_bins"] >= 5
        )

    transport_tpr_mixed = [
        float(np.mean(item["rates_by_bin"]["transport_jepa"]["mixed"]))
        for item in evaluations
    ]
    h3_absolute = {
        "values": transport_tpr_mixed,
        "mean": float(np.mean(transport_tpr_mixed)),
        "minimum": 0.70,
        "passed": float(np.mean(transport_tpr_mixed)) >= 0.70,
    }
    sanity_external = {
        method: {
            "values": [
                float(np.mean(item["rates_by_bin"][method]["external_only"]))
                for item in evaluations
            ]
        }
        for method in CONDITIONS + ("pixel_change", "yaw_warp")
    }
    for value in sanity_external.values():
        value["mean"] = float(np.mean(value["values"]))
        value["finite"] = bool(np.all(np.isfinite(value["values"])))

    h4 = {}
    for kind in ("moving_self_test", "micro_self_test"):
        per_seed_bins = np.asarray(
            [
                item["rates_by_bin"]["transport_jepa"][kind]
                for item in evaluations
            ],
            dtype=np.float64,
        )
        mean_bins = np.mean(per_seed_bins, axis=0)
        h4[kind] = {
            "per_seed_by_bin": per_seed_bins.tolist(),
            "mean_by_bin": mean_bins.tolist(),
            "global_fpr": float(np.mean(mean_bins)),
            "max_bin_fpr": float(np.max(mean_bins)),
            "passed": bool(np.mean(mean_bins) <= 0.07 and np.max(mean_bins) <= 0.10),
        }
    h1_passed = all(tests[f"h1_vs_{control}"]["passed"] for control in ("concat_relative_jepa", "no_command_jepa"))
    h3_passed = h3_absolute["passed"] and all(
        tests[f"h3_vs_{baseline}"]["passed"]
        for baseline in (
            "concat_relative_jepa",
            "no_command_jepa",
            "pixel_change",
            "yaw_warp",
        )
    )
    h5_passed = all(tests[f"h5_{name}"]["passed"] for name in ("permuted", "inverted"))
    h4_passed = all(value["passed"] for value in h4.values())
    guards = {
        "learner": all(
            item["learner_guard"][condition]["passed"]
            for item in evaluations
            for condition in CONDITIONS
        ),
        "sanity_external_finite": all(
            value["finite"] for value in sanity_external.values()
        ),
    }
    eligible = bool(
        h1_passed
        and h3_passed
        and h4_passed
        and h5_passed
        and all(guards.values())
    )
    return {
        "seeds": list(RESERVED_SEEDS),
        "analysis_seed": ANALYSIS_SEED,
        "holm_family_size": 8,
        "tests": tests,
        "h1_passed": h1_passed,
        "h3_absolute": h3_absolute,
        "h3_passed": h3_passed,
        "h4": h4,
        "h4_passed": h4_passed,
        "h5_passed": h5_passed,
        "sanity_external": sanity_external,
        "guards": guards,
        "decision": {
            "eligible_for_contradictory_review": eligible,
            "promotion_forbidden_before_review": True,
            "variant_closed": True,
        },
    }
