"""Small math helpers for robot control and geometry."""

from __future__ import annotations

import math


TAU = 2.0 * math.pi


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def wrap_angle(angle: float) -> float:
    """Wrap an angle to [-pi, pi)."""
    return (angle + math.pi) % TAU - math.pi


def shortest_angle_delta(target: float, current: float) -> float:
    return wrap_angle(target - current)


def lerp(a: float, b: float, alpha: float) -> float:
    return a + (b - a) * alpha
