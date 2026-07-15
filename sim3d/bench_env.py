"""Simulation environment for the bench v1.0 head digital twin.

Control runs at 50 Hz (PWM period), physics at 1 kHz, and the IMU is sampled
at 100 Hz like the real Mega firmware. IMU samples are exposed in the raw LSB
units used by `j0.mechanics` (gyro +/-250 dps -> 131 LSB per deg/s, accel
+/-2 g -> 16384 LSB per g) so the qualification report is computed by the
same code path as on the physical bench.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import mujoco
import numpy as np

from common.math_utils import clamp
from sim3d import bench_model
from sim3d.bench_model import BenchConfig

GRAVITY = 9.80665
INT16_MAX = 32767


@dataclass
class BenchObservation:
    time: float
    requested_deg: float
    as5600_deg: float
    gyro_raw: tuple[int, int, int]
    accel_raw: tuple[int, int, int]
    distance_m: float

    def as_array(self) -> np.ndarray:
        return np.array(
            [self.distance_m, self.as5600_deg, float(self.gyro_raw[2])],
            dtype=np.float32,
        )


class BenchHeadEnv:
    def __init__(self, config: BenchConfig | None = None):
        self.base_config = config or BenchConfig()
        self.rng = np.random.default_rng(self.base_config.seed)
        self.viewer = None
        self._renderer = None
        self._renderer_size: tuple[int, int] | None = None
        self.model: mujoco.MjModel | None = None
        self.data: mujoco.MjData | None = None
        self.imu_samples: list[dict] = []
        self.command_log: list[dict] = []
        self.reset(seed=self.base_config.seed)

    # ------------------------------------------------------------------ setup

    def reset(self, seed: int | None = None) -> BenchObservation:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
            self._renderer_size = None

        self.config = self.base_config
        room_rng = self.rng if self.config.randomize_room else np.random.default_rng(0)
        objects = bench_model.sample_room_objects(self.config.room, room_rng)
        panels = bench_model.sample_wall_panels(self.config.room, room_rng)
        xml = bench_model.build_bench_mjcf(self.config, objects, panels)
        self.model = mujoco.MjModel.from_xml_string(xml)
        self.data = mujoco.MjData(self.model)

        self._n_substeps = max(1, round(self.config.control_dt / self.config.physics_timestep))
        self.model.opt.timestep = self.config.control_dt / self._n_substeps
        self._imu_every = max(1, round(1.0 / (self.config.sensors.imu_rate_hz * self.model.opt.timestep)))
        self._substep_counter = 0

        self._qpos_servo = self.model.joint(bench_model.JOINT_SERVO).qposadr[0]
        self._qvel_servo = self.model.joint(bench_model.JOINT_SERVO).dofadr[0]
        self._ctrl_servo = self.model.actuator(bench_model.ACT_SERVO).id
        self._adr_range = self.model.sensor(bench_model.SENSOR_RANGE).adr[0]
        self._adr_gyro = self.model.sensor(bench_model.SENSOR_GYRO).adr[0]
        self._adr_accel = self.model.sensor(bench_model.SENSOR_ACCEL).adr[0]

        sensors = self.config.sensors
        self._gyro_bias_dps = self.rng.normal(0.0, sensors.gyro_bias_dps_std, size=3)
        self._accel_bias_g = self.rng.normal(0.0, sensors.accel_bias_g_std, size=3)
        self._as5600_step_deg = 360.0 / float(2 ** sensors.as5600_bits)
        self._gyro_lsb_per_dps = (INT16_MAX + 1) / sensors.gyro_range_dps
        self._accel_lsb_per_g = (INT16_MAX + 1) / sensors.accel_range_g

        self.time = 0.0
        self.step_count = 0
        self.imu_samples = []
        self.command_log = []
        self._requested_deg = self.config.servo.neutral_deg
        self._limited_deg = self.config.servo.neutral_deg

        self.data.qpos[self._qpos_servo] = 0.0
        self.data.qvel[:] = 0.0
        mujoco.mj_forward(self.model, self.data)
        return self._read_observation()

    # ------------------------------------------------------------------- step

    def step(self, servo_target_deg: float) -> BenchObservation:
        servo = self.config.servo
        target = clamp(float(servo_target_deg), servo.min_deg, servo.max_deg)
        if target != self._requested_deg:
            self.command_log.append(
                {"timestamp_ns": int(round(self.time * 1e9)), "requested_angle_deg": float(target)}
            )
        self._requested_deg = target

        max_delta = servo.max_speed_deg_s * self.config.control_dt
        delta = clamp(target - self._limited_deg, -max_delta, max_delta)
        self._limited_deg = clamp(self._limited_deg + delta, servo.min_deg, servo.max_deg)
        self.data.ctrl[self._ctrl_servo] = math.radians(self._limited_deg - servo.neutral_deg)

        for _ in range(self._n_substeps):
            mujoco.mj_step(self.model, self.data)
            self._substep_counter += 1
            if self._substep_counter % self._imu_every == 0:
                self._record_imu_sample()

        self.time += self.config.control_dt
        self.step_count += 1
        return self._read_observation()

    # ---------------------------------------------------------------- sensing

    def _raw_imu(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        sensors = self.config.sensors
        gyro_rad = np.array(self.data.sensordata[self._adr_gyro : self._adr_gyro + 3])
        accel_ms2 = np.array(self.data.sensordata[self._adr_accel : self._adr_accel + 3])

        gyro_dps = np.degrees(gyro_rad) + self._gyro_bias_dps + self.rng.normal(0.0, sensors.gyro_noise_dps, size=3)
        accel_g = accel_ms2 / GRAVITY + self._accel_bias_g + self.rng.normal(0.0, sensors.accel_noise_g, size=3)

        gyro_raw = np.clip(np.round(gyro_dps * self._gyro_lsb_per_dps), -INT16_MAX - 1, INT16_MAX).astype(int)
        accel_raw = np.clip(np.round(accel_g * self._accel_lsb_per_g), -INT16_MAX - 1, INT16_MAX).astype(int)
        return tuple(gyro_raw.tolist()), tuple(accel_raw.tolist())

    def _record_imu_sample(self) -> None:
        gyro_raw, accel_raw = self._raw_imu()
        timestamp_ns = int(round(self.data.time * 1e9))
        self.imu_samples.append(
            {"timestamp_ns": timestamp_ns, "gyro_raw": list(gyro_raw), "accel_raw": list(accel_raw)}
        )

    def servo_angle_deg(self) -> float:
        return self.config.servo.neutral_deg + math.degrees(float(self.data.qpos[self._qpos_servo]))

    def _as5600_deg(self) -> float:
        return round(self.servo_angle_deg() / self._as5600_step_deg) * self._as5600_step_deg

    def _distance(self) -> float:
        sensors = self.config.sensors
        reading = float(self.data.sensordata[self._adr_range])
        if reading < 0.0:
            reading = sensors.ultrasonic_max_range
        reading += float(self.rng.normal(0.0, sensors.ultrasonic_noise_m))
        return float(max(0.02, min(reading, sensors.ultrasonic_max_range)))

    def _read_observation(self) -> BenchObservation:
        gyro_raw, accel_raw = self._raw_imu()
        return BenchObservation(
            time=float(self.time),
            requested_deg=float(self._requested_deg),
            as5600_deg=float(self._as5600_deg()),
            gyro_raw=gyro_raw,
            accel_raw=accel_raw,
            distance_m=self._distance(),
        )

    # -------------------------------------------------------------- rendering

    def _clean_scene_option(self) -> mujoco.MjvOption:
        option = mujoco.MjvOption()
        option.flags[mujoco.mjtVisFlag.mjVIS_RANGEFINDER] = False
        option.sitegroup[:] = 0
        return option

    def render_camera(self, width: int = 128, height: int = 128, camera: str = bench_model.CAMERA_HEAD) -> np.ndarray:
        if self._renderer is not None and self._renderer_size != (width, height):
            self._renderer.close()
            self._renderer = None
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, height=height, width=width)
            self._renderer_size = (width, height)
        self._renderer.update_scene(self.data, camera=camera, scene_option=self._clean_scene_option())
        return self._renderer.render()

    def sync_viewer(self) -> None:
        if self.viewer is None:
            import mujoco.viewer

            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        if self.viewer.is_running():
            self.viewer.sync()

    def save_frame(self, path: str, camera: str = "bench_overview", width: int = 1280, height: int = 960) -> None:
        renderer = mujoco.Renderer(self.model, height=height, width=width)
        try:
            renderer.update_scene(self.data, camera=camera, scene_option=self._clean_scene_option())
            pixels = renderer.render()
        finally:
            renderer.close()

        import matplotlib.image

        matplotlib.image.imsave(path, pixels)

    def close(self) -> None:
        if self.viewer is not None:
            self.viewer.close()
            self.viewer = None
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None
