import unittest

import numpy as np

from learning.datasets import build_context_transitions
from learning.evaluate_jepa import (
    apply_linear_probe,
    fit_ridge_probe,
    latest_observation_from_context,
    observation_probe_metrics,
    split_indices,
)


class JepaEvaluationTests(unittest.TestCase):
    def test_episode_split_keeps_last_episode_for_validation(self):
        arrays = {
            "obs": np.zeros((6, 3), dtype=np.float32),
            "episode": np.array([0, 0, 1, 1, 2, 2], dtype=np.int64),
        }
        train_idx, test_idx = split_indices(arrays, 0.34)
        self.assertEqual(train_idx.tolist(), [0, 1, 2, 3])
        self.assertEqual(test_idx.tolist(), [4, 5])

    def test_ridge_probe_recovers_linear_mapping(self):
        features = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
        targets = np.array([[1.0], [3.0], [4.0], [6.0]], dtype=np.float32)
        weights = fit_ridge_probe(features, targets, alpha=1e-9)
        prediction = apply_linear_probe(features, weights)
        self.assertTrue(np.allclose(prediction, targets, atol=1e-4))

    def test_observation_probe_metrics_have_fields(self):
        target = np.array([[1.0, 0.0, 0.1], [2.0, 0.1, 0.2]], dtype=np.float32)
        decoded = target.copy()
        persistence = np.zeros_like(target)
        mean = np.repeat(target.mean(axis=0, keepdims=True), len(target), axis=0)
        metrics = observation_probe_metrics(decoded, target, persistence, mean)
        self.assertIn("distance", metrics["per_field"])
        self.assertAlmostEqual(metrics["rmse_mean"], 0.0)

    def test_context_transitions_stay_inside_episode(self):
        arrays = {
            "obs": np.arange(18, dtype=np.float32).reshape(6, 3),
            "action": np.ones((6, 3), dtype=np.float32),
            "next_obs": np.arange(100, 118, dtype=np.float32).reshape(6, 3),
            "episode": np.array([0, 0, 0, 1, 1, 1], dtype=np.int64),
            "reward": np.zeros(6, dtype=np.float32),
            "done": np.array([False, False, True, False, False, True]),
        }
        context = build_context_transitions(arrays, context_steps=2)
        self.assertEqual(context["obs"].shape, (4, 9))
        self.assertEqual(context["episode"].tolist(), [0, 0, 1, 1])

        latest = latest_observation_from_context(context["obs"], context_steps=2)
        self.assertTrue(np.allclose(latest[0], arrays["obs"][1]))


if __name__ == "__main__":
    unittest.main()
