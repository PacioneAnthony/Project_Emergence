"""DC-002 benchmark: curiosity from fixed-anchor learning interventions."""

from __future__ import annotations

import numpy as np

from learning.curiosity_benchmark import (
    BabblingPolicy,
    ContinuousLearningWorld,
    RegionalLearningProgressPolicy,
    RoundRobinHabituationPolicy,
    allocation,
    coverage_entropy,
)
from learning.developmental_curiosity import InterventionalCuriosity


CONDITIONS = ("interventional", "babbling", "round_robin_habituation", "regional_lp")


class InterventionalPolicy:
    def __init__(self):
        self.scheduler = InterventionalCuriosity(
            descriptor_dim=1,
            home_descriptor=np.array([0.10]),
            bandwidth=0.08,
            min_evidence=5.0,
            frontier=0.09,
            epsilon=0.05,
            max_observations=512,
        )

    def choose(self, grid: np.ndarray, rng: np.random.Generator) -> float:
        sample_size = min(48, len(grid))
        sampled = rng.choice(len(grid), size=sample_size, replace=False)
        anchors = np.array([0, int(round(0.10 * (len(grid) - 1))), len(grid) - 1])
        indices = np.unique(np.concatenate([sampled, anchors]))
        candidates = grid[indices, None]
        selected = self.scheduler.choose(candidates, rng)
        return float(grid[indices[selected]])

    def observe(self, x: float, before: float, after: float) -> None:
        self.scheduler.observe(np.array([x]), before, after)


def make_policy(condition: str):
    if condition == "interventional":
        return InterventionalPolicy()
    if condition == "babbling":
        return BabblingPolicy()
    if condition == "round_robin_habituation":
        return RoundRobinHabituationPolicy()
    if condition == "regional_lp":
        return RegionalLearningProgressPolicy()
    raise ValueError(f"Unknown condition: {condition}")


def run_condition(condition: str, seed: int, sample_budget: int = 1200, samples_per_intervention: int = 4) -> dict:
    if sample_budget % samples_per_intervention != 0:
        raise ValueError("sample_budget must be divisible by samples_per_intervention")
    interventions = sample_budget // samples_per_intervention
    world = ContinuousLearningWorld(seed, sample_budget)
    policy = make_policy(condition)
    rng = np.random.default_rng(seed + 200_000)
    choices = np.empty(interventions, dtype=np.float64)
    gains = np.empty(interventions, dtype=np.float64)

    for index in range(interventions):
        choice = policy.choose(world.grid, rng)
        before, after, _ = world.intervene(
            choice,
            start_step=index * samples_per_intervention,
            samples=samples_per_intervention,
        )
        if condition == "interventional":
            policy.observe(choice, before, after)
        else:
            policy.observe(choice, after)
        choices[index] = choice
        gains[index] = max(before - after, 0.0)

    first = choices[: interventions // 5]
    middle = choices[interventions * 3 // 10 : interventions * 7 // 10]
    final = choices[-interventions // 5 :]
    signature = {
        "first": allocation(first),
        "middle": allocation(middle),
        "final": allocation(final),
    }
    signature_pass = (
        signature["first"]["base"] > 0.50
        and signature["middle"]["structured"] > 0.50
        and signature["final"]["noise"] < 0.15
    )
    result = {
        "condition": condition,
        "seed": seed,
        "sample_budget": sample_budget,
        "interventions": interventions,
        "structured_error_final": world.structured_error(),
        "noise_fraction": allocation(choices)["noise"],
        "coverage_entropy": coverage_entropy(choices),
        "mean_interventional_gain": float(np.mean(gains)),
        "signature": signature,
        "signature_pass": bool(signature_pass),
    }
    if condition == "interventional":
        result["scheduler"] = policy.scheduler.diagnostics()
    return result
