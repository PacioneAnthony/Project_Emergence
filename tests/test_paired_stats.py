"""Reference tests for the DC-003R paired statistics and runner smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from learning.paired_stats import (
    bca_bootstrap_ci,
    cohen_dz,
    exact_sign_flip_pvalue,
    holm_correction,
    noninferiority_sign_flip_pvalue,
    paired_sign_counts,
    rank_biserial,
)


def test_exact_pvalue_matches_hand_enumeration():
    # diffs (1, 2, 3): among the 8 sign assignments only +++ reaches mean 2.
    assert exact_sign_flip_pvalue([1.0, 2.0, 3.0], "greater") == pytest.approx(1 / 8)
    assert exact_sign_flip_pvalue([-1.0, -2.0, -3.0], "less") == pytest.approx(1 / 8)
    # Observed mean 0 sits in the middle of a symmetric null: p = 1 both sides
    # for a single zero difference.
    assert exact_sign_flip_pvalue([0.0], "greater") == pytest.approx(1.0)


def test_exact_pvalue_counts_ties_conservatively():
    # diffs (1, 1): assignments ++, +-, -+, -- give means 1, 0, 0, -1.
    assert exact_sign_flip_pvalue([1.0, 1.0], "greater") == pytest.approx(1 / 4)
    # diffs (1, -1): means under the 4 assignments are 0, 1, -1, 0; the
    # observed mean 0 is tied or exceeded by three of them.
    assert exact_sign_flip_pvalue([1.0, -1.0], "greater") == pytest.approx(3 / 4)


def test_noninferiority_with_zero_margin_is_standard_test():
    diffs = [-0.3, -0.1, -0.2, 0.05]
    assert noninferiority_sign_flip_pvalue(diffs, 0.0) == pytest.approx(
        exact_sign_flip_pvalue(diffs, "less")
    )


def test_noninferiority_rejects_when_far_below_margin():
    diffs = np.full(12, -0.02)
    assert noninferiority_sign_flip_pvalue(diffs, 0.05) == pytest.approx(1 / 2**12)
    # The same differences are inferior against a margin far below them.
    assert noninferiority_sign_flip_pvalue(diffs, -0.30) == pytest.approx(1.0)


def test_holm_correction_reference_values():
    adjusted = holm_correction([0.01, 0.04])
    assert adjusted == pytest.approx([0.02, 0.04])
    # Order-independent and monotone.
    assert holm_correction([0.04, 0.01]) == pytest.approx([0.04, 0.02])
    assert holm_correction([0.03, 0.02, 0.9]) == pytest.approx([0.06, 0.06, 0.9])


def test_sign_counts_and_effect_sizes():
    diffs = [1.0, 2.0, 3.0, -1.5, 0.0]
    assert paired_sign_counts(diffs) == {"positive": 3, "negative": 1, "zero": 1}
    assert cohen_dz([1.0, 2.0, 3.0]) == pytest.approx(2.0)
    assert np.isnan(cohen_dz([1.0, 1.0]))
    # |diffs| ranks for (-1, 2, 3): W+ = 2 + 3, W- = 1.
    assert rank_biserial([-1.0, 2.0, 3.0]) == pytest.approx((5 - 1) / 6)
    assert rank_biserial([1.0, 2.0]) == pytest.approx(1.0)
    assert rank_biserial([0.0]) == 0.0


def test_bca_brackets_mean_with_sane_width_and_is_deterministic():
    rng = np.random.default_rng(7)
    values = rng.normal(0.5, 1.0, size=40)
    low, high = bca_bootstrap_ci(values, np.mean, n_boot=4000, seed=11)
    assert low < values.mean() < high
    standard_error = values.std(ddof=1) / np.sqrt(values.size)
    assert 2 * standard_error < high - low < 6 * standard_error
    assert (low, high) == bca_bootstrap_ci(values, np.mean, n_boot=4000, seed=11)


def test_bca_is_shift_equivariant():
    rng = np.random.default_rng(3)
    values = rng.normal(0.0, 1.0, size=25)
    low, high = bca_bootstrap_ci(values, np.mean, n_boot=3000, seed=5)
    shifted_low, shifted_high = bca_bootstrap_ci(values + 10.0, np.mean, n_boot=3000, seed=5)
    assert shifted_low == pytest.approx(low + 10.0, abs=1e-9)
    assert shifted_high == pytest.approx(high + 10.0, abs=1e-9)


def test_replication_runner_smoke(tmp_path: Path):
    output = tmp_path / "dc003r_smoke"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.research.run_fractional_replication",
            "--seed-start",
            "6301",
            "--seed-count",
            "2",
            "--sample-budget",
            "120",
            "--protocol",
            "DC-003R-SMOKE",
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    assert payload["protocol"] == "DC-003R-SMOKE"
    assert payload["status"] == "complete"
    assert len(payload["results"]) == 8
    gates = payload["gates"]
    for key in ("r_h1", "r_h1b", "r_h2", "r_h3", "coverage", "stability"):
        assert key in gates
    assert isinstance(payload["promote_dc004"], bool)
    assert "Décision pré-enregistrée" in (output / "summary.md").read_text(encoding="utf-8")
