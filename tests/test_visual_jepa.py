import unittest

import numpy as np

try:
    import torch  # noqa: F401

    TORCH_AVAILABLE = True
except ModuleNotFoundError:
    TORCH_AVAILABLE = False

try:
    import mujoco  # noqa: F401

    MUJOCO_AVAILABLE = True
except ModuleNotFoundError:
    MUJOCO_AVAILABLE = False

from sim3d.bench_corpus import babbling_targets


class BabblingTests(unittest.TestCase):
    def test_targets_stay_in_servo_range(self):
        rng = np.random.default_rng(3)
        targets = babbling_targets(rng, 10.0, 170.0, 90.0, 0.02, 5000)
        self.assertEqual(targets.shape, (5000,))
        self.assertGreaterEqual(targets.min(), 10.0)
        self.assertLessEqual(targets.max(), 170.0)

    def test_targets_actually_move(self):
        rng = np.random.default_rng(4)
        targets = babbling_targets(rng, 10.0, 170.0, 90.0, 0.02, 5000)
        self.assertGreater(targets.std(), 10.0)


@unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is not installed")
class VisualJEPATests(unittest.TestCase):
    def test_forward_shapes(self):
        from learning.visual_jepa import VisualJEPA

        model = VisualJEPA(latent_dim=32, hidden_dim=64, encoder_width=8)
        frames = torch.rand(4, 3, 64, 64)
        action = torch.rand(4, 1)
        latent, prediction = model(frames, action)
        self.assertEqual(latent.shape, (4, 32))
        self.assertEqual(prediction.shape, (4, 32))

    def test_no_action_variant_ignores_action(self):
        from learning.visual_jepa import VisualJEPA

        model = VisualJEPA(latent_dim=16, hidden_dim=32, encoder_width=8, use_action=False)
        model.eval()
        frames = torch.rand(2, 3, 64, 64)
        with torch.no_grad():
            _, pred_a = model(frames, torch.zeros(2, 1))
            _, pred_b = model(frames, torch.ones(2, 1))
        self.assertTrue(torch.allclose(pred_a, pred_b))

    def test_action_variant_uses_action(self):
        from learning.visual_jepa import VisualJEPA

        model = VisualJEPA(latent_dim=16, hidden_dim=32, encoder_width=8, use_action=True)
        model.eval()
        frames = torch.rand(2, 3, 64, 64)
        with torch.no_grad():
            _, pred_a = model(frames, torch.zeros(2, 1))
            _, pred_b = model(frames, torch.ones(2, 1))
        self.assertFalse(torch.allclose(pred_a, pred_b))

    def test_pairs_do_not_cross_episode_boundaries(self):
        from learning.train_visual_jepa import build_pairs

        episodes = np.array([0, 0, 0, 1, 1, 2], dtype=np.int32)
        pairs = build_pairs(episodes)
        self.assertEqual(pairs.tolist(), [0, 1, 3])

    def test_downsample_box_average(self):
        from learning.train_visual_jepa import downsample_frames

        frames = np.zeros((2, 128, 128, 3), dtype=np.uint8)
        frames[:, :64, :, :] = 200
        small = downsample_frames(frames, 64)
        self.assertEqual(small.shape, (2, 64, 64, 3))
        self.assertEqual(int(small[0, 0, 0, 0]), 200)
        self.assertEqual(int(small[0, 63, 0, 0]), 0)


if __name__ == "__main__":
    unittest.main()
