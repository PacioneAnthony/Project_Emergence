from __future__ import annotations

from collections import Counter

import numpy as np

from cognitive.models import ExperimentSignals
from learning.life_009 import PolicyHistory
from learning.life_010 import (
    EXPERIMENT_MOTIF,
    LIFE010_EXPERIMENTS,
    LIFE010_PLANS,
    PLAN_COST_DEG,
    PLAN_STEPS,
    DynamicsTransition,
    ProtectedResidualCompetence,
    build_life010_private_bank,
    execute_direct_plan,
    life010_policy_features,
    plan_change_count,
    plan_command_cost,
    prior_prediction,
    regime_for_seed,
    sample_life010_organism,
)
from learning.life_010_campaign import build_life010_teacher


def test_life010_plans_are_exactly_equal_cost_and_temporally_distinct():
    audit = {
        plan.primitive: (
            len(plan.targets_deg),
            plan_command_cost(plan.targets_deg),
            plan.targets_deg[-1],
            plan_change_count(plan.targets_deg),
        )
        for plan in LIFE010_PLANS
    }
    assert sorted(value[:3] for value in audit.values()) == [
        (PLAN_STEPS, PLAN_COST_DEG, 90.0)
    ] * 3
    assert sorted(value[3] for value in audit.values()) == [5, 14, 28]


def test_life010_prior_is_rate_ramp_not_as5600_bound():
    transition = DynamicsTransition(
        current_angle_deg=90.0,
        previous_target_deg=90.0,
        next_target_deg=160.0,
        previous_angle_delta_deg=0.0,
        previous_command_delta_deg=0.0,
        next_angle_deg=90.0,
        sequence_id=0,
        motif="step_hold",
    )
    assert prior_prediction(transition) == 102.0
    reverse = DynamicsTransition(
        current_angle_deg=20.0,
        previous_target_deg=20.0,
        next_target_deg=160.0,
        previous_angle_delta_deg=15.0,
        previous_command_delta_deg=-140.0,
        next_angle_deg=40.0,
        sequence_id=1,
        motif="step_hold",
    )
    assert prior_prediction(reverse) == 32.0


def test_private_bank_and_protected_update_are_finite():
    organism = sample_life010_organism(99101)
    bank = build_life010_private_bank(organism)
    assert len(bank) == 192
    assert Counter(item.motif for item in bank) == {
        "micro": 64,
        "reversal": 64,
        "step_hold": 64,
    }
    trial = execute_direct_plan(
        organism,
        experiment_id="probe_micro",
        execution_seed=9910101,
    )
    model = ProtectedResidualCompetence()
    initial_private = model.mae(bank)
    update = model.update(trial)
    assert len(model.fit_data) == 16
    assert len(model.public_data) == 16
    assert not update.accepted or (
        update.candidate_public_mae <= update.current_public_mae + 1e-12
    )
    assert np.isfinite(model.mae(bank))
    assert initial_private > 0.0
    vector = life010_policy_features(
        model,
        experiment_id="probe_micro",
        cycle_index=1,
        history=PolicyHistory(("probe_micro",)),
        signals=ExperimentSignals(0.5, 0.5, 0.5, 0.5, 0.1, 0.5),
    )
    assert np.all(np.isfinite(vector))


def test_smoke_seed_regimes_are_balanced_without_hidden_feature():
    regimes = [regime_for_seed(seed) for seed in range(18191, 18197)]
    assert Counter(regimes) == {
        "speed_dominant": 2,
        "settling_dominant": 2,
        "friction_dominant": 2,
    }
    assert all(EXPERIMENT_MOTIF[name] in {"micro", "reversal", "step_hold"} for name in LIFE010_EXPERIMENTS)


def test_life010_teacher_branches_are_isolated(tmp_path):
    organism = sample_life010_organism(99102)
    bank = build_life010_private_bank(organism)
    result = build_life010_teacher(
        tmp_path / "teacher",
        organism=organism,
        private_bank=bank,
        cycles=2,
    )
    assert len(result.examples) == 6
    assert result.replay_bit_identical
    assert result.protection_integrity
    assert result.main_counts == {
        "proposals": 2,
        "executions": 2,
        "j0_sessions": 2,
        "cycles": 2,
        "complete_cycles": 2,
        "assessments": 2,
        "running_executions": 0,
    }

