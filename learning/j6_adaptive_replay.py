"""J6-AR001 adaptive replay under a current-plasticity constraint."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from learning.j6_replay import (
    J6Spec,
    _batch_arrays,
    _episode_indices,
    _load_npz,
    _sample_from_data,
    _sha256,
    _validate_anchor_bank,
    _validate_corpus,
    _write_json,
    evaluate_banks,
    make_learner,
    state_digest,
)
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
from learning.train_visual_jepa import normalize_action
from learning.tv_exploration import (
    ANGLE_BINS,
    CONTEXT_BINS,
    TV_LOW_DEG,
    AnchorBank,
    UniformTelevisionPolicy,
    anchor_errors,
    apply_television,
    collect_tv_episode,
    visual_context_id,
)
from sim3d.j6_adaptive_domains import DOMAINS, adaptive_bench_config

try:
    import torch
except ModuleNotFoundError:
    torch = None


CONDITIONS = ("naive", "uniform_50", "adaptive_replay")
RESERVED_SEEDS = tuple(range(11301, 11317))
SMOKE_SEED = 11991
STRUCTURED_BINS = tuple(range(6))
ANALYSIS_SEED = 2026072001
SPEC_VERSION = "j6-ar001-c1-c4-v1"


@dataclass(frozen=True)
class AdaptiveSpec(J6Spec):
    monitor_block_steps: int = 100
    anchors_per_cell: int = 32
    version: str = SPEC_VERSION


def corpus_path(root: Path, seed: int, domain: str) -> Path:
    return root / "corpora" / f"seed_{seed}" / f"domain_{domain}.npz"


def bank_path(root: Path, seed: int, domain: str, kind: str) -> Path:
    if kind not in {"monitor", "decision"}:
        raise ValueError(kind)
    return root / f"{kind}_banks" / f"seed_{seed}" / f"domain_{domain}.npz"


def generate_domain_corpus(seed: int, domain: str, path: Path, spec: AdaptiveSpec) -> dict:
    expected_frames = spec.episodes_per_domain * spec.frames_per_episode
    expected_decisions = spec.episodes_per_domain * spec.decisions_per_episode
    if path.exists():
        data = _load_npz(path)
        _validate_corpus(data, expected_frames, expected_decisions)
        return {"path": str(path), "sha256": _sha256(path), "frames": expected_frames, "decisions": expected_decisions}

    from sim3d.bench_env import BenchHeadEnv

    env = BenchHeadEnv(adaptive_bench_config(domain, seed))
    policy = UniformTelevisionPolicy()
    # Identical action stream and room schedule across domains and conditions.
    rng = np.random.default_rng(seed + 17_100_000)
    frames: list[np.ndarray] = []
    requested: list[float] = []
    as5600: list[float] = []
    distance: list[float] = []
    episodes: list[np.ndarray] = []
    decisions: list[float] = []
    try:
        for episode in range(spec.episodes_per_domain):
            room_seed = 121_000_000 + seed * 100 + episode
            result = collect_tv_episode(env, policy, rng, spec.frames_per_episode, spec.image_size, room_seed)
            ep_frames, ep_requested, ep_as5600, ep_distance, _, ep_decisions = result
            frames.extend(ep_frames)
            requested.extend(ep_requested)
            as5600.extend(ep_as5600)
            distance.extend(ep_distance)
            episodes.append(np.full(spec.frames_per_episode, episode, dtype=np.int16))
            decisions.extend(ep_decisions)
    finally:
        env.close()
    data = {
        "frames": np.stack(frames).astype(np.uint8),
        "requested_deg": np.asarray(requested, dtype=np.float32),
        "as5600_deg": np.asarray(as5600, dtype=np.float32),
        "distance_m": np.asarray(distance, dtype=np.float32),
        "episode": np.concatenate(episodes),
        "decision_targets": np.asarray(decisions, dtype=np.float32),
    }
    _validate_corpus(data, expected_frames, expected_decisions)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **data)
    return {"path": str(path), "sha256": _sha256(path), "frames": expected_frames, "decisions": expected_decisions}


def generate_anchor_bank(seed: int, domain: str, kind: str, path: Path, spec: AdaptiveSpec) -> AnchorBank:
    expected = ANGLE_BINS * CONTEXT_BINS * spec.anchors_per_cell
    if path.exists():
        bank = AnchorBank.load(path)
        _validate_anchor_bank(bank, expected, spec.anchors_per_cell)
        return bank

    from sim3d.bench_env import BenchHeadEnv

    prefix = 131_000_000 if kind == "monitor" else 151_000_000
    env = BenchHeadEnv(adaptive_bench_config(domain, seed))
    rng = np.random.default_rng(seed + (18_100_000 if kind == "monitor" else 19_100_000))
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
                raise RuntimeError(f"could not balance {kind} bank for {domain}")
            room_seed = prefix + seed * 1000 + candidate
            candidate += 1
            env.reset(seed=room_seed)
            for _ in range(20):
                env.step(90.0)
            context = visual_context_id(env.render_camera(spec.image_size, spec.image_size))
            needed = [angle for angle in range(ANGLE_BINS) if counts[angle, context] < spec.anchors_per_cell]
            tv_rng = np.random.default_rng(room_seed + 710_000)
            for angle in needed:
                repeats = min(8, spec.anchors_per_cell - int(counts[angle, context]))
                low = 10.0 + 20.0 * angle
                for _ in range(repeats):
                    for _ in range(20):
                        env.step(90.0)
                    obs_start = env.step(90.0)
                    frame_start = apply_television(
                        env.render_camera(spec.image_size, spec.image_size), obs_start.as5600_deg, tv_rng
                    )
                    target = float(rng.uniform(low + 0.25, low + 19.75))
                    for _ in range(15):
                        env.step(target)
                    obs_end = env.step(target)
                    frame_end = apply_television(
                        env.render_camera(spec.image_size, spec.image_size), obs_end.as5600_deg, tv_rng
                    )
                    action = np.zeros(spec.max_horizon, dtype=np.float32)
                    action[:3] = normalize_action(np.full(3, target, dtype=np.float32))
                    starts.append(frame_start)
                    ends.append(frame_end)
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


def monitor_metrics(model, banks: dict[str, AnchorBank], device) -> dict[str, dict]:
    result = {}
    for domain, bank in banks.items():
        errors = anchor_errors(model, bank, np.arange(len(bank), dtype=np.int64), device)
        by_bin = [float(np.mean(errors[bank.angle_bins == angle])) for angle in range(ANGLE_BINS)]
        result[domain] = {"error_by_bin": by_bin, "structured_error": float(np.mean(by_bin[:6])), "anchors": len(bank)}
    return result


def evaluation_digest(metrics: dict) -> str:
    payload = json.dumps(metrics, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def adaptive_fraction(current_metrics: dict, acquisition: dict, session_start: dict, current_domain: str, old_domains: tuple[str, ...]) -> dict:
    old_debts = []
    for domain in old_domains:
        for angle in STRUCTURED_BINS:
            old_debts.append(
                max(current_metrics[domain]["error_by_bin"][angle] / max(acquisition[domain]["error_by_bin"][angle], 1e-8) - 1.0, 0.0)
            )
    current_deficits = [
        max(
            current_metrics[current_domain]["error_by_bin"][angle]
            / max(session_start[current_domain]["error_by_bin"][angle], 1e-8)
            - 0.80,
            0.0,
        )
        for angle in STRUCTURED_BINS
    ]
    d_old = float(max(old_debts, default=0.0))
    d_current = float(max(current_deficits, default=0.0))
    q = 0.5 * d_old / (d_old + d_current + 1e-3)
    rho = float(np.clip(math.floor(16.0 * q + 0.5) / 16.0, 0.0, 0.5))
    return {"d_old": d_old, "d_current": d_current, "q": q, "rho": rho}


def recompute_rho(d_old: float, d_current: float) -> float:
    q = 0.5 * float(d_old) / (float(d_old) + float(d_current) + 1e-3)
    return float(np.clip(math.floor(16.0 * q + 0.5) / 16.0, 0.0, 0.5))


def _old_episode_pools(old: dict[str, dict[str, np.ndarray]], spec: AdaptiveSpec):
    episodes = [(domain, int(ep)) for domain, data in old.items() for ep in np.unique(data["episode"])]
    pools = {
        domain: {k: _episode_indices(data, k) for k in range(1, spec.max_horizon + 1)}
        for domain, data in old.items()
    }
    return episodes, pools


def _sample_old(old, episodes, pools, size: int, k: int, rng):
    chosen = rng.integers(0, len(episodes), size=size)
    by_domain: dict[str, list[int]] = {domain: [] for domain in old}
    for episode_index in chosen:
        domain, episode = episodes[int(episode_index)]
        pool = pools[domain][k][episode]
        by_domain[domain].append(int(pool[int(rng.integers(0, len(pool)))]))
    return {domain: np.asarray(indices, dtype=np.int64) for domain, indices in by_domain.items() if indices}


def train_session(
    model,
    probes,
    optimizer,
    current: dict[str, np.ndarray],
    old: dict[str, dict[str, np.ndarray]],
    condition: str,
    monitor_banks: dict[str, AnchorBank],
    acquisition: dict,
    current_domain: str,
    spec: AdaptiveSpec,
    seed: int,
    session_index: int,
    device,
    deadline: float | None = None,
) -> tuple[dict, dict]:
    """Train one session with equal monitoring and exact effective composition."""

    if condition not in CONDITIONS:
        raise ValueError(condition)
    if spec.optimizer_steps % spec.monitor_block_steps:
        raise RuntimeError("optimizer steps must be divisible by monitor block size")
    rng = np.random.default_rng(seed + session_index * 10_000 + CONDITIONS.index(condition) * 1_000_000)
    old_domains = tuple(old)
    episodes, old_pools = _old_episode_pools(old, spec) if old else ([], {})
    autocast_dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    histories = []
    losses: list[float] = []
    tv_counts = {domain: {"replayed": 0, "television": 0} for domain in old}
    total_monitor_evaluations = 0
    session_start = None
    model.train()
    probes.train()

    blocks = spec.optimizer_steps // spec.monitor_block_steps
    for block in range(blocks):
        if deadline is not None and time.perf_counter() >= deadline:
            raise TimeoutError("J6-AR001 75-minute GPU wall-clock cap reached")
        metrics = monitor_metrics(model, monitor_banks, device)
        total_monitor_evaluations += 1
        model.train()
        probes.train()
        if session_start is None:
            session_start = metrics
        formula = adaptive_fraction(metrics, acquisition, session_start, current_domain, old_domains)
        if condition == "naive" or not old:
            rho = 0.0
        elif condition == "uniform_50":
            rho = 0.5
        else:
            rho = formula["rho"]
        old_count = int(round(spec.batch_size * rho))
        current_count = spec.batch_size - old_count
        if old_count != spec.batch_size * rho or current_count + old_count != spec.batch_size:
            raise RuntimeError("adaptive replay batch composition is not exact")
        block_old_pairs = 0
        block_current_pairs = 0
        for _ in range(spec.monitor_block_steps):
            k = int(rng.integers(1, spec.max_horizon + 1))
            current_index = _sample_from_data(current, current_count, k, rng)
            chunks = [_batch_arrays(current, current_index, k, spec)]
            block_current_pairs += len(current_index)
            if old_count:
                selected = _sample_old(old, episodes, old_pools, old_count, k, rng)
                for domain, indices in selected.items():
                    chunk = _batch_arrays(old[domain], indices, k, spec)
                    chunks.append(chunk)
                    replayed = len(indices)
                    tv_counts[domain]["replayed"] += replayed
                    tv_counts[domain]["television"] += int(np.sum(chunk[3] >= TV_LOW_DEG))
                    block_old_pairs += replayed
            start_frames = np.concatenate([chunk[0] for chunk in chunks])
            end_frames = np.concatenate([chunk[1] for chunk in chunks])
            actions = np.concatenate([chunk[2] for chunk in chunks])
            angles = np.concatenate([chunk[3] for chunk in chunks])
            distances = np.concatenate([chunk[4] for chunk in chunks])
            if len(start_frames) != spec.batch_size:
                raise RuntimeError("effective batch size diverged")
            x = torch.from_numpy(start_frames).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            y = torch.from_numpy(end_frames).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            action = torch.from_numpy(actions).to(device)
            horizon = torch.full((spec.batch_size, 1), k / spec.max_horizon, device=device)
            angle_true = torch.from_numpy(np.radians(angles)).to(device).float()
            distance_true = torch.from_numpy(distances).to(device).float()
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
        expected_old = spec.monitor_block_steps * old_count
        expected_current = spec.monitor_block_steps * current_count
        if block_old_pairs != expected_old or block_current_pairs != expected_current:
            raise RuntimeError("effective block composition diverged")
        histories.append(
            {
                "step": block * spec.monitor_block_steps,
                "monitor_digest": evaluation_digest(metrics),
                "monitor_bank_sizes": {domain: len(bank) for domain, bank in monitor_banks.items()},
                **formula,
                "applied_rho": rho,
                "old_per_batch": old_count,
                "current_per_batch": current_count,
                "effective_old_pairs": block_old_pairs,
                "effective_current_pairs": block_current_pairs,
            }
        )

    final_metrics = monitor_metrics(model, monitor_banks, device)
    total_monitor_evaluations += 1
    histories.append(
        {
            "step": spec.optimizer_steps,
            "monitor_digest": evaluation_digest(final_metrics),
            "monitor_bank_sizes": {domain: len(bank) for domain, bank in monitor_banks.items()},
            "terminal": True,
        }
    )
    replayed_total = sum(item["replayed"] for item in tv_counts.values())
    television_total = sum(item["television"] for item in tv_counts.values())
    tv_fraction = television_total / replayed_total if replayed_total else None
    report = {
        "steps": spec.optimizer_steps,
        "batch_size": spec.batch_size,
        "monitor_evaluations": total_monitor_evaluations,
        "monitor_steps": [item["step"] for item in histories],
        "monitor_bank_sizes": {domain: len(bank) for domain, bank in monitor_banks.items()},
        "blocks": histories,
        "loss_first": losses[0],
        "loss_last": losses[-1],
        "loss_mean": float(np.mean(losses)),
        "replay": {
            "pairs_by_domain": tv_counts,
            "effective_tv_fraction_among_replayed": tv_fraction,
            "replayed_pairs": replayed_total,
            "television_pairs": television_total,
        },
    }
    return report, final_metrics


def prepare_seed(seed: int, root: Path, spec: AdaptiveSpec, device, deadline: float | None = None) -> dict:
    started = time.perf_counter()
    corpora = {}
    corpus_manifest = {}
    monitor_banks = {}
    decision_banks = {}
    bank_manifest = {"monitor": {}, "decision": {}}
    for domain in DOMAINS:
        if deadline is not None and time.perf_counter() >= deadline:
            raise TimeoutError("J6-AR001 75-minute GPU wall-clock cap reached")
        cpath = corpus_path(root, seed, domain)
        corpus_manifest[domain] = generate_domain_corpus(seed, domain, cpath, spec)
        corpora[domain] = _load_npz(cpath)
        for kind, destination in (("monitor", monitor_banks), ("decision", decision_banks)):
            bpath = bank_path(root, seed, domain, kind)
            destination[domain] = generate_anchor_bank(seed, domain, kind, bpath, spec)
            bank_manifest[kind][domain] = {"path": str(bpath), "sha256": _sha256(bpath), "anchors": len(destination[domain])}
    if sum(item["frames"] for item in corpus_manifest.values()) != 12_000:
        raise RuntimeError("J6-AR001 image budget diverged")
    if sum(item["decisions"] for item in corpus_manifest.values()) != 2_400:
        raise RuntimeError("J6-AR001 decision budget diverged")

    shared_path = root / "shared" / f"seed_{seed}_post_d.pt"
    metadata_path = root / "shared" / f"seed_{seed}_post_d.json"
    if shared_path.exists() and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("spec_digest") != spec.digest()
            or metadata.get("corpus_manifest") != corpus_manifest
            or metadata.get("bank_manifest") != bank_manifest
        ):
            raise RuntimeError("J6-AR001 shared post-D manifest diverges")
        return metadata

    model, probes, optimizer = make_learner(seed, spec, device)
    initial_decision = evaluate_banks(model, probes, decision_banks, device)
    initial_monitor = monitor_metrics(model, monitor_banks, device)
    train_d, post_d_monitor = train_session(
        model,
        probes,
        optimizer,
        corpora["D"],
        {},
        "naive",
        monitor_banks,
        {},
        "D",
        spec,
        seed,
        0,
        device,
        deadline,
    )
    post_d_decision = evaluate_banks(model, probes, decision_banks, device)
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
        "bank_manifest": bank_manifest,
        "initial_decision": initial_decision,
        "initial_monitor": initial_monitor,
        "post_D_decision": post_d_decision,
        "post_D_monitor": post_d_monitor,
        "post_D_state_digest": state_digest(model, probes),
        "post_D_checkpoint_sha256": _sha256(shared_path),
        "train_D": train_d,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(metadata_path, metadata)
    return metadata


def _load_shared(seed: int, root: Path, spec: AdaptiveSpec, device):
    model, probes, optimizer = make_learner(seed, spec, device)
    state = torch.load(root / "shared" / f"seed_{seed}_post_d.pt", map_location=device, weights_only=False)
    if state["seed"] != seed or state["spec_digest"] != spec.digest():
        raise RuntimeError("J6-AR001 post-D checkpoint diverges")
    model.load_state_dict(state["model"])
    probes.load_state_dict(state["probes"])
    optimizer.load_state_dict(state["optimizer"])
    return model, probes, optimizer


def run_condition(seed: int, condition: str, root: Path, spec: AdaptiveSpec, device, deadline: float | None = None) -> dict:
    if condition not in CONDITIONS:
        raise ValueError(condition)
    result_path = root / "runs" / f"seed_{seed}_{condition}.json"
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("complete") and result.get("spec_digest") == spec.digest():
            return result
        raise RuntimeError(f"partial or divergent J6-AR001 run: {result_path}")
    shared = prepare_seed(seed, root, spec, device, deadline)
    corpora = {domain: _load_npz(corpus_path(root, seed, domain)) for domain in DOMAINS}
    monitor_banks = {domain: AnchorBank.load(bank_path(root, seed, domain, "monitor")) for domain in DOMAINS}
    decision_banks = {domain: AnchorBank.load(bank_path(root, seed, domain, "decision")) for domain in DOMAINS}
    model, probes, optimizer = _load_shared(seed, root, spec, device)
    if state_digest(model, probes) != shared["post_D_state_digest"]:
        raise RuntimeError("J6-AR001 B3 post-D state identity failed")
    started = time.perf_counter()
    acquisition = {"D": shared["post_D_monitor"]["D"]}
    train_e, post_e_monitor = train_session(
        model,
        probes,
        optimizer,
        corpora["E"],
        {"D": corpora["D"]},
        condition,
        monitor_banks,
        acquisition,
        "E",
        spec,
        seed,
        1,
        device,
        deadline,
    )
    post_e_decision = evaluate_banks(model, probes, decision_banks, device)
    acquisition["E"] = post_e_monitor["E"]
    train_f, post_f_monitor = train_session(
        model,
        probes,
        optimizer,
        corpora["F"],
        {"D": corpora["D"], "E": corpora["E"]},
        condition,
        monitor_banks,
        acquisition,
        "F",
        spec,
        seed,
        2,
        device,
        deadline,
    )
    post_f_decision = evaluate_banks(model, probes, decision_banks, device)
    regression_relative = {}
    regression_absolute = {}
    for domain, acquired in (("D", shared["post_D_decision"]), ("E", post_e_decision)):
        e_acq = np.asarray(acquired[domain]["error_by_bin"][:6], dtype=float)
        e_final = np.asarray(post_f_decision[domain]["error_by_bin"][:6], dtype=float)
        regression_relative[domain] = (e_final / np.maximum(e_acq, 1e-8) - 1.0).tolist()
        regression_absolute[domain] = (e_final - e_acq).tolist()
    result = {
        "complete": True,
        "seed": seed,
        "condition": condition,
        "spec_digest": spec.digest(),
        "corpus_sha256": {domain: shared["corpus_manifest"][domain]["sha256"] for domain in DOMAINS},
        "bank_sha256": shared["bank_manifest"],
        "budgets": {"images": 12_000, "decisions": 2_400, "optimizer_steps": 4_500, "session_steps": 1_500, "batch_size": 256},
        "evaluations": {
            "initial": shared["initial_decision"],
            "post_D": shared["post_D_decision"],
            "post_E": post_e_decision,
            "post_F": post_f_decision,
        },
        "post_D_state_digest": shared["post_D_state_digest"],
        "training": {"D": shared["train_D"], "E": train_e, "F": train_f},
        "post_E_monitor": post_e_monitor,
        "post_F_monitor": post_f_monitor,
        "regression_relative": regression_relative,
        "regression_abs": regression_absolute,
        "elapsed_seconds_after_D": time.perf_counter() - started,
    }
    _write_json(result_path, result)
    return result


def _summary(values, offset: int = 0) -> dict:
    values = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(values)),
        "bca_95": list(bca_bootstrap_ci(values, n_boot=10_000, seed=ANALYSIS_SEED + offset)),
        "signs": paired_sign_counts(values),
        "p_exact_greater": exact_sign_flip_pvalue(values, "greater"),
        "cohen_dz": cohen_dz(values),
        "rank_biserial": rank_biserial(values),
    }


def analyze_results(results: list[dict]) -> dict:
    indexed = {(item["seed"], item["condition"]): item for item in results}
    seeds = sorted({item["seed"] for item in results})
    if len(seeds) != 16 or len(results) != 48 or any((seed, condition) not in indexed for seed in seeds for condition in CONDITIONS):
        raise RuntimeError("J6-AR001 requires exactly 16 complete triplets / 48 runs")

    def reg(seed, condition, kind, domain):
        return np.asarray(indexed[(seed, condition)][kind][domain], dtype=float)

    analysis: dict = {"seeds": seeds, "b1_forgetting_guard": {}, "h1_uniform_value": {}, "h2_retention_noninferiority": {}}
    for domain_index, domain in enumerate(("D", "E")):
        naive = np.asarray([np.mean(reg(seed, "naive", "regression_relative", domain)) for seed in seeds])
        guard = _summary(naive, domain_index)
        guard["passed"] = bool(guard["mean"] >= 0.05 and guard["bca_95"][0] > 0)
        analysis["b1_forgetting_guard"][domain] = guard

        h1_relative = np.asarray([
            np.mean(reg(seed, "naive", "regression_relative", domain) - reg(seed, "uniform_50", "regression_relative", domain))
            for seed in seeds
        ])
        h1_absolute = np.asarray([
            np.mean(reg(seed, "naive", "regression_abs", domain) - reg(seed, "uniform_50", "regression_abs", domain))
            for seed in seeds
        ])
        relative_summary = _summary(h1_relative, 10 + domain_index)
        absolute_summary = _summary(h1_absolute, 20 + domain_index)
        bin_means = np.mean(
            np.stack([reg(seed, "naive", "regression_relative", domain) - reg(seed, "uniform_50", "regression_relative", domain) for seed in seeds]),
            axis=0,
        )
        analysis["h1_uniform_value"][domain] = {
            "relative": relative_summary,
            "absolute": absolute_summary,
            "favorable_bins": int(np.sum(bin_means > 0)),
            "b2_sign_agreement": bool(np.sign(relative_summary["mean"]) == np.sign(absolute_summary["mean"])),
        }

        relative_loss = np.asarray([
            np.mean(reg(seed, "adaptive_replay", "regression_relative", domain) - reg(seed, "uniform_50", "regression_relative", domain))
            for seed in seeds
        ])
        absolute_loss = np.asarray([
            np.mean(reg(seed, "adaptive_replay", "regression_abs", domain) - reg(seed, "uniform_50", "regression_abs", domain))
            for seed in seeds
        ])
        relative_loss_summary = _summary(relative_loss, 30 + domain_index)
        absolute_loss_summary = _summary(absolute_loss, 40 + domain_index)
        bin_losses = np.mean(
            np.stack([reg(seed, "adaptive_replay", "regression_relative", domain) - reg(seed, "uniform_50", "regression_relative", domain) for seed in seeds]),
            axis=0,
        )
        analysis["h2_retention_noninferiority"][domain] = {
            "relative_loss": relative_loss_summary,
            "absolute_loss": absolute_loss_summary,
            "p_exact_noninferiority": noninferiority_sign_flip_pvalue(relative_loss, 0.02),
            "bin_mean_losses": bin_losses.tolist(),
            "b2_absolute_significant_loss": bool(absolute_loss_summary["mean"] > 0 and absolute_loss_summary["bca_95"][0] > 0),
        }

    h1_holm = holm_correction([analysis["h1_uniform_value"][domain]["relative"]["p_exact_greater"] for domain in ("D", "E")])
    h2_holm = holm_correction([analysis["h2_retention_noninferiority"][domain]["p_exact_noninferiority"] for domain in ("D", "E")])
    for index, domain in enumerate(("D", "E")):
        h1 = analysis["h1_uniform_value"][domain]
        h1["p_holm"] = float(h1_holm[index])
        h1["passed"] = bool(
            analysis["b1_forgetting_guard"][domain]["passed"]
            and h1["relative"]["mean"] >= 0.05
            and h1["relative"]["bca_95"][0] > 0
            and h1["p_holm"] <= 0.05
            and h1["favorable_bins"] >= 5
            and h1["b2_sign_agreement"]
        )
        h1["interpretation"] = "NON INTERPRETABLE" if not analysis["b1_forgetting_guard"][domain]["passed"] else ("PASS" if h1["passed"] else "FAIL")
        h2 = analysis["h2_retention_noninferiority"][domain]
        h2["p_holm"] = float(h2_holm[index])
        relative_gate = bool(
            h2["relative_loss"]["mean"] <= 0.02
            and h2["p_holm"] <= 0.05
            and max(h2["bin_mean_losses"]) <= 0.05
        )
        h2["b2_violated"] = bool(relative_gate and h2["b2_absolute_significant_loss"])
        h2["passed"] = bool(relative_gate and not h2["b2_violated"])

    naive_f = np.asarray([
        np.mean(indexed[(seed, "naive")]["evaluations"]["post_F"]["F"]["error_by_bin"][:6]) for seed in seeds
    ])
    uniform_f = np.asarray([
        np.mean(indexed[(seed, "uniform_50")]["evaluations"]["post_F"]["F"]["error_by_bin"][:6]) for seed in seeds
    ])
    adaptive_f = np.asarray([
        np.mean(indexed[(seed, "adaptive_replay")]["evaluations"]["post_F"]["F"]["error_by_bin"][:6]) for seed in seeds
    ])
    gain_f = (uniform_f - adaptive_f) / np.maximum(uniform_f, 1e-8)
    h3a = _summary(gain_f, 50)
    bin_gains = []
    bin_worse = []
    for angle in STRUCTURED_BINS:
        uniform_values = np.asarray([indexed[(seed, "uniform_50")]["evaluations"]["post_F"]["F"]["error_by_bin"][angle] for seed in seeds])
        adaptive_values = np.asarray([indexed[(seed, "adaptive_replay")]["evaluations"]["post_F"]["F"]["error_by_bin"][angle] for seed in seeds])
        bin_gains.append(float(np.mean((uniform_values - adaptive_values) / np.maximum(uniform_values, 1e-8))))
        bin_worse.append(float(np.mean(adaptive_values / np.maximum(uniform_values, 1e-8) - 1.0)))
    h3a.update({"bin_relative_gains": bin_gains, "bin_relative_worse": bin_worse, "favorable_bins": int(np.sum(np.asarray(bin_gains) > 0))})
    h3b_difference = adaptive_f - naive_f
    h3b_margin = 0.05 * float(np.mean(naive_f))
    h3b = {
        "mean_absolute_difference": float(np.mean(h3b_difference)),
        "margin": h3b_margin,
        "p_exact_noninferiority": noninferiority_sign_flip_pvalue(h3b_difference, h3b_margin),
        "regional_relative": [],
    }
    for angle in STRUCTURED_BINS:
        ratios = [
            indexed[(seed, "adaptive_replay")]["evaluations"]["post_F"]["F"]["error_by_bin"][angle]
            / max(indexed[(seed, "naive")]["evaluations"]["post_F"]["F"]["error_by_bin"][angle], 1e-8)
            - 1.0
            for seed in seeds
        ]
        h3b["regional_relative"].append(float(np.mean(ratios)))
    h3_holm = holm_correction([h3a["p_exact_greater"], h3b["p_exact_noninferiority"]])
    h3a["p_holm"] = float(h3_holm[0])
    h3a["passed"] = bool(
        h3a["mean"] >= 0.05
        and h3a["bca_95"][0] > 0
        and h3a["p_holm"] <= 0.05
        and h3a["favorable_bins"] >= 5
        and max(h3a["bin_relative_worse"]) <= 0.05
    )
    h3b["p_holm"] = float(h3_holm[1])
    h3b["passed"] = bool(h3b["p_holm"] <= 0.05 and max(h3b["regional_relative"]) <= 0.10)
    analysis["h3a_plasticity_superiority"] = h3a
    analysis["h3b_current_noninferiority"] = h3b

    learner_failures = []
    for seed in seeds:
        for condition in CONDITIONS:
            evaluations = indexed[(seed, condition)]["evaluations"]
            for domain, phase in (("D", "post_D"), ("E", "post_E"), ("F", "post_F")):
                initial = evaluations["initial"][domain]["structured_error"]
                acquired = evaluations[phase][domain]["structured_error"]
                reduction = 1.0 - acquired / max(initial, 1e-8)
                if reduction < 0.20:
                    learner_failures.append({"seed": seed, "condition": condition, "domain": domain, "reduction": reduction})
    analysis["learner_guard"] = {"passed": not learner_failures, "failures": learner_failures}

    activation = {}
    for session in ("E", "F"):
        activated = []
        for seed in seeds:
            blocks = indexed[(seed, "adaptive_replay")]["training"][session]["blocks"][:-1]
            values = {float(block["applied_rho"]) for block in blocks}
            activated.append(len(values) >= 2 and any(0 < value < 0.5 for value in values))
        activation[session] = {"activated_seeds": int(sum(activated)), "passed": sum(activated) >= 12}
    analysis["activation_guard"] = activation

    tv_guard = {}
    for session in ("E", "F"):
        excesses = []
        empty = []
        for seed in seeds:
            adaptive_tv = indexed[(seed, "adaptive_replay")]["training"][session]["replay"]["effective_tv_fraction_among_replayed"]
            uniform_tv = indexed[(seed, "uniform_50")]["training"][session]["replay"]["effective_tv_fraction_among_replayed"]
            if adaptive_tv is None:
                empty.append(seed)
            else:
                excesses.append(float(adaptive_tv - uniform_tv))
        mean_excess = float(np.mean(excesses)) if excesses else None
        tv_guard[session] = {"mean_excess": mean_excess, "empty_adaptive_seeds": empty, "passed": bool(excesses and mean_excess <= 0.05)}
    analysis["tv_guard"] = tv_guard

    all_gates = (
        all(analysis["b1_forgetting_guard"][domain]["passed"] for domain in ("D", "E"))
        and all(analysis["h1_uniform_value"][domain]["passed"] for domain in ("D", "E"))
        and all(analysis["h2_retention_noninferiority"][domain]["passed"] for domain in ("D", "E"))
        and h3a["passed"]
        and h3b["passed"]
        and analysis["learner_guard"]["passed"]
        and all(item["passed"] for item in activation.values())
        and all(item["passed"] for item in tv_guard.values())
    )
    analysis["decision"] = {"adaptive_replay_eligible": bool(all_gates), "promotion_pending_claude_review": True}
    return analysis
