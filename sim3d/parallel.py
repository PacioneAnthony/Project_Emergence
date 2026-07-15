"""Episode-parallel simulation campaigns over multiple CPU processes.

Episodes are embarrassingly parallel here (no shared learner), so each worker
process owns one environment and runs whole episodes; the parent merges the
per-episode CSV shards and aggregates the same metrics as
`learning.rollout_lnn`. Per-episode results are bit-identical to a serial
run with the same seeds: an episode only depends on `reset(seed)`.

Lockstep batched stepping (RL-style vec-env) is intentionally not implemented:
without a learner in the loop it only adds per-step IPC, and its proper GPU
incarnation is MJX, kept for a future RL/population phase.
"""

from __future__ import annotations

import csv
import json
import multiprocessing
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sim2d.config import SimConfig
from sim2d.logger import CSVLogger
from sim2d.policies import RandomPolicy, WallAvoidancePolicy


@dataclass(frozen=True)
class CampaignSpec:
    """Picklable description of a rollout campaign (sent to workers)."""

    policy: str = "avoid"  # "avoid" | "random" | "lnn"
    checkpoint: str | None = None
    device: str = "cpu"
    backend: str = "sim3d"  # "sim3d" | "sim2d"
    episodes: int = 8
    steps: int = 6000
    base_seed: int = 1001
    dt: float | None = None
    pwm_period: float | None = None
    scan_hz: float = 0.5
    domain_randomization: bool = True
    collision_ends_episode: bool = False
    shard_dir: str = ""


def build_sim_config(spec: CampaignSpec) -> SimConfig:
    config = SimConfig(
        max_steps=spec.steps,
        domain_randomization=spec.domain_randomization,
    )
    if spec.dt is not None:
        config.dt = spec.dt
    if spec.pwm_period is not None:
        config.robot.pwm_period = spec.pwm_period
    config.reward.collision_ends_episode = spec.collision_ends_episode
    return config


_WORKER_ENV: dict[tuple, Any] = {}
_WORKER_POLICY: dict[tuple, Any] = {}


def _env_key(spec: CampaignSpec) -> tuple:
    return (spec.backend, spec.steps, spec.dt, spec.pwm_period, spec.domain_randomization, spec.collision_ends_episode)


def _get_env(spec: CampaignSpec):
    key = _env_key(spec)
    env = _WORKER_ENV.get(key)
    if env is None:
        config = build_sim_config(spec)
        if spec.backend == "sim3d":
            from sim3d.environment import RobotSim3DEnv

            env = RobotSim3DEnv(config)
        else:
            from sim2d.environment import RobotSimEnv

            env = RobotSimEnv(config)
        _WORKER_ENV.clear()
        _WORKER_ENV[key] = env
    return env


def _get_policy(spec: CampaignSpec, config: SimConfig, seed: int):
    if spec.policy == "avoid":
        return WallAvoidancePolicy(config.robot, scan_hz=spec.scan_hz)
    if spec.policy == "random":
        return RandomPolicy(config.robot, seed)
    if spec.policy != "lnn":
        raise ValueError(f"Unknown policy '{spec.policy}'")

    key = (spec.checkpoint, spec.device)
    policy = _WORKER_POLICY.get(key)
    if policy is None:
        from learning.rollout_lnn import LNNPolicy

        policy = LNNPolicy(Path(spec.checkpoint), spec.device)
        _WORKER_POLICY.clear()
        _WORKER_POLICY[key] = policy
    policy.reset()
    return policy


def run_episode(args: tuple[CampaignSpec, int]) -> dict[str, Any]:
    """Worker entry point: run one full episode and write its CSV shard."""

    spec, episode_index = args
    env = _get_env(spec)
    seed = spec.base_seed + episode_index
    obs = env.reset(seed=seed)
    policy = _get_policy(spec, env.config, seed)

    shard_path = Path(spec.shard_dir) / f"episode_{episode_index:05d}.csv"
    steps = 0
    reward_total = 0.0
    collision_ticks = 0
    collision_events = 0
    in_collision = False
    nearest_surface_min = float("inf")
    true_distance_min = float("inf")

    with CSVLogger(shard_path) as logger:
        for step in range(spec.steps):
            action = policy(obs)
            next_obs, reward, done, info = env.step(action)
            logger.write(episode_index, step, obs, action, next_obs, reward, done, info)

            collision = bool(info.get("collision", False))
            steps += 1
            reward_total += float(reward)
            collision_ticks += int(collision)
            if collision and not in_collision:
                collision_events += 1
            in_collision = collision
            nearest_surface_min = min(nearest_surface_min, float(info.get("nearest_surface", float("inf"))))
            true_distance_min = min(true_distance_min, float(info.get("true_distance", float("inf"))))

            obs = next_obs
            if done:
                break

    return {
        "episode": int(episode_index),
        "seed": int(seed),
        "steps": int(steps),
        "reward": float(reward_total),
        "collision_ticks": int(collision_ticks),
        "collision_events": int(collision_events),
        "nearest_surface_min": float(nearest_surface_min),
        "true_distance_min": float(true_distance_min),
        "shard": str(shard_path),
    }


def _merge_shards(episode_metrics: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(episode_metrics, key=lambda item: item["episode"])
    with output.open("w", newline="", encoding="utf-8") as merged:
        writer = None
        for item in ordered:
            with Path(item["shard"]).open("r", newline="", encoding="utf-8") as shard:
                reader = csv.reader(shard)
                header = next(reader)
                if writer is None:
                    writer = csv.writer(merged)
                    writer.writerow(header)
                for row in reader:
                    writer.writerow(row)


def run_campaign(
    spec: CampaignSpec,
    workers: int | None = None,
    output: Path | None = None,
    metrics_output: Path | None = None,
) -> dict[str, Any]:
    """Run `spec.episodes` episodes across worker processes and aggregate."""

    workers = max(1, min(workers or (os.cpu_count() or 1), spec.episodes))
    config = build_sim_config(spec)

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="sim_campaign_") as tmp_dir:
        sharded_spec = CampaignSpec(**{**asdict(spec), "shard_dir": tmp_dir})
        jobs = [(sharded_spec, index) for index in range(spec.episodes)]

        if workers == 1:
            episode_metrics = [run_episode(job) for job in jobs]
        else:
            context = multiprocessing.get_context("spawn")
            with context.Pool(processes=workers) as pool:
                episode_metrics = pool.map(run_episode, jobs, chunksize=1)

        if output is not None:
            _merge_shards(episode_metrics, output)
    elapsed = time.perf_counter() - started

    total_steps = sum(item["steps"] for item in episode_metrics)
    safe_total = max(1, total_steps)
    collision_ticks = sum(item["collision_ticks"] for item in episode_metrics)
    collision_events = sum(item["collision_events"] for item in episode_metrics)
    reward_total = sum(item["reward"] for item in episode_metrics)

    metrics = {
        "backend": spec.backend,
        "policy": spec.policy,
        "checkpoint": spec.checkpoint,
        "log": str(output) if output is not None else None,
        "episodes": int(spec.episodes),
        "steps_per_episode_limit": int(spec.steps),
        "total_steps": int(total_steps),
        "simulated_seconds": float(total_steps * config.dt),
        "reward_total": float(reward_total),
        "reward_mean_per_step": float(reward_total / safe_total),
        "collision_ticks": int(collision_ticks),
        "collision_rate": float(collision_ticks / safe_total),
        "collision_events": int(collision_events),
        "collision_events_per_1000_steps": float(1000.0 * collision_events / safe_total),
        "nearest_surface_min": float(min(item["nearest_surface_min"] for item in episode_metrics)),
        "true_distance_min": float(min(item["true_distance_min"] for item in episode_metrics)),
        "dt": float(config.dt),
        "pwm_period": float(config.robot.pwm_period),
        "domain_randomization": bool(spec.domain_randomization),
        "workers": int(workers),
        "wall_seconds": float(elapsed),
        "steps_per_second": float(total_steps / elapsed) if elapsed > 0 else 0.0,
        "episodes_detail": [
            {key: value for key, value in item.items() if key != "shard"}
            for item in sorted(episode_metrics, key=lambda item: item["episode"])
        ],
    }

    if metrics_output is not None:
        metrics_output.parent.mkdir(parents=True, exist_ok=True)
        metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
