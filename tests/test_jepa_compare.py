import json
import tempfile
import unittest
from pathlib import Path

from learning.compare_jepa_runs import infer_run_name, load_metric_row, render_markdown


class JepaCompareTests(unittest.TestCase):
    def test_infer_run_name_from_eval_metrics_path(self):
        path = Path("data/processed/experiments/example_run/eval/metrics.json")
        self.assertEqual(infer_run_name(path), "example_run")

    def test_render_markdown_contains_core_metrics(self):
        row = {
            "run": "run_a",
            "samples": 10,
            "latent_dim": 8,
            "latent_mse": 0.1,
            "latent_persistence_mse": 0.2,
            "latent_improvement": 0.5,
            "obs_decoder_rmse": 0.3,
            "obs_probe_rmse": 0.25,
            "obs_persistence_rmse": 0.35,
            "latent_std_mean": 0.4,
        }
        text = render_markdown([row])
        self.assertIn("run_a", text)
        self.assertIn("50.00%", text)
        self.assertIn("0.300000", text)

    def test_load_metric_row_reads_metrics_json(self):
        metrics = {
            "n_samples": 10,
            "checkpoint_dims": {"latent_dim": 8},
            "latent_prediction": {
                "mse": 0.1,
                "persistence_mse": 0.2,
                "improvement_vs_persistence": 0.5,
            },
            "observation_decoder": {
                "rmse_mean": 0.3,
                "persistence_rmse_mean": 0.35,
            },
            "observation_probe": {"rmse_mean": 0.25},
            "latent_health": {"std_mean": 0.4},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metrics.json"
            path.write_text(json.dumps(metrics), encoding="utf-8")
            row = load_metric_row(path)
        self.assertEqual(row["samples"], 10)
        self.assertEqual(row["latent_dim"], 8)
        self.assertAlmostEqual(row["latent_improvement"], 0.5)


if __name__ == "__main__":
    unittest.main()
