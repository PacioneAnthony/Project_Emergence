"""Collect DAgger-style LNN states relabelled by the simulator expert."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from common.types import Action, Observation, RobotState
from learning.rollout_lnn import LNNPolicy
from sim2d.actuators import SafetyLayer, ZeroOrderHold
from sim2d.config import SimConfig
from sim2d.environment import RobotSimEnv
from sim2d.logger import CSVLogger
from sim2d.policies import WallAvoidancePolicy


ACTION_NAMES = ("v_cmd", "omega_cmd", "servo_target")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Roll out a trained LNN in closed loop, but write expert labels for "
            "the visited states so the resulting CSV can be merged back into LNN training data."
        )
    )
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--policy-kind", choices=("lnn", "jepa-lnn"), default="lnn")
    parser.add_argument("--jepa-checkpoint", type=Path, default=None)
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=1201)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--pwm-period", type=float, default=None)
    parser.add_argument("--scan-hz", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path("data/raw/lnn_dagger_labels.csv"))
    parser.add_argument("--metrics-output", type=Path, default=Path("data/processed/lnn_dagger_labels_metrics.json"))
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--collision-ends-episode", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


class ExpertRelabelledCSVLogger:
    """CSV writer where canonical action columns are expert labels.

    The environment is still stepped with the student action. Extra student
    columns preserve what the LNN actually requested/applied for diagnostics.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self._fieldnames())
        self.writer.writeheader()

    def write(
        self,
        episode: int,
        step: int,
        obs: Observation,
        expert_action: Action,
        expert_safe_action: Action,
        expert_actuator_action: Action,
        student_action: Action,
        next_obs: Observation,
        reward: float,
        done: bool,
        info: dict[str, Any],
    ) -> None:
        state = info.get("state")
        if not isinstance(state, RobotState):
            raise ValueError("Logger info must contain a RobotState under key 'state'")

        student_safe_action = info.get("safe_action", student_action)
        if not isinstance(student_safe_action, Action):
            student_safe_action = student_action
        student_actuator_action = info.get("actuator_action", student_safe_action)
        if not isinstance(student_actuator_action, Action):
            student_actuator_action = student_safe_action

        reward_terms = info.get("reward_terms", {})
        row = {
            "episode": int(episode),
            "step": int(step),
            "t": float(next_obs.time),
            **obs.as_dict("obs"),
            **expert_action.as_dict("action"),
            **expert_safe_action.as_dict("safe_action"),
            **expert_actuator_action.as_dict("actuator_action"),
            **next_obs.as_dict("next_obs"),
            **state.as_dict("state"),
            "reward": float(reward),
            "done": int(bool(done)),
            "collision": int(bool(info.get("collision", False))),
            "true_distance": float(info.get("true_distance", 0.0)),
            "nearest_surface": float(info.get("nearest_surface", 0.0)),
            "reward_alive": float(reward_terms.get("alive", 0.0)),
            "reward_forward": float(reward_terms.get("forward", 0.0)),
            "reward_proximity": float(reward_terms.get("proximity", 0.0)),
            "reward_collision": float(reward_terms.get("collision", 0.0)),
            **student_action.as_dict("student_action"),
            **student_safe_action.as_dict("student_safe_action"),
            **student_actuator_action.as_dict("student_actuator_action"),
        }
        self.writer.writerow(row)

    def close(self) -> None:
        self.file.close()

    def __enter__(self) -> "ExpertRelabelledCSVLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def _fieldnames() -> list[str]:
        student_fields = []
        for prefix in ("student_action", "student_safe_action", "student_actuator_action"):
            student_fields.extend(f"{prefix}_{name}" for name in ACTION_NAMES)
        return CSVLogger._fieldnames() + student_fields


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)

    config = SimConfig(
        max_steps=args.steps,
        seed=args.seed,
        domain_randomization=not args.no_domain_randomization,
    )
    if args.dt is not None:
        config.dt = args.dt
    if args.pwm_period is not None:
        config.robot.pwm_period = args.pwm_period
    config.reward.collision_ends_episode = args.collision_ends_episode

    env = RobotSimEnv(config)
    student = build_student_policy(args)
    stats = new_aggregation_stats(args.episodes)

    with ExpertRelabelledCSVLogger(args.output) as logger:
        for episode in range(args.episodes):
            obs = env.reset(seed=args.seed + episode)
            student.reset()

            expert_policy = WallAvoidancePolicy(env.config.robot, scan_hz=args.scan_hz)
            expert_safety = SafetyLayer(env.config.robot)
            expert_hold = ZeroOrderHold(env.config.robot.pwm_period)
            expert_hold.reset(Action(servo_target=env.robot.state.servo_angle), env.time)

            episode_reward = 0.0
            episode_collisions = 0
            episode_steps = 0
            for step in range(args.steps):
                student_action = student(obs)
                expert_action, expert_safe, expert_actuator = expert_label_for_observation(
                    expert_policy=expert_policy,
                    expert_safety=expert_safety,
                    expert_hold=expert_hold,
                    obs=obs,
                    time=env.time,
                    dt=env.config.dt,
                )
                next_obs, reward, done, info = env.step(student_action)
                observe_student_step(student, info, student_action)
                logger.write(
                    episode,
                    step,
                    obs,
                    expert_action,
                    expert_safe,
                    expert_actuator,
                    student_action,
                    next_obs,
                    reward,
                    done,
                    info,
                )

                update_aggregation_stats(stats, reward, info, student_action, expert_actuator)
                episode_reward += float(reward)
                episode_collisions += int(bool(info.get("collision", False)))
                episode_steps += 1

                obs = next_obs
                if done:
                    break

            stats["episodes_detail"].append(
                {
                    "episode": int(episode),
                    "steps": int(episode_steps),
                    "reward": float(episode_reward),
                    "collision_ticks": int(episode_collisions),
                }
            )
            print(
                f"episode={episode + 1}/{args.episodes} steps={episode_steps} "
                f"collision_ticks={episode_collisions} reward={episode_reward:.3f}",
                flush=True,
            )

    metrics = finalize_aggregation_metrics(stats, args, config)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"DAgger aggregation complete: steps={metrics['total_steps']} "
        f"collision_ticks={metrics['collision_ticks']} "
        f"student_expert_rmse={metrics['student_expert_rmse_mean']:.6f} "
        f"log={args.output} metrics={args.metrics_output}",
        flush=True,
    )


def validate_args(args: argparse.Namespace) -> None:
    if args.episodes <= 0:
        raise ValueError("--episodes must be > 0.")
    if args.steps <= 0:
        raise ValueError("--steps must be > 0.")
    if args.scan_hz <= 0.0:
        raise ValueError("--scan-hz must be > 0.")
    if args.policy_kind == "jepa-lnn" and args.jepa_checkpoint is not None and not args.jepa_checkpoint.exists():
        raise FileNotFoundError(f"JEPA checkpoint not found: {args.jepa_checkpoint}")


def build_student_policy(args: argparse.Namespace):
    if args.policy_kind == "jepa-lnn":
        from learning.rollout_jepa_lnn import JEPALNNPolicy

        return JEPALNNPolicy(args.checkpoint, args.jepa_checkpoint, args.device)
    return LNNPolicy(args.checkpoint, args.device)


def observe_student_step(student, info: dict[str, Any], fallback_action: Action) -> None:
    observe = getattr(student, "observe_step", None)
    if callable(observe):
        observe(info, fallback_action)


def expert_label_for_observation(
    expert_policy: WallAvoidancePolicy,
    expert_safety: SafetyLayer,
    expert_hold: ZeroOrderHold,
    obs: Observation,
    time: float,
    dt: float,
) -> tuple[Action, Action, Action]:
    raw = expert_policy(obs)
    safe = expert_safety.apply(raw, dt)
    actuator = expert_hold.apply(safe, time)
    return raw, safe, actuator


def new_aggregation_stats(episodes: int) -> dict[str, Any]:
    return {
        "episodes": int(episodes),
        "total_steps": 0,
        "collision_ticks": 0,
        "reward_total": 0.0,
        "nearest_surface_min": float("inf"),
        "true_distance_min": float("inf"),
        "student_expert_squared_error": np.zeros(3, dtype=np.float64),
        "student_expert_absolute_error": np.zeros(3, dtype=np.float64),
        "episodes_detail": [],
    }


def update_aggregation_stats(
    stats: dict[str, Any],
    reward: float,
    info: dict[str, Any],
    student_action: Action,
    expert_actuator_action: Action,
) -> None:
    stats["total_steps"] += 1
    stats["reward_total"] += float(reward)
    stats["collision_ticks"] += int(bool(info.get("collision", False)))
    stats["nearest_surface_min"] = min(stats["nearest_surface_min"], float(info.get("nearest_surface", float("inf"))))
    stats["true_distance_min"] = min(stats["true_distance_min"], float(info.get("true_distance", float("inf"))))

    error = student_action.as_array().astype(np.float64) - expert_actuator_action.as_array().astype(np.float64)
    stats["student_expert_squared_error"] += error**2
    stats["student_expert_absolute_error"] += np.abs(error)


def finalize_aggregation_metrics(stats: dict[str, Any], args: argparse.Namespace, config: SimConfig) -> dict[str, Any]:
    total_steps = max(1, int(stats["total_steps"]))
    rmse = np.sqrt(stats["student_expert_squared_error"] / total_steps)
    mae = stats["student_expert_absolute_error"] / total_steps
    return {
        "checkpoint": str(args.checkpoint),
        "policy_kind": str(getattr(args, "policy_kind", "lnn")),
        "jepa_checkpoint": str(args.jepa_checkpoint) if getattr(args, "jepa_checkpoint", None) is not None else None,
        "log": str(args.output),
        "episodes": int(stats["episodes"]),
        "steps_per_episode_limit": int(args.steps),
        "total_steps": int(stats["total_steps"]),
        "simulated_seconds": float(stats["total_steps"] * config.dt),
        "reward_total": float(stats["reward_total"]),
        "reward_mean_per_step": float(stats["reward_total"] / total_steps),
        "collision_ticks": int(stats["collision_ticks"]),
        "collision_rate": float(stats["collision_ticks"] / total_steps),
        "nearest_surface_min": float(stats["nearest_surface_min"]),
        "true_distance_min": float(stats["true_distance_min"]),
        "dt": float(config.dt),
        "pwm_period": float(config.robot.pwm_period),
        "scan_hz": float(args.scan_hz),
        "domain_randomization": bool(config.domain_randomization),
        "student_expert_rmse_mean": float(np.mean(rmse)),
        "student_expert_per_action": {
            name: {"rmse": float(rmse[i]), "mae": float(mae[i])} for i, name in enumerate(ACTION_NAMES)
        },
        "episodes_detail": stats["episodes_detail"],
    }


if __name__ == "__main__":
    main()
