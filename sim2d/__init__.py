"""Minimal 2D robotics simulator for Project Emergence."""

from sim2d.config import SimConfig
from sim2d.environment import RobotSimEnv
from sim2d.world import CircleObstacle, World

__all__ = ["CircleObstacle", "RobotSimEnv", "SimConfig", "World"]
