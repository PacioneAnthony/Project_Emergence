"""Frozen REF-001 implementation: visual reafference and external change.

The scientific contract lives in
``docs/research/reafference_001_preregistration.md``.  This module contains no
adaptive hyper-parameter choices: it builds the shared data, trains the two
capacity-matched JEPA conditions, exports raw scores, and applies the frozen
paired analysis.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

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
from learning.train_visual_jepa import (
    ProbeHeads,
    action_sequence,
    build_pairs_multi,
    normalize_action,
)
from learning.visual_jepa import VisualJEPA
from sim3d.bench_model import BenchConfig, BenchRoomConfig

try:
    import torch
except ModuleNotFoundError:
    torch = None


CONDITIONS = ("no_action_jepa", "action_jepa")
METHODS = ("action_jepa", "no_action_jepa", "pixel_change", "pixel_change_action")
BASELINES = ("no_action_jepa", "pixel_change", "pixel_change_action")
BANKS = ("self_calibration", "self_test", "external_only", "mixed", "learner_validation")
RESERVED_SEEDS = tuple(range(12301, 12317))
SMOKE_SEED = 12991
STRUCTURED_CENTERS_DEG = (20.0, 40.0, 60.0, 80.0, 100.0, 120.0)
ANALYSIS_SEED = 2026072002
SPEC_VERSION = "ref-001-c1-c5-v1"


@dataclass(frozen=True)
class RefSpec:
    episodes: int = 20
    frames_per_episode: int = 600
    decisions_per_episode: int = 120
    optimizer_steps: int = 4_500
    batch_size: int = 256
    max_horizon: int = 5
    image_size: int = 64
    latent_dim: int = 128
    hidden_dim: int = 512
    encoder_width: int = 32
    lr: float = 3e-4
    weight_decay: float = 1e-4
    variance_weight: float = 1.0
    covariance_weight: float = 0.1
    pairs_per_bin: int = 128
    contexts: int = 2
    version: str = SPEC_VERSION

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
class RefBank:
    frames_start: np.ndarray
    frames_end: np.ndarray
    actions: np.ndarray
    angle_bins: np.ndarray
    contexts: np.ndarray
    head_delta_deg: np.ndarray
    object_delta_m: np.ndarray
    applied_target_deg: np.ndarray
    labels: np.ndarray

    def __len__(self) -> int:
        return int(self.frames_start.shape[0])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **{name: getattr(self, name) for name in self.__annotations__})

    @classmethod
    def load(cls, path: Path) -> "RefBank":
        with np.load(path) as stored:
            return cls(**{name: np.array(stored[name]) for name in cls.__annotations__})


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_hashes(frames: np.ndarray) -> set[bytes]:
    return {hashlib.sha256(frame.tobytes()).digest() for frame in frames}


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


def ref_bench_config(seed: int, bearing_deg: float = 70.0, context: int = 0) -> BenchConfig:
    """Return a fresh REF room; no D/E/F belt or previous experimental world."""

    if context not in (0, 1):
        raise ValueError("REF visual context must be 0 or 1")
    light = (0.72, 0.68, 0.62) if context == 0 else (0.46, 0.54, 0.72)
    fill = (0.36, 0.42, 0.48) if context == 0 else (0.58, 0.38, 0.34)
    room = BenchRoomConfig(
        object_count=7,
        primary_light_rgb=light,
        secondary_light_rgb=fill,
        headlight_ambient_rgb=(0.32, 0.32, 0.32),
        headlight_diffuse_rgb=(0.58, 0.58, 0.58),
        reafference_object=True,
        reafference_bearing_deg=float(bearing_deg),
        reafference_distance_m=1.15,
        reafference_travel_m=0.36,
    )
    return BenchConfig(seed=int(seed), randomize_room=True, room=room)


def _bounded_reflect(value: float, low: float, high: float) -> float:
    if value < low:
        return low + (low - value)
    if value > high:
        return high - (value - high)
    return value


def _correlation(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    if left.size != right.size or left.size < 2:
        raise ValueError("correlation arrays must have matching non-trivial size")
    if np.std(left) == 0 or np.std(right) == 0:
        return float("nan")
    return float(np.corrcoef(left, right)[0, 1])


def independent_motion_plan(seed: int, spec: RefSpec) -> dict[str, np.ndarray]:
    """Precompute action and object trajectories with the frozen independence guard."""

    action_rng = np.random.default_rng(31_000_000 + seed)
    mobile_rng = np.random.default_rng(32_000_000 + seed)
    mobile_episodes = np.zeros(spec.episodes, dtype=bool)
    mobile_episodes[mobile_rng.choice(spec.episodes, spec.episodes // 2, replace=False)] = True

    action_targets = np.empty(spec.decisions, dtype=np.float32)
    current = 90.0
    for index in range(spec.decisions):
        current = _bounded_reflect(current + float(action_rng.uniform(-22.0, 22.0)), 12.0, 168.0)
        action_targets[index] = current
    action_delta = np.diff(np.concatenate([[90.0], action_targets.astype(np.float64)]))

    half = 0.18
    decision_episode = np.repeat(np.arange(spec.episodes), spec.decisions_per_episode)
    for attempt in range(10_000):
        object_rng = np.random.default_rng(33_000_000 + seed * 10_000 + attempt)
        object_positions = np.zeros(spec.decisions, dtype=np.float32)
        position = 0.0
        for index, episode in enumerate(decision_episode):
            if mobile_episodes[episode]:
                position = _bounded_reflect(position + float(object_rng.uniform(-0.055, 0.055)), -half, half)
            object_positions[index] = position
        object_delta = np.diff(np.concatenate([[0.0], object_positions.astype(np.float64)]))
        corr = _correlation(action_delta, object_delta)
        if abs(corr) <= 0.045 and np.std(object_delta) > 0:
            return {
                "targets_deg": action_targets,
                "action_delta_deg": action_delta.astype(np.float32),
                "object_position_m": object_positions,
                "object_delta_m": object_delta.astype(np.float32),
                "mobile_episodes": mobile_episodes,
                "correlation": np.asarray(corr, dtype=np.float64),
            }
    raise RuntimeError("could not construct an independent REF corpus trajectory")


def _validate_corpus(data: dict[str, np.ndarray], spec: RefSpec) -> None:
    required = {
        "frames",
        "requested_deg",
        "as5600_deg",
        "episode",
        "decision_targets_deg",
        "decision_action_delta_deg",
        "decision_object_delta_m",
        "object_displacement_m",
        "episode_object_mobile",
    }
    if not required.issubset(data):
        raise RuntimeError(f"REF corpus missing {sorted(required - set(data))}")
    if data["frames"].shape != (spec.images, spec.image_size, spec.image_size, 3):
        raise RuntimeError(f"REF image budget diverges: {data['frames'].shape}")
    if any(len(data[name]) != spec.images for name in ("requested_deg", "as5600_deg", "episode", "object_displacement_m")):
        raise RuntimeError("REF per-frame arrays diverge")
    if any(len(data[name]) != spec.decisions for name in ("decision_targets_deg", "decision_action_delta_deg", "decision_object_delta_m")):
        raise RuntimeError("REF decision budget diverges")
    corr = _correlation(data["decision_action_delta_deg"], data["decision_object_delta_m"])
    if not np.isfinite(corr) or abs(corr) > 0.05:
        raise RuntimeError(f"REF corpus independence guard failed: {corr}")
    if int(np.sum(data["episode_object_mobile"])) != spec.episodes // 2:
        raise RuntimeError("REF mobile/static episode split diverges")


def generate_corpus(seed: int, path: Path, spec: RefSpec) -> dict:
    if path.exists():
        with np.load(path) as stored:
            data = {name: np.array(stored[name]) for name in stored.files}
        _validate_corpus(data, spec)
        return {"path": str(path), "sha256": _sha256(path), "images": spec.images, "decisions": spec.decisions}

    from sim3d.bench_env import BenchHeadEnv

    plan = independent_motion_plan(seed, spec)
    frames: list[np.ndarray] = []
    requested: list[float] = []
    actual: list[float] = []
    episodes: list[int] = []
    object_positions: list[float] = []
    decision_index = 0
    for episode in range(spec.episodes):
        context = episode % 2
        room_seed = 51_000_000 + seed * 100 + episode
        env = BenchHeadEnv(ref_bench_config(room_seed, bearing_deg=70.0, context=context))
        try:
            previous_object = 0.0 if decision_index == 0 else float(plan["object_position_m"][decision_index - 1])
            env.set_external_object_displacement(previous_object)
            for _ in range(spec.decisions_per_episode):
                target = float(plan["targets_deg"][decision_index])
                end_object = float(plan["object_position_m"][decision_index])
                for subframe in range(5):
                    fraction = (subframe + 1) / 5.0
                    env.set_external_object_displacement(previous_object + fraction * (end_object - previous_object))
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
        "decision_targets_deg": plan["targets_deg"].astype(np.float32),
        "decision_action_delta_deg": plan["action_delta_deg"].astype(np.float32),
        "decision_object_delta_m": plan["object_delta_m"].astype(np.float32),
        "object_displacement_m": np.asarray(object_positions, dtype=np.float32),
        "episode_object_mobile": plan["mobile_episodes"].astype(bool),
    }
    _validate_corpus(data, spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **data)
    return {"path": str(path), "sha256": _sha256(path), "images": spec.images, "decisions": spec.decisions}


def _bank_motion_plan(seed: int, kind: str, spec: RefSpec) -> tuple[np.ndarray, np.ndarray]:
    kind_index = BANKS.index(kind)
    size = len(STRUCTURED_CENTERS_DEG) * spec.pairs_per_bin
    action_rng = np.random.default_rng(61_000_000 + seed * 10 + kind_index)
    object_rng = np.random.default_rng(62_000_000 + seed * 10 + kind_index)
    head_delta = action_rng.uniform(3.0, 10.0, size=size) * action_rng.choice((-1.0, 1.0), size=size)
    object_delta = object_rng.uniform(0.06, 0.22, size=size) * object_rng.choice((-1.0, 1.0), size=size)
    if kind == "external_only":
        head_delta[:] = 0.0
    elif kind in ("self_calibration", "self_test"):
        object_delta[:] = 0.0
    elif kind == "learner_validation":
        selector = np.arange(size) % 3
        head_delta[selector == 1] = 0.0
        object_delta[selector == 0] = 0.0
    if kind == "mixed":
        for attempt in range(10_000):
            corr = _correlation(head_delta, object_delta)
            if abs(corr) <= 0.045:
                break
            object_rng.shuffle(object_delta)
        else:
            raise RuntimeError("could not construct independent mixed bank")
    return head_delta.astype(np.float32), object_delta.astype(np.float32)


def _validate_bank(bank: RefBank, kind: str, spec: RefSpec) -> None:
    expected = len(STRUCTURED_CENTERS_DEG) * spec.pairs_per_bin
    if len(bank) != expected:
        raise RuntimeError(f"REF {kind} bank size diverges: {len(bank)} != {expected}")
    if bank.frames_start.shape[1:] != (spec.image_size, spec.image_size, 3):
        raise RuntimeError(f"REF {kind} frame shape diverges")
    for angle_bin in range(len(STRUCTURED_CENTERS_DEG)):
        selected = bank.angle_bins == angle_bin
        if int(np.sum(selected)) != spec.pairs_per_bin:
            raise RuntimeError(f"REF {kind} bin {angle_bin} is unbalanced")
        counts = [int(np.sum(selected & (bank.contexts == context))) for context in range(spec.contexts)]
        if counts != [spec.pairs_per_bin // 2] * spec.contexts:
            raise RuntimeError(f"REF {kind} contexts diverge in bin {angle_bin}: {counts}")
    if kind in ("self_calibration", "self_test"):
        if np.any(bank.head_delta_deg == 0) or np.any(bank.object_delta_m != 0):
            raise RuntimeError(f"REF {kind} violates the structural self-motion filter")
    if kind == "external_only":
        if np.any(bank.head_delta_deg != 0) or np.any(bank.object_delta_m == 0):
            raise RuntimeError("REF external_only does not hold the head constant")
    if kind == "mixed":
        corr = _correlation(bank.head_delta_deg, bank.object_delta_m)
        if abs(corr) > 0.05:
            raise RuntimeError(f"REF mixed independence guard failed: {corr}")


def generate_bank(seed: int, kind: str, path: Path, spec: RefSpec) -> RefBank:
    if kind not in BANKS:
        raise ValueError(f"unknown REF bank {kind}")
    if path.exists():
        bank = RefBank.load(path)
        _validate_bank(bank, kind, spec)
        return bank

    from sim3d.bench_env import BenchHeadEnv

    head_plan, object_plan = _bank_motion_plan(seed, kind, spec)
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    actions: list[np.ndarray] = []
    bins: list[int] = []
    contexts: list[int] = []
    head_deltas: list[float] = []
    object_deltas: list[float] = []
    targets: list[float] = []
    labels: list[str] = []
    cursor = 0
    kind_index = BANKS.index(kind)
    for angle_bin, center in enumerate(STRUCTURED_CENTERS_DEG):
        for context in range(spec.contexts):
            room_seed = 81_000_000 + seed * 10_000 + kind_index * 1_000 + angle_bin * 10 + context
            env = BenchHeadEnv(ref_bench_config(room_seed, bearing_deg=center, context=context))
            rng = np.random.default_rng(room_seed + 700_000)
            try:
                for _ in range(spec.pairs_per_bin // spec.contexts):
                    planned_head = float(head_plan[cursor])
                    planned_object = float(object_plan[cursor])
                    start_angle = center - planned_head / 2.0
                    target_angle = center + planned_head / 2.0
                    if kind == "external_only":
                        start_angle = target_angle = center
                    object_start = -planned_object / 2.0
                    object_end = planned_object / 2.0
                    if kind in ("self_calibration", "self_test"):
                        object_start = object_end = float(rng.uniform(-0.12, 0.12))

                    env.set_external_object_displacement(object_start)
                    for _ in range(18):
                        start_observation = env.step(start_angle)
                    start = env.render_camera(spec.image_size, spec.image_size)
                    env.set_external_object_displacement(object_end)
                    for _ in range(18):
                        end_observation = env.step(target_angle)
                    end = env.render_camera(spec.image_size, spec.image_size)

                    actual_head_delta = float(end_observation.as5600_deg - start_observation.as5600_deg)
                    actual_object_delta = float(object_end - object_start)
                    action = np.full(spec.max_horizon, normalize_action(np.asarray([target_angle]))[0], dtype=np.float32)
                    label = kind
                    if kind == "learner_validation":
                        if actual_head_delta != 0 and actual_object_delta == 0:
                            label = "self_only"
                        elif actual_head_delta == 0 and actual_object_delta != 0:
                            label = "external_only"
                        else:
                            label = "mixed"
                    starts.append(start)
                    ends.append(end)
                    actions.append(action)
                    bins.append(angle_bin)
                    contexts.append(context)
                    head_deltas.append(actual_head_delta)
                    object_deltas.append(actual_object_delta)
                    targets.append(target_angle)
                    labels.append(label)
                    cursor += 1
            finally:
                env.close()

    bank = RefBank(
        frames_start=np.stack(starts).astype(np.uint8),
        frames_end=np.stack(ends).astype(np.uint8),
        actions=np.stack(actions).astype(np.float32),
        angle_bins=np.asarray(bins, dtype=np.int8),
        contexts=np.asarray(contexts, dtype=np.int8),
        head_delta_deg=np.asarray(head_deltas, dtype=np.float32),
        object_delta_m=np.asarray(object_deltas, dtype=np.float32),
        applied_target_deg=np.asarray(targets, dtype=np.float32),
        labels=np.asarray(labels, dtype="U24"),
    )
    _validate_bank(bank, kind, spec)
    bank.save(path)
    return bank


def load_corpus(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as stored:
        return {name: np.array(stored[name]) for name in stored.files}


def prepare_seed(seed: int, root: Path, spec: RefSpec) -> dict:
    started = time.perf_counter()
    corpus = generate_corpus(seed, corpus_path(root, seed), spec)
    banks = {}
    for kind in BANKS:
        bank = generate_bank(seed, kind, bank_path(root, seed, kind), spec)
        banks[kind] = {"path": str(bank_path(root, seed, kind)), "sha256": _sha256(bank_path(root, seed, kind)), "pairs": len(bank)}
    payload = {
        "seed": seed,
        "spec_digest": spec.digest(),
        "corpus": corpus,
        "banks": banks,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(root / "manifests" / f"seed_{seed}.json", payload)
    return payload


def make_learner(seed: int, condition: str, spec: RefSpec, device):
    if torch is None:
        raise ModuleNotFoundError("REF-001 requires PyTorch")
    if condition not in CONDITIONS:
        raise ValueError(f"unknown REF condition {condition}")
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
    model = VisualJEPA(
        latent_dim=spec.latent_dim,
        action_dim=spec.max_horizon,
        hidden_dim=spec.hidden_dim,
        encoder_width=spec.encoder_width,
        use_action=condition == "action_jepa",
        horizon_dim=1,
    ).to(device)
    probes = ProbeHeads(spec.latent_dim).to(device)
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(probes.parameters()),
        lr=spec.lr,
        weight_decay=spec.weight_decay,
    )
    return model, probes, optimizer


def state_digest(model, probes) -> str:
    digest = hashlib.sha256()
    for module in (model, probes):
        for name, value in sorted(module.state_dict().items()):
            digest.update(name.encode("utf-8"))
            digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def parameter_count(model, probes) -> int:
    return int(sum(parameter.numel() for module in (model, probes) for parameter in module.parameters()))


def _model_bank_scores(model, bank: RefBank, spec: RefSpec, device) -> tuple[np.ndarray, np.ndarray]:
    scores: list[np.ndarray] = []
    copies: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(bank), spec.batch_size):
            selected = slice(start, start + spec.batch_size)
            frame_start = torch.from_numpy(bank.frames_start[selected]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            frame_end = torch.from_numpy(bank.frames_end[selected]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            action = torch.from_numpy(bank.actions[selected]).to(device)
            horizon = torch.ones((frame_start.shape[0], 1), device=device)
            latent_start = model.encode(frame_start)
            latent_end = model.encode(frame_end)
            prediction = model.predict_next(latent_start, action, horizon)
            pred = torch.mean((prediction - latent_end) ** 2, dim=1)
            copy = torch.mean((latent_start - latent_end) ** 2, dim=1)
            scores.append((pred / torch.clamp(pred + copy, min=1e-8)).cpu().numpy())
            copies.append(copy.cpu().numpy())
    return np.concatenate(scores).astype(np.float64), np.concatenate(copies).astype(np.float64)


def pixel_change(bank: RefBank) -> np.ndarray:
    start = bank.frames_start.astype(np.float32)
    end = bank.frames_end.astype(np.float32)
    return np.mean(np.abs(end - start), axis=(1, 2, 3), dtype=np.float64) / 255.0


def _raw_score_export(model, banks: dict[str, RefBank], spec: RefSpec, device) -> dict:
    result = {}
    for kind, bank in banks.items():
        score, copy = _model_bank_scores(model, bank, spec, device)
        result[kind] = {
            "score": score.tolist(),
            "copy_mse": copy.tolist(),
            "pixel_change": pixel_change(bank).tolist(),
        }
    return result


def _learner_error(model, bank: RefBank, spec: RefSpec, device) -> float:
    score, _ = _model_bank_scores(model, bank, spec, device)
    return float(np.mean(score))


def train_condition(seed: int, condition: str, root: Path, spec: RefSpec, device, deadline: float | None = None) -> dict:
    result_file = run_path(root, seed, condition)
    checkpoint_file = checkpoint_path(root, seed, condition)
    if result_file.exists() and checkpoint_file.exists():
        result = json.loads(result_file.read_text(encoding="utf-8"))
        if result.get("spec_digest") == spec.digest() and result.get("status") == "complete":
            return result

    data = load_corpus(corpus_path(root, seed))
    banks = {kind: RefBank.load(bank_path(root, seed, kind)) for kind in BANKS}
    model, probes, optimizer = make_learner(seed, condition, spec, device)
    init_digest = state_digest(model, probes)
    initial_validation = _learner_error(model, banks["learner_validation"], spec, device)
    pairs_by_k = build_pairs_multi(data["episode"], spec.max_horizon)
    actions_norm = normalize_action(data["requested_deg"])
    rng = np.random.default_rng(91_000_000 + seed)
    batch_digest = hashlib.sha256()
    autocast_dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    started = time.perf_counter()
    loss_sum = 0.0

    for step in range(spec.optimizer_steps):
        if deadline is not None and time.perf_counter() >= deadline:
            raise TimeoutError("REF-001 wall-time cap reached during training")
        horizon_value = int(rng.integers(1, spec.max_horizon + 1))
        pool = pairs_by_k[horizon_value]
        indices = pool[rng.integers(0, len(pool), size=spec.batch_size)]
        batch_digest.update(np.asarray([horizon_value], dtype=np.int8).tobytes())
        batch_digest.update(indices.astype(np.int32).tobytes())

        frame_start = torch.from_numpy(data["frames"][indices]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
        frame_end = torch.from_numpy(data["frames"][indices + horizon_value]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
        action = torch.from_numpy(action_sequence(actions_norm, indices, horizon_value, spec.max_horizon)).to(device)
        horizon = torch.full((spec.batch_size, 1), horizon_value / spec.max_horizon, device=device)

        with torch.autocast(device_type=device.type, dtype=autocast_dtype, enabled=device.type == "cuda"):
            latent_start = model.encode(frame_start)
            latent_end = model.encode(frame_end)
            prediction = model.predict_next(latent_start, action, horizon)
            prediction_loss = torch.mean((prediction - latent_end.detach()) ** 2)
            regularizer = spec.variance_weight * 0.5 * (variance_loss(latent_start) + variance_loss(latent_end))
            regularizer = regularizer + spec.covariance_weight * 0.5 * (
                covariance_loss(latent_start) + covariance_loss(latent_end)
            )
            detached = latent_end.detach()
            angle = torch.from_numpy(np.radians(data["as5600_deg"][indices + horizon_value])).to(device).float()
            probe_angle = probes.angle(detached)
            probe_loss = torch.mean((probe_angle[:, 0] - torch.sin(angle)) ** 2)
            probe_loss = probe_loss + torch.mean((probe_angle[:, 1] - torch.cos(angle)) ** 2)
            loss = prediction_loss + regularizer + probe_loss

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        loss_sum += float(loss.item())

    final_validation = _learner_error(model, banks["learner_validation"], spec, device)
    raw_scores = _raw_score_export(model, banks, spec, device)
    elapsed = time.perf_counter() - started
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": {name: value.detach().cpu() for name, value in model.state_dict().items()},
            "probes_state_dict": {name: value.detach().cpu() for name, value in probes.state_dict().items()},
            "seed": seed,
            "condition": condition,
            "spec": asdict(spec),
        },
        checkpoint_file,
    )
    result = {
        "status": "complete",
        "seed": seed,
        "condition": condition,
        "spec_digest": spec.digest(),
        "corpus_sha256": _sha256(corpus_path(root, seed)),
        "bank_sha256": {kind: _sha256(bank_path(root, seed, kind)) for kind in BANKS},
        "initial_state_digest": init_digest,
        "batch_order_digest": batch_digest.hexdigest(),
        "parameter_count": parameter_count(model, probes),
        "optimizer_steps": spec.optimizer_steps,
        "batch_size": spec.batch_size,
        "examples_gradient": spec.optimizer_steps * spec.batch_size,
        "mean_train_loss": loss_sum / spec.optimizer_steps,
        "learner_validation_initial": initial_validation,
        "learner_validation_final": final_validation,
        "learner_relative_reduction": (initial_validation - final_validation) / max(initial_validation, 1e-12),
        "scores": raw_scores,
        "elapsed_seconds": elapsed,
        "checkpoint": str(checkpoint_file),
    }
    _write_json(result_file, result)
    return result


def load_learner(checkpoint: Path, spec: RefSpec, device):
    stored = torch.load(checkpoint, map_location=device, weights_only=False)
    model, probes, _ = make_learner(int(stored["seed"]), str(stored["condition"]), spec, device)
    model.load_state_dict(stored["model_state_dict"])
    probes.load_state_dict(stored["probes_state_dict"])
    return model, probes


def calibration_threshold(scores: np.ndarray) -> float:
    """Smallest observed score leaving at most 5% strictly above it."""

    values = np.sort(np.asarray(scores, dtype=np.float64))
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("threshold scores must be non-empty and finite")
    allowed_above = int(math.floor(0.05 * values.size))
    return float(values[max(0, values.size - allowed_above - 1)])


def fit_pixel_action(pixel: np.ndarray, amplitude: np.ndarray) -> tuple[float, float]:
    x = np.asarray(amplitude, dtype=np.float64)
    y = np.asarray(pixel, dtype=np.float64)
    design = np.column_stack([np.ones_like(x), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(coefficients[0]), float(coefficients[1])


def pixel_action_score(pixel: np.ndarray, amplitude: np.ndarray, fit: tuple[float, float]) -> np.ndarray:
    intercept, slope = fit
    prediction = intercept + slope * np.asarray(amplitude, dtype=np.float64)
    return np.maximum(np.asarray(pixel, dtype=np.float64) - prediction, 0.0)


def _auc(negative: np.ndarray, positive: np.ndarray) -> float:
    negative = np.asarray(negative, dtype=np.float64)
    positive = np.asarray(positive, dtype=np.float64)
    comparisons = positive[:, None] - negative[None, :]
    return float((np.sum(comparisons > 0) + 0.5 * np.sum(comparisons == 0)) / comparisons.size)


def evaluate_seed(seed: int, root: Path, spec: RefSpec) -> dict:
    target = evaluation_path(root, seed)
    results = {
        condition: json.loads(run_path(root, seed, condition).read_text(encoding="utf-8"))
        for condition in CONDITIONS
    }
    banks = {kind: RefBank.load(bank_path(root, seed, kind)) for kind in BANKS}
    scores: dict[str, dict[str, np.ndarray]] = {method: {} for method in METHODS}
    copy_mse: dict[str, dict[str, np.ndarray]] = {condition: {} for condition in CONDITIONS}
    for condition in CONDITIONS:
        for kind in BANKS:
            scores[condition][kind] = np.asarray(results[condition]["scores"][kind]["score"], dtype=np.float64)
            copy_mse[condition][kind] = np.asarray(results[condition]["scores"][kind]["copy_mse"], dtype=np.float64)
    for kind in BANKS:
        scores["pixel_change"][kind] = pixel_change(banks[kind])

    fits: dict[str, dict[str, float]] = {}
    for angle_bin in range(len(STRUCTURED_CENTERS_DEG)):
        mask = banks["self_calibration"].angle_bins == angle_bin
        amplitude = np.abs(banks["self_calibration"].head_delta_deg[mask]) / 160.0
        fit = fit_pixel_action(scores["pixel_change"]["self_calibration"][mask], amplitude)
        fits[str(angle_bin)] = {"intercept": fit[0], "slope": fit[1]}
        for kind in BANKS:
            selected = banks[kind].angle_bins == angle_bin
            if kind not in scores["pixel_change_action"]:
                scores["pixel_change_action"][kind] = np.zeros(len(banks[kind]), dtype=np.float64)
            amplitude_kind = np.abs(banks[kind].head_delta_deg[selected]) / 160.0
            scores["pixel_change_action"][kind][selected] = pixel_action_score(
                scores["pixel_change"][kind][selected], amplitude_kind, fit
            )

    thresholds: dict[str, list[float]] = {}
    for method in METHODS:
        thresholds[method] = []
        for angle_bin in range(len(STRUCTURED_CENTERS_DEG)):
            selected = banks["self_calibration"].angle_bins == angle_bin
            thresholds[method].append(calibration_threshold(scores[method]["self_calibration"][selected]))

    rates: dict[str, dict[str, list[float]]] = {method: {} for method in METHODS}
    for method in METHODS:
        for kind in ("self_calibration", "self_test", "external_only", "mixed"):
            values = []
            for angle_bin in range(len(STRUCTURED_CENTERS_DEG)):
                selected = banks[kind].angle_bins == angle_bin
                values.append(float(np.mean(scores[method][kind][selected] > thresholds[method][angle_bin])))
            rates[method][kind] = values

    diagnostics = {}
    for condition in CONDITIONS:
        diagnostics[condition] = {}
        for kind in BANKS:
            diagnostics[condition][kind] = []
            for angle_bin in range(len(STRUCTURED_CENTERS_DEG)):
                selected = banks[kind].angle_bins == angle_bin
                copy = copy_mse[condition][kind][selected]
                score = scores[condition][kind][selected]
                relation = _correlation(copy, score) if np.std(copy) > 0 and np.std(score) > 0 else None
                diagnostics[condition][kind].append(
                    {
                        "copy_mse_min": float(np.min(copy)),
                        "copy_mse_median": float(np.median(copy)),
                        "copy_mse_max": float(np.max(copy)),
                        "score_copy_correlation": relation,
                    }
                )

    auc = {}
    for method in METHODS:
        auc[method] = {}
        for external_kind in ("external_only", "mixed"):
            auc[method][external_kind] = []
            for angle_bin in range(len(STRUCTURED_CENTERS_DEG)):
                negative = scores[method]["self_test"][banks["self_test"].angle_bins == angle_bin]
                positive = scores[method][external_kind][banks[external_kind].angle_bins == angle_bin]
                auc[method][external_kind].append(_auc(negative, positive))

    payload = {
        "seed": seed,
        "spec_digest": spec.digest(),
        "thresholds": thresholds,
        "pixel_action_fits": fits,
        "rates_by_bin": rates,
        "self_error_by_bin": {
            condition: [
                float(np.mean(scores[condition]["self_test"][banks["self_test"].angle_bins == angle_bin]))
                for angle_bin in range(len(STRUCTURED_CENTERS_DEG))
            ]
            for condition in CONDITIONS
        },
        "learner_guard": {
            condition: {
                "initial": results[condition]["learner_validation_initial"],
                "final": results[condition]["learner_validation_final"],
                "relative_reduction": results[condition]["learner_relative_reduction"],
                "passed": results[condition]["learner_relative_reduction"] >= 0.20,
            }
            for condition in CONDITIONS
        },
        "auc_by_bin": auc,
        "copy_diagnostics": diagnostics,
        "independence": {
            "corpus": _correlation(
                load_corpus(corpus_path(root, seed))["decision_action_delta_deg"],
                load_corpus(corpus_path(root, seed))["decision_object_delta_m"],
            ),
            "mixed": _correlation(banks["mixed"].head_delta_deg, banks["mixed"].object_delta_m),
            "external_only_head_constant": bool(np.all(banks["external_only"].head_delta_deg == 0)),
        },
        "raw_calibration_scores": {
            method: scores[method]["self_calibration"].tolist() for method in METHODS
        },
        "calibration_bins": banks["self_calibration"].angle_bins.tolist(),
    }
    _write_json(target, payload)
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
    if len(evaluations) != 16 or sorted(item["seed"] for item in evaluations) != list(RESERVED_SEEDS):
        raise RuntimeError("REF analysis requires exactly the 16 reserved paired seeds")

    h1_values = []
    h1_bins = np.zeros(6, dtype=np.float64)
    for item in evaluations:
        no_action = np.asarray(item["self_error_by_bin"]["no_action_jepa"])
        action = np.asarray(item["self_error_by_bin"]["action_jepa"])
        difference = no_action - action
        h1_values.append(float(np.mean(difference)))
        h1_bins += difference
    h1_bins /= len(evaluations)
    h1 = _paired_summary(np.asarray(h1_values))
    h1["bin_mean_differences"] = h1_bins.tolist()
    h1["favorable_bins"] = int(np.sum(h1_bins > 0))
    h1["passed"] = bool(
        h1["mean"] >= 0.05
        and h1["ci_bca_95"][0] > 0
        and h1["p_exact_greater"] <= 0.05
        and h1["favorable_bins"] >= 5
    )

    comparisons = {}
    raw_p = []
    keys = []
    for kind in ("external_only", "mixed"):
        for baseline in BASELINES:
            values = []
            bin_differences = np.zeros(6, dtype=np.float64)
            for item in evaluations:
                action = np.asarray(item["rates_by_bin"]["action_jepa"][kind])
                control = np.asarray(item["rates_by_bin"][baseline][kind])
                difference = action - control
                values.append(float(np.mean(difference)))
                bin_differences += difference
            bin_differences /= len(evaluations)
            summary = _paired_summary(np.asarray(values))
            summary["bin_mean_differences"] = bin_differences.tolist()
            summary["favorable_bins"] = int(np.sum(bin_differences > 0))
            key = f"{kind}_vs_{baseline}"
            comparisons[key] = summary
            keys.append(key)
            raw_p.append(summary["p_exact_greater"])
    adjusted = holm_correction(raw_p)
    for key, adjusted_p in zip(keys, adjusted):
        summary = comparisons[key]
        summary["p_holm"] = float(adjusted_p)
        summary["passed"] = bool(
            summary["mean"] >= 0.10
            and summary["ci_bca_95"][0] > 0
            and summary["p_holm"] <= 0.05
            and summary["favorable_bins"] >= 5
        )

    absolute_tpr = {}
    for kind, minimum in (("external_only", 0.75), ("mixed", 0.70)):
        per_seed = [
            float(np.mean(item["rates_by_bin"]["action_jepa"][kind]))
            for item in evaluations
        ]
        absolute_tpr[kind] = {
            "values": per_seed,
            "mean": float(np.mean(per_seed)),
            "minimum": minimum,
            "passed": float(np.mean(per_seed)) >= minimum,
        }

    fpr_bins = np.mean(
        [np.asarray(item["rates_by_bin"]["action_jepa"]["self_test"]) for item in evaluations],
        axis=0,
    )
    h4 = {
        "fpr_by_bin": fpr_bins.tolist(),
        "global_fpr": float(np.mean(fpr_bins)),
        "max_bin_fpr": float(np.max(fpr_bins)),
        "passed": bool(np.mean(fpr_bins) <= 0.07 and np.max(fpr_bins) <= 0.10),
    }
    guards = {
        "learner": all(
            item["learner_guard"][condition]["passed"]
            for item in evaluations
            for condition in CONDITIONS
        ),
        "independence": all(
            abs(item["independence"]["corpus"]) <= 0.05
            and abs(item["independence"]["mixed"]) <= 0.05
            and item["independence"]["external_only_head_constant"]
            for item in evaluations
        ),
    }
    h2 = absolute_tpr["external_only"]["passed"] and all(
        comparisons[f"external_only_vs_{baseline}"]["passed"] for baseline in BASELINES
    )
    h3 = absolute_tpr["mixed"]["passed"] and all(
        comparisons[f"mixed_vs_{baseline}"]["passed"] for baseline in BASELINES
    )
    eligible = bool(h1["passed"] and h2 and h3 and h4["passed"] and all(guards.values()))
    return {
        "seeds": list(RESERVED_SEEDS),
        "analysis_seed": ANALYSIS_SEED,
        "h1": h1,
        "superiority": comparisons,
        "absolute_tpr": absolute_tpr,
        "h2_passed": h2,
        "h3_passed": h3,
        "h4": h4,
        "guards": guards,
        "decision": {
            "eligible_for_contradictory_review": eligible,
            "promotion_forbidden_before_review": True,
            "variant_closed": True,
        },
    }
