"""Typed contracts used by the simulated and real robot backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Protocol, Sequence

import numpy as np


OBSERVATION_FIELDS = ("distance", "servo_angle", "gyro_z")
ACTION_FIELDS = ("v_cmd", "omega_cmd", "servo_target")
STATE_FIELDS = ("x", "y", "heading", "servo_angle", "v", "omega")


@dataclass
class Observation:
    """Minimal sensor packet: ultrasonic distance, servo pose, gyro yaw rate."""

    distance: float
    servo_angle: float
    gyro_z: float
    time: float = 0.0

    def as_array(self) -> np.ndarray:
        return np.array([self.distance, self.servo_angle, self.gyro_z], dtype=np.float32)

    def as_dict(self, prefix: str = "obs") -> Dict[str, float]:
        return {
            f"{prefix}_distance": float(self.distance),
            f"{prefix}_servo_angle": float(self.servo_angle),
            f"{prefix}_gyro_z": float(self.gyro_z),
        }


@dataclass
class Action:
    """Continuous control command for the virtual robot."""

    v_cmd: float = 0.0
    omega_cmd: float = 0.0
    servo_target: float = 0.0

    @classmethod
    def from_array(cls, values: Sequence[float]) -> "Action":
        if len(values) != 3:
            raise ValueError(f"Action expects 3 values, got {len(values)}")
        return cls(float(values[0]), float(values[1]), float(values[2]))

    def as_array(self) -> np.ndarray:
        return np.array([self.v_cmd, self.omega_cmd, self.servo_target], dtype=np.float32)

    def as_dict(self, prefix: str = "action") -> Dict[str, float]:
        return {
            f"{prefix}_v_cmd": float(self.v_cmd),
            f"{prefix}_omega_cmd": float(self.omega_cmd),
            f"{prefix}_servo_target": float(self.servo_target),
        }


@dataclass
class RobotState:
    x: float
    y: float
    heading: float
    servo_angle: float
    v: float = 0.0
    omega: float = 0.0

    def as_array(self) -> np.ndarray:
        return np.array(
            [self.x, self.y, self.heading, self.servo_angle, self.v, self.omega],
            dtype=np.float32,
        )

    def as_dict(self, prefix: str = "state") -> Dict[str, float]:
        return {
            f"{prefix}_x": float(self.x),
            f"{prefix}_y": float(self.y),
            f"{prefix}_heading": float(self.heading),
            f"{prefix}_servo_angle": float(self.servo_angle),
            f"{prefix}_v": float(self.v),
            f"{prefix}_omega": float(self.omega),
        }


@dataclass
class Transition:
    obs: Observation
    action: Action
    reward: float
    next_obs: Observation
    state: RobotState
    done: bool
    info: Dict[str, Any] = field(default_factory=dict)


class SensorInterface(Protocol):
    def read(self) -> Observation:
        ...


class ActuatorInterface(Protocol):
    def apply(self, action: Action) -> None:
        ...
