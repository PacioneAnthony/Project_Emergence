"""Frozen D/E/F worlds for J6-AR001."""

from __future__ import annotations

from dataclasses import replace

from sim3d.bench_model import BenchConfig, BenchRoomConfig

DOMAINS = ("D", "E", "F")
STRUCTURED_CENTERS_DEG = (20.0, 40.0, 60.0, 80.0, 100.0, 120.0)


def adaptive_room_config(domain: str, *, belt: bool = True) -> BenchRoomConfig:
    base = BenchRoomConfig()
    pattern = None
    if domain == "D":
        pattern = "checker"
        room = replace(
            base,
            primary_light_rgb=(0.62, 0.70, 0.78),
            secondary_light_rgb=(0.34, 0.40, 0.46),
            headlight_ambient_rgb=(0.32, 0.35, 0.38),
            headlight_diffuse_rgb=(0.54, 0.60, 0.66),
            sector_belt_primary_rgba=(0.88, 0.04, 0.08, 1.0),
            sector_belt_secondary_rgba=(0.96, 0.96, 0.94, 1.0),
        )
    elif domain == "E":
        pattern = "vertical"
        room = replace(
            base,
            primary_light_rgb=tuple(0.65 * value for value in base.primary_light_rgb),
            secondary_light_rgb=tuple(0.65 * value for value in base.secondary_light_rgb),
            headlight_ambient_rgb=tuple(0.65 * value for value in base.headlight_ambient_rgb),
            headlight_diffuse_rgb=tuple(0.65 * value for value in base.headlight_diffuse_rgb),
            sector_belt_primary_rgba=(0.04, 0.82, 0.88, 1.0),
            sector_belt_secondary_rgba=(0.02, 0.05, 0.22, 1.0),
        )
    elif domain == "F":
        pattern = "horizontal"
        room = replace(
            base,
            primary_light_rgb=(1.00, 0.80, 0.615),
            secondary_light_rgb=(0.58, 0.45, 0.35),
            headlight_ambient_rgb=(0.44, 0.36, 0.25),
            headlight_diffuse_rgb=(0.76, 0.60, 0.44),
            sector_belt_primary_rgba=(0.98, 0.52, 0.03, 1.0),
            sector_belt_secondary_rgba=(0.48, 0.04, 0.68, 1.0),
        )
    else:
        raise ValueError(f"unknown J6-AR001 domain: {domain}")
    return replace(room, sector_belt_pattern=pattern if belt else None)


def adaptive_bench_config(domain: str, seed: int | None = None, *, belt: bool = True) -> BenchConfig:
    return BenchConfig(seed=seed, room=adaptive_room_config(domain, belt=belt))
