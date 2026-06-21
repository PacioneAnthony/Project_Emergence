"""World geometry and ray casting for the 2D simulator."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np

from sim2d.config import WorldConfig


EPS = 1e-9


@dataclass(frozen=True)
class CircleObstacle:
    x: float
    y: float
    radius: float


class World:
    def __init__(self, config: WorldConfig | None = None, obstacles: Iterable[CircleObstacle] | None = None):
        self.config = config or WorldConfig()
        self.width = float(self.config.width)
        self.height = float(self.config.height)
        if obstacles is None:
            obstacles = [CircleObstacle(*item) for item in self.config.fixed_obstacles]
        self.obstacles = list(obstacles)

    @classmethod
    def generate(cls, config: WorldConfig, rng: np.random.Generator, robot_radius: float) -> "World":
        obstacles = [CircleObstacle(*item) for item in config.fixed_obstacles]

        if config.random_obstacles:
            attempts = 0
            target = max(0, config.obstacle_count)
            spawn_clearance = max(0.65, robot_radius * 4.0)
            while len(obstacles) < len(config.fixed_obstacles) + target and attempts < target * 80 + 80:
                attempts += 1
                radius = float(rng.uniform(config.min_obstacle_radius, config.max_obstacle_radius))
                x = float(rng.uniform(radius + robot_radius, config.width - radius - robot_radius))
                y = float(rng.uniform(radius + robot_radius, config.height - radius - robot_radius))

                spawn_dx = x - config.width * 0.5
                spawn_dy = y - config.height * 0.5
                if math.hypot(spawn_dx, spawn_dy) < spawn_clearance:
                    continue

                if any(math.hypot(x - obs.x, y - obs.y) < radius + obs.radius + 0.15 for obs in obstacles):
                    continue

                obstacles.append(CircleObstacle(x, y, radius))

        return cls(config, obstacles)

    def raycast(self, origin: tuple[float, float], angle: float, max_range: float | None = None) -> float:
        max_range = float(max_range if max_range is not None else self.config.max_ultrasonic_range)
        ox, oy = origin
        dx = math.cos(angle)
        dy = math.sin(angle)
        best = max_range

        # Axis-aligned world borders.
        if abs(dx) > EPS:
            for boundary_x in (0.0, self.width):
                t = (boundary_x - ox) / dx
                if 0.0 <= t <= best:
                    y = oy + t * dy
                    if 0.0 <= y <= self.height:
                        best = t

        if abs(dy) > EPS:
            for boundary_y in (0.0, self.height):
                t = (boundary_y - oy) / dy
                if 0.0 <= t <= best:
                    x = ox + t * dx
                    if 0.0 <= x <= self.width:
                        best = t

        # Circular obstacles.
        for obs in self.obstacles:
            fx = ox - obs.x
            fy = oy - obs.y
            b = 2.0 * (fx * dx + fy * dy)
            c = fx * fx + fy * fy - obs.radius * obs.radius
            discriminant = b * b - 4.0 * c
            if discriminant < 0.0:
                continue

            root = math.sqrt(discriminant)
            for t in ((-b - root) * 0.5, (-b + root) * 0.5):
                if 0.0 <= t <= best:
                    best = t

        return float(max(0.0, min(best, max_range)))

    def collides_circle(self, x: float, y: float, radius: float) -> bool:
        if x - radius < 0.0 or x + radius > self.width:
            return True
        if y - radius < 0.0 or y + radius > self.height:
            return True

        for obs in self.obstacles:
            if math.hypot(x - obs.x, y - obs.y) <= radius + obs.radius:
                return True

        return False

    def distance_to_nearest_surface(self, x: float, y: float, radius: float = 0.0) -> float:
        wall_distance = min(x, self.width - x, y, self.height - y) - radius
        obstacle_distance = math.inf
        for obs in self.obstacles:
            obstacle_distance = min(obstacle_distance, math.hypot(x - obs.x, y - obs.y) - obs.radius - radius)
        return float(min(wall_distance, obstacle_distance))
