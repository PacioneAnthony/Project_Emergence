"""Reviewed LIFE-012 v4 plans and ramp/plateau/dead-time taxonomy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from learning.life_009 import canonical_digest, stable_seed
from learning.life_010 import (
    DynamicsTransition,
    Life010Organism,
    build_life010_private_bank,
    execute_direct_plan,
    plan_change_count,
    plan_command_cost,
    prior_prediction,
)
from sim3d.life_executor import BoundedPrimitivePlan


LIFE012_EXPERIMENTS = (
    "probe_micro_v4",
    "probe_reversal_v4",
    "probe_step_settle_v4",
)
LIFE012_PRIMITIVES = {
    "probe_micro_v4": "probe_micro_v4_bounded_servo",
    "probe_reversal_v4": "probe_reversal_v4_bounded_servo",
    "probe_step_settle_v4": "probe_step_settle_v4_bounded_servo",
}
LIFE012_EXPERIMENT_MOTIF = {
    "probe_micro_v4": "micro",
    "probe_reversal_v4": "reversal",
    "probe_step_settle_v4": "step_hold",
}
PLAN_STEPS = 32
PLAN_COST_DEG = 240.0
CRITICAL_STEP_DEG = 7.5
CRITICAL_SPEED_DEG_S = 375.0
MAX_PREDICTED_RISK = 0.50
MAX_MOTOR_COST = 0.80
CONSTANT_PREDICTED_RISK = 0.0
CONSTANT_MOTOR_COST = PLAN_COST_DEG / (160.0 * PLAN_STEPS)
PLATEAU_WINDOW_STEPS = 3

STEP_SETTLE_TARGETS = (
    (150.0,) * 8
    + (90.0,) * 8
    + (30.0,) * 8
    + (90.0,) * 8
)
REVERSAL_TARGETS = (
    (60.0,) * 4
    + (90.0,) * 4
    + (120.0,) * 4
    + (90.0,) * 4
) * 2
MICRO_TARGETS = (
    (75.0,) * 2
    + (90.0,) * 2
    + (105.0,) * 2
    + (90.0,) * 2
) * 4
LIFE012_PLANS = (
    BoundedPrimitivePlan(LIFE012_PRIMITIVES["probe_micro_v4"], MICRO_TARGETS),
    BoundedPrimitivePlan(LIFE012_PRIMITIVES["probe_reversal_v4"], REVERSAL_TARGETS),
    BoundedPrimitivePlan(LIFE012_PRIMITIVES["probe_step_settle_v4"], STEP_SETTLE_TARGETS),
)


@dataclass(frozen=True)
class ClassifiedRamp:
    limited_trace_deg: tuple[float, ...]
    displacement_deg: tuple[float, ...]
    classes: tuple[str, ...]
    reversals: int

    def count(self, name: str) -> int:
        return self.classes.count(name)


def classify_limited_ramp(
    targets: Sequence[float],
    *,
    max_step_deg: float,
) -> ClassifiedRamp:
    if max_step_deg <= 0.0:
        raise ValueError("max_step_deg must be positive")
    limited = 90.0
    trace: list[float] = []
    deltas: list[float] = []
    classes: list[str] = []
    steps_after_arrival: int | None = None
    for target in targets:
        delta = float(np.clip(float(target) - limited, -max_step_deg, max_step_deg))
        limited = float(np.clip(limited + delta, 10.0, 170.0))
        trace.append(limited)
        deltas.append(delta)
        if abs(delta) > 1e-12:
            classes.append("ramp")
            steps_after_arrival = 0 if abs(limited - float(target)) <= 1e-12 else None
        else:
            steps_after_arrival = (
                1 if steps_after_arrival is None else steps_after_arrival + 1
            )
            classes.append(
                "plateau"
                if steps_after_arrival <= PLATEAU_WINDOW_STEPS
                else "dead_time"
            )
    signs = [int(np.sign(delta)) for delta in deltas if abs(delta) > 1e-12]
    reversals = sum(left != right for left, right in zip(signs, signs[1:]))
    return ClassifiedRamp(
        limited_trace_deg=tuple(trace),
        displacement_deg=tuple(deltas),
        classes=tuple(classes),
        reversals=reversals,
    )


def plans_audit() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for step in (4.8, 7.5, 12.0, 14.4):
        result[str(step)] = {}
        for experiment_id in LIFE012_EXPERIMENTS:
            plan = next(
                item
                for item in LIFE012_PLANS
                if item.primitive == LIFE012_PRIMITIVES[experiment_id]
            )
            ramp = classify_limited_ramp(plan.targets_deg, max_step_deg=step)
            result[str(step)][experiment_id] = {
                "mobile_steps": ramp.count("ramp"),
                "plateau_steps": ramp.count("plateau"),
                "dead_time_steps": ramp.count("dead_time"),
                "reversals": ramp.reversals,
                "realized_displacement_deg": float(
                    sum(abs(value) for value in ramp.displacement_deg)
                ),
            }
    return result


def plan_construction_gate() -> bool:
    exact = all(
        len(plan.targets_deg) == PLAN_STEPS
        and plan_command_cost(plan.targets_deg) == PLAN_COST_DEG
        and plan.targets_deg[-1] == 90.0
        and min(plan.targets_deg) >= 30.0
        and max(plan.targets_deg) <= 150.0
        for plan in LIFE012_PLANS
    )
    audit = plans_audit()
    reversal_orders = [
        [
            int(by_plan[name]["reversals"])
            for name in LIFE012_EXPERIMENTS
        ]
        for by_plan in audit.values()
    ]
    return exact and all(order == [8, 4, 2] for order in reversal_orders)


def regime_for_seed(seed: int) -> str:
    return ("speed_dominant", "settling_dominant", "friction_dominant")[seed % 3]


def sample_life012_organism(seed: int) -> Life010Organism:
    regime = regime_for_seed(seed)
    rng = np.random.default_rng(stable_seed("life012-organism-v1", int(seed)))
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


def trial_guard_values(
    transitions: Sequence[DynamicsTransition],
) -> tuple[float, float]:
    if len(transitions) != PLAN_STEPS:
        raise AssertionError("LIFE-012 trial must contain 32 transitions")
    boundary = sum(
        item.next_target_deg <= 20.0
        or item.next_target_deg >= 160.0
        or item.next_angle_deg <= 20.0
        or item.next_angle_deg >= 160.0
        for item in transitions
    )
    return boundary / len(transitions), plan_command_cost(
        [item.next_target_deg for item in transitions]
    ) / (160.0 * len(transitions))


def assert_trial_invariant(transitions: Sequence[DynamicsTransition]) -> None:
    risk, cost = trial_guard_values(transitions)
    if risk > MAX_PREDICTED_RISK or cost > MAX_MOTOR_COST:
        raise AssertionError("LIFE-012 per-trial guard invariant failed")


def execute_life012_direct_plan(
    organism: Life010Organism,
    *,
    experiment_id: str,
    execution_seed: int,
) -> tuple[DynamicsTransition, ...]:
    transitions = execute_direct_plan(
        organism,
        experiment_id=experiment_id,
        execution_seed=execution_seed,
        plans=LIFE012_PLANS,
        primitives=LIFE012_PRIMITIVES,
        motif_by_experiment=LIFE012_EXPERIMENT_MOTIF,
    )
    assert_trial_invariant(transitions)
    return transitions


def build_life012_private_bank(
    organism: Life010Organism,
) -> tuple[DynamicsTransition, ...]:
    bank = build_life010_private_bank(
        organism,
        experiments=LIFE012_EXPERIMENTS,
        plans=LIFE012_PLANS,
        primitives=LIFE012_PRIMITIVES,
        motif_by_experiment=LIFE012_EXPERIMENT_MOTIF,
        seed_namespace="life012-private-bank-v1",
    )
    for start in range(0, len(bank), PLAN_STEPS):
        assert_trial_invariant(bank[start : start + PLAN_STEPS])
    return bank


def private_bank_classes(organism: Life010Organism) -> tuple[str, ...]:
    step = organism.max_speed_deg_s * 0.02
    result: list[str] = []
    for _ in range(2):
        for experiment_id in LIFE012_EXPERIMENTS:
            plan = next(
                item
                for item in LIFE012_PLANS
                if item.primitive == LIFE012_PRIMITIVES[experiment_id]
            )
            result.extend(
                classify_limited_ramp(
                    plan.targets_deg,
                    max_step_deg=step,
                ).classes
            )
    if len(result) != 192:
        raise AssertionError("LIFE-012 taxonomy must contain 192 transitions")
    if "dead_time" in result:
        raise AssertionError("LIFE-012 dead_time must be zero")
    return tuple(result)


def prior_mae_or_none(
    transitions: Sequence[DynamicsTransition],
) -> float | None:
    if not transitions:
        return None
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
            "protocol": "life012-v1",
            "b1_path": "B",
            "critical_speed_deg_s": CRITICAL_SPEED_DEG_S,
            "plans": [
                {
                    "primitive": plan.primitive,
                    "targets": list(plan.targets_deg),
                    "cost": plan_command_cost(plan.targets_deg),
                    "changes": plan_change_count(plan.targets_deg),
                }
                for plan in LIFE012_PLANS
            ],
        }
    )
