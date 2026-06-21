import unittest

import numpy as np

from learning.train_collision_risk import (
    average_precision,
    auroc,
    future_collision_labels,
    future_collision_labels_by_episode,
    split_episode_ids,
    split_episode_ids_three_way,
)


class CollisionRiskTests(unittest.TestCase):
    def test_future_collision_labels_exclude_current_step(self):
        labels = future_collision_labels(np.array([0, 0, 1, 1, 0]), horizon=2)
        np.testing.assert_array_equal(labels, np.array([1, 1, 1, 0, 0], dtype=np.float32))

    def test_future_labels_do_not_cross_episode_boundaries(self):
        collisions = np.array([0, 0, 0, 1])
        episodes = np.array([0, 0, 1, 1])
        labels = future_collision_labels_by_episode(collisions, episodes, horizon=3)
        np.testing.assert_array_equal(labels, np.array([0, 0, 1, 0], dtype=np.float32))

    def test_average_precision_is_one_for_perfect_ranking(self):
        labels = np.array([0, 1, 0, 1])
        scores = np.array([0.1, 0.9, 0.2, 0.8])
        self.assertAlmostEqual(average_precision(labels, scores), 1.0)
        self.assertAlmostEqual(auroc(labels, scores), 1.0)

    def test_episode_split_keeps_validation_disjoint(self):
        train, validation = split_episode_ids(np.array([0, 0, 1, 1, 2, 2]), 0.34)
        self.assertFalse(train & validation)
        self.assertEqual(train | validation, {0, 1, 2})

    def test_three_way_episode_split_is_disjoint(self):
        train, validation, test = split_episode_ids_three_way(np.arange(10), 0.2, 0.2)
        self.assertFalse(train & validation)
        self.assertFalse(train & test)
        self.assertFalse(validation & test)
        self.assertEqual(train | validation | test, set(range(10)))


if __name__ == "__main__":
    unittest.main()
