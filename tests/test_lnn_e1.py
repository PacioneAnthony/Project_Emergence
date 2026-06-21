import csv
from pathlib import Path
import tempfile
import unittest

from scripts.research.run_lnn_e1 import aggregate_rows, build_specs, collision_events_from_csv


class LnnE1Tests(unittest.TestCase):
    def test_existing_seed_tags_are_reused(self):
        specs = build_specs([4202, 5202], [7301])
        tags = {spec.tag for spec in specs}
        self.assertIn("lnn_jepa_aux_w03_001", tags)
        self.assertIn("lnn_e1_aux_w03_seed5202", tags)
        self.assertIn("lnn_e1_reference_seed7301", tags)

    def test_collision_events_reset_between_episodes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=("episode", "collision"))
                writer.writeheader()
                for episode, collision in ((0, 0), (0, 1), (0, 1), (1, 1), (1, 0), (1, 1)):
                    writer.writerow({"episode": episode, "collision": collision})
            self.assertEqual(collision_events_from_csv(path), 3)

    def test_aggregate_rows_reports_sample_spread(self):
        rows = [
            {
                "seed": 1,
                "validation_rmse": 0.3,
                "nominal_collision_rate": 0.01,
                "nominal_events_per_1000_steps": 1.0,
                "randomized_collision_rate": 0.02,
                "randomized_events_per_1000_steps": 2.0,
            },
            {
                "seed": 2,
                "validation_rmse": 0.4,
                "nominal_collision_rate": 0.03,
                "nominal_events_per_1000_steps": 3.0,
                "randomized_collision_rate": 0.04,
                "randomized_events_per_1000_steps": 4.0,
            },
        ]
        summary = aggregate_rows(rows)
        self.assertEqual(summary["n"], 2)
        self.assertAlmostEqual(summary["nominal_collision_rate"]["mean"], 0.02)
        self.assertEqual(summary["nominal_collision_rate"]["min"], 0.01)
        self.assertIsNotNone(summary["nominal_collision_rate"]["std"])


if __name__ == "__main__":
    unittest.main()
