"""Configuration for the MuJoCo 3D simulator.

The 3D backend reuses `sim2d.config.SimConfig` for everything the learning
contract depends on (dt, robot limits, sensor noise, reward, world layout) and
only adds the parameters that exist because the world is now extruded in 3D.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import numpy as np

from sim2d.config import SimConfig


@dataclass
class Body3DConfig:
    """Geometry of the extruded world and robot body."""

    body_height: float = 0.10
    sensor_height: float = 0.09
    wall_height: float = 0.30
    wall_thickness: float = 0.05
    obstacle_height: float = 0.30
    # Radial offset of the rangefinder site from the robot center. Measured
    # distances are re-referenced to the robot center so they stay comparable
    # with sim2d, which raycasts from the center.
    sensor_radial_offset_margin: float = 0.005
    # Ultrasonic cone approximation: number of rays fanned over the half angle.
    # 1 ray reproduces the sim2d single-ray behaviour exactly.
    cone_rays: int = 1
    cone_half_angle: float = math.radians(15.0)
    physics_timestep: float = 0.002
    velocity_gain: float = 60.0
    servo_position_gain: float = 30.0


@dataclass
class Sim3DConfig:
    base: SimConfig = field(default_factory=SimConfig)
    body: Body3DConfig = field(default_factory=Body3DConfig)


def randomize_episode_config(base: SimConfig, rng: np.random.Generator) -> SimConfig:
    """Per-episode domain randomization, identical to sim2d.RobotSimEnv."""

    cfg = copy.deepcopy(base)
    if not cfg.domain_randomization:
        return cfg

    cfg.sensors.ultrasonic_noise_std *= float(rng.uniform(0.5, 2.0))
    cfg.sensors.gyro_noise_std *= float(rng.uniform(0.5, 2.0))
    cfg.sensors.gyro_bias_std *= float(rng.uniform(0.5, 2.0))
    cfg.sensors.latency_seconds = float(rng.uniform(0.0, max(0.08, cfg.sensors.latency_seconds * 2.0)))
    cfg.robot.max_servo_speed *= float(rng.uniform(0.75, 1.25))
    cfg.robot.slip_std = float(rng.uniform(0.0, 0.05))
    cfg.world.obstacle_count = int(rng.integers(max(1, cfg.world.obstacle_count - 1), cfg.world.obstacle_count + 2))
    return cfg
