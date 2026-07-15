import tempfile
import unittest
from pathlib import Path

try:
    import mujoco  # noqa: F401

    MUJOCO_AVAILABLE = True
except ModuleNotFoundError:
    MUJOCO_AVAILABLE = False

from learning.datasets import load_simulation_csv

if MUJOCO_AVAILABLE:
    from sim2d.policies import WallAvoidancePolicy
    from sim3d.environment import RobotSim3DEnv
    from sim3d.parallel import CampaignSpec, build_sim_config, run_campaign


def small_spec(**overrides) -> "CampaignSpec":
    base = dict(
        policy="avoid",
        backend="sim3d",
        episodes=4,
        steps=150,
        base_seed=310,
        domain_randomization=False,
    )
    base.update(overrides)
    return CampaignSpec(**base)


def serial_reference(spec: "CampaignSpec") -> list[dict]:
    """Run the same episodes in-process, without the campaign machinery."""

    env = RobotSim3DEnv(build_sim_config(spec))
    results = []
    for index in range(spec.episodes):
        obs = env.reset(seed=spec.base_seed + index)
        policy = WallAvoidancePolicy(env.config.robot, scan_hz=spec.scan_hz)
        ticks = 0
        reward_total = 0.0
        for _ in range(spec.steps):
            obs, reward, done, info = env.step(policy(obs))
            ticks += int(bool(info["collision"]))
            reward_total += float(reward)
            if done:
                break
        results.append({"collision_ticks": ticks, "reward": reward_total})
    return results


@unittest.skipUnless(MUJOCO_AVAILABLE, "MuJoCo is not installed")
class ParallelRolloutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = small_spec()
        with tempfile.TemporaryDirectory() as tmpdir:
            cls.output = Path(tmpdir) / "campaign.csv"
            cls.metrics = run_campaign(cls.spec, workers=2, output=cls.output)
            cls.arrays = load_simulation_csv(cls.output)
        cls.reference = serial_reference(cls.spec)

    def test_metrics_totals_are_consistent(self):
        detail = self.metrics["episodes_detail"]
        self.assertEqual(len(detail), self.spec.episodes)
        self.assertEqual(self.metrics["total_steps"], sum(item["steps"] for item in detail))
        self.assertEqual(self.metrics["collision_ticks"], sum(item["collision_ticks"] for item in detail))
        self.assertEqual(self.metrics["total_steps"], self.spec.episodes * self.spec.steps)

    def test_merged_csv_has_all_episodes(self):
        self.assertEqual(self.arrays["obs"].shape[0], self.spec.episodes * self.spec.steps)
        episodes = sorted(set(int(value) for value in self.arrays["episode"]))
        self.assertEqual(episodes, list(range(self.spec.episodes)))

    def test_parallel_matches_serial_execution_exactly(self):
        for item, reference in zip(self.metrics["episodes_detail"], self.reference):
            self.assertEqual(item["collision_ticks"], reference["collision_ticks"])
            self.assertAlmostEqual(item["reward"], reference["reward"], places=9)

    def test_single_worker_path_matches_pool_path(self):
        metrics_single = run_campaign(self.spec, workers=1, output=None)
        for pooled, single in zip(self.metrics["episodes_detail"], metrics_single["episodes_detail"]):
            self.assertEqual(pooled["collision_ticks"], single["collision_ticks"])
            self.assertAlmostEqual(pooled["reward"], single["reward"], places=9)


if __name__ == "__main__":
    unittest.main()
