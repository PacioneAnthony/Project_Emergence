"""Build the MJCF model string for the extruded 2D world.

The world layout (walls at x in {0, width}, y in {0, height}, circular
obstacles) comes from `sim2d.world.World`, so a given seed produces the same
arena in 2D and 3D.
"""

from __future__ import annotations

import math

from sim2d.config import RobotConfig, WorldConfig
from sim2d.world import World
from sim3d.config import Body3DConfig

FLOOR_GEOM = "floor"
ROBOT_GEOM = "robot_collision"
ROBOT_BODY = "robot"
HEAD_BODY = "servo_head"
JOINT_X = "slide_x"
JOINT_Y = "slide_y"
JOINT_YAW = "yaw"
JOINT_SERVO = "servo"
ACT_X = "vel_x"
ACT_Y = "vel_y"
ACT_YAW = "vel_yaw"
ACT_SERVO = "servo_pos"
RANGEFINDER_PREFIX = "ultrasonic"


def ray_angles(cone_rays: int, cone_half_angle: float) -> list[float]:
    if cone_rays <= 1:
        return [0.0]
    span = 2.0 * cone_half_angle
    return [-cone_half_angle + span * i / (cone_rays - 1) for i in range(cone_rays)]


def sensor_radial_offset(robot: RobotConfig, body: Body3DConfig) -> float:
    return robot.radius + body.sensor_radial_offset_margin


def build_mjcf(world: World, robot: RobotConfig, body: Body3DConfig, world_config: WorldConfig) -> str:
    width = world.width
    height = world.height
    t = body.wall_thickness
    wall_hz = body.wall_height / 2.0
    r_off = sensor_radial_offset(robot, body)

    walls = f"""
    <geom name="wall_left" type="box" pos="{-t / 2:.6f} {height / 2:.6f} {wall_hz:.6f}" size="{t / 2:.6f} {height / 2 + t:.6f} {wall_hz:.6f}" rgba="0.55 0.55 0.6 1"/>
    <geom name="wall_right" type="box" pos="{width + t / 2:.6f} {height / 2:.6f} {wall_hz:.6f}" size="{t / 2:.6f} {height / 2 + t:.6f} {wall_hz:.6f}" rgba="0.55 0.55 0.6 1"/>
    <geom name="wall_bottom" type="box" pos="{width / 2:.6f} {-t / 2:.6f} {wall_hz:.6f}" size="{width / 2 + t:.6f} {t / 2:.6f} {wall_hz:.6f}" rgba="0.55 0.55 0.6 1"/>
    <geom name="wall_top" type="box" pos="{width / 2:.6f} {height + t / 2:.6f} {wall_hz:.6f}" size="{width / 2 + t:.6f} {t / 2:.6f} {wall_hz:.6f}" rgba="0.55 0.55 0.6 1"/>
"""

    obstacles = "".join(
        f'    <geom name="obstacle_{i}" type="cylinder" pos="{obs.x:.6f} {obs.y:.6f} {body.obstacle_height / 2:.6f}" '
        f'size="{obs.radius:.6f} {body.obstacle_height / 2:.6f}" rgba="0.75 0.4 0.25 1"/>\n'
        for i, obs in enumerate(world.obstacles)
    )

    sites = ""
    rangefinders = ""
    for i, angle in enumerate(ray_angles(body.cone_rays, body.cone_half_angle)):
        sx = r_off * math.cos(angle)
        sy = r_off * math.sin(angle)
        zx = math.cos(angle)
        zy = math.sin(angle)
        sites += (
            f'        <site name="{RANGEFINDER_PREFIX}_site_{i}" pos="{sx:.6f} {sy:.6f} {body.sensor_height:.6f}" '
            f'zaxis="{zx:.6f} {zy:.6f} 0" size="0.004" rgba="0.1 0.9 0.3 1"/>\n'
        )
        rangefinders += (
            f'    <rangefinder name="{RANGEFINDER_PREFIX}_{i}" site="{RANGEFINDER_PREFIX}_site_{i}" '
            f'cutoff="{world_config.max_ultrasonic_range:.6f}"/>\n'
        )

    body_hz = body.body_height / 2.0
    return f"""
<mujoco model="emergence_sim3d">
  <compiler angle="radian"/>
  <option timestep="{body.physics_timestep:.6f}" integrator="implicitfast"/>
  <visual>
    <global offwidth="1280" offheight="960"/>
    <headlight ambient="0.4 0.4 0.4" diffuse="0.7 0.7 0.7"/>
  </visual>
  <worldbody>
    <geom name="{FLOOR_GEOM}" type="plane" pos="{width / 2:.6f} {height / 2:.6f} 0" size="{width:.6f} {height:.6f} 0.1" rgba="0.85 0.85 0.82 1"/>
    <camera name="top" pos="{width / 2:.6f} {height / 2:.6f} {max(width, height) * 1.15:.6f}" zaxis="0 0 1"/>
{walls}{obstacles}
    <body name="{ROBOT_BODY}" pos="0 0 0">
      <joint name="{JOINT_X}" type="slide" axis="1 0 0"/>
      <joint name="{JOINT_Y}" type="slide" axis="0 1 0"/>
      <joint name="{JOINT_YAW}" type="hinge" axis="0 0 1"/>
      <geom name="{ROBOT_GEOM}" type="cylinder" pos="0 0 {0.01 + body_hz:.6f}" size="{robot.radius:.6f} {body_hz:.6f}" rgba="0.25 0.45 0.85 1"/>
      <geom name="robot_nose" type="box" pos="{robot.radius * 0.7:.6f} 0 {0.012 + body.body_height:.6f}" size="{robot.radius * 0.3:.6f} 0.015 0.008" rgba="0.95 0.9 0.2 1" contype="0" conaffinity="0" mass="0.001"/>
      <camera name="follow" pos="{-6.0 * robot.radius:.6f} 0 {body.body_height * 5.0:.6f}" xyaxes="0 -1 0 0.45 0 0.9" mode="track"/>
      <body name="{HEAD_BODY}" pos="0 0 0">
        <joint name="{JOINT_SERVO}" type="hinge" axis="0 0 1" range="{robot.servo_min:.6f} {robot.servo_max:.6f}" limited="true" damping="0.05"/>
        <geom name="head_visual" type="box" pos="{robot.radius * 0.55:.6f} 0 {body.sensor_height:.6f}" size="{robot.radius * 0.55:.6f} 0.012 0.012" rgba="0.15 0.85 0.4 1" contype="0" conaffinity="0" mass="0.01"/>
{sites}      </body>
    </body>
  </worldbody>
  <actuator>
    <velocity name="{ACT_X}" joint="{JOINT_X}" kv="{body.velocity_gain:.6f}" forcerange="-200 200"/>
    <velocity name="{ACT_Y}" joint="{JOINT_Y}" kv="{body.velocity_gain:.6f}" forcerange="-200 200"/>
    <velocity name="{ACT_YAW}" joint="{JOINT_YAW}" kv="{body.velocity_gain:.6f}" forcerange="-200 200"/>
    <position name="{ACT_SERVO}" joint="{JOINT_SERVO}" kp="{body.servo_position_gain:.6f}" ctrlrange="{robot.servo_min:.6f} {robot.servo_max:.6f}"/>
  </actuator>
  <sensor>
{rangefinders}  </sensor>
</mujoco>
"""
