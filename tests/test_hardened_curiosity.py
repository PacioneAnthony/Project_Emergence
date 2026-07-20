"""Tests for the DC-004 hardened benchmark (geometry, noise, determinism)."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from learning.hardened_curiosity_benchmark import (
    PermutedLayoutWorld,
    RegionalGainPolicy,
    allocation,
    make_hardened_world,
    run_condition_hardened,
)


def test_permuted_world_preserves_band_widths():
    standard = make_hardened_world(7302, 120, permuted=False)
    permuted = make_hardened_world(7302, 120, permuted=True)
    assert isinstance(permuted, PermutedLayoutWorld)
    # Same hidden parameter draws in both variants.
    assert permuted.base_limit == standard.base_limit
    assert permuted.structured_tau == standard.structured_tau
    noise_width = permuted.noise_high - permuted.noise_low
    assert noise_width == pytest.approx(1.0 - standard.noise_limit)
    structured_width = 1.0 - permuted.noise_high
    assert structured_width == pytest.approx(standard.noise_limit - standard.base_limit)
    # Home stays inside the base band.
    assert permuted.base_limit > 0.10


def test_permuted_world_weights_dominate_in_each_band():
    world = make_hardened_world(7304, 120, permuted=True)
    base, structured, noise = world.mechanism_weights(0.02)
    assert base > 0.95 and noise < 0.02
    center_noise = 0.5 * (world.noise_low + world.noise_high)
    base, structured, noise = world.mechanism_weights(center_noise)
    assert noise > 0.80 and base < 0.05
    center_structured = 0.5 * (world.noise_high + 1.0)
    base, structured, noise = world.mechanism_weights(center_structured)
    assert structured > 0.90 and noise < 0.05


def test_permuted_anchor_gain_is_near_zero_in_noise_zone():
    world = make_hardened_world(7306, 120, permuted=True)
    x = 0.5 * (world.noise_low + world.noise_high)
    before, after, _ = world.intervene(x, 0, 4)
    # Sigmoid transitions leak a small structured weight into the band
    # center (the original layout has the same boundary leakage), so the
    # anchor gain is near zero, not exactly zero.
    assert abs(before - after) < 0.01


def test_allocation_uses_world_bands():
    world = make_hardened_world(7302, 120, permuted=True)
    inside_noise = np.full(10, 0.5 * (world.noise_low + world.noise_high))
    shares = allocation(inside_noise, world.bands)
    assert shares["noise"] == 1.0 and shares["structured"] == 0.0


def test_regional_gain_policy_scores_mean_gain():
    policy = RegionalGainPolicy(min_samples=2)
    assert policy._progress(0) == math.inf
    policy.observe(0.05, 0.3)
    policy.observe(0.06, 0.1)
    assert policy._progress(0) == pytest.approx(0.2)


def test_run_condition_hardened_is_deterministic():
    first = run_condition_hardened("fractional", 7302, 0.05, True, sample_budget=120)
    second = run_condition_hardened("fractional", 7302, 0.05, True, sample_budget=120)
    assert first == second
    assert first["interventions"] == 30
    assert first["sigma"] == 0.05 and first["permuted"] is True


def test_sigma_zero_noise_zone_gain_stays_at_leakage_level():
    result = run_condition_hardened("fractional", 7302, 0.0, False, sample_budget=240)
    if result["noise_zone_clipped_gain_mean"] is not None:
        assert result["noise_zone_clipped_gain_mean"] < 0.01


def test_budget_and_conditions_reject_invalid_input():
    with pytest.raises(ValueError):
        run_condition_hardened("fractional", 7302, 0.0, False, sample_budget=121)
    with pytest.raises(ValueError):
        run_condition_hardened("unknown", 7302, 0.0, False, sample_budget=120)


def test_hardened_runner_smoke(tmp_path: Path):
    output = tmp_path / "dc004_smoke"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.research.run_hardened_curiosity",
            "--seed-start",
            "7301",
            "--seed-count",
            "2",
            "--sample-budget",
            "120",
            "--protocol",
            "DC-004-SMOKE",
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    assert payload["protocol"] == "DC-004-SMOKE"
    assert len(payload["results"]) == 3 * 4 * 2
    for key in ("d4_h1", "d4_h2", "d4_h3"):
        assert key in payload["gates"]
    assert set(payload["bias_report"]) == {"0.0", "0.02", "0.05"}
    assert isinstance(payload["promote_visual_simulation"], bool)
