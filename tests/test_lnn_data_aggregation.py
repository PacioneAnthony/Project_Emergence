import argparse
import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from common.types import Action, Observation, RobotState
from learning.aggregate_lnn_data import (
    ExpertRelabelledCSVLogger,
    finalize_aggregation_metrics,
    new_aggregation_stats,
    observe_student_step,
    update_aggregation_stats,
)
from learning.datasets import load_simulation_csv
from learning.merge_sim_logs import merge_logs
from sim2d.config import SimConfig


class LnnDataAggregationTests(unittest.TestCase):
    def test_relabelled_logger_uses_expert_action_as_training_target(self):
        obs = Observation(distance=1.0, servo_angle=0.0, gyro_z=0.0, time=0.0)
        next_obs = Observation(distance=0.8, servo_angle=0.1, gyro_z=0.2, time=0.02)
        expert = Action(v_cmd=0.1, omega_cmd=0.2, servo_target=0.3)
        student = Action(v_cmd=-0.4, omega_cmd=-0.5, servo_target=-0.6)
        info = {
            "state": RobotState(x=1.0, y=1.0, heading=0.0, servo_angle=0.1),
            "safe_action": student,
            "actuator_action": student,
            "collision": False,
            "true_distance": 0.9,
            "nearest_surface": 0.7,
            "reward_terms": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dagger.csv"
            with ExpertRelabelledCSVLogger(path) as logger:
                logger.write(0, 0, obs, expert, expert, expert, student, next_obs, 1.0, False, info)

            arrays = load_simulation_csv(path)
            with path.open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertTrue(np.allclose(arrays["action"][0], expert.as_array()))
        self.assertAlmostEqual(float(rows[0]["student_action_v_cmd"]), student.v_cmd)

    def test_aggregation_metrics_track_student_expert_error(self):
        stats = new_aggregation_stats(episodes=1)
        update_aggregation_stats(
            stats,
            reward=0.5,
            info={"collision": True, "nearest_surface": 0.1, "true_distance": 0.2},
            student_action=Action(v_cmd=1.0, omega_cmd=0.0, servo_target=-1.0),
            expert_actuator_action=Action(v_cmd=0.0, omega_cmd=0.0, servo_target=1.0),
        )
        args = argparse.Namespace(checkpoint=Path("model.pth"), output=Path("dagger.csv"), steps=10, scan_hz=0.5)
        metrics = finalize_aggregation_metrics(stats, args, SimConfig(dt=0.02))

        self.assertEqual(metrics["collision_ticks"], 1)
        self.assertEqual(metrics["collision_rate"], 1.0)
        self.assertAlmostEqual(metrics["student_expert_per_action"]["v_cmd"]["rmse"], 1.0)
        self.assertAlmostEqual(metrics["student_expert_per_action"]["servo_target"]["rmse"], 2.0)

    def test_merge_logs_offsets_episode_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = Path(tmpdir) / "first.csv"
            second = Path(tmpdir) / "second.csv"
            output = Path(tmpdir) / "merged.csv"
            first.write_text("episode,step,value\n0,0,a\n1,0,b\n", encoding="utf-8")
            second.write_text("episode,step,value\n0,0,c\n1,0,d\n", encoding="utf-8")

            written = merge_logs([first, second], output)
            with output.open("r", newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(written, 4)
        self.assertEqual([row["episode"] for row in rows], ["0", "1", "2", "3"])

    def test_observe_student_step_calls_policy_hook_when_available(self):
        class Policy:
            def __init__(self):
                self.calls = []

            def observe_step(self, info, fallback_action):
                self.calls.append((info, fallback_action))

        policy = Policy()
        action = Action(v_cmd=0.1)
        info = {"collision": False}

        observe_student_step(policy, info, action)

        self.assertEqual(policy.calls, [(info, action)])


if __name__ == "__main__":
    unittest.main()
