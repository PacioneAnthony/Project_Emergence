import unittest

from scripts.research.run_jepa_mpc_s4 import RunSpec, build_specs, paired_deltas


class JEPAMPCS4Tests(unittest.TestCase):
    def test_build_specs_pairs_each_family_on_each_seed(self):
        specs = build_specs([1], [2])
        self.assertEqual(len(specs), 6)
        self.assertIn(RunSpec("baseline", "nominal", 1), specs)
        self.assertIn(RunSpec("slow_only", "randomized", 2), specs)

    def test_paired_deltas_count_improvements_and_regressions(self):
        rows = [
            {"family": "baseline", "protocol": "nominal", "seed": 1, "collision_rate": 0.10},
            {"family": "slow_only", "protocol": "nominal", "seed": 1, "collision_rate": 0.08},
            {"family": "baseline", "protocol": "nominal", "seed": 2, "collision_rate": 0.10},
            {"family": "slow_only", "protocol": "nominal", "seed": 2, "collision_rate": 0.12},
        ]
        result = paired_deltas(rows)["slow_only_nominal"]
        self.assertEqual(result["improved_seeds"], 1)
        self.assertEqual(result["regressed_seeds"], 1)
        self.assertAlmostEqual(result["mean_collision_rate_delta"], 0.0)


if __name__ == "__main__":
    unittest.main()
