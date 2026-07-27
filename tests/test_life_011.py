from __future__ import annotations

from collections import Counter

import numpy as np

from learning.life_009 import ProgressRidgePolicy
from learning.life_010 import plan_change_count, plan_command_cost
from learning.life_011 import (
    CONSTANT_MOTOR_COST,
    LIFE011_EXPERIMENTS,
    LIFE011_PLANS,
    PLAN_COST_DEG,
    PLAN_STEPS,
    build_life011_private_bank,
    complementarity_audit,
    complementarity_gate,
    private_bank_mobile_mask,
    regime_for_seed,
    sample_life011_organism,
    trial_guard_values,
)
from learning.life_011_campaign import (
    POLICY_NAMES,
    _trajectory,
    run_eligibility_preflight,
)


def test_life011_v3_plans_are_exact_and_realized_complementary():
    values = [
        (
            len(plan.targets_deg),
            plan_command_cost(plan.targets_deg),
            plan.targets_deg[-1],
            min(plan.targets_deg),
            max(plan.targets_deg),
            plan_change_count(plan.targets_deg),
        )
        for plan in LIFE011_PLANS
    ]
    assert all(value[:3] == (PLAN_STEPS, PLAN_COST_DEG, 90.0) for value in values)
    assert all(value[3] >= 30.0 and value[4] <= 150.0 for value in values)
    assert sorted(value[5] for value in values) == [5, 16, 32]
    audit = complementarity_audit()
    assert complementarity_gate(audit)
    nominal = audit["12.0"]
    assert nominal["probe_step_hold_v3"].mobile_steps == 28
    assert nominal["probe_reversal_v3"].mobile_steps == 32
    assert nominal["probe_micro_v3"].mobile_steps == 32
    assert nominal["probe_step_hold_v3"].reversals == 4
    assert nominal["probe_reversal_v3"].reversals == 8
    assert nominal["probe_micro_v3"].reversals == 16


def test_life011_bank_guard_and_mobile_inert_decomposition():
    organism = sample_life011_organism(99501)
    bank = build_life011_private_bank(organism)
    mask = private_bank_mobile_mask(organism)
    assert len(bank) == len(mask) == 192
    assert any(mask)
    assert any(not value for value in mask)
    assert Counter(item.motif for item in bank) == {
        "micro": 64,
        "reversal": 64,
        "step_hold": 64,
    }
    for offset in range(0, 192, 32):
        risk, cost = trial_guard_values(bank[offset : offset + 32])
        assert risk <= 0.50
        assert cost == CONSTANT_MOTOR_COST


def test_life011_smoke_seed_regimes_are_balanced():
    assert Counter(regime_for_seed(seed) for seed in range(18491, 18497)) == {
        "speed_dominant": 2,
        "settling_dominant": 2,
        "friction_dominant": 2,
    }


def test_life011_eligibility_preflight_is_end_to_end(tmp_path):
    organism = sample_life011_organism(99502)
    result, elapsed = run_eligibility_preflight(tmp_path, organism=organism)
    assert set(result) == set(LIFE011_EXPERIMENTS)
    assert elapsed > 0.0
    assert all(value["eligible_after_own_history"] for value in result.values())
    assert all(value["predicted_risk"] == 0.0 for value in result.values())
    assert all(value["motor_cost"] == CONSTANT_MOTOR_COST for value in result.values())


def test_life011_short_round_robin_trajectory_has_diagnostics(tmp_path):
    organism = sample_life011_organism(99503)
    bank = build_life011_private_bank(organism)
    mobile = private_bank_mobile_mask(organism)
    trajectory = _trajectory(
        tmp_path / "round_robin",
        organism=organism,
        private_bank=bank,
        policy_name="round_robin",
        learned=ProgressRidgePolicy(alpha=1e-2),
        diagnostic_masks={
            "mobile": mobile,
            "inert": tuple(not value for value in mobile),
        },
    )
    assert "round_robin" in POLICY_NAMES
    assert len(trajectory.curve) == 25
    assert len(trajectory.diagnostic_curves["mobile"]) == 25
    assert len(trajectory.diagnostic_curves["inert"]) == 25
    assert np.isfinite(trajectory.auc)
