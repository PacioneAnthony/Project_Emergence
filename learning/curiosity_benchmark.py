"""Controlled continuous benchmark for developmental curiosity (DC-001).

The evaluator knows that the continuous axis blends a mastered mechanism, a
reducibly uncertain structured mechanism and irreducible noise.  Policies only
observe candidate coordinates and realized prediction errors.  The benchmark
isolates scheduling behavior from neural representation quality.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from learning.developmental_curiosity import DevelopmentalCuriosity


CONDITIONS = ("developmental", "babbling", "round_robin_habituation", "regional_lp")
BASE_LIMIT = 0.28
NOISE_LIMIT = 0.78


def _sigmoid(value: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-np.asarray(value)))


class ContinuousLearningWorld:
    """Hidden heterogeneous mechanisms mixed smoothly on a continuous axis."""

    def __init__(
        self,
        seed: int,
        budget: int,
        grid_size: int = 101,
        exposure_bandwidth: float = 0.035,
        base_limit: float = BASE_LIMIT,
        noise_limit: float = NOISE_LIMIT,
        base_tau: float = 5.0,
        structured_tau: float = 24.0,
        noise_scale: float = 0.25,
    ):
        self.grid = np.linspace(0.0, 1.0, grid_size)
        self.exposure_bandwidth = float(exposure_bandwidth)
        self.base_limit = float(base_limit)
        self.noise_limit = float(noise_limit)
        self.base_tau = float(base_tau)
        self.structured_tau = float(structured_tau)
        self.noise_scale = float(noise_scale)
        self.visits: list[float] = []
        rng = np.random.default_rng(seed)
        # Counterfactual table pairs observation noise across policies by step/x.
        self.noise_table = rng.normal(size=(budget, grid_size))
        # Fixed anchors make before/after comparisons causal: their nuisance
        # realization is identical on both sides of an intervention.
        self.anchor_noise = rng.normal(size=grid_size)

    def mechanism_weights(self, x: np.ndarray | float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        value = np.asarray(x, dtype=np.float64)
        noise = _sigmoid((value - self.noise_limit) / 0.025)
        base_share = _sigmoid((self.base_limit - value) / 0.035)
        base = (1.0 - noise) * base_share
        structured = np.maximum(1.0 - base - noise, 0.0)
        return np.asarray(base), np.asarray(structured), np.asarray(noise)

    def exposure(self, x: np.ndarray | float) -> np.ndarray:
        value = np.asarray(x, dtype=np.float64)
        if not self.visits:
            return np.zeros_like(value)
        visits = np.asarray(self.visits, dtype=np.float64)
        delta = value[..., None] - visits
        return np.exp(-0.5 * np.square(delta / self.exposure_bandwidth)).sum(axis=-1)

    def observe(self, x: float, step: int) -> float:
        exposure = float(self.exposure(x))
        base_weight, structured_weight, noise_weight = self.mechanism_weights(x)
        base_error = 0.04 + 0.20 * math.exp(-exposure / self.base_tau)
        structured_error = 0.10 + 0.90 * math.exp(-exposure / self.structured_tau)
        grid_index = int(np.clip(round(x * (len(self.grid) - 1)), 0, len(self.grid) - 1))
        noise_error = float(np.clip(1.0 + self.noise_scale * self.noise_table[step, grid_index], 0.2, 1.8))
        error = float(base_weight * base_error + structured_weight * structured_error + noise_weight * noise_error)
        self.visits.append(float(x))
        return error

    def anchor_error(self, x: float) -> float:
        exposure = float(self.exposure(x))
        base_weight, structured_weight, noise_weight = self.mechanism_weights(x)
        base_error = 0.04 + 0.20 * math.exp(-exposure / self.base_tau)
        structured_error = 0.10 + 0.90 * math.exp(-exposure / self.structured_tau)
        grid_index = int(np.clip(round(x * (len(self.grid) - 1)), 0, len(self.grid) - 1))
        noise_error = float(np.clip(1.0 + self.noise_scale * self.anchor_noise[grid_index], 0.2, 1.8))
        return float(base_weight * base_error + structured_weight * structured_error + noise_weight * noise_error)

    def intervene(self, x: float, start_step: int, samples: int = 4) -> tuple[float, float, float]:
        before = self.anchor_error(x)
        observed = [self.observe(x, start_step + offset) for offset in range(samples)]
        after = self.anchor_error(x)
        return before, after, float(np.mean(observed))

    def structured_error(self) -> float:
        held_out = np.linspace(self.base_limit + 0.06, self.noise_limit - 0.06, 79)
        exposure = self.exposure(held_out)
        return float(np.mean(0.10 + 0.90 * np.exp(-exposure / self.structured_tau)))


class BabblingPolicy:
    def choose(self, grid: np.ndarray, rng: np.random.Generator) -> float:
        return float(grid[int(rng.integers(0, len(grid)))])

    def observe(self, x: float, error: float) -> None:
        pass


class RoundRobinHabituationPolicy:
    """Uniform-bin baseline whose mastered bins lose priority."""

    def __init__(self, bins: int = 20):
        self.bins = bins
        self.visits = np.zeros(bins, dtype=np.int64)
        self.errors: list[deque[float]] = [deque(maxlen=20) for _ in range(bins)]
        self.all_errors: list[float] = []
        self.last_bin = 0

    def _bin(self, x: float) -> int:
        return min(int(x * self.bins), self.bins - 1)

    def choose(self, grid: np.ndarray, rng: np.random.Generator) -> float:
        global_scale = max(float(np.median(self.all_errors)) if self.all_errors else 1.0, 1e-8)
        score = np.empty(self.bins, dtype=np.float64)
        for index in range(self.bins):
            recent = float(np.mean(self.errors[index])) if self.errors[index] else global_scale
            habituation = math.exp(-recent / global_scale) if self.errors[index] else 0.0
            score[index] = (1.0 - 0.75 * habituation) / (1.0 + self.visits[index])
        best = np.flatnonzero(np.isclose(score, np.max(score)))
        self.last_bin = int(rng.choice(best))
        low = self.last_bin / self.bins
        high = (self.last_bin + 1) / self.bins
        candidates = grid[(grid >= low) & (grid <= high)]
        return float(rng.choice(candidates))

    def observe(self, x: float, error: float) -> None:
        index = self._bin(x)
        self.visits[index] += 1
        self.errors[index].append(float(error))
        self.all_errors.append(float(error))


class RegionalLearningProgressPolicy:
    """Eight-bin historical ablation, matching the rejected minimal policy."""

    def __init__(self, bins: int = 8, window: int = 40, min_samples: int = 6, epsilon: float = 0.2):
        self.bins = bins
        self.min_samples = min_samples
        self.epsilon = epsilon
        self.histories: list[deque[float]] = [deque(maxlen=window) for _ in range(bins)]

    def _bin(self, x: float) -> int:
        return min(int(x * self.bins), self.bins - 1)

    def _progress(self, index: int) -> float:
        history = list(self.histories[index])
        if len(history) < self.min_samples:
            return math.inf
        half = len(history) // 2
        return float(np.mean(history[:half]) - np.mean(history[half:]))

    def choose(self, grid: np.ndarray, rng: np.random.Generator) -> float:
        if rng.random() < self.epsilon:
            index = int(rng.integers(0, self.bins))
        else:
            scores = [self._progress(i) for i in range(self.bins)]
            best = max(scores)
            index = int(rng.choice([i for i, score in enumerate(scores) if score == best]))
        low = index / self.bins
        high = (index + 1) / self.bins
        candidates = grid[(grid >= low) & (grid <= high)]
        return float(rng.choice(candidates))

    def observe(self, x: float, error: float) -> None:
        self.histories[self._bin(x)].append(float(error))


class DevelopmentalPolicy:
    def __init__(self, seed: int):
        self.scheduler = DevelopmentalCuriosity(
            descriptor_dim=1,
            home_descriptor=np.array([0.10]),
            bandwidth=0.08,
            min_evidence=8.0,
            initial_frontier=0.07,
            max_frontier=0.32,
            epsilon=0.05,
            max_observations=512,
            seed=seed,
        )

    def choose(self, grid: np.ndarray, rng: np.random.Generator) -> float:
        sample_size = min(48, len(grid))
        sampled = rng.choice(len(grid), size=sample_size, replace=False)
        anchors = np.array([0, int(round(0.10 * (len(grid) - 1))), len(grid) - 1])
        indices = np.unique(np.concatenate([sampled, anchors]))
        candidates = grid[indices, None]
        return float(grid[indices[self.scheduler.choose(candidates, rng)]])

    def observe(self, x: float, error: float) -> None:
        self.scheduler.observe(np.array([x]), error)


def make_policy(condition: str, seed: int):
    if condition == "developmental":
        return DevelopmentalPolicy(seed)
    if condition == "babbling":
        return BabblingPolicy()
    if condition == "round_robin_habituation":
        return RoundRobinHabituationPolicy()
    if condition == "regional_lp":
        return RegionalLearningProgressPolicy()
    raise ValueError(f"Unknown condition: {condition}")


def coverage_entropy(choices: np.ndarray, bins: int = 20) -> float:
    histogram, _ = np.histogram(choices, bins=bins, range=(0.0, 1.0))
    probabilities = histogram[histogram > 0] / max(histogram.sum(), 1)
    return float(-(probabilities * np.log(probabilities)).sum() / math.log(bins))


def allocation(choices: np.ndarray) -> dict[str, float]:
    return {
        "base": float(np.mean(choices < BASE_LIMIT)),
        "structured": float(np.mean((choices >= BASE_LIMIT) & (choices < NOISE_LIMIT))),
        "noise": float(np.mean(choices >= NOISE_LIMIT)),
    }


def run_condition(condition: str, seed: int, budget: int = 1200) -> dict:
    world = ContinuousLearningWorld(seed, budget)
    policy = make_policy(condition, seed)
    rng = np.random.default_rng(seed + 100_000)
    choices = np.empty(budget, dtype=np.float64)
    errors = np.empty(budget, dtype=np.float64)

    for step in range(budget):
        choice = policy.choose(world.grid, rng)
        error = world.observe(choice, step)
        policy.observe(choice, error)
        choices[step] = choice
        errors[step] = error

    first = choices[: budget // 5]
    middle = choices[budget * 3 // 10 : budget * 7 // 10]
    final = choices[-budget // 5 :]
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
        "budget": budget,
        "structured_error_final": world.structured_error(),
        "noise_fraction": allocation(choices)["noise"],
        "coverage_entropy": coverage_entropy(choices),
        "mean_observed_error": float(np.mean(errors)),
        "signature": signature,
        "signature_pass": bool(signature_pass),
    }
    if condition == "developmental":
        result["scheduler"] = policy.scheduler.diagnostics()
    return result
