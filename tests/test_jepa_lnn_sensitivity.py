import unittest

import numpy as np

from learning.diagnose_jepa_lnn_sensitivity import sensitivity_metrics


class JepaLnnSensitivityTests(unittest.TestCase):
    def test_sensitivity_reports_total_and_per_dimension_ratios(self):
        obs_norm = np.array([2.0, 2.0])
        latent_norm = np.array([4.0, 4.0])

        metrics = sensitivity_metrics(obs_norm, latent_norm, obs_dim=4, latent_dim=16)

        self.assertAlmostEqual(metrics["latent_vs_obs_total_norm_ratio"], 2.0)
        self.assertAlmostEqual(metrics["latent_vs_obs_per_dim_rms_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
