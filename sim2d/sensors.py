"""Simulated ultrasonic and gyro sensors with noise and latency."""

from __future__ import annotations

from collections import deque
import math

import numpy as np

from sim2d.config import SensorConfig, WorldConfig
from sim2d.world import World
from common.types import RobotState


class LatencyLine:
    def __init__(self, latency_steps: int):
        self.latency_steps = max(0, int(latency_steps))
        self.values: deque[float] = deque(maxlen=self.latency_steps + 1)

    def reset(self, value: float) -> None:
        self.values.clear()
        for _ in range(self.latency_steps + 1):
            self.values.append(float(value))

    def push(self, value: float) -> float:
        self.values.append(float(value))
        return float(self.values[0])


class UltrasonicSensor:
    def __init__(self, sensor_config: SensorConfig, world_config: WorldConfig, dt: float):
        self.sensor_config = sensor_config
        self.world_config = world_config
        self.line = LatencyLine(round(sensor_config.latency_seconds / dt))
        self.last_true_distance = world_config.max_ultrasonic_range

    def reset(self, state: RobotState, world: World, rng: np.random.Generator) -> None:
        true_distance = self._measure_true(state, world)
        self.last_true_distance = true_distance
        self.line.reset(true_distance)

    def _measure_true(self, state: RobotState, world: World) -> float:
        sensor_angle = state.heading + state.servo_angle
        return world.raycast((state.x, state.y), sensor_angle, self.world_config.max_ultrasonic_range)

    def read(self, state: RobotState, world: World, rng: np.random.Generator) -> float:
        true_distance = self._measure_true(state, world)
        self.last_true_distance = true_distance

        if rng.random() < self.sensor_config.dropout_probability:
            measured = self.world_config.max_ultrasonic_range
        else:
            measured = true_distance + float(rng.normal(0.0, self.sensor_config.ultrasonic_noise_std))

        measured = max(0.0, min(float(measured), self.world_config.max_ultrasonic_range))
        return self.line.push(measured)


class GyroSensor:
    def __init__(self, sensor_config: SensorConfig, dt: float):
        self.sensor_config = sensor_config
        self.line = LatencyLine(round(sensor_config.latency_seconds / dt))
        self.bias = 0.0

    def reset(self, state: RobotState, rng: np.random.Generator) -> None:
        self.bias = float(rng.normal(0.0, self.sensor_config.gyro_bias_std))
        self.line.reset(state.omega + self.bias)

    def read(self, state: RobotState, rng: np.random.Generator) -> float:
        measured = state.omega + self.bias + float(rng.normal(0.0, self.sensor_config.gyro_noise_std))
        if not math.isfinite(measured):
            measured = 0.0
        return self.line.push(measured)
