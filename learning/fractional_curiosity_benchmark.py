"""DC-003: fractional interventional curiosity on randomized hidden worlds."""

from __future__ import annotations

import numpy as np

from learning.curiosity_benchmark import (
    BabblingPolicy,
    ContinuousLearningWorld,
    RegionalLearningProgressPolicy,
    RoundRobinHabituationPolicy,
    coverage_entropy,
)
from learning.developmental_curiosity import FractionalInterventionalCuriosity


CONDITIONS = ("fractional", "babbling", "round_robin_habituation", "regional_lp")


def make_world(seed: int, budget: int) -> ContinuousLearningWorld:
    rng = np.random.default_rng(seed + 300_000)
    return ContinuousLearningWorld(
        seed,
        budget,
        base_limit=float(rng.uniform(0.20, 0.35)),
        noise_limit=float(rng.uniform(0.70, 0.85)),
        base_tau=float(rng.uniform(3.0, 8.0)),
        structured_tau=float(rng.uniform(16.0, 40.0)),
        exposure_bandwidth=float(rng.uniform(0.025, 0.060)),
        noise_scale=float(rng.uniform(0.15, 0.35)),
    )


class FractionalPolicy:
    def __init__(self):
        self.scheduler = FractionalInterventionalCuriosity(
            1,
            np.array([0.10]),
            bandwidth=0.08,
            min_evidence=5.0,
            frontier=0.09,
            epsilon=0.05,
            max_observations=512,
        )

    def choose(self, grid: np.ndarray, rng: np.random.Generator) -> float:
        sampled = rng.choice(len(grid), size=min(48, len(grid)), replace=False)
        anchors = np.array([0, int(round(0.10 * (len(grid) - 1))), len(grid) - 1])
        indices = np.unique(np.concatenate([sampled, anchors]))
        selected = self.scheduler.choose(grid[indices, None], rng)
        return float(grid[indices[selected]])

    def observe(self, x: float, before: float, after: float) -> None:
        self.scheduler.observe(np.array([x]), before, after)


def make_policy(condition: str):
    if condition == "fractional":
        return FractionalPolicy()
    if condition == "babbling":
        return BabblingPolicy()
    if condition == "round_robin_habituation":
        return RoundRobinHabituationPolicy()
    if condition == "regional_lp":
        return RegionalLearningProgressPolicy()
    raise ValueError(condition)


def oracle_allocation(choices: np.ndarray, world: ContinuousLearningWorld) -> dict[str, float]:
    return {
        "base": float(np.mean(choices < world.base_limit)),
        "structured": float(np.mean((choices >= world.base_limit) & (choices < world.noise_limit))),
        "noise": float(np.mean(choices >= world.noise_limit)),
    }


def run_condition(condition: str, seed: int, sample_budget: int = 1200, samples_per_intervention: int = 4) -> dict:
    if sample_budget % samples_per_intervention:
        raise ValueError("sample_budget must be divisible by samples_per_intervention")
    count = sample_budget // samples_per_intervention
    world = make_world(seed, sample_budget)
    policy = make_policy(condition)
    rng = np.random.default_rng(seed + 400_000)
    choices = np.empty(count)
    for index in range(count):
        x = policy.choose(world.grid, rng)
        before, after, _ = world.intervene(x, index * samples_per_intervention, samples_per_intervention)
        if condition == "fractional":
            policy.observe(x, before, after)
        else:
            policy.observe(x, after)
        choices[index] = x

    first = choices[: count // 5]
    middle = choices[count * 3 // 10 : count * 7 // 10]
    final = choices[-count // 5 :]
    signature = {
        "first": oracle_allocation(first, world),
        "middle": oracle_allocation(middle, world),
        "final": oracle_allocation(final, world),
        "first_home_distance": float(np.median(np.abs(first - 0.10))),
        "middle_home_distance": float(np.median(np.abs(middle - 0.10))),
    }
    signature_pass = (
        signature["first_home_distance"] < signature["middle_home_distance"]
        and signature["middle"]["structured"] > 0.50
        and signature["final"]["noise"] < 0.15
    )
    return {
        "condition": condition,
        "seed": seed,
        "structured_error_final": world.structured_error(),
        "noise_fraction": oracle_allocation(choices, world)["noise"],
        "coverage_entropy": coverage_entropy(choices),
        "signature": signature,
        "signature_pass": bool(signature_pass),
        "world": {
            "base_limit": world.base_limit,
            "noise_limit": world.noise_limit,
            "base_tau": world.base_tau,
            "structured_tau": world.structured_tau,
            "exposure_bandwidth": world.exposure_bandwidth,
            "noise_scale": world.noise_scale,
        },
    }
