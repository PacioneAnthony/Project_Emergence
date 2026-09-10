from __future__ import annotations

from collections import Counter

import numpy as np

from learning.body_schema_001 import (
    PLAN_INSTANCES,
    BootstrapEnsemble,
    ensemble_basis,
    execute_plan,
    plan_gate,
    sample_organism,
)
from learning.body_schema_001_campaign import (
    build_trials,
    content_disjunction_gate,
    run_models,
)


def test_body_schema_plan_partition_is_exact_and_distinct():
    assert plan_gate()
    assert len(PLAN_INSTANCES) == 36
    assert len({plan.digest() for plan in PLAN_INSTANCES}) == 36
    counts = Counter((plan.motif, plan.role) for plan in PLAN_INSTANCES)
    for motif in ("impulse", "reversal", "micro"):
        assert counts[(motif, "protection")] == 1
        assert counts[(motif, "calibration")] == 1
        assert counts[(motif, "learning")] == 8
        assert counts[(motif, "private")] == 2


def test_as5600_replay_is_deterministic_for_same_plan():
    organism = sample_organism(99701)
    plan = PLAN_INSTANCES[0]
    first = execute_plan(organism, plan)
    second = execute_plan(organism, plan)
    assert first.angle_digest == second.angle_digest
    assert first.samples == second.samples


def test_content_partition_is_distinct_for_one_organism():
    organism = sample_organism(99702)
    trials = build_trials(organism)
    assert content_disjunction_gate(trials)
    assert {name: len(value) for name, value in trials.items() if name != "normal_all"} == {
        "protection": 3,
        "calibration": 3,
        "learning": 24,
        "private": 6,
        "blocked": 6,
        "degraded": 6,
    }


def test_probabilistic_model_is_finite_and_reproducible():
    organism = sample_organism(99703)
    trials = build_trials(organism)
    first = run_models(organism, trials)
    second = run_models(organism, trials)
    assert first["digests"] == second["digests"]
    assert len(ensemble_basis(trials["learning"][0].samples[0])) == 18
    assert first["updates"]["ensemble"]["accepted"] + first["updates"]["ensemble"]["rejected"] == 24
    assert np.isfinite(first["curves"]["ensemble"][-1]["angle_mae"])
    assert np.isfinite(first["uncertainty_final"]["coverage"])
    assert BootstrapEnsemble(organism.seed).members.shape == (16, 18)
