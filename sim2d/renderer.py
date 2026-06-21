"""Matplotlib renderer for quick visual inspection of the simulator."""

from __future__ import annotations

import math
from pathlib import Path


class MatplotlibRenderer:
    def __init__(self):
        import matplotlib.pyplot as plt

        self.plt = plt
        self.fig, self.ax = plt.subplots(figsize=(7, 5))

    def render(self, env, save_path: str | Path | None = None, pause: float | None = None) -> None:
        from matplotlib.patches import Circle, Rectangle

        ax = self.ax
        ax.clear()
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(0.0, env.world.width)
        ax.set_ylim(0.0, env.world.height)
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(f"Emergence sim2d t={env.time:.2f}s")
        ax.add_patch(Rectangle((0.0, 0.0), env.world.width, env.world.height, fill=False, linewidth=2.0))

        for obs in env.world.obstacles:
            ax.add_patch(Circle((obs.x, obs.y), obs.radius, color="#555555", alpha=0.75))

        state = env.robot.state
        ax.add_patch(Circle((state.x, state.y), env.config.robot.radius, color="#2b7a78", alpha=0.85))
        heading_len = env.config.robot.radius * 1.8
        ax.arrow(
            state.x,
            state.y,
            math.cos(state.heading) * heading_len,
            math.sin(state.heading) * heading_len,
            head_width=0.04,
            color="#17252a",
            length_includes_head=True,
        )

        sensor_angle = state.heading + state.servo_angle
        ray_len = env.last_sensor_info.get("true_distance", 0.0)
        ax.plot(
            [state.x, state.x + math.cos(sensor_angle) * ray_len],
            [state.y, state.y + math.sin(sensor_angle) * ray_len],
            color="#ffb703",
            linewidth=2.0,
        )

        if save_path:
            self.fig.savefig(save_path, dpi=140, bbox_inches="tight")
        if pause is not None:
            self.plt.pause(pause)
