import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from common.types import Action, Observation
from learning.jepa_lnn_features import build_live_context_vector, build_lnn_input_from_latent, load_context_action_array


class JepaLnnCouplingTests(unittest.TestCase):
    def test_live_context_uses_past_observations_current_observation_and_past_actions(self):
        obs_history = [
            Observation(distance=1.0, servo_angle=0.1, gyro_z=0.01),
            Observation(distance=0.9, servo_angle=0.2, gyro_z=0.02),
        ]
        action_history = [
            Action(v_cmd=0.1, omega_cmd=0.2, servo_target=0.3),
            Action(v_cmd=0.4, omega_cmd=0.5, servo_target=0.6),
        ]
        current = Observation(distance=0.8, servo_angle=0.3, gyro_z=0.03)

        context = build_live_context_vector(obs_history, action_history, current, context_steps=3)

        expected = np.array(
            [
                1.0,
                0.1,
                0.01,
                0.9,
                0.2,
                0.02,
                0.8,
                0.3,
                0.03,
                0.1,
                0.2,
                0.3,
                0.4,
                0.5,
                0.6,
            ],
            dtype=np.float32,
        )
        self.assertTrue(np.allclose(context, expected))

    def test_live_context_left_pads_missing_history_without_future_actions(self):
        current = Observation(distance=0.8, servo_angle=0.3, gyro_z=0.03)

        context = build_live_context_vector([], [], current, context_steps=2)

        expected = np.array([0.8, 0.3, 0.03, 0.8, 0.3, 0.03, 0.0, 0.0, 0.0], dtype=np.float32)
        self.assertTrue(np.allclose(context, expected))

    def test_context_actions_prefer_student_actuator_when_available_per_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "log.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "actuator_action_v_cmd",
                        "actuator_action_omega_cmd",
                        "actuator_action_servo_target",
                        "student_actuator_action_v_cmd",
                        "student_actuator_action_omega_cmd",
                        "student_actuator_action_servo_target",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "actuator_action_v_cmd": "1",
                        "actuator_action_omega_cmd": "2",
                        "actuator_action_servo_target": "3",
                        "student_actuator_action_v_cmd": "",
                        "student_actuator_action_omega_cmd": "",
                        "student_actuator_action_servo_target": "",
                    }
                )
                writer.writerow(
                    {
                        "actuator_action_v_cmd": "1",
                        "actuator_action_omega_cmd": "2",
                        "actuator_action_servo_target": "3",
                        "student_actuator_action_v_cmd": "4",
                        "student_actuator_action_omega_cmd": "5",
                        "student_actuator_action_servo_target": "6",
                    }
                )

            actions = load_context_action_array(path)

        self.assertEqual(actions.tolist(), [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])

    def test_fixed_latent_input_keeps_current_observation(self):
        obs = Observation(distance=0.8, servo_angle=0.3, gyro_z=0.03)
        latent = np.array([1.0, 2.0], dtype=np.float32)

        lnn_input = build_lnn_input_from_latent(obs, latent)

        self.assertTrue(np.allclose(lnn_input, [0.8, 0.3, 0.03, 1.0, 2.0]))


if __name__ == "__main__":
    unittest.main()
