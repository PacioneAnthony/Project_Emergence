import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from learning.j6_adaptive_replay import AdaptiveSpec, adaptive_fraction, recompute_rho
from scripts.research import run_j6_adaptive_replay
from sim3d.bench_model import build_bench_mjcf
from sim3d.j6_adaptive_domains import DOMAINS, adaptive_bench_config


def metrics(value):
    return {domain: {"error_by_bin": [value] * 8} for domain in DOMAINS}


class AdaptiveWorldTests(unittest.TestCase):
    def test_each_world_has_six_physical_panels(self):
        for domain in DOMAINS:
            xml = build_bench_mjcf(adaptive_bench_config(domain), [])
            for sector in range(6):
                self.assertIn(f'name="j6ar_panel_{sector}"', xml)

    def test_belt_can_be_removed_for_visual_control(self):
        xml = build_bench_mjcf(adaptive_bench_config("D", belt=False), [])
        self.assertNotIn('name="j6ar_panel_0"', xml)


class AdaptiveScheduleTests(unittest.TestCase):
    def test_session_starts_with_zero_replay_without_old_debt(self):
        current = metrics(1.0)
        acquisition = {"D": {"error_by_bin": [1.0] * 8}}
        result = adaptive_fraction(current, acquisition, current, "E", ("D",))
        self.assertEqual(result["d_old"], 0.0)
        self.assertAlmostEqual(result["d_current"], 0.2)
        self.assertEqual(result["rho"], 0.0)

    def test_fraction_is_quantized_and_offline_recomputable(self):
        current = metrics(0.8)
        current["D"]["error_by_bin"][2] = 1.2
        acquisition = {"D": {"error_by_bin": [1.0] * 8}}
        start = metrics(1.0)
        result = adaptive_fraction(current, acquisition, start, "E", ("D",))
        self.assertIn(result["rho"], np.arange(9) / 16.0)
        self.assertEqual(result["rho"], recompute_rho(result["d_old"], result["d_current"]))
        self.assertEqual(int(256 * result["rho"]), 256 * result["rho"])


class AdaptiveReviewGateTests(unittest.TestCase):
    def test_campaign_is_blocked_without_explicit_acceptance(self):
        allowed, reason = run_j6_adaptive_replay.campaign_authorized(False, AdaptiveSpec())
        self.assertFalse(allowed)
        self.assertIn("--review-accepted", reason)

    def test_review_flag_cannot_bypass_missing_smoke(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(run_j6_adaptive_replay, "SMOKE_RESULT", Path(temporary) / "missing.json"), patch.object(
                run_j6_adaptive_replay, "review_authorized", return_value=True
            ):
                allowed, reason = run_j6_adaptive_replay.campaign_authorized(True, AdaptiveSpec())
        self.assertFalse(allowed)
        self.assertIn("11991", reason)


if __name__ == "__main__":
    unittest.main()
