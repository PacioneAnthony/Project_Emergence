"""Action clipping and rate limiting before commands reach the robot body."""

from __future__ import annotations

from common.math_utils import clamp
from common.types import Action
from sim2d.config import RobotConfig


class SafetyLayer:
    def __init__(self, config: RobotConfig):
        self.config = config

    def apply(self, action: Action, dt: float | None = None) -> Action:
        return Action(
            v_cmd=clamp(action.v_cmd, -self.config.max_linear_speed, self.config.max_linear_speed),
            omega_cmd=clamp(action.omega_cmd, -self.config.max_angular_speed, self.config.max_angular_speed),
            servo_target=clamp(action.servo_target, self.config.servo_min, self.config.servo_max),
        )


class ZeroOrderHold:
    """Hold actuator commands between discrete controller/PWM updates."""

    def __init__(self, period: float):
        self.period = float(period)
        self.held_action = Action()
        self.next_update_time = 0.0

    def reset(self, initial_action: Action | None = None, time: float = 0.0) -> None:
        self.held_action = initial_action or Action()
        self.next_update_time = float(time)

    def apply(self, action: Action, time: float) -> Action:
        if self.period <= 0.0:
            self.held_action = action
            return self.held_action

        if float(time) + 1e-12 >= self.next_update_time:
            self.held_action = action
            while self.next_update_time <= float(time) + 1e-12:
                self.next_update_time += self.period
        return self.held_action
