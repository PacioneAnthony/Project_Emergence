import tempfile
import unittest
from pathlib import Path

from common.types import Action
from learning.datasets import load_simulation_csv
from sim2d.config import SimConfig, WorldConfig
from sim2d.environment import RobotSimEnv
from sim2d.logger import CSVLogger
from sim2d.world import World


class Sim2DTests(unittest.TestCase):
    def test_raycast_hits_world_wall(self):
        world = World(WorldConfig(width=10.0, height=10.0, fixed_obstacles=(), random_obstacles=False))
        self.assertAlmostEqual(world.raycast((5.0, 5.0), 0.0, max_range=20.0), 5.0, places=6)

    def test_environment_step_returns_valid_observation(self):
        config = SimConfig(max_steps=5, domain_randomization=False)
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSimEnv(config)
        obs = env.reset(seed=123)
        next_obs, reward, done, info = env.step(Action(v_cmd=0.2, omega_cmd=0.0, servo_target=0.0))

        self.assertEqual(obs.as_array().shape, (3,))
        self.assertEqual(next_obs.as_array().shape, (3,))
        self.assertIsInstance(reward, float)
        self.assertFalse(done)
        self.assertIn("state", info)

    def test_collision_detection_near_wall(self):
        world = World(WorldConfig(width=1.0, height=1.0, fixed_obstacles=(), random_obstacles=False))
        self.assertTrue(world.collides_circle(0.05, 0.5, 0.1))
        self.assertFalse(world.collides_circle(0.5, 0.5, 0.1))

    def test_csv_logger_writes_transition(self):
        config = SimConfig(max_steps=5, domain_randomization=False)
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSimEnv(config)
        obs = env.reset(seed=321)
        action = Action(v_cmd=0.1, omega_cmd=0.0, servo_target=0.0)
        next_obs, reward, done, info = env.step(action)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "log.csv"
            with CSVLogger(path) as logger:
                logger.write(0, 0, obs, action, next_obs, reward, done, info)
            text = path.read_text(encoding="utf-8")
            self.assertIn("obs_distance", text)
            self.assertIn("next_obs_distance", text)
            self.assertIn("actuator_action_servo_target", text)

    def test_pwm_zero_order_hold_keeps_servo_command_between_ticks(self):
        config = SimConfig(dt=0.01, max_steps=5, domain_randomization=False)
        config.robot.pwm_period = 0.02
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSimEnv(config)
        env.reset(seed=123)

        _, _, _, first_info = env.step(Action(servo_target=1.0))
        _, _, _, second_info = env.step(Action(servo_target=-1.0))
        _, _, _, third_info = env.step(Action(servo_target=-1.0))

        self.assertAlmostEqual(first_info["actuator_action"].servo_target, 1.0)
        self.assertAlmostEqual(second_info["actuator_action"].servo_target, 1.0)
        self.assertAlmostEqual(third_info["actuator_action"].servo_target, -1.0)

    def test_dataset_uses_actuator_action_when_available(self):
        config = SimConfig(dt=0.01, max_steps=5, domain_randomization=False)
        config.robot.pwm_period = 0.02
        config.world.fixed_obstacles = ()
        config.world.random_obstacles = False
        env = RobotSimEnv(config)
        obs = env.reset(seed=321)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "log.csv"
            with CSVLogger(path) as logger:
                action = Action(servo_target=1.0)
                next_obs, reward, done, info = env.step(action)
                logger.write(0, 0, obs, action, next_obs, reward, done, info)
                obs = next_obs

                action = Action(servo_target=-1.0)
                next_obs, reward, done, info = env.step(action)
                logger.write(0, 1, obs, action, next_obs, reward, done, info)

            arrays = load_simulation_csv(path)

        self.assertAlmostEqual(float(arrays["action"][0, 2]), 1.0)
        self.assertAlmostEqual(float(arrays["action"][1, 2]), 1.0)


if __name__ == "__main__":
    unittest.main()
