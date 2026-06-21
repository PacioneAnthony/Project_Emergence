import unittest

from scripts.research.run_lnn_e3 import build_specs


class LnnE3Tests(unittest.TestCase):
    def test_build_specs_uses_two_families_per_seed(self):
        specs = build_specs([4202, 5202])
        self.assertEqual(len(specs), 4)
        self.assertEqual({spec.family for spec in specs}, {"control", "aux_0.3"})
        self.assertEqual({spec.seed for spec in specs}, {4202, 5202})


if __name__ == "__main__":
    unittest.main()
