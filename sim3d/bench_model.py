"""MJCF digital twin of the bench v1.0 head (BENCH_DESIGN.md) in a visual room.

Geometry follows the bench design document: neck axis vertical, sliding track
at z=60 mm, head plate at z=64 mm, camera optical center on the neck axis at
z=100 mm, HC-SR04 transducers at z=130 mm, magnet platform at z=150 mm, AS5600
gantry behind the head. All z values are measured from the top of the base
plate and expressed here in meters, in a room whose objects give the rotating
camera something to look at.

The head is a rigid-body approximation (~250 g, gyration radius ~54 mm): it
can pre-validate inertia, servo dynamics and clearances, and generate the
visual corpus. It cannot predict PLA structural vibration in absolute terms;
the mechanics ratio stays a comparative tool.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class BenchServoConfig:
    """MF90 (MG90S class) pan servo."""

    min_deg: float = 10.0
    max_deg: float = 170.0
    neutral_deg: float = 90.0
    max_speed_deg_s: float = 600.0  # ~0.1 s / 60 deg, no load
    stall_torque_nm: float = 0.176  # 1.8 kg.cm (documentation; load is ~10x below)
    # PD drive tuned near critical damping for the ~6e-4 kg.m^2 head, so the
    # speed profile follows the rate-limited target like a real servo loop.
    # forcerange is intentionally wider than stall: with a naive P+clip model
    # the head coasts past the no-load speed, which a real servo never does.
    position_gain: float = 10.0
    velocity_damping: float = 0.15
    drive_forcerange_nm: float = 0.5
    joint_damping: float = 0.004
    joint_frictionloss: float = 0.0147  # track friction budget from BENCH_DESIGN
    joint_armature: float = 2.0e-4  # reflected gearbox inertia


@dataclass
class BenchSensorConfig:
    imu_rate_hz: float = 100.0
    # MPU full-scale ranges; +/-250 dps saturates during full-speed pans
    # (~600 deg/s), exactly like the real part would.
    gyro_range_dps: float = 250.0
    accel_range_g: float = 2.0
    gyro_noise_dps: float = 0.06
    gyro_bias_dps_std: float = 0.3
    accel_noise_g: float = 0.002
    accel_bias_g_std: float = 0.01
    ultrasonic_noise_m: float = 0.003
    ultrasonic_max_range: float = 4.0
    as5600_bits: int = 12
    camera_fovy_deg: float = 30.0  # BRIO 100 ~58 deg diagonal at 16:9


@dataclass
class BenchRoomConfig:
    width: float = 3.0  # x
    depth: float = 4.0  # y
    wall_height: float = 2.4
    object_count: int = 10
    min_object_size: float = 0.06
    max_object_size: float = 0.28
    table_size: tuple[float, float, float] = (0.8, 0.6, 0.72)
    bench_position: tuple[float, float] = (1.5, 3.2)  # neck axis, faces -y


@dataclass
class BenchConfig:
    physics_timestep: float = 0.001
    control_dt: float = 0.02  # 50 Hz PWM
    servo: BenchServoConfig = field(default_factory=BenchServoConfig)
    sensors: BenchSensorConfig = field(default_factory=BenchSensorConfig)
    room: BenchRoomConfig = field(default_factory=BenchRoomConfig)
    seed: int | None = None
    randomize_room: bool = True


HEAD_BODY = "bench_head"
JOINT_SERVO = "neck_servo"
ACT_SERVO = "neck_servo_pos"
SITE_IMU = "imu_site"
SITE_RANGE = "ultrasonic_site"
SENSOR_RANGE = "ultrasonic"
SENSOR_GYRO = "imu_gyro"
SENSOR_ACCEL = "imu_accel"
CAMERA_HEAD = "head_cam"

# Bench frame constants (meters, from BENCH_DESIGN.md).
Z_PLATE_TOP = 0.006
Z_TRACK = 0.060
Z_HEAD_PLATE = 0.064
Z_CAMERA = 0.100
Z_ULTRASONIC = 0.130
Z_MAGNET = 0.150


@dataclass(frozen=True)
class RoomObject:
    kind: str  # "box" | "cylinder" | "sphere"
    x: float
    y: float
    size: tuple[float, float, float]
    rgba: tuple[float, float, float, float]


def sample_room_objects(config: BenchRoomConfig, rng: np.random.Generator) -> list[RoomObject]:
    """Scatter simple solids in the area the camera sweeps (in front of the bench)."""

    objects: list[RoomObject] = []
    kinds = ("box", "cylinder", "sphere")
    bx, by = config.bench_position
    attempts = 0
    while len(objects) < config.object_count and attempts < config.object_count * 40:
        attempts += 1
        kind = kinds[int(rng.integers(0, len(kinds)))]
        size_a = float(rng.uniform(config.min_object_size, config.max_object_size))
        height = float(rng.uniform(0.3, 1.7))
        x = float(rng.uniform(0.25, config.width - 0.25))
        y = float(rng.uniform(0.35, by - 0.9))
        if math.hypot(x - bx, y - by) < 1.0:
            continue
        if any(math.hypot(x - o.x, y - o.y) < size_a + max(o.size[0], o.size[1]) + 0.12 for o in objects):
            continue
        rgba = (
            float(rng.uniform(0.15, 0.95)),
            float(rng.uniform(0.15, 0.95)),
            float(rng.uniform(0.15, 0.95)),
            1.0,
        )
        objects.append(RoomObject(kind=kind, x=x, y=y, size=(size_a, size_a, height), rgba=rgba))
    return objects


def sample_wall_panels(config: BenchRoomConfig, rng: np.random.Generator, count: int = 8) -> str:
    """Colored panels at camera height on the three walls the camera can sweep."""

    geoms = ""
    for i in range(count):
        wall = int(rng.integers(0, 3))  # 0 front (y=0), 1 left (x=0), 2 right (x=width)
        half_w = float(rng.uniform(0.12, 0.45))
        half_h = float(rng.uniform(0.10, 0.35))
        z = float(rng.uniform(0.5, 1.6))
        rgba = f"{rng.uniform(0.1, 0.95):.3f} {rng.uniform(0.1, 0.95):.3f} {rng.uniform(0.1, 0.95):.3f} 1"
        if wall == 0:
            x = float(rng.uniform(0.4, config.width - 0.4))
            pos, size = f"{x:.3f} 0.012 {z:.3f}", f"{half_w:.3f} 0.01 {half_h:.3f}"
        elif wall == 1:
            y = float(rng.uniform(0.4, config.depth - 1.0))
            pos, size = f"0.012 {y:.3f} {z:.3f}", f"0.01 {half_w:.3f} {half_h:.3f}"
        else:
            y = float(rng.uniform(0.4, config.depth - 1.0))
            pos, size = f"{config.width - 0.012:.3f} {y:.3f} {z:.3f}", f"0.01 {half_w:.3f} {half_h:.3f}"
        geoms += f'    <geom name="wall_panel_{i}" type="box" pos="{pos}" size="{size}" rgba="{rgba}"/>\n'
    return geoms


def _object_geom(index: int, obj: RoomObject) -> str:
    rgba = " ".join(f"{c:.3f}" for c in obj.rgba)
    a, _, h = obj.size
    if obj.kind == "box":
        return (
            f'    <geom name="room_object_{index}" type="box" pos="{obj.x:.4f} {obj.y:.4f} {h / 2:.4f}" '
            f'size="{a:.4f} {a:.4f} {h / 2:.4f}" rgba="{rgba}"/>\n'
        )
    if obj.kind == "cylinder":
        return (
            f'    <geom name="room_object_{index}" type="cylinder" pos="{obj.x:.4f} {obj.y:.4f} {h / 2:.4f}" '
            f'size="{a:.4f} {h / 2:.4f}" rgba="{rgba}"/>\n'
        )
    return (
        f'    <geom name="room_object_{index}" type="sphere" pos="{obj.x:.4f} {obj.y:.4f} {a:.4f}" '
        f'size="{a:.4f}" rgba="{rgba}"/>\n'
    )


def build_bench_mjcf(config: BenchConfig, objects: list[RoomObject], wall_panels: str = "") -> str:
    room = config.room
    servo = config.servo
    sensors = config.sensors
    bx, by = room.bench_position
    table_lx, table_ly, table_h = room.table_size
    base_z = table_h + Z_PLATE_TOP  # top of the base plate in world coordinates
    range_hi = math.radians(servo.max_deg - servo.neutral_deg)
    range_lo = math.radians(servo.min_deg - servo.neutral_deg)

    object_geoms = "".join(_object_geom(i, obj) for i, obj in enumerate(objects))

    # Head local frame: +x = forward (camera axis), +z = up, hinge on the neck axis.
    return f"""
<mujoco model="emergence_bench_v1">
  <compiler angle="radian"/>
  <option timestep="{config.physics_timestep:.6f}" integrator="implicitfast"/>
  <visual>
    <global offwidth="1280" offheight="960"/>
    <headlight ambient="0.35 0.35 0.35" diffuse="0.6 0.6 0.6"/>
  </visual>
  <asset>
    <texture name="floor_tex" type="2d" builtin="checker" rgb1="0.72 0.66 0.55" rgb2="0.62 0.55 0.44" width="256" height="256"/>
    <material name="floor_mat" texture="floor_tex" texrepeat="8 10"/>
    <texture name="wall_tex" type="2d" builtin="checker" rgb1="0.88 0.88 0.9" rgb2="0.82 0.84 0.88" width="128" height="128"/>
    <material name="wall_mat" texture="wall_tex" texrepeat="6 3"/>
    <texture name="sky" type="skybox" builtin="gradient" rgb1="0.6 0.75 0.95" rgb2="0.15 0.2 0.35" width="128" height="128"/>
  </asset>
  <worldbody>
    <light pos="{room.width / 2:.3f} {room.depth / 2:.3f} 2.3" dir="0 0 -1" diffuse="0.7 0.7 0.7"/>
    <light pos="{bx:.3f} {by - 1.5:.3f} 2.2" dir="0 0.3 -1" diffuse="0.4 0.4 0.4"/>
    <geom name="room_floor" type="plane" pos="{room.width / 2:.3f} {room.depth / 2:.3f} 0" size="{room.width:.3f} {room.depth:.3f} 0.1" material="floor_mat"/>
    <geom name="room_wall_front" type="box" pos="{room.width / 2:.3f} -0.05 {room.wall_height / 2:.3f}" size="{room.width / 2 + 0.1:.3f} 0.05 {room.wall_height / 2:.3f}" material="wall_mat"/>
    <geom name="room_wall_back" type="box" pos="{room.width / 2:.3f} {room.depth + 0.05:.3f} {room.wall_height / 2:.3f}" size="{room.width / 2 + 0.1:.3f} 0.05 {room.wall_height / 2:.3f}" material="wall_mat"/>
    <geom name="room_wall_left" type="box" pos="-0.05 {room.depth / 2:.3f} {room.wall_height / 2:.3f}" size="0.05 {room.depth / 2 + 0.1:.3f} {room.wall_height / 2:.3f}" rgba="0.75 0.82 0.9 1"/>
    <geom name="room_wall_right" type="box" pos="{room.width + 0.05:.3f} {room.depth / 2:.3f} {room.wall_height / 2:.3f}" size="0.05 {room.depth / 2 + 0.1:.3f} {room.wall_height / 2:.3f}" rgba="0.9 0.82 0.75 1"/>
{object_geoms}{wall_panels}
    <geom name="bench_table" type="box" pos="{bx:.4f} {by:.4f} {table_h / 2:.4f}" size="{table_lx / 2:.4f} {table_ly / 2:.4f} {table_h / 2:.4f}" rgba="0.5 0.36 0.25 1"/>
    <geom name="bench_plate" type="box" pos="{bx:.4f} {by:.4f} {table_h + Z_PLATE_TOP / 2:.4f}" size="0.110 0.105 {Z_PLATE_TOP / 2:.4f}" rgba="0.2 0.2 0.22 1"/>
    <geom name="bench_tower" type="cylinder" pos="{bx:.4f} {by:.4f} {base_z + Z_TRACK / 2:.4f}" size="0.035 {Z_TRACK / 2:.4f}" rgba="0.25 0.25 0.3 1"/>
    <geom name="bench_gantry_column" type="box" pos="{bx:.4f} {by + 0.065:.4f} {base_z + 0.095:.4f}" size="0.015 0.015 0.095" rgba="0.3 0.3 0.35 1"/>
    <geom name="bench_gantry_arm" type="box" pos="{bx:.4f} {by + 0.028:.4f} {base_z + 0.184:.4f}" size="0.008 0.0525 0.006" rgba="0.3 0.3 0.35 1"/>
    <geom name="bench_as5600" type="box" pos="{bx:.4f} {by:.4f} {base_z + 0.176:.4f}" size="0.010 0.012 0.002" rgba="0.1 0.5 0.2 1"/>

    <body name="{HEAD_BODY}" pos="{bx:.4f} {by:.4f} {base_z:.4f}" euler="0 0 {-math.pi / 2:.6f}">
      <joint name="{JOINT_SERVO}" type="hinge" axis="0 0 1" range="{range_lo:.6f} {range_hi:.6f}" limited="true"
             damping="{servo.joint_damping:.6f}" frictionloss="{servo.joint_frictionloss:.6f}" armature="{servo.joint_armature:.6f}"/>
      <geom name="head_plate" type="cylinder" pos="0 0 {Z_HEAD_PLATE:.4f}" size="0.040 0.002" rgba="0.85 0.85 0.9 1" contype="0" conaffinity="0" mass="0.060"/>
      <geom name="head_columns" type="box" pos="-0.022 0 {Z_HEAD_PLATE + 0.014:.4f}" size="0.005 0.024 0.014" rgba="0.85 0.85 0.9 1" contype="0" conaffinity="0" mass="0.020"/>
      <geom name="head_camera_pill" type="cylinder" fromto="-0.020 -0.0515 {Z_CAMERA:.4f} -0.020 0.0215 {Z_CAMERA:.4f}" size="0.016" rgba="0.1 0.1 0.12 1" contype="0" conaffinity="0" mass="0.090"/>
      <geom name="head_cradle" type="box" pos="-0.020 0 {Z_CAMERA - 0.020:.4f}" size="0.014 0.020 0.004" rgba="0.85 0.85 0.9 1" contype="0" conaffinity="0" mass="0.030"/>
      <geom name="head_hcsr04" type="box" pos="0.008 0 {Z_ULTRASONIC:.4f}" size="0.008 0.0225 0.010" rgba="0.2 0.3 0.7 1" contype="0" conaffinity="0" mass="0.009"/>
      <geom name="head_imu" type="box" pos="-0.018 0.028 {Z_HEAD_PLATE + 0.016:.4f}" size="0.008 0.013 0.002" rgba="0.6 0.2 0.6 1" contype="0" conaffinity="0" mass="0.005"/>
      <geom name="head_mast" type="box" pos="-0.030 0 {Z_CAMERA + 0.028:.4f}" size="0.004 0.006 {0.026:.4f}" rgba="0.85 0.85 0.9 1" contype="0" conaffinity="0" mass="0.015"/>
      <geom name="head_mast_platform" type="box" pos="0 0 {Z_MAGNET - 0.002:.4f}" size="0.008 0.008 0.002" rgba="0.85 0.85 0.9 1" contype="0" conaffinity="0" mass="0.010"/>
      <geom name="head_magnet" type="cylinder" pos="0 0 {Z_MAGNET + 0.00025:.5f}" size="0.003 0.00125" rgba="0.7 0.7 0.75 1" contype="0" conaffinity="0" mass="0.001"/>
      <site name="{SITE_IMU}" pos="-0.018 0.028 {Z_HEAD_PLATE + 0.018:.4f}" size="0.003" rgba="1 0 1 0.5"/>
      <site name="{SITE_RANGE}" pos="0.030 0 {Z_ULTRASONIC:.4f}" zaxis="1 0 0" size="0.003" rgba="0.1 0.9 0.3 0.5"/>
      <camera name="{CAMERA_HEAD}" pos="0 0 {Z_CAMERA:.4f}" xyaxes="0 -1 0 0 0 1" fovy="{sensors.camera_fovy_deg:.3f}"/>
    </body>
    <camera name="bench_overview" pos="{bx + 0.55:.3f} {by - 0.65:.3f} {table_h + 0.55:.3f}" xyaxes="0.76 0.65 0 -0.28 0.33 0.9"/>
    <camera name="room_overview" pos="{room.width / 2:.3f} {by - 2.8:.3f} 1.9" xyaxes="1 0 0 0 0.45 0.89"/>
  </worldbody>
  <actuator>
    <position name="{ACT_SERVO}" joint="{JOINT_SERVO}" kp="{servo.position_gain:.6f}" kv="{servo.velocity_damping:.6f}"
              forcerange="{-servo.drive_forcerange_nm:.6f} {servo.drive_forcerange_nm:.6f}"
              ctrlrange="{range_lo:.6f} {range_hi:.6f}"/>
  </actuator>
  <sensor>
    <rangefinder name="{SENSOR_RANGE}" site="{SITE_RANGE}" cutoff="{sensors.ultrasonic_max_range:.4f}"/>
    <gyro name="{SENSOR_GYRO}" site="{SITE_IMU}"/>
    <accelerometer name="{SENSOR_ACCEL}" site="{SITE_IMU}"/>
  </sensor>
</mujoco>
"""
