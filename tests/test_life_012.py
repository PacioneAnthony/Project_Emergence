from __future__ import annotations

from collections import Counter

from learning.life_009 import ProgressRidgePolicy
from learning.life_010 import Life010Organism, plan_change_count, plan_command_cost
from learning.life_010_campaign import run_life010_trajectory
from learning.life_012 import (
    CONSTANT_MOTOR_COST,
    LIFE012_EXPERIMENT_MOTIF,
    LIFE012_EXPERIMENTS,
    LIFE012_PLANS,
    PLAN_COST_DEG,
    PLAN_STEPS,
    build_life012_private_bank,
    plan_construction_gate,
    plans_audit,
    private_bank_classes,
    sample_life012_organism,
    trial_guard_values,
)
from learning.life_012_campaign import (
    LEARNED_POLICY,
    POLICY_NAMES,
    life012_run_options,
    run_eligibility_preflight,
)


def test_life012_v4_plan_arithmetic_and_taxonomy():
    assert plan_construction_gate()
    assert sorted(plan_change_count(plan.targets_deg) for plan in LIFE012_PLANS) == [
        4,
        8,
        16,
    ]
    assert all(
        len(plan.targets_deg) == PLAN_STEPS
        and plan_command_cost(plan.targets_deg) == PLAN_COST_DEG
        and plan.targets_deg[-1] == 90.0
        for plan in LIFE012_PLANS
    )
    audit = plans_audit()
    nominal = audit["12.0"]
    assert [
        nominal[name]["mobile_steps"] for name in LIFE012_EXPERIMENTS
    ] == [32, 24, 20]
    assert [
        nominal[name]["plateau_steps"] for name in LIFE012_EXPERIMENTS
    ] == [0, 8, 12]
    assert all(
        by_plan[name]["dead_time_steps"] == 0
        for by_plan in audit.values()
        for name in LIFE012_EXPERIMENTS
    )


def test_life012_nominal_bank_is_152_ramp_40_plateau_zero_dead():
    organism = Life010Organism(seed=99601, regime="settling_dominant")
    bank = build_life012_private_bank(organism)
    classes = private_bank_classes(organism)
    assert len(bank) == len(classes) == 192
    assert Counter(classes) == {"ramp": 152, "plateau": 40}
    for start in range(0, 192, 32):
        risk, cost = trial_guard_values(bank[start : start + 32])
        assert risk <= 0.50
        assert cost == CONSTANT_MOTOR_COST


def test_life012_slow_speed_has_valid_empty_plateau_class(tmp_path):
    organism = Life010Organism(
        seed=99602,
        regime="speed_dominant",
        max_speed_deg_s=240.0,
    )
    bank = build_life012_private_bank(organism)
    classes = private_bank_classes(organism)
    assert Counter(classes) == {"ramp": 192}
    ramp = tuple(value == "ramp" for value in classes)
    plateau = tuple(value == "plateau" for value in classes)
    dead = tuple(value == "dead_time" for value in classes)
    trajectory = run_life010_trajectory(
        tmp_path / "short",
        organism=organism,
        private_bank=bank,
        policy_name="round_robin",
        learned=ProgressRidgePolicy(alpha=1e-2),
        cycles=24,
        policy_names=POLICY_NAMES,
        experiments=LIFE012_EXPERIMENTS,
        motif_by_experiment=LIFE012_EXPERIMENT_MOTIF,
        run_options=life012_run_options(),
        temporary_prefix="life012-test",
        learned_policy_name=LEARNED_POLICY,
        command_cost_deg=PLAN_COST_DEG,
        diagnostic_masks={
            "ramp": ramp,
            "plateau": plateau,
            "dead_time": dead,
        },
    )
    assert len(trajectory.diagnostic_curves["ramp"]) == 25
    assert trajectory.diagnostic_curves["plateau"] == ()
    assert trajectory.diagnostic_curves["dead_time"] == ()


def test_life012_preflight_is_end_to_end(tmp_path):
    organism = sample_life012_organism(99603)
    result, elapsed = run_eligibility_preflight(tmp_path, organism=organism)
    assert elapsed > 0.0
    assert set(result) == set(LIFE012_EXPERIMENTS)
    assert all(value["eligible_after_own_history"] for value in result.values())
    assert all(value["predicted_risk"] == 0.0 for value in result.values())
    assert all(value["motor_cost"] == CONSTANT_MOTOR_COST for value in result.values())
