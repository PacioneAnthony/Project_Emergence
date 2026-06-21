"""Configuration objects for the 2D simulator."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class WorldConfig:
    width: float = 4.0
    height: float = 3.0
    max_ultrasonic_range: float = 3.0
    obstacle_count: int = 4
    min_obstacle_radius: float = 0.12
    max_obstacle_radius: float = 0.30
    random_obstacles: bool = True
    fixed_obstacles: tuple[tuple[float, float, float], ...] = (
        (1.2, 1.7, 0.20),
        (2.3, 0.9, 0.24),
        (3.1, 2.1, 0.18),
    )


@dataclass
class RobotConfig:
    radius: float = 0.12
    max_linear_speed: float = 0.55
    max_angular_speed: float = 2.8
    max_linear_accel: float = 1.4
    max_angular_accel: float = 6.0
    servo_min: float = -math.pi / 2.0
    servo_max: float = math.pi / 2.0
    max_servo_speed: float = 3.5
    pwm_period: float = 0.02
    slip_std: float = 0.0


@dataclass
class SensorConfig:
    ultrasonic_noise_std: float = 0.015
    gyro_noise_std: float = 0.015
    gyro_bias_std: float = 0.01
    latency_seconds: float = 0.04
    dropout_probability: float = 0.0


@dataclass
class RewardConfig:
    alive_bonus: float = 0.01
    forward_weight: float = 0.05
    min_obstacle_distance: float = 0.25
    proximity_weight: float = 2.0
    collision_penalty: float = 3.0
    collision_ends_episode: bool = False


@dataclass
class SimConfig:
    dt: float = 0.02
    max_steps: int = 6000
    seed: int | None = None
    domain_randomization: bool = True
    world: WorldConfig = field(default_factory=WorldConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)
    sensors: SensorConfig = field(default_factory=SensorConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)


def default_config() -> SimConfig:
    return SimConfig()
