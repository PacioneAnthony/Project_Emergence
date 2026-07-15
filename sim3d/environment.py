"""MuJoCo-backed environment exposing the exact sim2d contract.

Observation: [distance_ultrason, angle_servo, gyro_z]
Action:      [v_cmd, omega_cmd, servo_target]

The safety layer, PWM zero-order hold, servo rate limiter, acceleration
clamps, sensor noise model, reward and domain randomization are shared with
or replicated from sim2d. MuJoCo owns the rigid bodies, contacts and the
rangefinder rays.
"""

from __future__ import annotations

import math
from typing import Any

import mujoco
import numpy as np

from common.math_utils import clamp, wrap_angle
from common.types import Action, Observation, RobotState
from sim2d.actuators import SafetyLayer, ZeroOrderHold
from sim2d.config import SimConfig
from sim2d.robot import Servo
from sim2d.sensors import GyroSensor
from sim2d.world import World
from sim3d import model_builder
from sim3d.config import Body3DConfig, Sim3DConfig, randomize_episode_config
from sim3d.sensors import Ultrasonic3DSensor


class RobotSim3DEnv:
    """Drop-in 3D replacement for sim2d.environment.RobotSimEnv."""

    def __init__(self, config: Sim3DConfig | SimConfig | None = None):
        if isinstance(config, Sim3DConfig):
            self.config3d = config
        elif isinstance(config, SimConfig):
            self.config3d = Sim3DConfig(base=config)
        else:
            self.config3d = Sim3DConfig()

        self.base_config = self.config3d.base
        self.body_config: Body3DConfig = self.config3d.body
        self.rng = np.random.default_rng(self.base_config.seed)
        self.viewer = None
        self.model: mujoco.MjModel | None = None
        self.data: mujoco.MjData | None = None
        self.time = 0.0
        self.step_count = 0
        self.last_obs: Observation | None = None
        self.last_sensor_info: dict[str, float] = {}
        self._setup_episode(state=None, build_only=True)

    # ------------------------------------------------------------------ setup

    def _setup_episode(self, state: RobotState | None, build_only: bool = False) -> None:
        self.config = randomize_episode_config(self.base_config, self.rng)
        self.world = World.generate(self.config.world, self.rng, self.config.robot.radius)
        self.safety = SafetyLayer(self.config.robot)
        self.actuator_hold = ZeroOrderHold(self.config.robot.pwm_period)
        self.servo = Servo(self.config.robot)
        self.ultrasonic = Ultrasonic3DSensor(self.config.sensors, self.config.world, self.config.dt)
        self.gyro = GyroSensor(self.config.sensors, self.config.dt)
        self.time = 0.0
        self.step_count = 0
        self._v_int = 0.0
        self._omega_int = 0.0

        xml = model_builder.build_mjcf(self.world, self.config.robot, self.body_config, self.config.world)
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(self.model)

        self._n_substeps = max(1, round(self.config.dt / self.body_config.physics_timestep))
        self.model.opt.timestep = self.config.dt / self._n_substeps

        self._qpos_x = self.model.joint(model_builder.JOINT_X).qposadr[0]
        self._qpos_y = self.model.joint(model_builder.JOINT_Y).qposadr[0]
        self._qpos_yaw = self.model.joint(model_builder.JOINT_YAW).qposadr[0]
        self._qpos_servo = self.model.joint(model_builder.JOINT_SERVO).qposadr[0]
        self._qvel_x = self.model.joint(model_builder.JOINT_X).dofadr[0]
        self._qvel_y = self.model.joint(model_builder.JOINT_Y).dofadr[0]
        self._qvel_yaw = self.model.joint(model_builder.JOINT_YAW).dofadr[0]
        self._ctrl_x = self.model.actuator(model_builder.ACT_X).id
        self._ctrl_y = self.model.actuator(model_builder.ACT_Y).id
        self._ctrl_yaw = self.model.actuator(model_builder.ACT_YAW).id
        self._ctrl_servo = self.model.actuator(model_builder.ACT_SERVO).id
        self._robot_geom_id = self.model.geom(model_builder.ROBOT_GEOM).id
        self._range_adrs = [
            self.model.sensor(f"{model_builder.RANGEFINDER_PREFIX}_{i}").adr[0]
            for i in range(max(1, self.body_config.cone_rays))
        ]
        self._sensor_offset = model_builder.sensor_radial_offset(self.config.robot, self.body_config)

        if build_only:
            return

        if state is None:
            state = self._sample_start_state()
        self._write_state(state)
        self.servo.reset(state.servo_angle)
        self._v_int = float(state.v)
        self._omega_int = float(state.omega)
        self.actuator_hold.reset(Action(servo_target=state.servo_angle), self.time)
        mujoco.mj_forward(self.model, self.data)
        self.ultrasonic.reset(self._true_distance())
        self.gyro.reset(self._read_state(), self.rng)

    def reset(self, seed: int | None = None, state: RobotState | None = None) -> Observation:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

        self._setup_episode(state)
        self.last_obs = self._read_observation()
        return self.last_obs

    def _sample_start_state(self) -> RobotState:
        radius = self.config.robot.radius
        for _ in range(200):
            x = float(self.rng.uniform(radius + 0.2, self.config.world.width - radius - 0.2))
            y = float(self.rng.uniform(radius + 0.2, self.config.world.height - radius - 0.2))
            if not self.world.collides_circle(x, y, radius):
                return RobotState(x=x, y=y, heading=float(self.rng.uniform(-math.pi, math.pi)), servo_angle=0.0)

        return RobotState(
            x=self.config.world.width * 0.5,
            y=self.config.world.height * 0.5,
            heading=0.0,
            servo_angle=0.0,
        )

    def _write_state(self, state: RobotState) -> None:
        self.data.qpos[self._qpos_x] = state.x
        self.data.qpos[self._qpos_y] = state.y
        self.data.qpos[self._qpos_yaw] = state.heading
        self.data.qpos[self._qpos_servo] = clamp(state.servo_angle, self.config.robot.servo_min, self.config.robot.servo_max)
        self.data.qvel[:] = 0.0
        self.data.qvel[self._qvel_x] = state.v * math.cos(state.heading)
        self.data.qvel[self._qvel_y] = state.v * math.sin(state.heading)
        self.data.qvel[self._qvel_yaw] = state.omega

    # ------------------------------------------------------------------- step

    def step(self, action: Action | np.ndarray | list[float] | tuple[float, ...]) -> tuple[Observation, float, bool, dict[str, Any]]:
        if self.last_obs is None:
            self.reset()

        if not isinstance(action, Action):
            action = Action.from_array(action)

        cfg = self.config
        safe_action = self.safety.apply(action, cfg.dt)
        actuator_action = self.actuator_hold.apply(safe_action, self.time)

        v_delta = clamp(actuator_action.v_cmd - self._v_int, -cfg.robot.max_linear_accel * cfg.dt, cfg.robot.max_linear_accel * cfg.dt)
        omega_delta = clamp(actuator_action.omega_cmd - self._omega_int, -cfg.robot.max_angular_accel * cfg.dt, cfg.robot.max_angular_accel * cfg.dt)
        self._v_int = clamp(self._v_int + v_delta, -cfg.robot.max_linear_speed, cfg.robot.max_linear_speed)
        self._omega_int = clamp(self._omega_int + omega_delta, -cfg.robot.max_angular_speed, cfg.robot.max_angular_speed)

        slip = 1.0
        if cfg.robot.slip_std > 0.0:
            slip += float(self.rng.normal(0.0, cfg.robot.slip_std))
        v_applied = self._v_int * slip

        servo_ctrl = self.servo.step(actuator_action.servo_target, cfg.dt)

        collision = False
        for _ in range(self._n_substeps):
            heading = float(self.data.qpos[self._qpos_yaw])
            self.data.ctrl[self._ctrl_x] = v_applied * math.cos(heading)
            self.data.ctrl[self._ctrl_y] = v_applied * math.sin(heading)
            self.data.ctrl[self._ctrl_yaw] = self._omega_int
            self.data.ctrl[self._ctrl_servo] = servo_ctrl
            mujoco.mj_step(self.model, self.data)
            collision = collision or self._robot_in_contact()

        if collision:
            # sim2d parity: a blocked robot loses its linear momentum.
            self._v_int = 0.0

        self.time += cfg.dt
        self.step_count += 1

        next_obs = self._read_observation()
        reward, reward_terms = self._reward(collision)
        done = self.step_count >= cfg.max_steps
        if collision and cfg.reward.collision_ends_episode:
            done = True

        state = self._read_state()
        info = {
            "state": state,
            "collision": collision,
            "safe_action": safe_action,
            "actuator_action": actuator_action,
            "true_distance": self.ultrasonic.last_true_distance,
            "nearest_surface": self.world.distance_to_nearest_surface(state.x, state.y, cfg.robot.radius),
            "reward_terms": reward_terms,
        }
        self.last_obs = next_obs
        return next_obs, reward, done, info

    def _robot_in_contact(self) -> bool:
        for i in range(self.data.ncon):
            contact = self.data.contact[i]
            if self._robot_geom_id in (contact.geom1, contact.geom2):
                return True
        return False

    # ---------------------------------------------------------------- sensing

    def _true_distance(self) -> float:
        max_range = self.config.world.max_ultrasonic_range
        best = max_range
        for adr in self._range_adrs:
            reading = float(self.data.sensordata[adr])
            if reading < 0.0:
                continue
            # Re-reference edge-mounted rays to the robot center, like sim2d.
            best = min(best, reading + self._sensor_offset)
        return float(max(0.0, min(best, max_range)))

    def _read_state(self) -> RobotState:
        heading = wrap_angle(float(self.data.qpos[self._qpos_yaw]))
        vx = float(self.data.qvel[self._qvel_x])
        vy = float(self.data.qvel[self._qvel_y])
        return RobotState(
            x=float(self.data.qpos[self._qpos_x]),
            y=float(self.data.qpos[self._qpos_y]),
            heading=heading,
            servo_angle=float(self.data.qpos[self._qpos_servo]),
            v=float(vx * math.cos(heading) + vy * math.sin(heading)),
            omega=float(self.data.qvel[self._qvel_yaw]),
        )

    def _read_observation(self) -> Observation:
        state = self._read_state()
        distance = self.ultrasonic.read(self._true_distance(), self.rng)
        gyro_z = self.gyro.read(state, self.rng)
        self.last_sensor_info = {
            "true_distance": float(self.ultrasonic.last_true_distance),
            "measured_distance": float(distance),
            "gyro_z": float(gyro_z),
        }
        return Observation(
            distance=float(distance),
            servo_angle=float(state.servo_angle),
            gyro_z=float(gyro_z),
            time=float(self.time),
        )

    def _reward(self, collision: bool) -> tuple[float, dict[str, float]]:
        cfg = self.config.reward
        state = self._read_state()
        nearest = self.world.distance_to_nearest_surface(state.x, state.y, self.config.robot.radius)
        forward = self.config.reward.forward_weight * max(0.0, state.v)
        proximity = -cfg.proximity_weight * max(0.0, cfg.min_obstacle_distance - nearest) ** 2
        collision_term = -cfg.collision_penalty if collision else 0.0
        reward = cfg.alive_bonus + forward + proximity + collision_term
        return float(reward), {
            "alive": float(cfg.alive_bonus),
            "forward": float(forward),
            "proximity": float(proximity),
            "collision": float(collision_term),
        }

    # -------------------------------------------------------------- rendering

    def sync_viewer(self) -> None:
        """Open the interactive MuJoCo viewer lazily and mirror the current state."""

        if self.viewer is None:
            import mujoco.viewer

            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        if self.viewer.is_running():
            self.viewer.sync()

    def close(self) -> None:
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None

    def save_frame(self, path: str, camera: str = "top", width: int = 1280, height: int = 960) -> None:
        renderer = mujoco.Renderer(self.model, height=height, width=width)
        try:
            renderer.update_scene(self.data, camera=camera)
            pixels = renderer.render()
        finally:
            renderer.close()

        import matplotlib.image

        matplotlib.image.imsave(path, pixels)
