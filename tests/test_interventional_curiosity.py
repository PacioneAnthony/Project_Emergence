import unittest

from learning.curiosity_benchmark import ContinuousLearningWorld
from learning.interventional_curiosity_benchmark import CONDITIONS, run_condition
from learning.fractional_curiosity_benchmark import make_world, run_condition as run_fractional


class InterventionalBenchmarkTests(unittest.TestCase):
    def test_fixed_anchor_gain_separates_structured_from_noise(self):
        structured = ContinuousLearningWorld(seed=10, budget=16)
        s_before, s_after, _ = structured.intervene(0.5, 0, samples=4)
        noisy = ContinuousLearningWorld(seed=10, budget=16)
        n_before, n_after, _ = noisy.intervene(0.95, 0, samples=4)
        self.assertGreater(s_before - s_after, n_before - n_after)

    def test_intervention_consumes_exact_sample_budget(self):
        world = ContinuousLearningWorld(seed=11, budget=12)
        world.intervene(0.4, 0, samples=4)
        world.intervene(0.6, 4, samples=4)
        self.assertEqual(len(world.visits), 8)

    def test_all_conditions_run_deterministically(self):
        for condition in CONDITIONS:
            first = run_condition(condition, seed=12, sample_budget=80)
            second = run_condition(condition, seed=12, sample_budget=80)
            self.assertEqual(first, second)
            self.assertEqual(first["interventions"], 20)

    def test_rejects_non_divisible_budget(self):
        with self.assertRaises(ValueError):
            run_condition("interventional", seed=13, sample_budget=81)

    def test_randomized_world_is_seeded_and_within_protocol_ranges(self):
        first = make_world(5301, 80)
        second = make_world(5301, 80)
        self.assertEqual(first.base_limit, second.base_limit)
        self.assertGreaterEqual(first.base_limit, 0.20)
        self.assertLessEqual(first.noise_limit, 0.85)

    def test_fractional_condition_runs_deterministically(self):
        first = run_fractional("fractional", 5302, sample_budget=80)
        second = run_fractional("fractional", 5302, sample_budget=80)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
