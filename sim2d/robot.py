"""Robot body dynamics for the 2D simulator."""

from __future__ import annotations

import math

import numpy as np

from common.math_utils import clamp, shortest_angle_delta, wrap_angle
from common.types import Action, RobotState
from sim2d.config import RobotConfig
from sim2d.world import World


class Servo:
    def __init__(self, config: RobotConfig):
        self.config = config
        self.angle = 0.0

    def reset(self, angle: float = 0.0) -> None:
        self.angle = clamp(angle, self.config.servo_min, self.config.servo_max)

    def step(self, target: float, dt: float) -> float:
        target = clamp(target, self.config.servo_min, self.config.servo_max)
        max_delta = self.config.max_servo_speed * dt
        delta = clamp(shortest_angle_delta(target, self.angle), -max_delta, max_delta)
        self.angle = clamp(self.angle + delta, self.config.servo_min, self.config.servo_max)
        return self.angle


class Robot:
    def __init__(self, config: RobotConfig | None = None, state: RobotState | None = None):
        self.config = config or RobotConfig()
        self.servo = Servo(self.config)
        self.state = state or RobotState(x=0.0, y=0.0, heading=0.0, servo_angle=0.0)
        self.servo.reset(self.state.servo_angle)

    def reset(self, state: RobotState) -> None:
        self.state = state
        self.servo.reset(state.servo_angle)

    def step(self, action: Action, world: World, dt: float, rng: np.random.Generator) -> bool:
        cfg = self.config
        state = self.state

        v_delta = clamp(action.v_cmd - state.v, -cfg.max_linear_accel * dt, cfg.max_linear_accel * dt)
        omega_delta = clamp(action.omega_cmd - state.omega, -cfg.max_angular_accel * dt, cfg.max_angular_accel * dt)

        new_v = clamp(state.v + v_delta, -cfg.max_linear_speed, cfg.max_linear_speed)
        new_omega = clamp(state.omega + omega_delta, -cfg.max_angular_speed, cfg.max_angular_speed)
        new_servo_angle = self.servo.step(action.servo_target, dt)

        slip = 1.0
        if cfg.slip_std > 0.0:
            slip += float(rng.normal(0.0, cfg.slip_std))

        new_heading = wrap_angle(state.heading + new_omega * dt)
        new_x = state.x + new_v * slip * math.cos(new_heading) * dt
        new_y = state.y + new_v * slip * math.sin(new_heading) * dt

        collision = world.collides_circle(new_x, new_y, cfg.radius)
        if collision:
            new_x = state.x
            new_y = state.y
            new_v = 0.0

        self.state = RobotState(
            x=float(new_x),
            y=float(new_y),
            heading=float(new_heading),
            servo_angle=float(new_servo_angle),
            v=float(new_v),
            omega=float(new_omega),
        )
        return collision
