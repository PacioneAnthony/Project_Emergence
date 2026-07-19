import unittest

import numpy as np

from learning.developmental_curiosity import DevelopmentalCuriosity, InterventionalCuriosity


class DevelopmentalCuriosityTests(unittest.TestCase):
    def test_starts_from_home_without_authored_levels(self):
        curiosity = DevelopmentalCuriosity(1, np.array([0.0]), epsilon=0.0, seed=1)
        candidates = np.array([[0.0], [0.2], [0.6], [1.0]])
        components = curiosity.score_components(candidates)
        self.assertEqual(int(np.argmax(components["score"])), 0)
        self.assertGreater(components["reachability"][1], components["reachability"][2])

    def test_mastery_expands_the_continuous_frontier(self):
        curiosity = DevelopmentalCuriosity(1, np.array([0.0]), epsilon=0.0, seed=2)
        for error in np.linspace(1.0, 0.05, 24):
            curiosity.observe(np.array([0.0]), float(error))
        self.assertGreater(curiosity.mastery(), 0.7)
        candidates = np.array([[0.0], [0.35], [0.9]])
        components = curiosity.score_components(candidates)
        self.assertGreater(components["reachability"][1], 0.7)
        self.assertGreater(components["score"][1], components["score"][0])

    def test_prefers_learnable_frontier_and_rejects_persistent_noise(self):
        curiosity = DevelopmentalCuriosity(
            1,
            np.array([0.0]),
            bandwidth=0.08,
            initial_frontier=0.2,
            max_frontier=1.0,
            epsilon=0.0,
            seed=3,
        )
        # Familiar mastered experience.
        for error in np.linspace(0.8, 0.03, 20):
            curiosity.observe(np.array([0.0]), float(error))
        # Learnable experience: error decreases consistently.
        for error in np.linspace(1.0, 0.15, 20):
            curiosity.observe(np.array([0.45]), float(error))
        # Unlearnable experience: high, noisy error persists.
        for error in [1.4, 0.7, 1.5, 0.8, 1.3, 0.9, 1.6, 0.7, 1.5, 0.8] * 2:
            curiosity.observe(np.array([0.8]), error)

        candidates = np.array([[0.0], [0.45], [0.8]])
        components = curiosity.score_components(candidates)
        self.assertEqual(int(np.argmax(components["score"])), 1)
        self.assertGreater(components["progress"][1], components["progress"][2])
        self.assertGreater(components["irreducible"][2], components["irreducible"][1])

    def test_risk_and_controllability_gate_curiosity(self):
        curiosity = DevelopmentalCuriosity(2, np.array([0.0, 0.0]), epsilon=0.0, seed=4)
        candidates = np.array([[0.0, 0.0], [0.0, 0.1]])
        safe = curiosity.score_components(candidates)
        gated = curiosity.score_components(
            candidates,
            controllability=np.array([1.0, 0.0]),
            risk=np.array([0.0, 1.0]),
        )
        self.assertGreater(safe["score"][1], gated["score"][1])
        self.assertLess(gated["score"][1], gated["score"][0])

    def test_bootstrap_uncertainty_falls_with_local_evidence(self):
        curiosity = DevelopmentalCuriosity(1, np.array([0.0]), bandwidth=0.1, epsilon=0.0, seed=5)
        candidate = np.array([[0.5]])
        before = curiosity.score_components(candidate)["epistemic"][0]
        for _ in range(80):
            curiosity.observe(np.array([0.5]), 0.4)
        after = curiosity.score_components(candidate)["epistemic"][0]
        self.assertGreater(after, before)
        # Compare against an equally distant but unseen point after the scale is known.
        unseen = curiosity.score_components(np.array([[0.8]]))["epistemic"][0]
        self.assertLess(after, unseen)

    def test_online_memory_is_bounded(self):
        curiosity = DevelopmentalCuriosity(
            1, np.array([0.0]), max_observations=16, epsilon=0.0, seed=6
        )
        for index in range(40):
            curiosity.observe(np.array([index / 40]), 0.5)
        self.assertEqual(curiosity.observation_count, 16)


class InterventionalCuriosityTests(unittest.TestCase):
    def test_starts_at_home_and_prefers_measured_reducible_gain(self):
        curiosity = InterventionalCuriosity(1, np.array([0.1]), epsilon=0.0)
        candidates = np.array([[0.1], [0.45], [0.85]])
        self.assertEqual(curiosity.choose(candidates, np.random.default_rng(7)), 0)

        for before, after in [(0.24, 0.14), (0.14, 0.08), (0.08, 0.06), (0.06, 0.055), (0.055, 0.054)]:
            curiosity.observe(np.array([0.1]), before, after)
        for before, after in [(1.0, 0.84), (0.84, 0.70), (0.70, 0.58), (0.58, 0.48), (0.48, 0.40)]:
            curiosity.observe(np.array([0.45]), before, after)
        for _ in range(8):
            curiosity.observe(np.array([0.85]), 1.0, 1.0)

        components = curiosity.score_components(candidates)
        self.assertEqual(int(np.argmax(components["score"])), 1)
        self.assertGreater(components["confirmed_gain"][1], components["confirmed_gain"][2])
        self.assertGreater(components["unproductive"][2], components["unproductive"][1])

    def test_gain_is_derived_from_same_anchor_before_after(self):
        curiosity = InterventionalCuriosity(1, np.array([0.0]), epsilon=0.0)
        curiosity.observe(np.array([0.2]), 0.8, 0.5)
        curiosity.observe(np.array([0.8]), 1.1, 1.1)
        self.assertAlmostEqual(curiosity.diagnostics()["mean_gain"], 0.15)


if __name__ == "__main__":
    unittest.main()
