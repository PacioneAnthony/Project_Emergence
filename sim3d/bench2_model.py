"""Two-axis neck for the bench digital twin: pan plus tilt, under D-060.

The one-axis bench of `sim3d.bench_model` is frozen: its bytes are referenced by
116 manifests, so it is reused and never rewritten (D-061). This module takes the
MJCF that `build_bench_mjcf` produces and performs two anchored transformations:

1. the head camera and its barrel move into a nested body carried by a tilt
   hinge, horizontal and perpendicular to the viewing direction and running
   through the barrel, so the moving body is balanced about it -- which is where
   a real pan-tilt bracket puts it. The axis is `0 -1 0`, not `0 1 0`: the camera
   looks along the head's +x, so a right-handed rotation about +y would tip it
   *down* and a positive command would lower the view, the opposite of what any
   caller assumes;
2. a second position actuator drives that hinge.

At zero tilt the camera pose is identical to the frozen bench -- verified
pixel-exact, not asserted -- so the two-axis world differs from the one-axis
world by the tilt joint and by nothing else.

Why the second axis exists. A 30 degree field over 160 degrees of pan gives about
5.3 distinct views, which is not a spatial memory. Adding 60 degrees of tilt
travel puts the view centers on a 5 x 3 grid: fifteen cells, and an angle that
points at a portion of the world rather than being the state of the world.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from sim3d import bench_model
from sim3d.bench_model import BenchConfig, RoomObject

# Barrel center in the head frame; the frozen bench puts the lens 20 mm in front.
X_BARREL = -0.020

BODY_TILT = "bench_head_tilt"
JOINT_TILT = "neck_tilt"
ACT_TILT = "neck_tilt_pos"

# Re-exported so callers need only one import.
BODY_HEAD = bench_model.HEAD_BODY
JOINT_PAN = bench_model.JOINT_SERVO
ACT_PAN = bench_model.ACT_SERVO
CAMERA_HEAD = bench_model.CAMERA_HEAD


@dataclass
class BenchTiltConfig:
    """Second MG90S-class servo, tilting the camera about the head's y axis.

    Angles are relative to the horizontal: 0 is level, positive looks up. The
    +/-30 degree travel is what turns 5.3 pan views into a 5 x 3 grid; it is not
    a mechanical measurement, and no such bracket has been built (D-008).
    """

    min_deg: float = -30.0
    max_deg: float = 30.0
    neutral_deg: float = 0.0
    max_speed_deg_s: float = 600.0
    position_gain: float = 10.0
    velocity_damping: float = 0.15
    drive_forcerange_nm: float = 0.5
    joint_damping: float = 0.004
    joint_frictionloss: float = 0.0147
    joint_armature: float = 2.0e-4


@dataclass
class Bench2Config(BenchConfig):
    """A `BenchConfig` plus the tilt axis. Every inherited field keeps its value.

    `extra_mjcf` is appended to the wall-panel string that `build_bench_mjcf`
    already accepts, which is how a task puts content in cells without touching
    the frozen bench. See `sim3d.bench2_content`.
    """

    tilt: BenchTiltConfig = field(default_factory=BenchTiltConfig)
    extra_mjcf: str = ""


# --------------------------------------------------------------------- cells


def view_cells(config: Bench2Config) -> list[tuple[float, float]]:
    """Cell centers, spaced one field of view apart and clipped to both ranges.

    Returned row-major: tilt descending (top row first), pan ascending, so the
    list reads like the grid looks.
    """

    fov = config.sensors.camera_fovy_deg
    pans = _centers(config.servo.neutral_deg, config.servo.min_deg, config.servo.max_deg, fov)
    tilts = _centers(config.tilt.neutral_deg, config.tilt.min_deg, config.tilt.max_deg, fov)
    return [(pan, tilt) for tilt in reversed(tilts) for pan in pans]


def _centers(neutral: float, low: float, high: float, step: float) -> list[float]:
    """Centers at neutral + k*step that stay inside [low, high]."""

    k_lo = math.ceil((low - neutral) / step - 1e-9)
    k_hi = math.floor((high - neutral) / step + 1e-9)
    return [neutral + k * step for k in range(k_lo, k_hi + 1)]


def grid_shape(config: Bench2Config) -> tuple[int, int]:
    """(columns, rows) of the view grid."""

    fov = config.sensors.camera_fovy_deg
    cols = len(_centers(config.servo.neutral_deg, config.servo.min_deg, config.servo.max_deg, fov))
    rows = len(_centers(config.tilt.neutral_deg, config.tilt.min_deg, config.tilt.max_deg, fov))
    return cols, rows


# ---------------------------------------------------------------------- MJCF

# Anchors taken verbatim from the frozen `build_bench_mjcf` template. They are
# asserted to appear exactly once, so a change to the frozen bench fails loudly
# here instead of silently producing a one-axis world.
_CAMERA_ANCHOR = (
    '      <camera name="{camera}" pos="0 0 {z:.4f}" xyaxes="0 -1 0 0 0 1" fovy="{fovy:.3f}"/>\n'
)
_PILL_ANCHOR = (
    '      <geom name="head_camera_pill" type="cylinder"'
    ' fromto="-0.020 -0.0515 {z:.4f} -0.020 0.0215 {z:.4f}" size="0.016"'
    ' rgba="0.1 0.1 0.12 1" contype="0" conaffinity="0" mass="0.090"/>\n'
)
_ACTUATOR_ANCHOR = "  </actuator>\n"


def build_bench2_mjcf(
    config: Bench2Config, objects: list[RoomObject], wall_panels: str = ""
) -> str:
    """The frozen bench MJCF with the camera moved onto a tilt hinge."""

    xml = bench_model.build_bench_mjcf(config, objects, wall_panels)
    tilt = config.tilt
    z_cam = bench_model.Z_CAMERA

    camera_line = _CAMERA_ANCHOR.format(
        camera=bench_model.CAMERA_HEAD, z=z_cam, fovy=config.sensors.camera_fovy_deg
    )
    pill_line = _PILL_ANCHOR.format(z=z_cam)
    for name, anchor in (("camera", camera_line), ("pill", pill_line), ("actuator", _ACTUATOR_ANCHOR)):
        if xml.count(anchor) != 1:
            raise RuntimeError(
                f"bench2: {name} anchor found {xml.count(anchor)} times in the frozen bench MJCF; "
                "sim3d/bench_model.py changed and the tilt transformation must be revisited"
            )

    range_lo = math.radians(tilt.min_deg - tilt.neutral_deg)
    range_hi = math.radians(tilt.max_deg - tilt.neutral_deg)

    # The barrel travels with the camera: the hinge runs along it, exactly like a
    # webcam on a tilt bracket. Its mass is what gives the moving body inertia.
    # The hinge runs through the barrel, not through the lens: that is where a
    # pan-tilt bracket puts it, and it leaves the moving body balanced about the
    # axis. Hinged at the lens instead, 90 g would hang on a 20 mm arm and the
    # camera would droop 0.101 degrees under its own weight at rest.
    tilt_body = (
        f'      <body name="{BODY_TILT}" pos="{X_BARREL:.4f} 0 {z_cam:.4f}">\n'
        f'        <joint name="{JOINT_TILT}" type="hinge" axis="0 -1 0"'
        f' range="{range_lo:.6f} {range_hi:.6f}" limited="true"'
        f' damping="{tilt.joint_damping:.6f}" frictionloss="{tilt.joint_frictionloss:.6f}"'
        f' armature="{tilt.joint_armature:.6f}"/>\n'
        f'        <geom name="head_camera_pill" type="cylinder"'
        f' fromto="0 -0.0515 0 0 0.0215 0" size="0.016"'
        f' rgba="0.1 0.1 0.12 1" contype="0" conaffinity="0" mass="0.090"/>\n'
        f'        <camera name="{bench_model.CAMERA_HEAD}" pos="{-X_BARREL:.4f} 0 0"'
        f' xyaxes="0 -1 0 0 0 1" fovy="{config.sensors.camera_fovy_deg:.3f}"/>\n'
        f"      </body>\n"
    )

    tilt_actuator = (
        f'    <position name="{ACT_TILT}" joint="{JOINT_TILT}"'
        f' kp="{tilt.position_gain:.6f}" kv="{tilt.velocity_damping:.6f}"\n'
        f'              forcerange="{-tilt.drive_forcerange_nm:.6f} {tilt.drive_forcerange_nm:.6f}"\n'
        f'              ctrlrange="{range_lo:.6f} {range_hi:.6f}"/>\n'
    )

    xml = xml.replace(pill_line, "")
    xml = xml.replace(camera_line, tilt_body)
    xml = xml.replace(_ACTUATOR_ANCHOR, tilt_actuator + _ACTUATOR_ANCHOR)
    return xml
