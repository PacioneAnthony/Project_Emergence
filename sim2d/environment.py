"""Gym-like environment around the 2D robot simulation."""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from common.types import Action, Observation, RobotState
from sim2d.actuators import SafetyLayer, ZeroOrderHold
from sim2d.config import SimConfig
from sim2d.robot import Robot
from sim2d.sensors import GyroSensor, UltrasonicSensor
from sim2d.world import World


class RobotSimEnv:
    """Minimal simulation backend matching the future real robot contract."""

    def __init__(self, config: SimConfig | None = None):
        self.base_config = config or SimConfig()
        self.rng = np.random.default_rng(self.base_config.seed)
        self.config = copy.deepcopy(self.base_config)
        self.world = World.generate(self.config.world, self.rng, self.config.robot.radius)
        self.robot = Robot(self.config.robot)
        self.safety = SafetyLayer(self.config.robot)
        self.actuator_hold = ZeroOrderHold(self.config.robot.pwm_period)
        self.ultrasonic = UltrasonicSensor(self.config.sensors, self.config.world, self.config.dt)
        self.gyro = GyroSensor(self.config.sensors, self.config.dt)
        self.time = 0.0
        self.step_count = 0
        self.last_obs: Observation | None = None
        self.last_sensor_info: dict[str, float] = {}

    def reset(self, seed: int | None = None, state: RobotState | None = None) -> Observation:
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        self.config = self._episode_config()
        self.world = World.generate(self.config.world, self.rng, self.config.robot.radius)
        self.robot = Robot(self.config.robot)
        self.safety = SafetyLayer(self.config.robot)
        self.actuator_hold = ZeroOrderHold(self.config.robot.pwm_period)
        self.ultrasonic = UltrasonicSensor(self.config.sensors, self.config.world, self.config.dt)
        self.gyro = GyroSensor(self.config.sensors, self.config.dt)
        self.time = 0.0
        self.step_count = 0

        if state is None:
            state = self._sample_start_state()
        self.robot.reset(state)
        self.actuator_hold.reset(Action(servo_target=state.servo_angle), self.time)
        self.ultrasonic.reset(self.robot.state, self.world, self.rng)
        self.gyro.reset(self.robot.state, self.rng)
        self.last_obs = self._read_observation()
        return self.last_obs

    def step(self, action: Action | np.ndarray | list[float] | tuple[float, ...]) -> tuple[Observation, float, bool, dict[str, Any]]:
        if self.last_obs is None:
            self.reset()

        if not isinstance(action, Action):
            action = Action.from_array(action)

        safe_action = self.safety.apply(action, self.config.dt)
        actuator_action = self.actuator_hold.apply(safe_action, self.time)
        collision = self.robot.step(actuator_action, self.world, self.config.dt, self.rng)
        self.time += self.config.dt
        self.step_count += 1

        next_obs = self._read_observation()
        reward, reward_terms = self._reward(collision)
        done = self.step_count >= self.config.max_steps
        if collision and self.config.reward.collision_ends_episode:
            done = True

        info = {
            "state": self.robot.state,
            "collision": collision,
            "safe_action": safe_action,
            "actuator_action": actuator_action,
            "true_distance": self.ultrasonic.last_true_distance,
            "nearest_surface": self.world.distance_to_nearest_surface(
                self.robot.state.x,
                self.robot.state.y,
                self.config.robot.radius,
            ),
            "reward_terms": reward_terms,
        }
        self.last_obs = next_obs
        return next_obs, reward, done, info

    def _episode_config(self) -> SimConfig:
        cfg = copy.deepcopy(self.base_config)
        if not cfg.domain_randomization:
            return cfg

        cfg.sensors.ultrasonic_noise_std *= float(self.rng.uniform(0.5, 2.0))
        cfg.sensors.gyro_noise_std *= float(self.rng.uniform(0.5, 2.0))
        cfg.sensors.gyro_bias_std *= float(self.rng.uniform(0.5, 2.0))
        cfg.sensors.latency_seconds = float(self.rng.uniform(0.0, max(0.08, cfg.sensors.latency_seconds * 2.0)))
        cfg.robot.max_servo_speed *= float(self.rng.uniform(0.75, 1.25))
        cfg.robot.slip_std = float(self.rng.uniform(0.0, 0.05))
        cfg.world.obstacle_count = int(self.rng.integers(max(1, cfg.world.obstacle_count - 1), cfg.world.obstacle_count + 2))
        return cfg

    def _sample_start_state(self) -> RobotState:
        radius = self.config.robot.radius
        for _ in range(200):
            x = float(self.rng.uniform(radius + 0.2, self.config.world.width - radius - 0.2))
            y = float(self.rng.uniform(radius + 0.2, self.config.world.height - radius - 0.2))
            if not self.world.collides_circle(x, y, radius):
                return RobotState(x=x, y=y, heading=float(self.rng.uniform(-math.pi, math.pi)), servo_angle=0.0)

        return RobotState(
            x=self.config.world.width * 0.5,
            y=self.config.world.height * 0.5,
            heading=0.0,
            servo_angle=0.0,
        )

    def _read_observation(self) -> Observation:
        distance = self.ultrasonic.read(self.robot.state, self.world, self.rng)
        gyro_z = self.gyro.read(self.robot.state, self.rng)
        self.last_sensor_info = {
            "true_distance": float(self.ultrasonic.last_true_distance),
            "measured_distance": float(distance),
            "gyro_z": float(gyro_z),
        }
        return Observation(
            distance=float(distance),
            servo_angle=float(self.robot.state.servo_angle),
            gyro_z=float(gyro_z),
            time=float(self.time),
        )

    def _reward(self, collision: bool) -> tuple[float, dict[str, float]]:
        cfg = self.config.reward
        nearest = self.world.distance_to_nearest_surface(
            self.robot.state.x,
            self.robot.state.y,
            self.config.robot.radius,
        )
        forward = cfg.forward_weight * max(0.0, self.robot.state.v)
        proximity = -cfg.proximity_weight * max(0.0, cfg.min_obstacle_distance - nearest) ** 2
        collision_term = -cfg.collision_penalty if collision else 0.0
        reward = cfg.alive_bonus + forward + proximity + collision_term
        return float(reward), {
            "alive": float(cfg.alive_bonus),
            "forward": float(forward),
            "proximity": float(proximity),
            "collision": float(collision_term),
        }
