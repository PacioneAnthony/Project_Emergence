"""Frozen visual domains for J6-R001 sequential retention."""

from __future__ import annotations

from dataclasses import replace

from sim3d.bench_model import BenchConfig, BenchRoomConfig

DOMAINS = ("A", "B", "C")
LANDMARK_BINS = {"A": 1, "B": 4, "C": 2}


def j6_room_config(domain: str) -> BenchRoomConfig:
    base = BenchRoomConfig()
    if domain == "A":
        return replace(
            base,
            landmark_angle_deg=40.0,
            landmark_rgba=(0.90, 0.05, 0.05, 1.0),
        )
    if domain == "B":
        return replace(
            base,
            landmark_angle_deg=100.0,
            landmark_rgba=(0.90, 0.05, 0.05, 1.0),
            primary_light_rgb=tuple(0.70 * value for value in base.primary_light_rgb),
            secondary_light_rgb=tuple(0.70 * value for value in base.secondary_light_rgb),
            headlight_ambient_rgb=tuple(0.70 * value for value in base.headlight_ambient_rgb),
            headlight_diffuse_rgb=tuple(0.70 * value for value in base.headlight_diffuse_rgb),
        )
    if domain == "C":
        return replace(
            base,
            landmark_angle_deg=60.0,
            landmark_rgba=(0.90, 0.05, 0.05, 1.0),
            # Mean intensity is exactly 1.15 x nominal; unequal channels add
            # the frozen warm component before rendering.
            primary_light_rgb=(1.00, 0.80, 0.615),
            secondary_light_rgb=(0.58, 0.45, 0.35),
            headlight_ambient_rgb=(0.44, 0.36, 0.25),
            headlight_diffuse_rgb=(0.76, 0.60, 0.44),
        )
    raise ValueError(f"unknown J6 domain: {domain}")


def j6_bench_config(domain: str, seed: int | None = None, *, landmark: bool = True) -> BenchConfig:
    room = j6_room_config(domain)
    if not landmark:
        room = replace(room, landmark_angle_deg=None)
    return BenchConfig(seed=seed, room=room)
