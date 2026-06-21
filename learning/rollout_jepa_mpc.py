"""Roll out an observation-only LNN with a frozen JEPA MPC-lite veto."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Any

import numpy as np

from common.types import Action, Observation
from learning.jepa_lnn_features import build_live_context_vector, load_jepa_bundle
from learning.rollout_lnn import (
    LNNPolicy,
    begin_rollout_episode,
    finalize_metrics,
    new_rollout_stats,
    update_rollout_stats,
)
from learning.train_lnn import resolve_device
from sim2d.config import RobotConfig, SimConfig
from sim2d.environment import RobotSimEnv
from sim2d.logger import CSVLogger

try:
    import torch
except ModuleNotFoundError:
    torch = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Roll out an LNN with a frozen JEPA MPC-lite action veto.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--jepa-checkpoint", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=1001)
    parser.add_argument("--dt", type=float, default=0.02)
    parser.add_argument("--pwm-period", type=float, default=0.02)
    parser.add_argument("--decision-interval", type=int, default=5)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--activation-distance", type=float, default=0.60)
    parser.add_argument("--risk-threshold", type=float, default=0.25)
    parser.add_argument("--min-improvement", type=float, default=0.08)
    parser.add_argument("--turn-delta", type=float, default=0.60)
    parser.add_argument("--action-deviation-penalty", type=float, default=0.08)
    parser.add_argument("--candidate-profile", choices=("slow_only", "conservative"), default="conservative")
    parser.add_argument("--output", type=Path, default=Path("data/raw/jepa_mpc_rollout.csv"))
    parser.add_argument("--metrics-output", type=Path, default=Path("data/processed/jepa_mpc_rollout/metrics.json"))
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


class JEPAMPCPolicy:
    def __init__(
        self,
        checkpoint: Path,
        jepa_checkpoint: Path,
        *,
        device_name: str,
        decision_interval: int,
        horizon: int,
        activation_distance: float,
        risk_threshold: float,
        min_improvement: float,
        turn_delta: float,
        action_deviation_penalty: float,
        candidate_profile: str,
    ):
        if torch is None:
            raise ModuleNotFoundError("PyTorch is required for JEPA MPC rollouts.")
        self.device = resolve_device(device_name)
        self.reflex = LNNPolicy(checkpoint, device_name)
        self.jepa = load_jepa_bundle(jepa_checkpoint, self.device)
        if self.jepa.model.obs_decoder is None:
            raise ValueError("S4 requires a JEPA checkpoint with an observation decoder.")
        self.decision_interval = int(decision_interval)
        self.horizon = int(horizon)
        self.activation_distance = float(activation_distance)
        self.risk_threshold = float(risk_threshold)
        self.min_improvement = float(min_improvement)
        self.turn_delta = float(turn_delta)
        self.action_deviation_penalty = float(action_deviation_penalty)
        self.candidate_profile = candidate_profile
        self.robot = RobotConfig()
        self.obs_history: deque[Observation] = deque(maxlen=self.jepa.context_steps - 1)
        self.action_history: deque[Action] = deque(maxlen=self.jepa.context_steps - 1)
        self.step_index = 0
        self.mode = "base"
        self.last_decision: dict[str, Any] | None = None
        self.decision_count = 0
        self.intervention_count = 0
        self.predicted_improvement_total = 0.0
        self.mode_counts: dict[str, int] = {}
        self.decision_mode_counts: dict[str, int] = {}
        self.active_decision_count = 0
        self.risky_base_decision_count = 0
        self.candidate_spread_total = 0.0
        self.candidate_spread_max = 0.0
        self.episode_index = -1
        self.intervention_records: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.episode_index += 1
        self.reflex.reset()
        self.obs_history.clear()
        self.action_history.clear()
        self.step_index = 0
        self.mode = "base"
        self.last_decision = None

    def __call__(self, obs: Observation) -> Action:
        base = self.reflex(obs)
        decision_due = self.step_index % self.decision_interval == 0
        if decision_due:
            self.mode, self.last_decision = self._select_mode(obs, base)
            self.decision_count += 1
            self.decision_mode_counts[self.mode] = self.decision_mode_counts.get(self.mode, 0) + 1
            if "candidate_distances" in self.last_decision:
                self.active_decision_count += 1
                spread = float(self.last_decision["candidate_spread"])
                self.candidate_spread_total += spread
                self.candidate_spread_max = max(self.candidate_spread_max, spread)
                if self.last_decision["base_predicted_min_distance"] < self.risk_threshold:
                    self.risky_base_decision_count += 1
            if self.mode != "base":
                self.intervention_count += 1
                self.predicted_improvement_total += float(self.last_decision["predicted_improvement"])
        action = candidate_action(self.mode, base, self.robot, self.turn_delta)
        if decision_due and self.mode != "base" and len(self.intervention_records) < 100:
            self.intervention_records.append(
                {
                    "episode": int(self.episode_index),
                    "step": int(self.step_index),
                    "observed_distance": float(obs.distance),
                    "selected_mode": self.mode,
                    "base_action": base.as_array().astype(float).tolist(),
                    "selected_action": action.as_array().astype(float).tolist(),
                    **self.last_decision,
                }
            )
        self.mode_counts[self.mode] = self.mode_counts.get(self.mode, 0) + 1
        self.step_index += 1
        return action

    def observe_applied(self, obs: Observation, actuator_action: Action) -> None:
        self.obs_history.append(obs)
        self.action_history.append(actuator_action)

    def _select_mode(self, obs: Observation, base: Action) -> tuple[str, dict[str, Any]]:
        modes = candidate_modes(self.candidate_profile)
        if obs.distance > self.activation_distance:
            return "base", {"reason": "inactive_distance", "predicted_improvement": 0.0}
        actions = [candidate_action(mode, base, self.robot, self.turn_delta) for mode in modes]
        context = build_live_context_vector(
            list(self.obs_history),
            list(self.action_history),
            obs,
            self.jepa.context_steps,
        )
        risks = predict_candidate_distances(self.jepa, context, actions, self.horizon, self.device)
        scores = score_candidates(risks, actions, base, self.robot, self.action_deviation_penalty)
        base_distance = float(risks[0])
        best_index = int(np.argmax(scores))
        best_distance = float(risks[best_index])
        improvement = best_distance - base_distance
        selected = "base"
        reason = "base_safe"
        if base_distance < self.risk_threshold and best_index != 0 and improvement >= self.min_improvement:
            selected = modes[best_index]
            reason = "veto"
        return selected, {
            "reason": reason,
            "base_predicted_min_distance": base_distance,
            "best_predicted_min_distance": best_distance,
            "predicted_improvement": improvement,
            "candidate_spread": float(np.max(risks) - np.min(risks)),
            "candidate_distances": {mode: float(value) for mode, value in zip(modes, risks)},
            "candidate_scores": {mode: float(value) for mode, value in zip(modes, scores)},
        }

    def mpc_metrics(self) -> dict[str, Any]:
        return {
            "decision_count": int(self.decision_count),
            "intervention_count": int(self.intervention_count),
            "intervention_rate": float(self.intervention_count / max(1, self.decision_count)),
            "mean_predicted_improvement_when_active": float(
                self.predicted_improvement_total / max(1, self.intervention_count)
            ),
            "mode_steps": dict(self.mode_counts),
            "decision_modes": dict(self.decision_mode_counts),
            "active_decision_count": int(self.active_decision_count),
            "risky_base_decision_count": int(self.risky_base_decision_count),
            "mean_candidate_spread": float(self.candidate_spread_total / max(1, self.active_decision_count)),
            "max_candidate_spread": float(self.candidate_spread_max),
            "intervention_records": list(self.intervention_records),
        }


def candidate_modes(profile: str = "conservative") -> tuple[str, ...]:
    if profile == "slow_only":
        return ("base", "slow")
    if profile == "conservative":
        return ("base", "slow", "left", "right")
    raise ValueError(f"Unknown candidate profile: {profile}")


def candidate_action(mode: str, base: Action, robot: RobotConfig, turn_delta: float) -> Action:
    v = float(np.clip(base.v_cmd, -robot.max_linear_speed, robot.max_linear_speed))
    omega = float(np.clip(base.omega_cmd, -robot.max_angular_speed, robot.max_angular_speed))
    servo = float(np.clip(base.servo_target, robot.servo_min, robot.servo_max))
    if mode == "base":
        return Action(v, omega, servo)
    if mode == "slow":
        return Action(float(np.clip(0.35 * v, -0.12, 0.12)), omega, servo)
    if mode == "left":
        return Action(float(np.clip(0.45 * v, -0.14, 0.14)), float(np.clip(omega + turn_delta, -robot.max_angular_speed, robot.max_angular_speed)), servo)
    if mode == "right":
        return Action(float(np.clip(0.45 * v, -0.14, 0.14)), float(np.clip(omega - turn_delta, -robot.max_angular_speed, robot.max_angular_speed)), servo)
    raise ValueError(f"Unknown MPC candidate mode: {mode}")


def score_candidates(
    distances: np.ndarray,
    actions: list[Action],
    base: Action,
    robot: RobotConfig,
    action_deviation_penalty: float,
) -> np.ndarray:
    """Prefer predicted clearance without rewarding large model-exploiting actions."""

    penalties = []
    for action in actions:
        v_delta = abs(action.v_cmd - base.v_cmd) / max(robot.max_linear_speed, 1e-6)
        omega_delta = abs(action.omega_cmd - base.omega_cmd) / max(robot.max_angular_speed, 1e-6)
        penalties.append(action_deviation_penalty * (v_delta + omega_delta))
    return np.asarray(distances, dtype=np.float32) - np.asarray(penalties, dtype=np.float32)


def predict_candidate_distances(bundle, context: np.ndarray, actions: list[Action], horizon: int, device) -> np.ndarray:
    if horizon <= 0:
        raise ValueError("horizon must be > 0.")
    context_t = torch.from_numpy(context).float().unsqueeze(0).to(device)
    action_t = torch.from_numpy(np.stack([action.as_array() for action in actions])).float().to(device)
    with torch.no_grad():
        latent = bundle.model.encode(context_t).repeat(len(actions), 1)
        minimum = torch.full((len(actions),), float("inf"), device=device)
        for _ in range(horizon):
            latent = bundle.model.predictor(torch.cat([latent, action_t], dim=-1))
            decoded = bundle.model.decode_observation(latent)
            minimum = torch.minimum(minimum, decoded[:, 0])
    return minimum.detach().cpu().numpy().astype(np.float32)


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)
    config = SimConfig(
        dt=args.dt,
        max_steps=args.steps,
        seed=args.seed,
        domain_randomization=not args.no_domain_randomization,
    )
    config.robot.pwm_period = args.pwm_period
    env = RobotSimEnv(config)
    policy = JEPAMPCPolicy(
        args.checkpoint,
        args.jepa_checkpoint,
        device_name=args.device,
        decision_interval=args.decision_interval,
        horizon=args.horizon,
        activation_distance=args.activation_distance,
        risk_threshold=args.risk_threshold,
        min_improvement=args.min_improvement,
        turn_delta=args.turn_delta,
        action_deviation_penalty=args.action_deviation_penalty,
        candidate_profile=args.candidate_profile,
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
                policy.observe_applied(obs, info["actuator_action"])
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
    metrics = finalize_metrics(stats, args, config)
    metrics["jepa_checkpoint"] = str(args.jepa_checkpoint)
    metrics["mpc"] = {
        "decision_interval": args.decision_interval,
        "horizon": args.horizon,
        "activation_distance": args.activation_distance,
        "risk_threshold": args.risk_threshold,
        "min_improvement": args.min_improvement,
        "turn_delta": args.turn_delta,
        "action_deviation_penalty": args.action_deviation_penalty,
        "candidate_profile": args.candidate_profile,
        **policy.mpc_metrics(),
    }
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"JEPA MPC rollout complete: steps={metrics['total_steps']} collisions={metrics['collision_ticks']} "
        f"events={metrics['collision_events']} interventions={metrics['mpc']['intervention_count']}",
        flush=True,
    )


def validate_args(args: argparse.Namespace) -> None:
    if args.episodes <= 0 or args.steps <= 0:
        raise ValueError("Episodes and steps must be > 0.")
    if args.decision_interval <= 0 or args.horizon <= 0:
        raise ValueError("Decision interval and horizon must be > 0.")
    if args.activation_distance <= 0.0 or args.risk_threshold <= 0.0:
        raise ValueError("Distance thresholds must be > 0.")
    if args.min_improvement < 0.0 or args.turn_delta <= 0.0 or args.action_deviation_penalty < 0.0:
        raise ValueError("Improvement and action penalty must be non-negative; turn delta must be positive.")


if __name__ == "__main__":
    main()
