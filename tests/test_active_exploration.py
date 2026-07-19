import unittest

import numpy as np

from learning.active_exploration import (
    DevelopmentalCuriosityChooser,
    LearningProgressChooser,
    UniformChooser,
    coverage_entropy,
)


class LearningProgressChooserTests(unittest.TestCase):
    def test_targets_stay_in_range(self):
        chooser = LearningProgressChooser(10.0, 170.0)
        rng = np.random.default_rng(1)
        for _ in range(200):
            target = chooser.choose(rng)
            self.assertGreaterEqual(target, 10.0)
            self.assertLessEqual(target, 170.0)

    def test_optimistic_init_visits_every_bin(self):
        chooser = LearningProgressChooser(10.0, 170.0, bins=8, epsilon=0.0)
        rng = np.random.default_rng(2)
        for _ in range(80):
            target = chooser.choose(rng)
            chooser.update(target, 1.0)
        self.assertTrue(all(count > 0 for count in chooser.visit_counts()))

    def test_prefers_bin_with_decreasing_error(self):
        chooser = LearningProgressChooser(10.0, 170.0, bins=2, window=20, min_samples=4, epsilon=0.0)
        # Bin 0 (10-90): error drops -> positive learning progress.
        for error in np.linspace(2.0, 0.2, 12):
            chooser.update(30.0, float(error))
        # Bin 1 (90-170): flat error -> no progress.
        for _ in range(12):
            chooser.update(130.0, 1.0)
        rng = np.random.default_rng(3)
        picks_in_bin0 = sum(1 for _ in range(50) if chooser.choose(rng) < 90.0)
        self.assertEqual(picks_in_bin0, 50)

    def test_uniform_chooser_covers_range(self):
        chooser = UniformChooser(10.0, 170.0)
        rng = np.random.default_rng(4)
        targets = [chooser.choose(rng) for _ in range(500)]
        self.assertLess(min(targets), 30.0)
        self.assertGreater(max(targets), 150.0)

    def test_coverage_entropy_bounds(self):
        uniform = np.random.default_rng(5).uniform(10.0, 170.0, size=5000)
        collapsed = np.full(5000, 42.0)
        self.assertGreater(coverage_entropy(uniform, 10.0, 170.0), 0.95)
        self.assertLess(coverage_entropy(collapsed, 10.0, 170.0), 0.05)

    def test_developmental_adapter_uses_continuous_safe_targets(self):
        chooser = DevelopmentalCuriosityChooser(10.0, 170.0, 90.0, seed=6)
        rng = np.random.default_rng(6)
        first = chooser.choose(rng, current_deg=90.0)
        self.assertGreaterEqual(first, 10.0)
        self.assertLessEqual(first, 170.0)
        for error in np.linspace(0.9, 0.1, 20):
            chooser.update_transition(90.0, first, float(error))
        later = chooser.choose(rng, current_deg=first)
        self.assertGreaterEqual(later, 10.0)
        self.assertLessEqual(later, 170.0)
        self.assertEqual(chooser.diagnostics()["observations"], 20)


if __name__ == "__main__":
    unittest.main()
