"""Simple policies for generating first simulation logs before learning."""

from __future__ import annotations

import math

import numpy as np

from common.types import Action, Observation
from sim2d.config import RobotConfig


class RandomPolicy:
    def __init__(self, robot_config: RobotConfig, seed: int | None = None):
        self.robot_config = robot_config
        self.rng = np.random.default_rng(seed)

    def __call__(self, obs: Observation) -> Action:
        return Action(
            v_cmd=float(self.rng.uniform(-0.15, self.robot_config.max_linear_speed)),
            omega_cmd=float(self.rng.uniform(-self.robot_config.max_angular_speed, self.robot_config.max_angular_speed)),
            servo_target=float(self.rng.uniform(self.robot_config.servo_min, self.robot_config.servo_max)),
        )


class WallAvoidancePolicy:
    """A small hand-coded reflex policy for collecting safe bootstrap data."""

    def __init__(self, robot_config: RobotConfig, scan_hz: float = 0.5):
        self.robot_config = robot_config
        self.scan_hz = scan_hz

    def __call__(self, obs: Observation) -> Action:
        span = min(abs(self.robot_config.servo_min), abs(self.robot_config.servo_max))
        servo_target = span * math.sin(2.0 * math.pi * self.scan_hz * obs.time)

        if obs.distance < 0.38:
            side = 1.0 if obs.servo_angle >= 0.0 else -1.0
            return Action(
                v_cmd=-0.16,
                omega_cmd=-side * self.robot_config.max_angular_speed * 0.95,
                servo_target=servo_target,
            )

        if obs.distance < 0.80:
            side = 1.0 if obs.servo_angle >= 0.0 else -1.0
            return Action(
                v_cmd=0.08,
                omega_cmd=-side * self.robot_config.max_angular_speed * 0.60,
                servo_target=servo_target,
            )

        return Action(
            v_cmd=self.robot_config.max_linear_speed * 0.42,
            omega_cmd=0.12 * math.sin(0.45 * obs.time),
            servo_target=servo_target,
        )
