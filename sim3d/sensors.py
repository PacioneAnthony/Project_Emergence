"""Sensor noise pipeline for the 3D backend.

The true ultrasonic distance now comes from MuJoCo rangefinders instead of a
2D raycast; noise, dropout and latency reproduce sim2d exactly. The gyro is
reused directly from sim2d (`sim2d.sensors.GyroSensor`).
"""

from __future__ import annotations

import numpy as np

from sim2d.config import SensorConfig, WorldConfig
from sim2d.sensors import LatencyLine


class Ultrasonic3DSensor:
    def __init__(self, sensor_config: SensorConfig, world_config: WorldConfig, dt: float):
        self.sensor_config = sensor_config
        self.world_config = world_config
        self.line = LatencyLine(round(sensor_config.latency_seconds / dt))
        self.last_true_distance = world_config.max_ultrasonic_range

    def reset(self, true_distance: float) -> None:
        self.last_true_distance = float(true_distance)
        self.line.reset(float(true_distance))

    def read(self, true_distance: float, rng: np.random.Generator) -> float:
        self.last_true_distance = float(true_distance)

        if rng.random() < self.sensor_config.dropout_probability:
            measured = self.world_config.max_ultrasonic_range
        else:
            measured = true_distance + float(rng.normal(0.0, self.sensor_config.ultrasonic_noise_std))

        measured = max(0.0, min(float(measured), self.world_config.max_ultrasonic_range))
        return self.line.push(measured)
