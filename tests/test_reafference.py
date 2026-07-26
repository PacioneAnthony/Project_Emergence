import tempfile
import unittest
from pathlib import Path

import numpy as np

from learning.reafference import (
    BANKS,
    CONDITIONS,
    RefBank,
    RefSpec,
    _bank_motion_plan,
    _correlation,
    calibration_threshold,
    fit_pixel_action,
    independent_motion_plan,
    make_learner,
    parameter_count,
    pixel_action_score,
    pixel_change,
    ref_bench_config,
    state_digest,
)
from learning.train_visual_jepa import resolve_device
from scripts.research.run_reafference import amendments_integrated, review_authorized
from sim3d import bench_model
from sim3d.bench_env import BenchHeadEnv


class RefProtocolTests(unittest.TestCase):
    def test_frozen_budgets(self):
        spec = RefSpec()
        self.assertEqual(spec.images, 12_000)
        self.assertEqual(spec.decisions, 2_400)
        self.assertEqual(spec.optimizer_steps * spec.batch_size, 1_152_000)

    def test_independent_corpus_plan(self):
        spec = RefSpec()
        plan = independent_motion_plan(12991, spec)
        self.assertEqual(len(plan["targets_deg"]), spec.decisions)
        self.assertEqual(int(np.sum(plan["mobile_episodes"])), 10)
        self.assertLessEqual(abs(_correlation(plan["action_delta_deg"], plan["object_delta_m"])), 0.05)

    def test_bank_plans_obey_structural_guards(self):
        spec = RefSpec(pairs_per_bin=8)
        calibration_head, calibration_object = _bank_motion_plan(12991, "self_calibration", spec)
        external_head, external_object = _bank_motion_plan(12991, "external_only", spec)
        mixed_head, mixed_object = _bank_motion_plan(12991, "mixed", spec)
        self.assertTrue(np.all(calibration_head != 0))
        self.assertTrue(np.all(calibration_object == 0))
        self.assertTrue(np.all(external_head == 0))
        self.assertTrue(np.all(external_object != 0))
        self.assertLessEqual(abs(_correlation(mixed_head, mixed_object)), 0.05)

    def test_amendments_and_review_are_present(self):
        self.assertTrue(amendments_integrated())
        self.assertTrue(review_authorized())


class RefScoreTests(unittest.TestCase):
    def test_threshold_leaves_at_most_five_percent_strictly_above(self):
        scores = np.arange(128, dtype=np.float64)
        threshold = calibration_threshold(scores)
        self.assertEqual(threshold, 121.0)
        self.assertLessEqual(np.mean(scores > threshold), 0.05)

    def test_threshold_ties_are_non_external(self):
        scores = np.ones(128, dtype=np.float64)
        threshold = calibration_threshold(scores)
        self.assertEqual(threshold, 1.0)
        self.assertEqual(int(np.sum(scores > threshold)), 0)

    def test_pixel_action_removes_linear_self_motion(self):
        amplitude = np.linspace(0.0, 1.0, 128)
        pixel = 0.02 + 0.4 * amplitude
        fit = fit_pixel_action(pixel, amplitude)
        residual = pixel_action_score(pixel, amplitude, fit)
        self.assertTrue(np.allclose(fit, (0.02, 0.4)))
        self.assertTrue(np.allclose(residual, 0.0, atol=1e-12))

    def test_pixel_change_normalizes_uint8_once(self):
        zeros = np.zeros((1, 4, 4, 3), dtype=np.uint8)
        full = np.full((1, 4, 4, 3), 255, dtype=np.uint8)
        bank = RefBank(
            frames_start=zeros,
            frames_end=full,
            actions=np.zeros((1, 5), dtype=np.float32),
            angle_bins=np.zeros(1, dtype=np.int8),
            contexts=np.zeros(1, dtype=np.int8),
            head_delta_deg=np.ones(1, dtype=np.float32),
            object_delta_m=np.zeros(1, dtype=np.float32),
            applied_target_deg=np.ones(1, dtype=np.float32),
            labels=np.asarray(["self_test"]),
        )
        self.assertEqual(float(pixel_change(bank)[0]), 1.0)

    def test_bank_round_trip_preserves_audit_fields(self):
        bank = RefBank(
            frames_start=np.zeros((2, 2, 2, 3), dtype=np.uint8),
            frames_end=np.ones((2, 2, 2, 3), dtype=np.uint8),
            actions=np.zeros((2, 5), dtype=np.float32),
            angle_bins=np.asarray([0, 1], dtype=np.int8),
            contexts=np.asarray([0, 1], dtype=np.int8),
            head_delta_deg=np.asarray([1.0, 2.0], dtype=np.float32),
            object_delta_m=np.asarray([0.0, 0.1], dtype=np.float32),
            applied_target_deg=np.asarray([20.0, 40.0], dtype=np.float32),
            labels=np.asarray(["self_test", "mixed"]),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bank.npz"
            bank.save(path)
            loaded = RefBank.load(path)
        for name in RefBank.__annotations__:
            self.assertTrue(np.array_equal(getattr(bank, name), getattr(loaded, name)))


class RefWorldAndEquityTests(unittest.TestCase):
    def test_ref_world_contains_real_slide_body(self):
        env = BenchHeadEnv(ref_bench_config(12991, 70.0, 0))
        try:
            self.assertGreaterEqual(env.model.joint(bench_model.JOINT_EXTERNAL).id, 0)
            self.assertGreaterEqual(env.model.geom(bench_model.GEOM_EXTERNAL).id, 0)
            env.set_external_object_displacement(0.5)
            self.assertAlmostEqual(env.external_object_displacement(), 0.18)
            env.set_external_object_displacement(-0.5)
            self.assertAlmostEqual(env.external_object_displacement(), -0.18)
        finally:
            env.close()

    def test_conditions_have_identical_initial_state_and_capacity(self):
        try:
            device = resolve_device("cpu")
            action, action_probes, _ = make_learner(12991, CONDITIONS[1], RefSpec(), device)
            control, control_probes, _ = make_learner(12991, CONDITIONS[0], RefSpec(), device)
        except ModuleNotFoundError:
            self.skipTest("PyTorch unavailable")
        self.assertEqual(state_digest(action, action_probes), state_digest(control, control_probes))
        self.assertEqual(parameter_count(action, action_probes), parameter_count(control, control_probes))

    def test_ref_config_is_not_a_j6_belt_world(self):
        config = ref_bench_config(12301, 80.0, 1)
        self.assertTrue(config.room.reafference_object)
        self.assertIsNone(config.room.sector_belt_pattern)
        self.assertIsNone(config.room.landmark_angle_deg)
        self.assertEqual(config.room.reafference_bearing_deg, 80.0)


if __name__ == "__main__":
    unittest.main()
