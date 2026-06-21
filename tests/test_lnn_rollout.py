import argparse
import unittest
from pathlib import Path

from learning.rollout_lnn import begin_rollout_episode, finalize_metrics, new_rollout_stats, update_rollout_stats
from sim2d.config import SimConfig


class LnnRolloutTests(unittest.TestCase):
    def test_rollout_stats_accumulate_collision_and_reward(self):
        stats = new_rollout_stats(episodes=2)
        update_rollout_stats(stats, 0.5, {"collision": False, "nearest_surface": 1.2, "true_distance": 2.0})
        update_rollout_stats(stats, -1.0, {"collision": True, "nearest_surface": 0.0, "true_distance": 0.3})

        self.assertEqual(stats["total_steps"], 2)
        self.assertEqual(stats["collision_ticks"], 1)
        self.assertEqual(stats["collision_events"], 1)
        self.assertAlmostEqual(stats["reward_total"], -0.5)
        self.assertAlmostEqual(stats["nearest_surface_min"], 0.0)
        self.assertAlmostEqual(stats["true_distance_min"], 0.3)

    def test_finalize_metrics_computes_rates(self):
        stats = new_rollout_stats(episodes=1)
        update_rollout_stats(stats, 1.0, {"collision": False, "nearest_surface": 1.0, "true_distance": 1.0})
        update_rollout_stats(stats, -1.0, {"collision": True, "nearest_surface": 0.0, "true_distance": 0.2})
        args = argparse.Namespace(checkpoint=Path("model.pth"), output=Path("rollout.csv"), steps=10)
        config = SimConfig(dt=0.02)

        metrics = finalize_metrics(stats, args, config)

        self.assertEqual(metrics["total_steps"], 2)
        self.assertEqual(metrics["collision_rate"], 0.5)
        self.assertAlmostEqual(metrics["simulated_seconds"], 0.04)

    def test_collision_events_count_contact_entries_not_ticks(self):
        stats = new_rollout_stats(episodes=2)
        begin_rollout_episode(stats)
        for collision in (False, True, True, False, True):
            update_rollout_stats(stats, 0.0, {"collision": collision})
        self.assertEqual(stats["collision_ticks"], 3)
        self.assertEqual(stats["collision_events"], 2)

        begin_rollout_episode(stats)
        update_rollout_stats(stats, 0.0, {"collision": True})
        self.assertEqual(stats["collision_events"], 3)
        self.assertEqual(stats["_episode_collision_events"], 1)


if __name__ == "__main__":
    unittest.main()
