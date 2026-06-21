import unittest

import numpy as np

from learning.diagnose_jepa_latent_shift import (
    collision_conditioned_summary,
    fit_regularized_gaussian,
    mahalanobis_distance,
)


class JepaLatentShiftTests(unittest.TestCase):
    def test_training_cloud_has_smaller_distance_than_shifted_cloud(self):
        rng = np.random.default_rng(7)
        reference = rng.normal(size=(2000, 4)).astype(np.float32)
        shifted = rng.normal(loc=3.0, size=(500, 4)).astype(np.float32)
        mean, precision = fit_regularized_gaussian(reference, shrinkage=0.05)

        reference_distance = mahalanobis_distance(reference, mean, precision)
        shifted_distance = mahalanobis_distance(shifted, mean, precision)

        self.assertGreater(np.percentile(shifted_distance, 95), np.percentile(reference_distance, 95) * 2.0)

    def test_collision_summary_separates_masks(self):
        distance = np.array([1.0, 2.0, 10.0, 12.0])
        collision = np.array([False, False, True, True])

        summary = collision_conditioned_summary(distance, collision)

        self.assertEqual(summary["collision_samples"], 2)
        self.assertAlmostEqual(summary["collision"]["mean"], 11.0)
        self.assertGreater(summary["mean_ratio_collision_vs_non_collision"], 7.0)


if __name__ == "__main__":
    unittest.main()
