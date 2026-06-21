import unittest

from learning.train_jepa import validation_improved
from learning.refine_jepa_decoder import build_parser as build_refine_decoder_parser
from scripts.research.run_jepa_overnight import build_parser as build_overnight_parser
from scripts.research.simulate import build_parser as build_simulate_parser


class JepaTrainingControlTests(unittest.TestCase):
    def test_validation_improvement_respects_min_delta(self):
        self.assertTrue(validation_improved(0.99, 1.0, 0.0))
        self.assertFalse(validation_improved(1.0, 1.0, 0.0))
        self.assertFalse(validation_improved(0.995, 1.0, 0.01))
        self.assertTrue(validation_improved(0.989, 1.0, 0.01))

    def test_overnight_defaults_limit_wasted_training(self):
        args = build_overnight_parser().parse_args([])
        self.assertEqual(args.epochs, 10000)
        self.assertEqual(args.early_stopping_patience, 5)
        self.assertEqual(args.early_stopping_min_delta, 0.0)
        self.assertEqual(args.scan_hz, 0.5)
        self.assertFalse(args.refine_decoder)
        self.assertEqual(args.refine_decoder_epochs, 2000)

    def test_simulate_defaults_use_faster_ultrasonic_scan(self):
        args = build_simulate_parser().parse_args([])
        self.assertEqual(args.scan_hz, 0.5)

    def test_refine_decoder_defaults_target_auxiliary_phase(self):
        args = build_refine_decoder_parser().parse_args(
            [
                "--log",
                "data/raw/log.csv",
                "--checkpoint",
                "models/model.pth",
                "--output",
                "models/refined.pth",
            ]
        )
        self.assertEqual(args.epochs, 2000)
        self.assertEqual(args.distance_loss_weight, 1.0)
        self.assertEqual(args.early_stopping_patience, 20)


if __name__ == "__main__":
    unittest.main()
