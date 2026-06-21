import unittest

from scripts.research.run_lnn_e2 import build_specs


class LnnE2Tests(unittest.TestCase):
    def test_build_specs_creates_one_scheduled_run_per_seed(self):
        specs = build_specs([4202, 5202, 6202])
        self.assertEqual(len(specs), 3)
        self.assertEqual({spec.family for spec in specs}, {"aux_1.0_to_0.1"})
        self.assertEqual({spec.seed for spec in specs}, {4202, 5202, 6202})


if __name__ == "__main__":
    unittest.main()
