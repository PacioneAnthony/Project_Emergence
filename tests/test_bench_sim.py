import unittest

try:
    import mujoco  # noqa: F401

    MUJOCO_AVAILABLE = True
except ModuleNotFoundError:
    MUJOCO_AVAILABLE = False

if MUJOCO_AVAILABLE:
    from sim3d.bench_env import BenchHeadEnv
    from sim3d.bench_mechanics import run_qualification
    from sim3d.bench_model import BenchConfig, BenchSensorConfig


@unittest.skipUnless(MUJOCO_AVAILABLE, "MuJoCo is not installed")
class BenchSimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = BenchHeadEnv(BenchConfig(seed=5))

    @classmethod
    def tearDownClass(cls):
        cls.env.close()

    def test_reset_starts_at_neutral_with_quantized_as5600(self):
        obs = self.env.reset(seed=5)
        self.assertAlmostEqual(obs.as5600_deg, 90.0, places=2)
        step = 360.0 / 4096.0
        remainder = (obs.as5600_deg / step) - round(obs.as5600_deg / step)
        self.assertAlmostEqual(remainder, 0.0, places=6)

    def test_servo_reaches_target_and_respects_limits(self):
        self.env.reset(seed=5)
        obs = None
        for _ in range(100):
            obs = self.env.step(120.0)
        self.assertAlmostEqual(obs.as5600_deg, 120.0, delta=0.5)

        for _ in range(200):
            obs = self.env.step(500.0)  # clamped to 170
        self.assertLessEqual(obs.as5600_deg, 170.5)
        self.assertAlmostEqual(obs.as5600_deg, 170.0, delta=1.0)

    def test_imu_sampled_at_100hz(self):
        self.env.reset(seed=5)
        for _ in range(50):  # 1 s at 50 Hz control
            self.env.step(90.0)
        self.assertEqual(len(self.env.imu_samples), 100)

    def test_gyro_saturates_at_default_range_but_not_at_1000dps(self):
        def max_gyro(config: BenchConfig) -> int:
            env = BenchHeadEnv(config)
            try:
                env.reset(seed=5)
                peak = 0
                for _ in range(50):
                    env.step(170.0)
                for sample in env.imu_samples:
                    peak = max(peak, abs(int(sample["gyro_raw"][2])))
                return peak
            finally:
                env.close()

        saturated = max_gyro(BenchConfig(seed=5))
        wide = max_gyro(BenchConfig(seed=5, sensors=BenchSensorConfig(gyro_range_dps=1000.0)))
        self.assertGreaterEqual(saturated, 32767)
        self.assertLess(wide, 32767)

    def test_camera_renders_uint8_frames(self):
        self.env.reset(seed=5)
        frame = self.env.render_camera(64, 64)
        self.assertEqual(frame.shape, (64, 64, 3))
        self.assertEqual(frame.dtype.name, "uint8")

    def test_deterministic_per_seed(self):
        env_b = BenchHeadEnv(BenchConfig(seed=9))
        try:
            obs_a = self.env.reset(seed=9)
            obs_b = env_b.reset(seed=9)
            for _ in range(20):
                obs_a = self.env.step(130.0)
                obs_b = env_b.step(130.0)
            self.assertEqual(obs_a.as5600_deg, obs_b.as5600_deg)
            self.assertEqual(obs_a.gyro_raw, obs_b.gyro_raw)
            self.assertEqual(obs_a.distance_m, obs_b.distance_m)
        finally:
            env_b.close()

    def test_qualification_report_matches_j0_schema(self):
        env = BenchHeadEnv(BenchConfig(seed=3))
        try:
            report = run_qualification(env, rest_seconds=5.0, dwell_seconds=2.0, seed=3)
        finally:
            env.close()

        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["provisional_settling_limit_ratio"], 3.0)
        self.assertIn("passes_provisional_stability_check", report)
        evaluated = [c for c in report["commands"] if abs(c["step_deg"]) > 0]
        self.assertEqual(len(evaluated), 3)
        for command in evaluated:
            self.assertGreater(command["settling_gyro_ratio_to_baseline"], 0.0)
            self.assertLess(command["settling_gyro_ratio_to_baseline"], 100.0)


if __name__ == "__main__":
    unittest.main()
