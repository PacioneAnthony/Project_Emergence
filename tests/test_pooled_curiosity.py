"""Tests for the DC-005 aggregate-then-clip scheduler."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from learning.developmental_curiosity import FractionalInterventionalCuriosity
from learning.hardened_curiosity_benchmark import run_condition_hardened
from learning.pooled_curiosity import PooledFractionalCuriosity


def make_scheduler(cls):
    return cls(
        1,
        np.array([0.10]),
        bandwidth=0.08,
        min_evidence=5.0,
        frontier=0.09,
        epsilon=0.05,
        max_observations=512,
    )


def feed_symmetric_noise(scheduler, descriptor: float, pairs: int = 30, level: float = 0.8, delta: float = 0.05):
    # Alternating +/- delta anchor noise around a constant unlearnable level:
    # signed gains are (+2delta, -2delta, ...) with exactly zero mean.
    for index in range(pairs):
        if index % 2 == 0:
            scheduler.observe(np.array([descriptor]), level + delta, level - delta)
        else:
            scheduler.observe(np.array([descriptor]), level - delta, level + delta)


def test_pooled_kills_the_clip_bias_where_fractional_keeps_it():
    pooled = make_scheduler(PooledFractionalCuriosity)
    fractional = make_scheduler(FractionalInterventionalCuriosity)
    feed_symmetric_noise(pooled, 0.5)
    feed_symmetric_noise(fractional, 0.5)
    candidate = np.array([[0.5]])
    pooled_gain = float(pooled.score_components(candidate)["fractional_gain"][0])
    fractional_gain = float(fractional.score_components(candidate)["fractional_gain"][0])
    # Same data: the per-observation clip manufactures a large phantom gain,
    # the pooled estimator does not.
    assert pooled_gain == pytest.approx(0.0, abs=1e-6)
    assert fractional_gain > 0.03
    assert fractional_gain > 100 * max(pooled_gain, 1e-9)


def test_pooled_detects_real_learning():
    pooled = make_scheduler(PooledFractionalCuriosity)
    for _ in range(20):
        pooled.observe(np.array([0.5]), 0.9, 0.6)
    gain = float(pooled.score_components(np.array([[0.5]]))["fractional_gain"][0])
    assert gain > 0.2


def test_pooled_matches_fractional_interface_and_determinism():
    pooled = make_scheduler(PooledFractionalCuriosity)
    components = pooled.score_components(np.array([[0.10], [0.50]]))
    assert set(components) == {
        "score",
        "fractional_gain",
        "familiarity",
        "habituation",
        "unproductive",
        "reachability",
    }
    first = run_condition_hardened("pooled", 8302, 0.05, True, sample_budget=120)
    second = run_condition_hardened("pooled", 8302, 0.05, True, sample_budget=120)
    assert first == second
    assert first["condition"] == "pooled"
    assert first["noise_zone_interventions"] is not None


def test_pooled_rejects_negative_anchor_errors_like_frozen_base():
    pooled = make_scheduler(PooledFractionalCuriosity)
    with pytest.raises(ValueError):
        pooled.observe(np.array([0.5]), -0.01, 0.2)


def test_pooled_runner_smoke(tmp_path: Path):
    output = tmp_path / "dc005_smoke"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.research.run_pooled_curiosity",
            "--seed-start",
            "8301",
            "--seed-count",
            "2",
            "--sample-budget",
            "120",
            "--protocol",
            "DC-005-SMOKE",
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    assert payload["protocol"] == "DC-005-SMOKE"
    assert len(payload["results"]) == 3 * 4 * 2
    for key in ("d5_h1", "d5_h2", "d5_h3"):
        assert key in payload["gates"]
    assert "positive_control" in payload
    assert isinstance(payload["promote"], bool)
