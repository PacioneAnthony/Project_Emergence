import unittest

from common.types import Action
import numpy as np

from learning.rollout_jepa_mpc import candidate_action, candidate_modes, score_candidates
from sim2d.config import RobotConfig


class JEPAMPCTests(unittest.TestCase):
    def test_candidates_preserve_servo_to_avoid_sensor_gaming(self):
        robot = RobotConfig()
        base = Action(0.4, 0.3, 0.72)
        candidates = [candidate_action(mode, base, robot, 1.2) for mode in candidate_modes()]
        self.assertTrue(all(candidate.servo_target == base.servo_target for candidate in candidates))

    def test_base_candidate_preserves_reverse_command(self):
        robot = RobotConfig()
        base = Action(-0.2, 0.3, -0.4)
        self.assertEqual(candidate_action("base", base, robot, 0.6), base)

    def test_slow_candidate_reduces_reverse_magnitude_without_flipping_sign(self):
        robot = RobotConfig()
        slow = candidate_action("slow", Action(-0.2, 0.0, 0.0), robot, 0.6)
        self.assertLess(slow.v_cmd, 0.0)
        self.assertLess(abs(slow.v_cmd), 0.2)

    def test_turn_candidates_slow_down_and_turn_both_directions(self):
        robot = RobotConfig()
        base = Action(0.4, 0.0, 0.0)
        left = candidate_action("left", base, robot, 1.2)
        right = candidate_action("right", base, robot, 1.2)
        self.assertLess(left.v_cmd, base.v_cmd)
        self.assertGreater(left.omega_cmd, 0.0)
        self.assertLess(right.omega_cmd, 0.0)

    def test_candidates_exclude_extreme_turns(self):
        self.assertEqual(candidate_modes(), ("base", "slow", "left", "right"))
        self.assertEqual(candidate_modes("slow_only"), ("base", "slow"))

    def test_action_penalty_breaks_close_prediction_toward_base(self):
        robot = RobotConfig()
        base = Action(0.4, 0.0, 0.0)
        actions = [base, candidate_action("left", base, robot, 0.6)]
        scores = score_candidates(np.array([0.30, 0.31]), actions, base, robot, 0.08)
        self.assertGreater(scores[0], scores[1])


if __name__ == "__main__":
    unittest.main()
