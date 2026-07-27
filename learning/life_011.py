"""Reviewed LIFE-011 plans, organisms, guard invariants, and diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

import numpy as np

from cognitive.models import ExperimentSignals
from learning.life_009 import PolicyHistory, canonical_digest, stable_seed
from learning.life_010 import (
    DynamicsTransition,
    Life010Organism,
    ProtectedResidualCompetence,
    build_life010_private_bank,
    execute_direct_plan,
    life010_bench_config,
    life010_policy_features,
    plan_change_count,
    plan_command_cost,
    prior_prediction,
)
from sim3d.life_executor import BoundedPrimitivePlan


LIFE011_EXPERIMENTS = (
    "probe_micro_v3",
    "probe_reversal_v3",
    "probe_step_hold_v3",
)
LIFE011_PRIMITIVES = {
    "probe_micro_v3": "probe_micro_v3_bounded_servo",
    "probe_reversal_v3": "probe_reversal_v3_bounded_servo",
    "probe_step_hold_v3": "probe_step_hold_v3_bounded_servo",
}
LIFE011_MOTIFS = ("micro", "reversal", "step_hold")
LIFE011_EXPERIMENT_MOTIF = {
    "probe_micro_v3": "micro",
    "probe_reversal_v3": "reversal",
    "probe_step_hold_v3": "step_hold",
}
PLAN_STEPS = 32
PLAN_COST_DEG = 480.0
MAX_PREDICTED_RISK = 0.50
MAX_MOTOR_COST = 0.80
CONSTANT_PREDICTED_RISK = 0.0
CONSTANT_MOTOR_COST = PLAN_COST_DEG / (160.0 * PLAN_STEPS)

STEP_HOLD_V3_TARGETS = (
    (150.0,) * 7
    + (30.0,) * 7
    + (150.0,) * 7
    + (30.0,) * 7
    + (90.0,) * 4
)
REVERSAL_V3_TARGETS = (60.0, 60.0, 90.0, 90.0, 120.0, 120.0, 90.0, 90.0) * 4
MICRO_V3_TARGETS = (75.0, 90.0, 105.0, 90.0) * 8
LIFE011_PLANS = (
    BoundedPrimitivePlan(LIFE011_PRIMITIVES["probe_micro_v3"], MICRO_V3_TARGETS),
    BoundedPrimitivePlan(LIFE011_PRIMITIVES["probe_reversal_v3"], REVERSAL_V3_TARGETS),
    BoundedPrimitivePlan(LIFE011_PRIMITIVES["probe_step_hold_v3"], STEP_HOLD_V3_TARGETS),
)


@dataclass(frozen=True)
class RampAudit:
    mobile_steps: int
    reversals: int
    holds_outside_neutral: int
    realized_displacement_deg: float
    limited_trace_deg: tuple[float, ...]
    mobile_mask: tuple[bool, ...]


def audit_limited_ramp(
    targets: Sequence[float],
    *,
    max_step_deg: float,
) -> RampAudit:
    if max_step_deg <= 0.0:
        raise ValueError("max_step_deg must be positive")
    limited = 90.0
    trace: list[float] = []
    deltas: list[float] = []
    for target in targets:
        delta = float(np.clip(float(target) - limited, -max_step_deg, max_step_deg))
        limited = float(np.clip(limited + delta, 10.0, 170.0))
        deltas.append(delta)
        trace.append(limited)
    nonzero_signs = [int(np.sign(delta)) for delta in deltas if abs(delta) > 1e-12]
    reversals = sum(
        current != previous
        for previous, current in zip(nonzero_signs, nonzero_signs[1:])
    )
    mobile_mask = tuple(abs(delta) > 1e-12 for delta in deltas)
    return RampAudit(
        mobile_steps=sum(mobile_mask),
        reversals=reversals,
        holds_outside_neutral=sum(
            not mobile and abs(angle - 90.0) > 1e-12
            for mobile, angle in zip(mobile_mask, trace)
        ),
        realized_displacement_deg=float(sum(abs(delta) for delta in deltas)),
        limited_trace_deg=tuple(trace),
        mobile_mask=mobile_mask,
    )


def complementarity_audit() -> dict[str, dict[str, RampAudit]]:
    result: dict[str, dict[str, RampAudit]] = {}
    for step in (4.8, 12.0, 14.4):
        result[str(step)] = {
            experiment_id: audit_limited_ramp(
                next(
                    plan.targets_deg
                    for plan in LIFE011_PLANS
                    if plan.primitive == LIFE011_PRIMITIVES[experiment_id]
                ),
                max_step_deg=step,
            )
            for experiment_id in LIFE011_EXPERIMENTS
        }
    return result


def complementarity_gate(audit: Mapping[str, Mapping[str, RampAudit]]) -> bool:
    pairs = (
        ("probe_micro_v3", "probe_reversal_v3"),
        ("probe_micro_v3", "probe_step_hold_v3"),
        ("probe_reversal_v3", "probe_step_hold_v3"),
    )
    attributes = (
        "mobile_steps",
        "reversals",
        "holds_outside_neutral",
        "realized_displacement_deg",
    )
    for left, right in pairs:
        useful_attribute = False
        for attribute in attributes:
            differences = [
                float(getattr(by_plan[left], attribute))
                - float(getattr(by_plan[right], attribute))
                for by_plan in audit.values()
            ]
            if all(abs(value) > 1e-12 for value in differences) and (
                all(value > 0.0 for value in differences)
                or all(value < 0.0 for value in differences)
            ):
                useful_attribute = True
                break
        if not useful_attribute:
            return False
    return True


def regime_for_seed(seed: int) -> str:
    return ("speed_dominant", "settling_dominant", "friction_dominant")[seed % 3]


def sample_life011_organism(seed: int) -> Life010Organism:
    regime = regime_for_seed(seed)
    rng = np.random.default_rng(stable_seed("life011-organism-v1", int(seed)))
    values: dict[str, float | int | str] = {"seed": int(seed), "regime": regime}
    if regime == "speed_dominant":
        values["max_speed_deg_s"] = float(rng.uniform(240.0, 720.0))
    elif regime == "settling_dominant":
        values["position_gain"] = float(rng.uniform(7.0, 13.0))
        values["velocity_damping"] = float(rng.uniform(0.08, 0.24))
    else:
        values["joint_frictionloss"] = float(rng.uniform(0.006, 0.030))
        values["joint_armature"] = float(rng.uniform(1e-4, 4e-4))
    return Life010Organism(**values)


def life011_config_factory(organism: Life010Organism):
    return lambda execution_seed: life010_bench_config(organism, execution_seed)


def execute_life011_direct_plan(
    organism: Life010Organism,
    *,
    experiment_id: str,
    execution_seed: int,
) -> tuple[DynamicsTransition, ...]:
    transitions = execute_direct_plan(
        organism,
        experiment_id=experiment_id,
        execution_seed=execution_seed,
        plans=LIFE011_PLANS,
        primitives=LIFE011_PRIMITIVES,
        motif_by_experiment=LIFE011_EXPERIMENT_MOTIF,
    )
    assert_trial_invariant(transitions)
    return transitions


def trial_guard_values(
    transitions: Sequence[DynamicsTransition],
) -> tuple[float, float]:
    if len(transitions) != PLAN_STEPS:
        raise AssertionError("LIFE-011 trial must contain 32 transitions")
    boundary_count = sum(
        item.next_target_deg <= 20.0
        or item.next_target_deg >= 160.0
        or item.next_angle_deg <= 20.0
        or item.next_angle_deg >= 160.0
        for item in transitions
    )
    targets = [item.next_target_deg for item in transitions]
    return boundary_count / len(transitions), plan_command_cost(targets) / (
        160.0 * len(transitions)
    )


def assert_trial_invariant(transitions: Sequence[DynamicsTransition]) -> None:
    risk, cost = trial_guard_values(transitions)
    if risk > MAX_PREDICTED_RISK or cost > MAX_MOTOR_COST:
        raise AssertionError("LIFE-011 per-trial guard invariant failed")


def build_life011_private_bank(
    organism: Life010Organism,
) -> tuple[DynamicsTransition, ...]:
    bank = build_life010_private_bank(
        organism,
        experiments=LIFE011_EXPERIMENTS,
        plans=LIFE011_PLANS,
        primitives=LIFE011_PRIMITIVES,
        motif_by_experiment=LIFE011_EXPERIMENT_MOTIF,
        seed_namespace="life011-private-bank-v1",
    )
    for offset in range(0, len(bank), PLAN_STEPS):
        assert_trial_invariant(bank[offset : offset + PLAN_STEPS])
    return bank


def life011_policy_features(
    model: ProtectedResidualCompetence,
    *,
    experiment_id: str,
    cycle_index: int,
    history: PolicyHistory,
    signals: ExperimentSignals,
) -> np.ndarray:
    return life010_policy_features(
        model,
        experiment_id=experiment_id,
        cycle_index=cycle_index,
        history=history,
        signals=signals,
        experiments=LIFE011_EXPERIMENTS,
        motif_by_experiment=LIFE011_EXPERIMENT_MOTIF,
    )


def private_bank_mobile_mask(
    organism: Life010Organism,
) -> tuple[bool, ...]:
    result: list[bool] = []
    step = organism.max_speed_deg_s * 0.02
    for _ in range(2):
        for experiment_id in LIFE011_EXPERIMENTS:
            plan = next(
                plan
                for plan in LIFE011_PLANS
                if plan.primitive == LIFE011_PRIMITIVES[experiment_id]
            )
            result.extend(audit_limited_ramp(plan.targets_deg, max_step_deg=step).mobile_mask)
    if len(result) != 192:
        raise AssertionError("LIFE-011 private bank mask must contain 192 entries")
    return tuple(result)


def prior_mae(transitions: Sequence[DynamicsTransition]) -> float:
    if not transitions:
        raise ValueError("prior MAE requires transitions")
    return float(
        np.mean(
            [
                abs(prior_prediction(item) - item.next_angle_deg)
                for item in transitions
            ]
        )
    )


def plans_digest() -> str:
    return canonical_digest(
        {
            "plans": [
                {
                    "primitive": plan.primitive,
                    "targets": list(plan.targets_deg),
                    "cost": plan_command_cost(plan.targets_deg),
                    "changes": plan_change_count(plan.targets_deg),
                }
                for plan in LIFE011_PLANS
            ]
        }
    )
