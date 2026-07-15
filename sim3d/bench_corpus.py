"""Parallel visual corpus generation on the bench head digital twin.

Each worker process owns a BenchHeadEnv, runs whole episodes (one freshly
randomized room per episode) with varied motor babbling, and writes one NPZ
shard per episode: camera frames (uint8) plus the synchronized servo command,
AS5600 angle, raw gyro z and ultrasonic distance. A manifest.json describes
the corpus for the training side.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from common.math_utils import clamp


@dataclass(frozen=True)
class BenchCorpusSpec:
    episodes: int = 120
    seconds: float = 90.0
    capture_hz: float = 10.0
    image_size: int = 128
    base_seed: int = 7000
    output_dir: str = "data/raw/bench_visual_corpus"


def babbling_targets(rng: np.random.Generator, min_deg: float, max_deg: float, neutral: float, dt: float, steps: int) -> np.ndarray:
    """Mixed motor babbling: holds, sinusoidal scans and saccades with jitter."""

    targets = np.empty(steps, dtype=np.float64)
    index = 0
    current = neutral
    while index < steps:
        mode = rng.choice(("hold", "scan", "saccade"))
        segment = int(clamp(rng.uniform(1.0, 3.0) / dt, 1, steps - index))
        if mode == "hold":
            current = float(rng.uniform(min_deg, max_deg))
            targets[index : index + segment] = current
        elif mode == "scan":
            center = float(rng.uniform(min_deg + 20.0, max_deg - 20.0))
            amplitude = float(rng.uniform(10.0, min(center - min_deg, max_deg - center)))
            frequency = float(rng.uniform(0.1, 0.6))
            phase = float(rng.uniform(0.0, 2.0 * np.pi))
            t = np.arange(segment) * dt
            targets[index : index + segment] = center + amplitude * np.sin(2.0 * np.pi * frequency * t + phase)
            current = float(targets[index + segment - 1])
        else:  # saccade: jump then fixate with micro-jitter
            current = float(rng.uniform(min_deg, max_deg))
            jitter = rng.normal(0.0, 1.5, size=segment).cumsum() * 0.1
            targets[index : index + segment] = np.clip(current + jitter, min_deg, max_deg)
        index += segment
    return targets


def generate_episode(args: tuple[BenchCorpusSpec, int]) -> dict[str, Any]:
    """Worker entry point: one room, one babbling episode, one NPZ shard."""

    spec, episode_index = args
    from sim3d.bench_env import BenchHeadEnv
    from sim3d.bench_model import BenchConfig

    seed = spec.base_seed + episode_index
    env = generate_episode._env if getattr(generate_episode, "_env", None) is not None else BenchHeadEnv(BenchConfig(seed=seed))
    generate_episode._env = env

    obs = env.reset(seed=seed)
    config = env.config
    rng = np.random.default_rng(seed + 500_000)
    steps = max(1, round(spec.seconds / config.control_dt))
    capture_every = max(1, round(1.0 / (spec.capture_hz * config.control_dt)))
    targets = babbling_targets(
        rng,
        config.servo.min_deg,
        config.servo.max_deg,
        config.servo.neutral_deg,
        config.control_dt,
        steps,
    )

    frames: list[np.ndarray] = []
    requested: list[float] = []
    as5600: list[float] = []
    gyro_z: list[int] = []
    distance: list[float] = []
    times: list[float] = []

    for step in range(steps):
        obs = env.step(float(targets[step]))
        if step % capture_every == 0:
            frames.append(env.render_camera(spec.image_size, spec.image_size))
            requested.append(obs.requested_deg)
            as5600.append(obs.as5600_deg)
            gyro_z.append(obs.gyro_raw[2])
            distance.append(obs.distance_m)
            times.append(obs.time)

    shard_path = Path(spec.output_dir) / f"episode_{episode_index:04d}.npz"
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        shard_path,
        frames=np.stack(frames).astype(np.uint8),
        requested_deg=np.asarray(requested, dtype=np.float32),
        as5600_deg=np.asarray(as5600, dtype=np.float32),
        gyro_z_raw=np.asarray(gyro_z, dtype=np.int32),
        distance_m=np.asarray(distance, dtype=np.float32),
        t=np.asarray(times, dtype=np.float32),
        seed=np.int64(seed),
    )
    return {"episode": episode_index, "seed": seed, "frames": len(frames), "shard": shard_path.name}


generate_episode._env = None


def generate_corpus(spec: BenchCorpusSpec, workers: int | None = None) -> dict[str, Any]:
    output_dir = Path(spec.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"

    existing: dict[int, dict[str, Any]] = {}
    if manifest_path.exists():
        for item in json.loads(manifest_path.read_text(encoding="utf-8")).get("episodes_detail", []):
            if (output_dir / item["shard"]).exists():
                existing[int(item["episode"])] = item

    pending = [index for index in range(spec.episodes) if index not in existing]
    workers = max(1, min(workers or (os.cpu_count() or 1), max(1, len(pending))))

    started = time.perf_counter()
    if pending:
        jobs = [(spec, index) for index in pending]
        if workers == 1:
            results = [generate_episode(job) for job in jobs]
        else:
            context = multiprocessing.get_context("spawn")
            with context.Pool(processes=workers) as pool:
                results = pool.map(generate_episode, jobs, chunksize=1)
        for item in results:
            existing[int(item["episode"])] = item
    elapsed = time.perf_counter() - started

    detail = [existing[index] for index in sorted(existing)]
    manifest = {
        "spec": asdict(spec),
        "episodes": len(detail),
        "total_frames": int(sum(item["frames"] for item in detail)),
        "generated_now": len(pending),
        "wall_seconds": float(elapsed),
        "episodes_detail": detail,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
