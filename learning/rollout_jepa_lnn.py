"""Run a closed-loop simulator rollout with an LNN conditioned by frozen JEPA latents."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from common.types import Action, Observation
from learning.jepa_lnn_features import (
    build_live_context_vector,
    build_live_lnn_input,
    build_lnn_input_from_latent,
    compute_jepa_latent_mean,
    load_jepa_bundle,
)
from learning.lnn import SimpleLNN
from learning.rollout_lnn import begin_rollout_episode, finalize_metrics, new_rollout_stats, update_rollout_stats
from learning.train_lnn import action_scales_from_config, resolve_device
from sim2d.config import RobotConfig, SimConfig
from sim2d.environment import RobotSimEnv
from sim2d.logger import CSVLogger
from sim2d.renderer import MatplotlibRenderer

try:
    import torch
except ModuleNotFoundError:
    torch = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Roll out a trained JEPA-conditioned LNN policy in the 2D simulator.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--jepa-checkpoint", type=Path, default=None)
    parser.add_argument("--latent-mode", choices=("dynamic", "zero", "mean"), default="dynamic")
    parser.add_argument(
        "--latent-mean-log",
        type=Path,
        default=None,
        help="Training log used to compute the frozen mean latent when --latent-mode=mean.",
    )
    parser.add_argument("--latent-mean-batch-size", type=int, default=4096)
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=909)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--pwm-period", type=float, default=None)
    parser.add_argument("--output", type=Path, default=Path("data/raw/jepa_lnn_rollout.csv"))
    parser.add_argument("--metrics-output", type=Path, default=Path("data/processed/jepa_lnn_rollout_metrics.json"))
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--collision-ends-episode", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--render-every", type=int, default=2)
    parser.add_argument("--save-final-frame", type=Path, default=None)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


class JEPALNNPolicy:
    def __init__(
        self,
        checkpoint_path: Path,
        jepa_checkpoint_path: Path | None = None,
        device_name: str = "auto",
        latent_mode: str = "dynamic",
        latent_mean_log: Path | None = None,
        latent_mean_batch_size: int = 4096,
    ):
        if torch is None:
            raise ModuleNotFoundError("PyTorch is required to run JEPA-LNN rollouts.")

        self.device = resolve_device(device_name)
        self.checkpoint = load_checkpoint(checkpoint_path)
        checkpoint_jepa = self.checkpoint.get("jepa_checkpoint")
        resolved_jepa = jepa_checkpoint_path or (Path(checkpoint_jepa) if checkpoint_jepa else None)
        if resolved_jepa is None:
            raise ValueError("JEPA-LNN checkpoint does not contain jepa_checkpoint; pass --jepa-checkpoint explicitly.")

        self.jepa = load_jepa_bundle(resolved_jepa, self.device)
        self.context_steps = int(self.checkpoint.get("jepa_context_steps", self.jepa.context_steps))
        self.latent_mode = latent_mode
        self.latent_mean_meta: dict[str, Any] | None = None
        self.fixed_latent = None
        if latent_mode == "zero":
            self.fixed_latent = np.zeros(self.jepa.latent_dim, dtype=np.float32)
        elif latent_mode == "mean":
            if latent_mean_log is None:
                raise ValueError("latent_mean_log is required when latent_mode='mean'.")
            self.fixed_latent, self.latent_mean_meta = compute_jepa_latent_mean(
                latent_mean_log,
                self.jepa.checkpoint_path,
                device=self.device,
                batch_size=latent_mean_batch_size,
            )
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
        self.obs_history: deque[Observation] = deque(maxlen=max(1, self.context_steps - 1))
        self.action_history: deque[Action] = deque(maxlen=max(0, self.context_steps - 1))

    def reset(self) -> None:
        self.x = torch.zeros_like(self.x)
        self.obs_history.clear()
        self.action_history.clear()

    def __call__(self, obs: Observation) -> Action:
        if self.latent_mode == "dynamic":
            context = build_live_context_vector(
                obs_history=list(self.obs_history),
                action_history=list(self.action_history),
                current_obs=obs,
                context_steps=self.context_steps,
            )
            lnn_input = build_live_lnn_input(self.jepa, context, obs, self.device)
        else:
            lnn_input = build_lnn_input_from_latent(obs, self.fixed_latent)
        input_t = torch.from_numpy(lnn_input).float().unsqueeze(0).to(self.device)
        with torch.no_grad():
            action_norm = self.model.act(self.x, input_t)
            action = (action_norm * self.action_scales_t).squeeze(0).detach().cpu().numpy()
            self.x = self.model.step(self.x, input_t, self.dt)
        self.obs_history.append(obs)
        return Action.from_array(action.tolist())

    def observe_step(self, info: dict[str, Any], fallback_action: Action) -> None:
        actuator_action = info.get("actuator_action", fallback_action)
        if not isinstance(actuator_action, Action):
            actuator_action = fallback_action
        self.action_history.append(actuator_action)


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
    policy = JEPALNNPolicy(
        args.checkpoint,
        args.jepa_checkpoint,
        args.device,
        latent_mode=args.latent_mode,
        latent_mean_log=args.latent_mean_log,
        latent_mean_batch_size=args.latent_mean_batch_size,
    )
    renderer = MatplotlibRenderer() if args.render or args.save_final_frame else None
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
                policy.observe_step(info, action)
                logger.write(episode, step, obs, action, next_obs, reward, done, info)

                update_rollout_stats(stats, reward, info)
                episode_reward += float(reward)
                episode_collisions += int(bool(info.get("collision", False)))
                episode_steps += 1

                if args.render and renderer is not None and step % max(1, args.render_every) == 0:
                    renderer.render(env, pause=0.001)

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

    metrics = finalize_metrics(stats, args, config)
    metrics["jepa_checkpoint"] = str(policy.jepa.checkpoint_path)
    metrics["jepa_context_steps"] = int(policy.context_steps)
    metrics["latent_mode"] = str(policy.latent_mode)
    metrics["latent_mean"] = policy.latent_mean_meta
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"JEPA-LNN rollout complete: steps={metrics['total_steps']} "
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
    if args.latent_mean_batch_size <= 0:
        raise ValueError("--latent-mean-batch-size must be > 0.")
    if args.latent_mode == "mean" and args.latent_mean_log is None:
        raise ValueError("--latent-mean-log is required when --latent-mode=mean.")
    if args.latent_mean_log is not None and not args.latent_mean_log.exists():
        raise FileNotFoundError(f"Latent mean log not found: {args.latent_mean_log}")
    if not args.checkpoint.exists():
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint}")
    if args.jepa_checkpoint is not None and not args.jepa_checkpoint.exists():
        raise FileNotFoundError(f"JEPA checkpoint not found: {args.jepa_checkpoint}")


def load_checkpoint(path: Path) -> dict[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


if __name__ == "__main__":
    main()
