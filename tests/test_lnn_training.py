import importlib.util
import unittest

import numpy as np

from learning.train_lnn import (
    action_scales_from_config,
    auxiliary_weight_for_epoch,
    evaluate_lnn_mini_rollouts,
    lnn_sequence_loss,
    normalize_actions,
    prepare_auxiliary_targets,
    rollout_selection_key,
    sequence_start_indices,
    split_episode_ids,
)
from learning.lnn import AuxiliaryLatentHead, SimpleLNN
from sim2d.config import RobotConfig

TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


class LnnTrainingTests(unittest.TestCase):
    def test_auxiliary_weight_cosine_schedule_hits_endpoints(self):
        self.assertAlmostEqual(auxiliary_weight_for_epoch(1, 100, 1.0, 0.1), 1.0)
        self.assertAlmostEqual(auxiliary_weight_for_epoch(100, 100, 1.0, 0.1), 0.1)
        self.assertAlmostEqual(auxiliary_weight_for_epoch(50.5, 100, 1.0, 0.1), 0.55)

    def test_action_normalization_uses_robot_limits(self):
        scales = action_scales_from_config(RobotConfig())
        actions = np.array([[0.55, -2.8, np.pi / 2]], dtype=np.float32)
        normalized = normalize_actions(actions, scales)
        self.assertTrue(np.allclose(normalized, [[1.0, -1.0, 1.0]], atol=1e-5))

    def test_action_normalization_clips_out_of_range_values(self):
        scales = action_scales_from_config(RobotConfig())
        actions = np.array([[10.0, -10.0, 10.0]], dtype=np.float32)
        normalized = normalize_actions(actions, scales)
        self.assertEqual(normalized.tolist(), [[1.0, -1.0, 1.0]])

    def test_sequence_start_indices_do_not_cross_episodes(self):
        episodes = np.array([0, 0, 0, 1, 1, 1, 1], dtype=np.int64)
        starts = sequence_start_indices(episodes, sequence_length=3, allowed_episodes={0, 1})
        self.assertEqual(starts.tolist(), [0, 3, 4])

    def test_split_episode_ids_keeps_last_episode_for_validation(self):
        episodes = np.array([0, 0, 1, 1, 2, 2], dtype=np.int64)
        train_eps, val_eps = split_episode_ids(episodes, val_fraction=0.34)
        self.assertEqual(train_eps, {0, 1})
        self.assertEqual(val_eps, {2})

    def test_split_episode_ids_does_not_put_appended_data_only_in_validation(self):
        episodes = np.repeat(np.arange(60, dtype=np.int64), 2)
        train_eps, val_eps = split_episode_ids(episodes, val_fraction=0.2)

        appended_eps = set(range(50, 60))
        self.assertTrue(appended_eps & train_eps)
        self.assertTrue(appended_eps & val_eps)
        self.assertFalse(appended_eps <= val_eps)

    def test_auxiliary_targets_are_normalized_from_training_episodes_only(self):
        arrays = {
            "jepa_aux_target": np.array([[1.0, 10.0], [3.0, 14.0], [100.0, 200.0]], dtype=np.float32)
        }
        episodes = np.array([0, 0, 1], dtype=np.int64)

        normalized, meta = prepare_auxiliary_targets(arrays, episodes, {0}, {"jepa_aux_checkpoint": "jepa.pth"})

        self.assertTrue(np.allclose(meta["target_mean"], [2.0, 12.0]))
        self.assertTrue(np.allclose(normalized[:2].mean(axis=0), [0.0, 0.0]))
        self.assertGreater(float(normalized[2, 0]), 10.0)

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is required for the auxiliary-loss execution test")
    def test_auxiliary_loss_is_added_without_changing_lnn_input_contract(self):
        import torch

        model = SimpleLNN(state_dim=4, input_dim=3, action_dim=3, hidden_dim=8)
        aux_head = AuxiliaryLatentHead(state_dim=4, latent_dim=5, hidden_dim=8)
        obs = torch.zeros((2, 3, 3))
        actions = torch.zeros((2, 3, 3))
        targets = torch.ones((2, 3, 5))

        total, action_loss, smooth_loss, aux_loss = lnn_sequence_loss(
            model,
            obs,
            actions,
            dt=0.02,
            state_smooth_weight=1e-3,
            aux_head=aux_head,
            aux_target_seq=targets,
            aux_weight=0.3,
        )

        self.assertEqual(model.policy[0].in_features, 7)
        self.assertGreater(aux_loss, 0.0)
        self.assertAlmostEqual(float(total.item()), action_loss + 1e-3 * smooth_loss + 0.3 * aux_loss, places=6)

    def test_rollout_selection_prioritizes_worst_protocol(self):
        better_worst_case = {
            "selection": {
                "worst_collision_rate": 0.02,
                "mean_collision_rate": 0.019,
                "worst_events_per_1000_steps": 4.0,
                "worst_reward_mean_per_step": -0.1,
                "activity_shortfall": 0.0,
            }
        }
        better_average_only = {
            "selection": {
                "worst_collision_rate": 0.03,
                "mean_collision_rate": 0.01,
                "worst_events_per_1000_steps": 2.0,
                "worst_reward_mean_per_step": 0.0,
                "activity_shortfall": 0.0,
            }
        }
        self.assertLess(rollout_selection_key(better_worst_case), rollout_selection_key(better_average_only))

    @unittest.skipUnless(TORCH_AVAILABLE, "PyTorch is required for the mini-rollout execution test")
    def test_mini_rollout_returns_both_protocols_and_selection_score(self):
        import torch

        model = SimpleLNN(state_dim=4, input_dim=3, action_dim=3, hidden_dim=8)
        metrics = evaluate_lnn_mini_rollouts(
            model,
            action_scales_from_config(RobotConfig()),
            dt=0.02,
            device=torch.device("cpu"),
            episodes=1,
            steps=5,
            nominal_seed=11,
            randomized_seed=21,
            min_mean_forward_speed=0.0,
        )

        self.assertEqual(metrics["nominal"]["steps"], 5)
        self.assertEqual(metrics["randomized"]["steps"], 5)
        self.assertIn("worst_collision_rate", metrics["selection"])

    def test_rollout_selection_rejects_stationary_zero_collision_policy(self):
        stationary = {
            "selection": {
                "activity_shortfall": 0.04,
                "worst_collision_rate": 0.0,
                "mean_collision_rate": 0.0,
                "worst_events_per_1000_steps": 0.0,
                "worst_reward_mean_per_step": 0.0,
            }
        }
        moving = {
            "selection": {
                "activity_shortfall": 0.0,
                "worst_collision_rate": 0.03,
                "mean_collision_rate": 0.02,
                "worst_events_per_1000_steps": 4.0,
                "worst_reward_mean_per_step": -0.1,
            }
        }
        self.assertLess(rollout_selection_key(moving), rollout_selection_key(stationary))


if __name__ == "__main__":
    unittest.main()
