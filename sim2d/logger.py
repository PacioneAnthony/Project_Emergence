"""CSV logging for simulation trajectories."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from common.types import Action, Observation, RobotState


class CSVLogger:
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
        action: Action,
        next_obs: Observation,
        reward: float,
        done: bool,
        info: dict[str, Any],
    ) -> None:
        state = info.get("state")
        if not isinstance(state, RobotState):
            raise ValueError("Logger info must contain a RobotState under key 'state'")

        safe_action = info.get("safe_action", action)
        if not isinstance(safe_action, Action):
            safe_action = action
        actuator_action = info.get("actuator_action", safe_action)
        if not isinstance(actuator_action, Action):
            actuator_action = safe_action

        reward_terms = info.get("reward_terms", {})
        row = {
            "episode": episode,
            "step": step,
            "t": next_obs.time,
            **obs.as_dict("obs"),
            **action.as_dict("action"),
            **safe_action.as_dict("safe_action"),
            **actuator_action.as_dict("actuator_action"),
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
        }
        self.writer.writerow(row)

    def close(self) -> None:
        self.file.close()

    def __enter__(self) -> "CSVLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def _fieldnames() -> list[str]:
        return [
            "episode",
            "step",
            "t",
            "obs_distance",
            "obs_servo_angle",
            "obs_gyro_z",
            "action_v_cmd",
            "action_omega_cmd",
            "action_servo_target",
            "safe_action_v_cmd",
            "safe_action_omega_cmd",
            "safe_action_servo_target",
            "actuator_action_v_cmd",
            "actuator_action_omega_cmd",
            "actuator_action_servo_target",
            "next_obs_distance",
            "next_obs_servo_angle",
            "next_obs_gyro_z",
            "state_x",
            "state_y",
            "state_heading",
            "state_servo_angle",
            "state_v",
            "state_omega",
            "reward",
            "done",
            "collision",
            "true_distance",
            "nearest_surface",
            "reward_alive",
            "reward_forward",
            "reward_proximity",
            "reward_collision",
        ]
