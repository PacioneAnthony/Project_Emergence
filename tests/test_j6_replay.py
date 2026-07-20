import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from learning.j6_replay import J6Spec, frozen_priority_weights
from scripts.research import run_j6_replay
from sim3d.bench_model import build_bench_mjcf
from sim3d.j6_domains import LANDMARK_BINS, j6_bench_config


class J6WorldTests(unittest.TestCase):
    def test_landmark_is_a_real_domain_specific_mjcf_geom(self):
        for domain, angle_bin in LANDMARK_BINS.items():
            config = j6_bench_config(domain, seed=1)
            xml = build_bench_mjcf(config, [])
            self.assertIn('name="j6_landmark_panel"', xml)
            self.assertIn(f'landmark_angle_deg', repr(config.room))
            self.assertEqual(int((config.room.landmark_angle_deg - 10.0) / 20.0), angle_bin)

    def test_domain_b_scales_every_light_to_seventy_percent(self):
        nominal = j6_bench_config("A").room
        dark = j6_bench_config("B").room
        for field in (
            "primary_light_rgb",
            "secondary_light_rgb",
            "headlight_ambient_rgb",
            "headlight_diffuse_rgb",
        ):
            np.testing.assert_allclose(getattr(dark, field), 0.70 * np.asarray(getattr(nominal, field)))


class J6ReplayRuleTests(unittest.TestCase):
    def test_frozen_priority_is_exact_and_normalized(self):
        errors = np.asarray([0.0, 0.2, 0.8])
        expected = (errors + 1e-3) / np.sum(errors + 1e-3)
        np.testing.assert_array_equal(frozen_priority_weights(errors), expected)
        self.assertAlmostEqual(float(np.sum(frozen_priority_weights(errors))), 1.0)

    def test_review_accepted_flag_never_bypasses_missing_smoke(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "smoke.json"
            with patch.object(run_j6_replay, "SMOKE_RESULT", missing), patch.object(
                run_j6_replay, "review_authorized", return_value=True
            ):
                allowed, reason = run_j6_replay.campaign_authorized(True, J6Spec())
        self.assertFalse(allowed)
        self.assertIn("smoke 10991", reason)

    def test_campaign_is_blocked_without_review_accepted_flag(self):
        allowed, reason = run_j6_replay.campaign_authorized(False, J6Spec())
        self.assertFalse(allowed)
        self.assertIn("--review-accepted", reason)


if __name__ == "__main__":
    unittest.main()
