import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from learning.tv_exploration import (
    RegionalGainTelevisionPolicy,
    angle_bin,
    apply_television,
    select_probe_batches,
    television_lag_correlation,
    television_rectangle,
    visual_context_id,
)


class TelevisionWorldTests(unittest.TestCase):
    def test_angle_bins_cover_servo_range(self):
        self.assertEqual(angle_bin(10.0), 0)
        self.assertEqual(angle_bin(129.9), 5)
        self.assertEqual(angle_bin(130.0), 6)
        self.assertEqual(angle_bin(170.0), 7)

    def test_structured_frame_is_unchanged(self):
        frame = np.arange(64 * 64 * 3, dtype=np.uint8).reshape(64, 64, 3)
        result = apply_television(frame, 90.0, np.random.default_rng(1))
        np.testing.assert_array_equal(result, frame)
        self.assertIsNot(result, frame)

    def test_television_changes_only_screen_and_bezel(self):
        frame = np.full((64, 64, 3), 127, dtype=np.uint8)
        result = apply_television(frame, 150.0, np.random.default_rng(2))
        ys, xs = television_rectangle(frame)
        self.assertFalse(np.array_equal(result[ys, xs], frame[ys, xs]))
        self.assertEqual(int(result[0, 0, 0]), 127)

    def test_television_noise_passes_independence_check(self):
        self.assertLessEqual(abs(television_lag_correlation(1234, pairs=128)), 0.02)

    def test_visual_context_is_pixel_derived_and_stable(self):
        rng = np.random.default_rng(3)
        frame = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
        self.assertEqual(visual_context_id(frame), visual_context_id(frame.copy()))
        self.assertIn(visual_context_id(frame), (0, 1))


class RegionalGainPolicyTests(unittest.TestCase):
    def test_signed_gains_are_aggregated_before_clip(self):
        policy = RegionalGainTelevisionPolicy(epsilon=0.0)
        cell = (2, 1)
        policy.update(cell, 0.2)
        policy.update(cell, -0.4)
        self.assertEqual(policy.score(cell), 0.0)
        policy.update(cell, 0.5)
        self.assertAlmostEqual(policy.score(cell), 0.1)

    def test_unobserved_cells_are_optimistic(self):
        policy = RegionalGainTelevisionPolicy(epsilon=0.0)
        policy.update((0, 0), 0.1)
        policy.update((0, 0), 0.1)
        _, selected = policy.choose(0, np.random.default_rng(4))
        self.assertNotEqual(selected, (0, 0))
        self.assertEqual(selected[1], 0)


class CalibrationRuleTests(unittest.TestCase):
    def test_low_noise_selects_smallest_window(self):
        values = np.tile(np.array([-0.0001, 0.0001, -0.00005, 0.00005]), 64)
        selected, report = select_probe_batches(values, median_error=0.5)
        self.assertEqual(selected, 4)
        self.assertTrue(report["candidates"]["4"]["passed"])

    def test_excessive_noise_stops_protocol(self):
        rng = np.random.default_rng(5)
        values = rng.normal(0.0, 0.2, size=2048)
        selected, report = select_probe_batches(values, median_error=0.2)
        self.assertIsNone(selected)
        self.assertFalse(any(item["passed"] for item in report["candidates"].values()))


class RunnerReviewGateTests(unittest.TestCase):
    def test_calibration_is_blocked_without_accepted_review(self):
        from scripts.research import run_tv_real_jepa

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "sys.argv",
                ["run_tv_real_jepa", "--calibration-only", "--output-dir", str(Path(temp_dir) / "out")],
            ), patch.object(run_tv_real_jepa, "run_calibration") as calibration:
                with self.assertRaisesRegex(SystemExit, "calibration and campaign require --review-accepted"):
                    run_tv_real_jepa.main()
        calibration.assert_not_called()


if __name__ == "__main__":
    unittest.main()
