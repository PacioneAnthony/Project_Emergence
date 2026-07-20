"""DC-004: hardened fractional curiosity benchmark.

Three manipulations frozen in docs/research/dc004_preregistration.md:
noisy anchors (policy-visible before/after values), a permuted layout that
places the unlearnable noise band between the base and the structured band,
and an informational control (regional scheduler fed the same before-after
gain as the fractional policy). Existing benchmark modules are reused without
modification; the frozen algorithm in developmental_curiosity.py is untouched.
"""

from __future__ import annotations

import math

import numpy as np

from learning.curiosity_benchmark import (
    BabblingPolicy,
    ContinuousLearningWorld,
    RegionalLearningProgressPolicy,
    coverage_entropy,
)
from learning.fractional_curiosity_benchmark import FractionalPolicy

CONDITIONS = ("fractional", "babbling", "regional_lp", "regional_lp_gain")


def _sigmoid(value: np.ndarray | float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(value)))


class PermutedLayoutWorld(ContinuousLearningWorld):
    """Noise band relocated between the base and the structured band.

    Band widths are preserved exactly from the drawn hidden parameters, so a
    permuted world and its standard sibling differ only in geometry:
    base [0, base_limit), noise [base_limit, base_limit + (1 - noise_limit)),
    structured above. Home (0.10) stays inside the base band.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.noise_low = self.base_limit
        self.noise_high = self.base_limit + (1.0 - self.noise_limit)
        self.bands = {
            "base": (0.0, self.base_limit),
            "noise": (self.noise_low, self.noise_high),
            "structured": (self.noise_high, 1.0),
        }

    def mechanism_weights(self, x: np.ndarray | float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        value = np.asarray(x, dtype=np.float64)
        noise = _sigmoid((value - self.noise_low) / 0.025) * _sigmoid((self.noise_high - value) / 0.025)
        base_share = _sigmoid((self.base_limit - value) / 0.035)
        base = (1.0 - noise) * base_share
        structured = np.maximum(1.0 - base - noise, 0.0)
        return np.asarray(base), np.asarray(structured), np.asarray(noise)

    def structured_error(self) -> float:
        held_out = np.linspace(self.noise_high + 0.06, 0.94, 79)
        exposure = self.exposure(held_out)
        return float(np.mean(0.10 + 0.90 * np.exp(-exposure / self.structured_tau)))


def make_hardened_world(seed: int, budget: int, permuted: bool) -> ContinuousLearningWorld:
    """Same hidden-parameter draws as DC-003's make_world, optional permutation."""
    rng = np.random.default_rng(seed + 300_000)
    params = dict(
        base_limit=float(rng.uniform(0.20, 0.35)),
        noise_limit=float(rng.uniform(0.70, 0.85)),
        base_tau=float(rng.uniform(3.0, 8.0)),
        structured_tau=float(rng.uniform(16.0, 40.0)),
        exposure_bandwidth=float(rng.uniform(0.025, 0.060)),
        noise_scale=float(rng.uniform(0.15, 0.35)),
    )
    if permuted:
        return PermutedLayoutWorld(seed, budget, **params)
    world = ContinuousLearningWorld(seed, budget, **params)
    world.bands = {
        "base": (0.0, world.base_limit),
        "structured": (world.base_limit, world.noise_limit),
        "noise": (world.noise_limit, 1.0),
    }
    return world


class RegionalGainPolicy(RegionalLearningProgressPolicy):
    """Informational control: regional scheduler scored by recent mean gain.

    Receives exactly the before-after gain the fractional policy consumes
    (raw, unclipped), with the same bins, window, epsilon and optimistic
    initialization as the historical regional_lp control.
    """

    def _progress(self, index: int) -> float:
        history = list(self.histories[index])
        if len(history) < self.min_samples:
            return math.inf
        return float(np.mean(history))


def make_hardened_policy(condition: str):
    if condition == "fractional":
        return FractionalPolicy()
    if condition == "babbling":
        return BabblingPolicy()
    if condition == "regional_lp":
        return RegionalLearningProgressPolicy()
    if condition == "regional_lp_gain":
        return RegionalGainPolicy()
    raise ValueError(condition)


def allocation(choices: np.ndarray, bands: dict[str, tuple[float, float]]) -> dict[str, float]:
    shares = {}
    for name, (low, high) in bands.items():
        upper = choices <= high if high >= 1.0 else choices < high
        shares[name] = float(np.mean((choices >= low) & upper))
    return shares


def run_condition_hardened(
    condition: str,
    seed: int,
    sigma: float,
    permuted: bool,
    sample_budget: int = 1200,
    samples_per_intervention: int = 4,
) -> dict:
    if sample_budget % samples_per_intervention:
        raise ValueError("sample_budget must be divisible by samples_per_intervention")
    count = sample_budget // samples_per_intervention
    world = make_hardened_world(seed, sample_budget, permuted)
    policy = make_hardened_policy(condition)
    rng = np.random.default_rng(seed + 400_000)
    anchor_rng = np.random.default_rng(seed + 500_000)
    noise_low, noise_high = world.bands["noise"]
    choices = np.empty(count)
    noise_zone_gains: list[float] = []
    for index in range(count):
        x = policy.choose(world.grid, rng)
        before, after, _ = world.intervene(x, index * samples_per_intervention, samples_per_intervention)
        # Truncation at zero respects the frozen algorithm's input domain
        # (anchor errors must be non-negative) and applies identically to
        # every anchor-consuming policy; documented in the pre-registration.
        noisy_before = max(before + sigma * float(anchor_rng.normal()), 0.0)
        noisy_after = max(after + sigma * float(anchor_rng.normal()), 0.0)
        if condition == "fractional":
            policy.observe(x, noisy_before, noisy_after)
            if noise_low <= x < noise_high:
                noise_zone_gains.append(max(noisy_before - noisy_after, 0.0))
        elif condition == "regional_lp_gain":
            policy.observe(x, noisy_before - noisy_after)
        else:
            policy.observe(x, noisy_after)
        choices[index] = x
    shares = allocation(choices, world.bands)
    return {
        "condition": condition,
        "seed": seed,
        "sigma": float(sigma),
        "permuted": bool(permuted),
        "interventions": count,
        "structured_error_final": world.structured_error(),
        "noise_fraction": shares["noise"],
        "allocation": shares,
        "coverage_entropy": coverage_entropy(choices),
        "noise_zone_interventions": len(noise_zone_gains) if condition == "fractional" else None,
        "noise_zone_clipped_gain_mean": (
            float(np.mean(noise_zone_gains)) if condition == "fractional" and noise_zone_gains else None
        ),
        "world": {
            "base_limit": world.base_limit,
            "noise_limit": world.noise_limit,
            "bands": {name: list(band) for name, band in world.bands.items()},
            "base_tau": world.base_tau,
            "structured_tau": world.structured_tau,
            "exposure_bandwidth": world.exposure_bandwidth,
            "noise_scale": world.noise_scale,
        },
    }
