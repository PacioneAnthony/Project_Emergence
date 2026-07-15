import tempfile
import unittest
from pathlib import Path

try:
    import mujoco  # noqa: F401

    MUJOCO_AVAILABLE = True
except ModuleNotFoundError:
    MUJOCO_AVAILABLE = False

from common.types import Action
from learning.datasets import load_simulation_csv
from sim2d.config import SimConfig
from sim2d.environment import RobotSimEnv
from sim2d.logger import CSVLogger

if MUJOCO_AVAILABLE:
    from sim3d.config import Body3DConfig, Sim3DConfig
    from sim3d.environment import RobotSim3DEnv


def quiet_config(**kwargs) -> SimConfig:
    config = SimConfig(domain_randomization=False, **kwargs)
    config.sensors.ultrasonic_noise_std = 0.0
    config.sensors.gyro_noise_std = 0.0
    config.sensors.gyro_bias_std = 0.0
    config.sensors.latency_seconds = 0.0
    return config


@unittest.skipUnless(MUJOCO_AVAILABLE, "MuJoCo is not installed")
class Sim3DTests(unittest.TestCase):
    def test_environment_step_returns_valid_observation(self):
        config = SimConfig(max_steps=5, domain_randomization=False)
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSim3DEnv(config)
        obs = env.reset(seed=123)
        next_obs, reward, done, info = env.step(Action(v_cmd=0.2, omega_cmd=0.0, servo_target=0.0))

        self.assertEqual(obs.as_array().shape, (3,))
        self.assertEqual(next_obs.as_array().shape, (3,))
        self.assertIsInstance(reward, float)
        self.assertFalse(done)
        self.assertIn("state", info)
        self.assertIn("safe_action", info)
        self.assertIn("actuator_action", info)

    def test_true_distance_matches_sim2d_raycast_at_reset(self):
        for seed in (1, 7, 42, 999):
            env2d = RobotSimEnv(quiet_config(max_steps=5))
            env3d = RobotSim3DEnv(quiet_config(max_steps=5))
            obs2d = env2d.reset(seed=seed)
            obs3d = env3d.reset(seed=seed)

            state2d = env2d.robot.state
            state3d = env3d._read_state()
            self.assertAlmostEqual(state2d.x, state3d.x, places=9)
            self.assertAlmostEqual(state2d.y, state3d.y, places=9)
            self.assertAlmostEqual(state2d.heading, state3d.heading, places=9)
            self.assertAlmostEqual(obs2d.distance, obs3d.distance, places=3)

    def test_reset_is_deterministic_per_seed(self):
        env_a = RobotSim3DEnv(SimConfig(max_steps=20))
        env_b = RobotSim3DEnv(SimConfig(max_steps=20))
        obs_a = env_a.reset(seed=77)
        obs_b = env_b.reset(seed=77)
        self.assertEqual(obs_a.as_array().tolist(), obs_b.as_array().tolist())

        action = Action(v_cmd=0.3, omega_cmd=0.5, servo_target=0.4)
        for _ in range(10):
            obs_a, _, _, _ = env_a.step(action)
            obs_b, _, _, _ = env_b.step(action)
        self.assertEqual(obs_a.as_array().tolist(), obs_b.as_array().tolist())

    def test_servo_tracks_rate_limited_target(self):
        config = quiet_config(max_steps=200)
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSim3DEnv(config)
        env.reset(seed=5)
        obs = None
        for _ in range(100):
            obs, _, _, _ = env.step(Action(servo_target=1.0))
        self.assertAlmostEqual(obs.servo_angle, 1.0, places=2)

    def test_driving_into_wall_reports_collision_and_stays_in_bounds(self):
        config = quiet_config(max_steps=600)
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSim3DEnv(config)
        env.reset(seed=11)

        collided = False
        state = None
        for _ in range(600):
            _, _, _, info = env.step(Action(v_cmd=0.5, omega_cmd=0.0, servo_target=0.0))
            state = info["state"]
            collided = collided or bool(info["collision"])
        self.assertTrue(collided)
        margin = env.config.robot.radius * 0.5
        self.assertGreaterEqual(state.x, -margin)
        self.assertLessEqual(state.x, env.config.world.width + margin)
        self.assertGreaterEqual(state.y, -margin)
        self.assertLessEqual(state.y, env.config.world.height + margin)

    def test_pwm_zero_order_hold_keeps_servo_command_between_ticks(self):
        config = SimConfig(dt=0.01, max_steps=5, domain_randomization=False)
        config.robot.pwm_period = 0.02
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSim3DEnv(config)
        env.reset(seed=123)

        _, _, _, first_info = env.step(Action(servo_target=1.0))
        _, _, _, second_info = env.step(Action(servo_target=-1.0))
        _, _, _, third_info = env.step(Action(servo_target=-1.0))

        self.assertAlmostEqual(first_info["actuator_action"].servo_target, 1.0)
        self.assertAlmostEqual(second_info["actuator_action"].servo_target, 1.0)
        self.assertAlmostEqual(third_info["actuator_action"].servo_target, -1.0)

    def test_csv_log_is_loadable_by_learning_datasets(self):
        config = SimConfig(max_steps=5, domain_randomization=False)
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSim3DEnv(config)
        obs = env.reset(seed=321)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "log.csv"
            with CSVLogger(path) as logger:
                for step in range(3):
                    action = Action(v_cmd=0.1, omega_cmd=0.0, servo_target=0.0)
                    next_obs, reward, done, info = env.step(action)
                    logger.write(0, step, obs, action, next_obs, reward, done, info)
                    obs = next_obs
            arrays = load_simulation_csv(path)

        self.assertEqual(arrays["obs"].shape, (3, 3))
        self.assertEqual(arrays["action"].shape, (3, 3))
        self.assertEqual(arrays["state"].shape, (3, 6))

    def test_cone_rays_reduce_or_keep_distance(self):
        cone_env = RobotSim3DEnv(Sim3DConfig(base=quiet_config(max_steps=5), body=Body3DConfig(cone_rays=5)))
        single_env = RobotSim3DEnv(Sim3DConfig(base=quiet_config(max_steps=5), body=Body3DConfig(cone_rays=1)))
        for seed in (3, 21):
            cone_obs = cone_env.reset(seed=seed)
            single_obs = single_env.reset(seed=seed)
            self.assertLessEqual(cone_obs.distance, single_obs.distance + 1e-6)


if __name__ == "__main__":
    unittest.main()
