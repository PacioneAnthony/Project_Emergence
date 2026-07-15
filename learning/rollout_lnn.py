"""Run a closed-loop simulator rollout with a trained standalone LNN policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from common.types import Action, Observation
from learning.train_lnn import action_scales_from_config, resolve_device
from learning.lnn import SimpleLNN
from sim2d.config import RobotConfig, SimConfig
from sim2d.environment import RobotSimEnv
from sim2d.logger import CSVLogger
from sim2d.renderer import MatplotlibRenderer

try:
    import torch
except ModuleNotFoundError:
    torch = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Roll out a trained LNN policy in the 2D simulator.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=909)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--pwm-period", type=float, default=None)
    parser.add_argument("--output", type=Path, default=Path("data/raw/lnn_rollout.csv"))
    parser.add_argument("--metrics-output", type=Path, default=Path("data/processed/lnn_rollout_metrics.json"))
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--collision-ends-episode", action="store_true")
    parser.add_argument("--backend", choices=("sim2d", "sim3d"), default="sim2d")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--render-every", type=int, default=2)
    parser.add_argument("--save-final-frame", type=Path, default=None)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


class LNNPolicy:
    def __init__(self, checkpoint_path: Path, device_name: str = "auto"):
        if torch is None:
            raise ModuleNotFoundError("PyTorch is required to run LNN rollouts.")

        self.device = resolve_device(device_name)
        self.checkpoint = load_checkpoint(checkpoint_path)
        self.dt = float(self.checkpoint.get("dt", 0.02))
        self.action_scales = np.array(
            self.checkpoint.get("action_scales") or action_scales_from_config(RobotConfig()).tolist(),
            dtype=np.float32,
        )
        self.action_scales_t = torch.from_numpy(self.action_scales).float().to(self.device)
        self.model = SimpleLNN(
            state_dim=int(self.checkpoint["state_dim"]),
            input_dim=int(self.checkpoint["input_dim"]),
            action_dim=int(self.checkpoint["action_dim"]),
            hidden_dim=int(self.checkpoint["hidden_dim"]),
            tau_min=float(self.checkpoint.get("tau_min", 0.05)),
            tau_max=float(self.checkpoint.get("tau_max", 1.5)),
        ).to(self.device)
        self.model.load_state_dict(self.checkpoint["model_state_dict"])
        self.model.eval()
        self.x = torch.zeros((1, int(self.checkpoint["state_dim"])), device=self.device)

    def reset(self) -> None:
        self.x = torch.zeros_like(self.x)

    def __call__(self, obs: Observation) -> Action:
        obs_t = torch.from_numpy(obs.as_array()).float().unsqueeze(0).to(self.device)
        with torch.no_grad():
            action_norm = self.model.act(self.x, obs_t)
            action = (action_norm * self.action_scales_t).squeeze(0).detach().cpu().numpy()
            self.x = self.model.step(self.x, obs_t, self.dt)
        return Action.from_array(action.tolist())


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

    if args.backend == "sim3d":
        from sim3d.environment import RobotSim3DEnv

        env = RobotSim3DEnv(config)
    else:
        env = RobotSimEnv(config)
    policy = LNNPolicy(args.checkpoint, args.device)
    renderer = (
        MatplotlibRenderer()
        if (args.render or args.save_final_frame) and args.backend == "sim2d"
        else None
    )
    stats = new_rollout_stats(args.episodes)

    with CSVLogger(args.output) as logger:
        for episode in range(args.episodes):
            obs = env.reset(seed=args.seed + episode)
            policy.reset()
            begin_rollout_episode(stats)
            episode_reward = 0.0
            episode_collisions = 0
            episode_steps = 0
            for step in range(args.steps):
                action = policy(obs)
                next_obs, reward, done, info = env.step(action)
                logger.write(episode, step, obs, action, next_obs, reward, done, info)

                update_rollout_stats(stats, reward, info)
                episode_reward += float(reward)
                episode_collisions += int(bool(info.get("collision", False)))
                episode_steps += 1

                if args.render and renderer is not None and step % max(1, args.render_every) == 0:
                    renderer.render(env, pause=0.001)
                elif args.render and args.backend == "sim3d":
                    env.sync_viewer()

                obs = next_obs
                if done:
                    break
            stats["episodes_detail"].append(
                {
                    "episode": int(episode),
                    "steps": int(episode_steps),
                    "reward": float(episode_reward),
                    "collision_ticks": int(episode_collisions),
                    "collision_events": int(stats["_episode_collision_events"]),
                }
            )

    if renderer is not None and args.save_final_frame:
        renderer.render(env, save_path=args.save_final_frame)
    elif args.backend == "sim3d" and args.save_final_frame:
        args.save_final_frame.parent.mkdir(parents=True, exist_ok=True)
        env.save_frame(str(args.save_final_frame))
    if args.backend == "sim3d":
        env.close()

    metrics = finalize_metrics(stats, args, config)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"LNN rollout complete: steps={metrics['total_steps']} "
        f"collision_ticks={metrics['collision_ticks']} reward={metrics['reward_total']:.3f} "
        f"log={args.output} metrics={args.metrics_output}",
        flush=True,
    )


def validate_args(args: argparse.Namespace) -> None:
    if args.episodes <= 0:
        raise ValueError("--episodes must be > 0.")
    if args.steps <= 0:
        raise ValueError("--steps must be > 0.")
    if args.render_every <= 0:
        raise ValueError("--render-every must be > 0.")


def load_checkpoint(path: Path) -> dict[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def new_rollout_stats(episodes: int) -> dict[str, Any]:
    return {
        "episodes": int(episodes),
        "total_steps": 0,
        "collision_ticks": 0,
        "collision_events": 0,
        "reward_total": 0.0,
        "nearest_surface_min": float("inf"),
        "true_distance_min": float("inf"),
        "episodes_detail": [],
        "_in_collision": False,
        "_episode_collision_events": 0,
    }


def begin_rollout_episode(stats: dict[str, Any]) -> None:
    stats["_in_collision"] = False
    stats["_episode_collision_events"] = 0


def update_rollout_stats(stats: dict[str, Any], reward: float, info: dict[str, Any]) -> None:
    collision = bool(info.get("collision", False))
    stats["total_steps"] += 1
    stats["reward_total"] += float(reward)
    stats["collision_ticks"] += int(collision)
    if collision and not bool(stats.get("_in_collision", False)):
        stats["collision_events"] += 1
        stats["_episode_collision_events"] = int(stats.get("_episode_collision_events", 0)) + 1
    stats["_in_collision"] = collision
    stats["nearest_surface_min"] = min(stats["nearest_surface_min"], float(info.get("nearest_surface", float("inf"))))
    stats["true_distance_min"] = min(stats["true_distance_min"], float(info.get("true_distance", float("inf"))))


def finalize_metrics(stats: dict[str, Any], args: argparse.Namespace, config: SimConfig) -> dict[str, Any]:
    total_steps = max(1, int(stats["total_steps"]))
    return {
        "checkpoint": str(args.checkpoint),
        "log": str(args.output),
        "backend": str(getattr(args, "backend", "sim2d")),
        "episodes": int(stats["episodes"]),
        "steps_per_episode_limit": int(args.steps),
        "total_steps": int(stats["total_steps"]),
        "simulated_seconds": float(stats["total_steps"] * config.dt),
        "reward_total": float(stats["reward_total"]),
        "reward_mean_per_step": float(stats["reward_total"] / total_steps),
        "collision_ticks": int(stats["collision_ticks"]),
        "collision_rate": float(stats["collision_ticks"] / total_steps),
        "collision_events": int(stats["collision_events"]),
        "collision_events_per_1000_steps": float(1000.0 * stats["collision_events"] / total_steps),
        "nearest_surface_min": float(stats["nearest_surface_min"]),
        "true_distance_min": float(stats["true_distance_min"]),
        "dt": float(config.dt),
        "pwm_period": float(config.robot.pwm_period),
        "domain_randomization": bool(config.domain_randomization),
        "episodes_detail": stats["episodes_detail"],
    }


if __name__ == "__main__":
    main()
