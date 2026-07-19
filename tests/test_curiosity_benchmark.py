import unittest

import numpy as np

from learning.curiosity_benchmark import CONDITIONS, ContinuousLearningWorld, run_condition


class CuriosityBenchmarkTests(unittest.TestCase):
    def test_local_experience_reduces_structured_heldout_error(self):
        world = ContinuousLearningWorld(seed=1, budget=80)
        before = world.structured_error()
        for step, x in enumerate(np.linspace(0.34, 0.72, 80)):
            world.observe(float(x), step)
        self.assertLess(world.structured_error(), before)

    def test_noise_is_paired_by_seed_step_and_coordinate(self):
        first = ContinuousLearningWorld(seed=2, budget=10)
        second = ContinuousLearningWorld(seed=2, budget=10)
        self.assertEqual(first.observe(0.95, 0), second.observe(0.95, 0))

    def test_every_condition_runs_and_reports_bounded_metrics(self):
        for condition in CONDITIONS:
            result = run_condition(condition, seed=3, budget=60)
            self.assertEqual(result["condition"], condition)
            self.assertGreaterEqual(result["noise_fraction"], 0.0)
            self.assertLessEqual(result["noise_fraction"], 1.0)
            self.assertGreaterEqual(result["coverage_entropy"], 0.0)
            self.assertLessEqual(result["coverage_entropy"], 1.0)

    def test_run_is_deterministic(self):
        first = run_condition("developmental", seed=4, budget=80)
        second = run_condition("developmental", seed=4, budget=80)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
