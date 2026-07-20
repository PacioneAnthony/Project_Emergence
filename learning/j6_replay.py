"""J6-R001 sequential visual retention experiment.

The frozen protocol is ``docs/research/j6_replay_001_preregistration.md``.
This module deliberately reuses the TV-001 image corruption and bounded anchor
error, but never uses held-out anchors for training or replay priorities.
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
    noninferiority_sign_flip_pvalue,
    paired_sign_counts,
    rank_biserial,
)
from learning.train_visual_jepa import ProbeHeads, action_sequence, build_pairs_multi, normalize_action
from learning.tv_exploration import (
    ANGLE_BINS,
    CONTEXT_BINS,
    TV_HIGH_DEG,
    TV_LOW_DEG,
    AnchorBank,
    UniformTelevisionPolicy,
    anchor_errors,
    apply_television,
    collect_tv_episode,
    visual_context_id,
)
from learning.visual_jepa import VisualJEPA
from sim3d.j6_domains import DOMAINS, LANDMARK_BINS, j6_bench_config

try:
    import torch
except ModuleNotFoundError:
    torch = None


CONDITIONS = ("naive", "uniform_replay", "error_prioritized_replay")
RESERVED_SEEDS = tuple(range(10301, 10313))
SMOKE_SEED = 10991
EPISODES_PER_DOMAIN = 20
FRAMES_PER_EPISODE = 200
DECISIONS_PER_EPISODE = 40
OPTIMIZER_STEPS = 1_500
BATCH_SIZE = 256
MAX_HORIZON = 5
PRIORITY_HORIZON = 3
J6_ANCHORS_PER_CELL = 32
STRUCTURED_BINS = tuple(range(6))
ANALYSIS_SEED = 20260720
SPEC_VERSION = "j6-r001-b1-b2-b3-v1"


@dataclass(frozen=True)
class J6Spec:
    episodes_per_domain: int = EPISODES_PER_DOMAIN
    frames_per_episode: int = FRAMES_PER_EPISODE
    decisions_per_episode: int = DECISIONS_PER_EPISODE
    optimizer_steps: int = OPTIMIZER_STEPS
    batch_size: int = BATCH_SIZE
    max_horizon: int = MAX_HORIZON
    priority_horizon: int = PRIORITY_HORIZON
    replay_fraction: float = 0.50
    image_size: int = 64
    latent_dim: int = 128
    hidden_dim: int = 512
    encoder_width: int = 32
    lr: float = 3e-4
    weight_decay: float = 1e-4
    variance_weight: float = 1.0
    covariance_weight: float = 0.1
    anchors_per_cell: int = J6_ANCHORS_PER_CELL
    version: str = SPEC_VERSION

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as stored:
        return {name: np.array(stored[name]) for name in stored.files}


def corpus_path(root: Path, seed: int, domain: str) -> Path:
    return root / "corpora" / f"seed_{seed}" / f"domain_{domain}.npz"


def anchor_path(root: Path, seed: int, domain: str) -> Path:
    return root / "anchors" / f"seed_{seed}" / f"domain_{domain}.npz"


def generate_domain_corpus(seed: int, domain: str, path: Path, spec: J6Spec) -> dict:
    """Generate once; every condition subsequently reads these exact bytes."""

    expected_frames = spec.episodes_per_domain * spec.frames_per_episode
    expected_decisions = spec.episodes_per_domain * spec.decisions_per_episode
    if path.exists():
        data = _load_npz(path)
        _validate_corpus(data, expected_frames, expected_decisions)
        return {"path": str(path), "sha256": _sha256(path), "frames": expected_frames, "decisions": expected_decisions}

    from sim3d.bench_env import BenchHeadEnv

    domain_index = DOMAINS.index(domain)
    env = BenchHeadEnv(j6_bench_config(domain, seed))
    policy = UniformTelevisionPolicy()
    rng = np.random.default_rng(seed + 3_100_000)
    frames: list[np.ndarray] = []
    requested: list[float] = []
    as5600: list[float] = []
    distance: list[float] = []
    episodes: list[np.ndarray] = []
    decision_targets: list[float] = []
    try:
        for episode in range(spec.episodes_per_domain):
            room_seed = 71_000_000 + seed * 100 + domain_index * spec.episodes_per_domain + episode
            result = collect_tv_episode(env, policy, rng, spec.frames_per_episode, spec.image_size, room_seed)
            ep_frames, ep_requested, ep_as5600, ep_distance, _, ep_targets = result
            frames.extend(ep_frames)
            requested.extend(ep_requested)
            as5600.extend(ep_as5600)
            distance.extend(ep_distance)
            episodes.append(np.full(spec.frames_per_episode, episode, dtype=np.int16))
            decision_targets.extend(ep_targets)
    finally:
        env.close()

    data = {
        "frames": np.stack(frames).astype(np.uint8),
        "requested_deg": np.asarray(requested, dtype=np.float32),
        "as5600_deg": np.asarray(as5600, dtype=np.float32),
        "distance_m": np.asarray(distance, dtype=np.float32),
        "episode": np.concatenate(episodes),
        "decision_targets": np.asarray(decision_targets, dtype=np.float32),
    }
    _validate_corpus(data, expected_frames, expected_decisions)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **data)
    return {"path": str(path), "sha256": _sha256(path), "frames": expected_frames, "decisions": expected_decisions}


def _validate_corpus(data: dict[str, np.ndarray], expected_frames: int, expected_decisions: int) -> None:
    required = {"frames", "requested_deg", "as5600_deg", "distance_m", "episode", "decision_targets"}
    if not required.issubset(data):
        raise RuntimeError(f"J6 corpus manifest diverges: missing {sorted(required - set(data))}")
    if data["frames"].shape != (expected_frames, 64, 64, 3):
        raise RuntimeError(f"J6 frame budget diverges: {data['frames'].shape}")
    if any(len(data[name]) != expected_frames for name in ("requested_deg", "as5600_deg", "distance_m", "episode")):
        raise RuntimeError("J6 per-frame arrays diverge")
    if len(data["decision_targets"]) != expected_decisions:
        raise RuntimeError(f"J6 decision budget diverges: {len(data['decision_targets'])}")


def generate_j6_anchor_bank(seed: int, domain: str, path: Path, spec: J6Spec) -> AnchorBank:
    """Held-out, room-disjoint bank balanced by angle bin and visual context."""

    expected = ANGLE_BINS * CONTEXT_BINS * spec.anchors_per_cell
    if path.exists():
        bank = AnchorBank.load(path)
        _validate_anchor_bank(bank, expected, spec.anchors_per_cell)
        return bank

    from sim3d.bench_env import BenchHeadEnv

    domain_index = DOMAINS.index(domain)
    env = BenchHeadEnv(j6_bench_config(domain, seed))
    rng = np.random.default_rng(seed + 6_100_000)
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    actions: list[np.ndarray] = []
    bins: list[int] = []
    contexts: list[int] = []
    targets: list[float] = []
    counts = np.zeros((ANGLE_BINS, CONTEXT_BINS), dtype=np.int16)
    candidate = 0
    try:
        while np.any(counts < spec.anchors_per_cell):
            if candidate >= 768:
                raise RuntimeError(f"could not balance held-out J6 anchors for domain {domain}")
            # 91M prefix is disjoint from the 71M training rooms.
            room_seed = 91_000_000 + seed * 1000 + domain_index * 800 + candidate
            candidate += 1
            env.reset(seed=room_seed)
            for _ in range(20):
                env.step(90.0)
            context = visual_context_id(env.render_camera(spec.image_size, spec.image_size))
            needed = [angle for angle in range(ANGLE_BINS) if counts[angle, context] < spec.anchors_per_cell]
            if not needed:
                continue
            tv_rng = np.random.default_rng(room_seed + 710_000)
            for angle in needed:
                repeats = min(8, spec.anchors_per_cell - int(counts[angle, context]))
                low = 10.0 + 20.0 * angle
                for _ in range(repeats):
                    for _ in range(20):
                        env.step(90.0)
                    obs_start = env.step(90.0)
                    start = apply_television(
                        env.render_camera(spec.image_size, spec.image_size), obs_start.as5600_deg, tv_rng
                    )
                    target = float(rng.uniform(low + 0.25, low + 19.75))
                    for _ in range(15):
                        env.step(target)
                    obs_end = env.step(target)
                    end = apply_television(
                        env.render_camera(spec.image_size, spec.image_size), obs_end.as5600_deg, tv_rng
                    )
                    action = np.zeros(spec.max_horizon, dtype=np.float32)
                    action[:PRIORITY_HORIZON] = normalize_action(
                        np.full(PRIORITY_HORIZON, target, dtype=np.float32)
                    )
                    starts.append(start)
                    ends.append(end)
                    actions.append(action)
                    bins.append(angle)
                    contexts.append(context)
                    targets.append(float(obs_end.as5600_deg))
                    counts[angle, context] += 1
    finally:
        env.close()

    bank = AnchorBank(
        frames_start=np.stack(starts).astype(np.uint8),
        frames_end=np.stack(ends).astype(np.uint8),
        actions=np.stack(actions).astype(np.float32),
        angle_bins=np.asarray(bins, dtype=np.int8),
        contexts=np.asarray(contexts, dtype=np.int8),
        target_deg=np.asarray(targets, dtype=np.float32),
    )
    _validate_anchor_bank(bank, expected, spec.anchors_per_cell)
    bank.save(path)
    return bank


def _validate_anchor_bank(bank: AnchorBank, expected: int, per_cell: int) -> None:
    if len(bank) != expected:
        raise RuntimeError(f"J6 anchor budget diverges: {len(bank)} != {expected}")
    for angle in range(ANGLE_BINS):
        for context in range(CONTEXT_BINS):
            if len(bank.cell_indices((angle, context))) != per_cell:
                raise RuntimeError(f"J6 anchor balance diverges at {(angle, context)}")


def make_learner(seed: int, spec: J6Spec, device):
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
    model = VisualJEPA(
        latent_dim=spec.latent_dim,
        action_dim=spec.max_horizon,
        hidden_dim=spec.hidden_dim,
        encoder_width=spec.encoder_width,
        use_action=True,
        horizon_dim=1,
    ).to(device)
    probes = ProbeHeads(spec.latent_dim).to(device)
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(probes.parameters()), lr=spec.lr, weight_decay=spec.weight_decay
    )
    return model, probes, optimizer


def state_digest(model, probes) -> str:
    digest = hashlib.sha256()
    for module in (model, probes):
        for name, value in sorted(module.state_dict().items()):
            digest.update(name.encode())
            digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def evaluate_banks(model, probes, banks: dict[str, AnchorBank], device) -> dict:
    model.eval()
    probes.eval()
    result: dict[str, dict] = {}
    with torch.no_grad():
        for domain, bank in banks.items():
            all_errors = anchor_errors(model, bank, np.arange(len(bank), dtype=np.int64), device)
            by_bin = [float(np.mean(all_errors[bank.angle_bins == angle])) for angle in range(ANGLE_BINS)]
            frame = torch.from_numpy(bank.frames_end).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            latent = model.encode(frame)
            angle_out = probes.angle(latent)
            angle_pred = torch.atan2(angle_out[:, 0], angle_out[:, 1])
            angle_true = torch.from_numpy(np.radians(bank.target_deg)).to(device)
            wrapped = torch.remainder(angle_pred - angle_true + math.pi, 2 * math.pi) - math.pi
            result[domain] = {
                "error_by_bin": by_bin,
                "structured_error": float(np.mean(by_bin[:6])),
                "television_error": float(np.mean(by_bin[6:])),
                "angle_probe_mae_deg": float(torch.mean(torch.abs(torch.rad2deg(wrapped))).item()),
                "anchors": len(bank),
                "structured_anchors_by_bin": [int(np.sum(bank.angle_bins == angle)) for angle in STRUCTURED_BINS],
            }
    return result


def _episode_indices(data: dict[str, np.ndarray], k: int) -> dict[int, np.ndarray]:
    valid = build_pairs_multi(data["episode"], k)[k]
    return {int(ep): valid[data["episode"][valid] == ep] for ep in np.unique(data["episode"])}


def frozen_priority_weights(errors) -> np.ndarray:
    """The pre-registered priority, with no exponent, mixture, or update."""

    values = np.asarray(errors, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("priority errors must be a non-empty finite non-negative vector")
    weights = values + 1e-3
    return weights / np.sum(weights)


def _bounded_pair_errors(model, data: dict[str, np.ndarray], indices: np.ndarray, k: int, spec: J6Spec, device) -> np.ndarray:
    values: list[np.ndarray] = []
    actions = normalize_action(data["requested_deg"])
    model.eval()
    with torch.no_grad():
        for start in range(0, len(indices), spec.batch_size):
            selected = indices[start : start + spec.batch_size]
            x = torch.from_numpy(data["frames"][selected]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            y = torch.from_numpy(data["frames"][selected + k]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            action = torch.from_numpy(action_sequence(actions, selected, k, spec.max_horizon)).to(device)
            horizon = torch.full((len(selected), 1), k / spec.max_horizon, device=device)
            z = model.encode(x)
            target = model.encode(y)
            prediction = model.predict_next(z, action, horizon)
            pred = torch.mean((prediction - target) ** 2, dim=1)
            copy = torch.mean((z - target) ** 2, dim=1)
            values.append((pred / torch.clamp(pred + copy, min=1e-8)).cpu().numpy())
    return np.concatenate(values)


def replay_probabilities(model, old: dict[str, dict[str, np.ndarray]], condition: str, spec: J6Spec, device) -> tuple[list[tuple[str, int]], np.ndarray, dict]:
    episodes: list[tuple[str, int]] = []
    errors: list[float] = []
    tv_fractions: list[float] = []
    for domain, data in old.items():
        for episode, pairs in _episode_indices(data, spec.priority_horizon).items():
            episodes.append((domain, episode))
            tv_fractions.append(float(np.mean(data["as5600_deg"][pairs + spec.priority_horizon] >= TV_LOW_DEG)))
            if condition == "error_prioritized_replay":
                errors.append(float(np.mean(_bounded_pair_errors(model, data, pairs, spec.priority_horizon, spec, device))))
            else:
                errors.append(1.0)
    score = np.asarray(errors, dtype=np.float64)
    if condition == "error_prioritized_replay":
        probability = frozen_priority_weights(score)
    else:
        probability = np.full(len(episodes), 1.0 / len(episodes))
    if not np.isclose(probability.sum(), 1.0, atol=1e-12):
        raise RuntimeError("J6 replay priority does not sum to one")
    by_domain = {
        domain: float(sum(p for item, p in zip(episodes, probability) if item[0] == domain))
        for domain in old
    }
    tv_by_domain = {
        domain: float(sum(p * tv for item, p, tv in zip(episodes, probability, tv_fractions) if item[0] == domain))
        for domain in old
    }
    return episodes, probability, {
        "probability_sum": float(probability.sum()),
        "probability_mass_by_domain": by_domain,
        "expected_tv_mass_by_domain": tv_by_domain,
        "episode_errors": errors,
    }


def _sample_from_data(data: dict[str, np.ndarray], size: int, k: int, rng: np.random.Generator) -> np.ndarray:
    pool = build_pairs_multi(data["episode"], k)[k]
    return pool[rng.integers(0, len(pool), size=size)]


def _sample_old(old_pools, episodes, probability, size, k, rng):
    chosen = rng.choice(len(episodes), size=size, p=probability)
    indices = np.empty(size, dtype=np.int64)
    domains: list[str] = []
    for position, episode_index in enumerate(chosen):
        domain, episode = episodes[int(episode_index)]
        pool = old_pools[domain][k][episode]
        indices[position] = pool[int(rng.integers(0, len(pool)))]
        domains.append(domain)
    return domains, indices


def _batch_arrays(data, index, k, spec):
    return (
        data["frames"][index],
        data["frames"][index + k],
        action_sequence(normalize_action(data["requested_deg"]), index, k, spec.max_horizon),
        data["as5600_deg"][index + k],
        data["distance_m"][index + k],
    )


def train_session(model, probes, optimizer, current, old, condition, spec: J6Spec, seed: int, session_index: int, device, deadline: float | None = None) -> dict:
    """Exactly 1,500 optimizer steps; replay batches are exactly 128+128."""

    rng = np.random.default_rng(seed + 10_000 * session_index + CONDITIONS.index(condition) * 1_000_000)
    replay = condition != "naive" and bool(old)
    episodes = None
    probability = None
    replay_report = None
    if replay:
        episodes, probability, replay_report = replay_probabilities(model, old, condition, spec, device)
        old_pools = {
            domain: {k: _episode_indices(data, k) for k in range(1, spec.max_horizon + 1)}
            for domain, data in old.items()
        }
    effective = {domain: {"total": 0, "television": 0} for domain in old}
    losses: list[float] = []
    autocast_dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    model.train()
    probes.train()
    for step in range(spec.optimizer_steps):
        if deadline is not None and step % 25 == 0 and time.perf_counter() >= deadline:
            raise TimeoutError("J6 90-minute GPU wall-clock cap reached")
        k = int(rng.integers(1, spec.max_horizon + 1))
        current_size = spec.batch_size // 2 if replay else spec.batch_size
        current_index = _sample_from_data(current, current_size, k, rng)
        chunks = [_batch_arrays(current, current_index, k, spec)]
        if replay:
            old_domains, old_index = _sample_old(old_pools, episodes, probability, spec.batch_size // 2, k, rng)
            for domain in old:
                positions = np.flatnonzero(np.asarray(old_domains) == domain)
                if len(positions):
                    chunk = _batch_arrays(old[domain], old_index[positions], k, spec)
                    chunks.append(chunk)
                    effective[domain]["total"] += len(positions)
                    effective[domain]["television"] += int(np.sum(chunk[3] >= TV_LOW_DEG))
        start_frames = np.concatenate([chunk[0] for chunk in chunks])
        end_frames = np.concatenate([chunk[1] for chunk in chunks])
        action_values = np.concatenate([chunk[2] for chunk in chunks])
        angle_values = np.concatenate([chunk[3] for chunk in chunks])
        distance_values = np.concatenate([chunk[4] for chunk in chunks])
        if len(start_frames) != spec.batch_size:
            raise RuntimeError("J6 50/50 replay batch diverges")
        x = torch.from_numpy(start_frames).to(device).permute(0, 3, 1, 2).float().div_(255.0)
        y = torch.from_numpy(end_frames).to(device).permute(0, 3, 1, 2).float().div_(255.0)
        action = torch.from_numpy(action_values).to(device)
        horizon = torch.full((spec.batch_size, 1), k / spec.max_horizon, device=device)
        angle_true = torch.from_numpy(np.radians(angle_values)).to(device).float()
        distance_true = torch.from_numpy(distance_values).to(device).float()
        with torch.autocast(device_type=device.type, dtype=autocast_dtype, enabled=device.type == "cuda"):
            latent = model.encode(x)
            target = model.encode(y)
            prediction = model.predict_next(latent, action, horizon)
            pred_loss = torch.mean((prediction - target.detach()) ** 2)
            regularizer = spec.variance_weight * 0.5 * (variance_loss(latent) + variance_loss(target))
            regularizer += spec.covariance_weight * 0.5 * (covariance_loss(latent) + covariance_loss(target))
            detached = target.detach()
            angle_out = probes.angle(detached)
            probe_loss = torch.mean((angle_out[:, 0] - torch.sin(angle_true)) ** 2)
            probe_loss += torch.mean((angle_out[:, 1] - torch.cos(angle_true)) ** 2)
            probe_loss += torch.mean((probes.distance(detached).squeeze(-1) - distance_true) ** 2)
            loss = pred_loss + regularizer + probe_loss
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))
    if replay_report is not None:
        replay_report["effective_tv_fraction_by_domain"] = {
            domain: (counts["television"] / counts["total"] if counts["total"] else 0.0)
            for domain, counts in effective.items()
        }
        replay_report["effective_pairs_by_domain"] = effective
    return {
        "steps": spec.optimizer_steps,
        "batch_size": spec.batch_size,
        "current_fraction": 0.5 if replay else 1.0,
        "old_fraction": 0.5 if replay else 0.0,
        "loss_first": losses[0],
        "loss_last": losses[-1],
        "loss_mean": float(np.mean(losses)),
        "replay": replay_report,
    }


def prepare_seed(seed: int, root: Path, spec: J6Spec, device, deadline: float | None = None) -> dict:
    """Build shared corpus/anchors and the one authoritative post-A state."""

    started = time.perf_counter()
    corpus_manifest = {}
    corpora = {}
    banks = {}
    for domain in DOMAINS:
        if deadline is not None and time.perf_counter() >= deadline:
            raise TimeoutError("J6 90-minute GPU wall-clock cap reached")
        path = corpus_path(root, seed, domain)
        corpus_manifest[domain] = generate_domain_corpus(seed, domain, path, spec)
        corpora[domain] = _load_npz(path)
        banks[domain] = generate_j6_anchor_bank(seed, domain, anchor_path(root, seed, domain), spec)
    total_frames = sum(item["frames"] for item in corpus_manifest.values())
    total_decisions = sum(item["decisions"] for item in corpus_manifest.values())
    if total_frames != 12_000 or total_decisions != 2_400:
        raise RuntimeError(f"J6 total interaction budget diverges: {total_frames}/{total_decisions}")

    shared_path = root / "shared" / f"seed_{seed}_post_a.pt"
    metadata_path = root / "shared" / f"seed_{seed}_post_a.json"
    if shared_path.exists() and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("spec_digest") != spec.digest() or metadata.get("corpus_manifest") != corpus_manifest:
            raise RuntimeError("J6 shared post-A manifest diverges")
        return metadata

    model, probes, optimizer = make_learner(seed, spec, device)
    initial = evaluate_banks(model, probes, banks, device)
    train_a = train_session(model, probes, optimizer, corpora["A"], {}, "naive", spec, seed, 0, device, deadline)
    post_a = evaluate_banks(model, probes, banks, device)
    state = {
        "model": model.state_dict(),
        "probes": probes.state_dict(),
        "optimizer": optimizer.state_dict(),
        "seed": seed,
        "spec_digest": spec.digest(),
    }
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, shared_path)
    metadata = {
        "complete": True,
        "seed": seed,
        "spec_digest": spec.digest(),
        "corpus_manifest": corpus_manifest,
        "total_frames": total_frames,
        "total_decisions": total_decisions,
        "initial": initial,
        "post_A": post_a,
        "post_A_state_digest": state_digest(model, probes),
        "post_A_checkpoint_sha256": _sha256(shared_path),
        "train_A": train_a,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(metadata_path, metadata)
    return metadata


def _load_shared(seed: int, root: Path, spec: J6Spec, device):
    model, probes, optimizer = make_learner(seed, spec, device)
    state = torch.load(root / "shared" / f"seed_{seed}_post_a.pt", map_location=device, weights_only=False)
    if state["spec_digest"] != spec.digest() or state["seed"] != seed:
        raise RuntimeError("J6 post-A checkpoint diverges")
    model.load_state_dict(state["model"])
    probes.load_state_dict(state["probes"])
    optimizer.load_state_dict(state["optimizer"])
    return model, probes, optimizer


def run_condition(seed: int, condition: str, root: Path, spec: J6Spec, device, deadline: float | None = None) -> dict:
    if condition not in CONDITIONS:
        raise ValueError(condition)
    result_path = root / "runs" / f"seed_{seed}_{condition}.json"
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("complete") and result.get("spec_digest") == spec.digest():
            return result
        raise RuntimeError(f"J6 partial/divergent run exists: {result_path}")
    shared = prepare_seed(seed, root, spec, device, deadline)
    corpora = {domain: _load_npz(corpus_path(root, seed, domain)) for domain in DOMAINS}
    banks = {domain: AnchorBank.load(anchor_path(root, seed, domain)) for domain in DOMAINS}
    model, probes, optimizer = _load_shared(seed, root, spec, device)
    if state_digest(model, probes) != shared["post_A_state_digest"]:
        raise RuntimeError("J6 B3 post-A state identity failed")
    started = time.perf_counter()
    train_b = train_session(model, probes, optimizer, corpora["B"], {"A": corpora["A"]}, condition, spec, seed, 1, device, deadline)
    post_b = evaluate_banks(model, probes, banks, device)
    train_c = train_session(
        model, probes, optimizer, corpora["C"], {"A": corpora["A"], "B": corpora["B"]},
        condition, spec, seed, 2, device, deadline,
    )
    post_c = evaluate_banks(model, probes, banks, device)
    relative = {}
    absolute = {}
    for domain, acquisition in (("A", shared["post_A"]), ("B", post_b)):
        acquired = np.asarray(acquisition[domain]["error_by_bin"][:6], dtype=float)
        final = np.asarray(post_c[domain]["error_by_bin"][:6], dtype=float)
        relative[domain] = (final / np.maximum(acquired, 1e-8) - 1.0).tolist()
        absolute[domain] = (final - acquired).tolist()
    result = {
        "complete": True,
        "seed": seed,
        "condition": condition,
        "spec_digest": spec.digest(),
        "corpus_sha256": {domain: shared["corpus_manifest"][domain]["sha256"] for domain in DOMAINS},
        "budgets": {"images": 12_000, "decisions": 2_400, "optimizer_steps": 4_500, "session_steps": spec.optimizer_steps},
        "evaluations": {"initial": shared["initial"], "post_A": shared["post_A"], "post_B": post_b, "post_C": post_c},
        "post_A_state_digest": shared["post_A_state_digest"],
        "training": {"A": shared["train_A"], "B": train_b, "C": train_c},
        "regression_relative": relative,
        "regression_abs": absolute,
        "elapsed_seconds_after_A": time.perf_counter() - started,
    }
    _write_json(result_path, result)
    return result


def _paired_summary(values: np.ndarray, seed_offset: int = 0) -> dict:
    values = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(values)),
        "bca_95": list(bca_bootstrap_ci(values, n_boot=10_000, seed=ANALYSIS_SEED + seed_offset)),
        "signs": paired_sign_counts(values),
        "p_exact_greater": exact_sign_flip_pvalue(values, "greater"),
        "cohen_dz": cohen_dz(values),
        "rank_biserial": rank_biserial(values),
    }


def analyze_results(results: list[dict]) -> dict:
    """Apply every frozen gate, including amendments B1 and B2."""

    indexed = {(item["seed"], item["condition"]): item for item in results}
    seeds = sorted({item["seed"] for item in results})
    if len(seeds) != 12 or len(results) != 36 or any((seed, c) not in indexed for seed in seeds for c in CONDITIONS):
        raise RuntimeError("J6 campaign requires exactly 12 complete triplets / 36 runs")

    def reg(seed, condition, kind, domain):
        return np.asarray(indexed[(seed, condition)][kind][domain], dtype=float)

    analysis: dict = {"seeds": seeds, "b1_forgetting_guard": {}, "h1": {}, "h2": {}}
    for domain_index, domain in enumerate(("A", "B")):
        naive_reg = np.asarray([np.mean(reg(s, "naive", "regression_relative", domain)) for s in seeds])
        b1 = _paired_summary(naive_reg, 10 + domain_index)
        b1["passed"] = b1["mean"] >= 0.05 and b1["bca_95"][0] > 0
        analysis["b1_forgetting_guard"][domain] = b1
        h1_rel = np.asarray([
            np.mean(reg(s, "naive", "regression_relative", domain) - reg(s, "uniform_replay", "regression_relative", domain))
            for s in seeds
        ])
        h1_abs = np.asarray([
            np.mean(reg(s, "naive", "regression_abs", domain) - reg(s, "uniform_replay", "regression_abs", domain))
            for s in seeds
        ])
        h2_rel = np.asarray([
            np.mean(reg(s, "uniform_replay", "regression_relative", domain) - reg(s, "error_prioritized_replay", "regression_relative", domain))
            for s in seeds
        ])
        h2_abs = np.asarray([
            np.mean(reg(s, "uniform_replay", "regression_abs", domain) - reg(s, "error_prioritized_replay", "regression_abs", domain))
            for s in seeds
        ])
        for target, rel, absolute, threshold, offset in (
            (analysis["h1"], h1_rel, h1_abs, 0.05, 20),
            (analysis["h2"], h2_rel, h2_abs, 0.03, 30),
        ):
            rel_summary = _paired_summary(rel, offset + domain_index)
            abs_summary = _paired_summary(absolute, offset + domain_index + 100)
            left, right = (("naive", "uniform_replay") if target is analysis["h1"] else ("uniform_replay", "error_prioritized_replay"))
            bin_differences = np.mean(
                np.stack([reg(s, left, "regression_relative", domain) - reg(s, right, "regression_relative", domain) for s in seeds]), axis=0
            )
            target[domain] = {
                "relative": rel_summary,
                "absolute": abs_summary,
                "favorable_bins": int(np.sum(bin_differences > 0)),
                "b2_sign_agreement": bool(np.sign(rel_summary["mean"]) == np.sign(abs_summary["mean"])),
                "threshold": threshold,
            }
    h1_holm = holm_correction([analysis["h1"][d]["relative"]["p_exact_greater"] for d in ("A", "B")])
    h2_holm = holm_correction([analysis["h2"][d]["relative"]["p_exact_greater"] for d in ("A", "B")])
    for i, domain in enumerate(("A", "B")):
        for name, corrected in (("h1", h1_holm), ("h2", h2_holm)):
            item = analysis[name][domain]
            item["p_holm"] = float(corrected[i])
            rel = item["relative"]
            statistical_pass = rel["mean"] >= item["threshold"] and rel["bca_95"][0] > 0 and item["p_holm"] <= 0.05 and item["favorable_bins"] >= 5
            item["passed"] = bool(statistical_pass and (domain != "B" or item["b2_sign_agreement"]))
            if name == "h1" and not analysis["b1_forgetting_guard"][domain]["passed"]:
                item["interpretation"] = "NON INTERPRETABLE: le monde n'a pas induit d'oubli mesurable"
            else:
                item["interpretation"] = "PASS" if item["passed"] else "FAIL"

    naive_c = np.asarray([
        np.mean(indexed[(s, "naive")]["evaluations"]["post_C"]["C"]["error_by_bin"][:6]) for s in seeds
    ])
    h3 = {}
    pvalues = []
    for condition in ("uniform_replay", "error_prioritized_replay"):
        replay_c = np.asarray([
            np.mean(indexed[(s, condition)]["evaluations"]["post_C"]["C"]["error_by_bin"][:6]) for s in seeds
        ])
        difference = replay_c - naive_c
        margin = 0.05 * float(np.mean(naive_c))
        pvalue = noninferiority_sign_flip_pvalue(difference, margin)
        pvalues.append(pvalue)
        regional = []
        for angle in STRUCTURED_BINS:
            ratios = [
                indexed[(s, condition)]["evaluations"]["post_C"]["C"]["error_by_bin"][angle]
                / max(indexed[(s, "naive")]["evaluations"]["post_C"]["C"]["error_by_bin"][angle], 1e-8) - 1
                for s in seeds
            ]
            regional.append(float(np.mean(ratios)))
        h3[condition] = {"mean_difference": float(np.mean(difference)), "margin": margin, "p_exact": pvalue, "regional_relative": regional}
    corrected = holm_correction(pvalues)
    for i, condition in enumerate(("uniform_replay", "error_prioritized_replay")):
        h3[condition]["p_holm"] = float(corrected[i])
        h3[condition]["passed"] = bool(corrected[i] <= 0.05 and max(h3[condition]["regional_relative"]) <= 0.10)
    analysis["h3"] = h3

    learner_failures = []
    for seed in seeds:
        for condition in CONDITIONS:
            evaluations = indexed[(seed, condition)]["evaluations"]
            for domain, phase in (("A", "post_A"), ("B", "post_B"), ("C", "post_C")):
                initial = evaluations["initial"][domain]["structured_error"]
                acquired = evaluations[phase][domain]["structured_error"]
                reduction = 1.0 - acquired / max(initial, 1e-8)
                if reduction < 0.20:
                    learner_failures.append({"seed": seed, "condition": condition, "domain": domain, "reduction": reduction})
    analysis["learner_guard"] = {"passed": not learner_failures, "failures": learner_failures}

    tv_guard = {}
    for session in ("B", "C"):
        diffs = []
        for seed in seeds:
            uniform = indexed[(seed, "uniform_replay")]["training"][session]["replay"]["effective_tv_fraction_by_domain"]
            priority = indexed[(seed, "error_prioritized_replay")]["training"][session]["replay"]["effective_tv_fraction_by_domain"]
            diffs.append(np.mean(list(priority.values())) - np.mean(list(uniform.values())))
        tv_guard[session] = {"mean_excess": float(np.mean(diffs)), "passed": bool(np.mean(diffs) <= 0.05)}
    analysis["tv_guard"] = tv_guard
    uniform_promoted = all(analysis["b1_forgetting_guard"][d]["passed"] and analysis["h1"][d]["passed"] for d in ("A", "B")) and h3["uniform_replay"]["passed"] and analysis["learner_guard"]["passed"]
    priority_promoted = uniform_promoted and all(analysis["h2"][d]["passed"] for d in ("A", "B")) and h3["error_prioritized_replay"]["passed"] and all(item["passed"] for item in tv_guard.values())
    analysis["decision"] = {"uniform_promoted": uniform_promoted, "error_prioritized_promoted": priority_promoted, "promotion_pending_claude_review": True}
    return analysis
