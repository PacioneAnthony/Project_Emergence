"""Simulation environment for the two-axis neck (D-060).

`BenchHeadEnv` is frozen -- 112 manifests reference its bytes -- so this subclass
reuses it and overrides only what the second axis changes: the model it builds,
the step API, which now takes two commands, and the observation contract.

The observation contract changes on purpose. On the one-axis bench the
observation was five scalars and the angle *was* the state of the world. Here the
observation is an image plus proprioception, and the two angles point at a portion
of the world. `Bench2Observation.proprioception()` returns those two angles;
the image comes from `render_camera()`.

Both angles are quantized with the same 12-bit step as the pan AS5600. On the
physical bench only the pan axis has an encoder: a second identical one is
assumed here so that the two axes are proprioceptively symmetric, since an
asymmetry between them would confound any spatial-memory task. Nothing is built
and nothing is bought (D-008).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import mujoco
import numpy as np

from common.math_utils import clamp
from sim3d import bench2_model, bench_model
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench2_model import Bench2Config


def release_renderer(renderer) -> None:
    """Close a mujoco.Renderer without blanking the others that are still alive.

    In this MuJoCo build, Renderer.close() frees its GPU resources in whichever
    OpenGL context happens to be current. When a newer renderer's context is the
    current one, it is the newer renderer's resources that get freed, and its next
    image comes back black -- luminance 154 to 0, measured on 2026-09-11. Making
    the renderer's own context current first leaves every other renderer intact.
    Relies on the private `_gl_context`, and falls back to a plain close without it.
    """

    if renderer is None:
        return
    context = getattr(renderer, "_gl_context", None)
    if context is not None:
        context.make_current()
    renderer.close()


@dataclass
class Bench2Observation:
    time: float
    requested_pan_deg: float
    requested_tilt_deg: float
    pan_deg: float
    tilt_deg: float
    gyro_raw: tuple[int, int, int]
    accel_raw: tuple[int, int, int]
    distance_m: float

    def proprioception(self) -> np.ndarray:
        """The two angles that say where the camera points."""

        return np.array([self.pan_deg, self.tilt_deg], dtype=np.float32)


class Bench2HeadEnv(BenchHeadEnv):
    """Pan-tilt head. `step` takes two targets; `render_camera` is inherited."""

    def __init__(self, config: Bench2Config | None = None):
        super().__init__(config or Bench2Config())
        # Called with each new observation at the end of step(). A callback must
        # not step the world, call mj_forward or draw from self.rng: the live
        # viewer is one, and it may watch an experiment but never change it.
        self.step_callbacks: list = []

    # ------------------------------------------------------------------ setup

    def reset(self, seed: int | None = None) -> Bench2Observation:
        # Mirrors BenchHeadEnv.reset step for step, including the order of every
        # draw from self.rng, so that for a given seed the room, the panels and
        # the sensor biases are identical to the one-axis bench.
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None
        if self._renderer is not None:
            release_renderer(self._renderer)
            self._renderer = None
            self._renderer_size = None

        self.config = self.base_config
        room_rng = self.rng if self.config.randomize_room else np.random.default_rng(0)
        objects = bench_model.sample_room_objects(self.config.room, room_rng)
        panels = bench_model.sample_wall_panels(self.config.room, room_rng)
        xml = bench2_model.build_bench2_mjcf(
            self.config, objects, panels + getattr(self.config, "extra_mjcf", "")
        )
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(self.model)

        self._n_substeps = max(1, round(self.config.control_dt / self.config.physics_timestep))
        self.model.opt.timestep = self.config.control_dt / self._n_substeps
        self._imu_every = max(1, round(1.0 / (self.config.sensors.imu_rate_hz * self.model.opt.timestep)))
        self._substep_counter = 0

        self._qpos_servo = self.model.joint(bench_model.JOINT_SERVO).qposadr[0]
        self._qvel_servo = self.model.joint(bench_model.JOINT_SERVO).dofadr[0]
        self._qpos_tilt = self.model.joint(bench2_model.JOINT_TILT).qposadr[0]
        self._qvel_tilt = self.model.joint(bench2_model.JOINT_TILT).dofadr[0]
        if self.config.room.reafference_object:
            self._qpos_external = self.model.joint(bench_model.JOINT_EXTERNAL).qposadr[0]
        else:
            self._qpos_external = None
        self._ctrl_servo = self.model.actuator(bench_model.ACT_SERVO).id
        self._ctrl_tilt = self.model.actuator(bench2_model.ACT_TILT).id
        self._adr_range = self.model.sensor(bench_model.SENSOR_RANGE).adr[0]
        self._adr_gyro = self.model.sensor(bench_model.SENSOR_GYRO).adr[0]
        self._adr_accel = self.model.sensor(bench_model.SENSOR_ACCEL).adr[0]

        sensors = self.config.sensors
        self._gyro_bias_dps = self.rng.normal(0.0, sensors.gyro_bias_dps_std, size=3)
        self._accel_bias_g = self.rng.normal(0.0, sensors.accel_bias_g_std, size=3)
        self._as5600_step_deg = 360.0 / float(2 ** sensors.as5600_bits)
        self._gyro_lsb_per_dps = (32767 + 1) / sensors.gyro_range_dps
        self._accel_lsb_per_g = (32767 + 1) / sensors.accel_range_g

        self.time = 0.0
        self.step_count = 0
        self.imu_samples = []
        self.command_log = []
        self._requested_deg = self.config.servo.neutral_deg
        self._limited_deg = self.config.servo.neutral_deg
        self._requested_tilt_deg = self.config.tilt.neutral_deg
        self._limited_tilt_deg = self.config.tilt.neutral_deg

        self.data.qpos[self._qpos_servo] = 0.0
        self.data.qpos[self._qpos_tilt] = 0.0
        if self._qpos_external is not None:
            self.data.qpos[self._qpos_external] = 0.0
        self.data.qvel[:] = 0.0
        mujoco.mj_forward(self.model, self.data)
        return self._read_observation()

    # ------------------------------------------------------------------- step

    def step(self, pan_target_deg: float, tilt_target_deg: float | None = None) -> Bench2Observation:
        """Drive both axes for one control period.

        `tilt_target_deg` defaults to holding the current tilt request, so a
        caller that only pans does not silently recenter the camera.
        """

        servo = self.config.servo
        tilt = self.config.tilt
        if tilt_target_deg is None:
            tilt_target_deg = self._requested_tilt_deg

        pan = clamp(float(pan_target_deg), servo.min_deg, servo.max_deg)
        tilt_target = clamp(float(tilt_target_deg), tilt.min_deg, tilt.max_deg)
        if pan != self._requested_deg or tilt_target != self._requested_tilt_deg:
            self.command_log.append(
                {
                    "timestamp_ns": int(round(self.time * 1e9)),
                    "requested_angle_deg": float(pan),
                    "requested_tilt_deg": float(tilt_target),
                }
            )
        self._requested_deg = pan
        self._requested_tilt_deg = tilt_target

        self._limited_deg = _rate_limited(
            self._limited_deg, pan, servo.max_speed_deg_s * self.config.control_dt,
            servo.min_deg, servo.max_deg,
        )
        self._limited_tilt_deg = _rate_limited(
            self._limited_tilt_deg, tilt_target, tilt.max_speed_deg_s * self.config.control_dt,
            tilt.min_deg, tilt.max_deg,
        )
        self.data.ctrl[self._ctrl_servo] = math.radians(self._limited_deg - servo.neutral_deg)
        self.data.ctrl[self._ctrl_tilt] = math.radians(self._limited_tilt_deg - tilt.neutral_deg)

        for _ in range(self._n_substeps):
            mujoco.mj_step(self.model, self.data)
            self._substep_counter += 1
            if self._substep_counter % self._imu_every == 0:
                self._record_imu_sample()

        self.time += self.config.control_dt
        self.step_count += 1
        observation = self._read_observation()
        for callback in self.step_callbacks:
            callback(observation)
        return observation

    # ---------------------------------------------------------------- sensing

    def tilt_angle_deg(self) -> float:
        return self.config.tilt.neutral_deg + math.degrees(float(self.data.qpos[self._qpos_tilt]))

    def _tilt_encoder_deg(self) -> float:
        return round(self.tilt_angle_deg() / self._as5600_step_deg) * self._as5600_step_deg

    def _read_observation(self) -> Bench2Observation:
        gyro_raw, accel_raw = self._raw_imu()
        return Bench2Observation(
            time=float(self.time),
            requested_pan_deg=float(self._requested_deg),
            requested_tilt_deg=float(self._requested_tilt_deg),
            pan_deg=float(self._as5600_deg()),
            tilt_deg=float(self._tilt_encoder_deg()),
            gyro_raw=gyro_raw,
            accel_raw=accel_raw,
            distance_m=self._distance(),
        )

    # ------------------------------------------------------------- navigation

    def settle_at(self, pan_deg: float, tilt_deg: float, max_steps: int = 200,
                  tol_deg: float = 0.05) -> Bench2Observation:
        """Drive both axes to a target and step until they stop moving.

        Returns as soon as both axes are within `tol_deg` of the request and the
        pose has stopped changing, so a caller that renders a cell gets a settled
        image rather than one taken mid-sweep.
        """

        observation = self.step(pan_deg, tilt_deg)
        previous = (self.servo_angle_deg(), self.tilt_angle_deg())
        for _ in range(max_steps - 1):
            observation = self.step(pan_deg, tilt_deg)
            current = (self.servo_angle_deg(), self.tilt_angle_deg())
            settled = (
                abs(current[0] - pan_deg) <= tol_deg
                and abs(current[1] - tilt_deg) <= tol_deg
                and abs(current[0] - previous[0]) <= tol_deg / 10.0
                and abs(current[1] - previous[1]) <= tol_deg / 10.0
            )
            previous = current
            if settled:
                break
        return observation

    # -------------------------------------------------------------- rendering

    def render_camera(self, width: int = 128, height: int = 128, camera: str = bench_model.CAMERA_HEAD) -> np.ndarray:
        # The frozen parent drops its renderer on a size change with a plain
        # close(); release it safely first so no other renderer is blanked.
        if self._renderer is not None and self._renderer_size != (width, height):
            release_renderer(self._renderer)
            self._renderer = None
            self._renderer_size = None
        return super().render_camera(width, height, camera)

    def close(self) -> None:
        release_renderer(self._renderer)
        self._renderer = None
        self._renderer_size = None
        super().close()


def _rate_limited(current: float, target: float, max_delta: float, low: float, high: float) -> float:
    delta = clamp(target - current, -max_delta, max_delta)
    return clamp(current + delta, low, high)
