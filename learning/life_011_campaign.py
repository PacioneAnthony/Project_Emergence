"""Reviewed two-stage smoke qualification for LIFE-011."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping

import numpy as np

from cognitive.experiments import SafeExperimentCatalog
from cognitive.models import ExperimentSignals, ExperimentSpec, SafetyContext
from cognitive.needs import CompetenceNeedRoute, PersistentNeedActivator
from learning.life_009 import (
    ProgressRidgePolicy,
    canonical_digest,
    normalized_auc,
)
from learning.life_010 import (
    POLICY_ALPHA,
    ProtectedResidualCompetence,
    plan_change_count,
    plan_command_cost,
)
from learning.life_010_campaign import (
    Life010Run,
    Life010TeacherResult,
    Life010Trajectory,
    _expected_counts,
    build_life010_teacher,
    run_life010_trajectory,
)
from learning.life_011 import (
    CONSTANT_MOTOR_COST,
    CONSTANT_PREDICTED_RISK,
    LIFE011_EXPERIMENT_MOTIF,
    LIFE011_EXPERIMENTS,
    LIFE011_PLANS,
    LIFE011_PRIMITIVES,
    MAX_MOTOR_COST,
    MAX_PREDICTED_RISK,
    PLAN_COST_DEG,
    PLAN_STEPS,
    RampAudit,
    build_life011_private_bank,
    complementarity_audit,
    complementarity_gate,
    plans_digest,
    prior_mae,
    private_bank_mobile_mask,
    regime_for_seed,
    sample_life011_organism,
)


LEARNED_POLICY = "learned_protected_progress_ridge_v2"
POLICY_NAMES = (
    LEARNED_POLICY,
    "greedy_public_residual",
    "greedy_uncertainty",
    "round_robin",
    "life006_transparent_score",
    "uniform_random",
)
MARGIN_POLICIES = ("round_robin", "greedy_public_residual", "oracle")
TIMING_POLICIES = (
    LEARNED_POLICY,
    "greedy_uncertainty",
    "life006_transparent_score",
    "uniform_random",
)
SMOKE_SEEDS = tuple(range(18491, 18497))


def build_life011_catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                experiment_id,
                LIFE011_PRIMITIVES[experiment_id],
                max_predicted_risk=MAX_PREDICTED_RISK,
                max_motor_cost=MAX_MOTOR_COST,
                max_proposals_per_session=100,
                metadata={
                    "life011_motif": LIFE011_EXPERIMENT_MOTIF[experiment_id],
                    "command_cost_deg": PLAN_COST_DEG,
                    "plan_steps": PLAN_STEPS,
                    "plans_digest": plans_digest(),
                },
            )
            for experiment_id in LIFE011_EXPERIMENTS
        ]
    )


def build_life011_base_activator() -> PersistentNeedActivator:
    prior = ExperimentSignals(0.5, 0.5, 0.5, 0.5, 0.1, 0.5)
    priors = {experiment_id: prior for experiment_id in LIFE011_EXPERIMENTS}
    route = CompetenceNeedRoute(
        competence_name="neck_dynamics_residual_prediction_v2",
        cold_start_signals=priors,
        unknown_experiments=LIFE011_EXPERIMENTS,
        learning_experiments=LIFE011_EXPERIMENTS,
        candidate_experiments=LIFE011_EXPERIMENTS,
        regressed_experiments=LIFE011_EXPERIMENTS,
    )
    return PersistentNeedActivator((route,))


SAFE_CONTEXT = SafetyContext(
    emergency_stop=False,
    hardware_healthy=True,
    model_update_in_progress=False,
    quota_state="ok",
    allowed_primitives=frozenset(LIFE011_PRIMITIVES.values()),
)


def life011_run_options() -> dict[str, Any]:
    return {
        "catalog_builder": build_life011_catalog,
        "activator_builder": build_life011_base_activator,
        "experiments": LIFE011_EXPERIMENTS,
        "plans": LIFE011_PLANS,
        "primitives": LIFE011_PRIMITIVES,
        "motif_by_experiment": LIFE011_EXPERIMENT_MOTIF,
        "seed_namespace": "life011-primitive-v1",
        "protocol_name": "life-011-protected-curriculum",
        "invariant_limits": (MAX_PREDICTED_RISK, MAX_MOTOR_COST),
        "safety_context": SAFE_CONTEXT,
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _serialize_ramp_audit(
    audit: Mapping[str, Mapping[str, RampAudit]],
) -> dict[str, Any]:
    return {
        cadence: {
            name: asdict(value)
            for name, value in by_plan.items()
        }
        for cadence, by_plan in audit.items()
    }


def _plan_gate() -> tuple[bool, dict[str, Any]]:
    ramp = complementarity_audit()
    plans = {
        plan.primitive: {
            "steps": len(plan.targets_deg),
            "command_cost_deg": plan_command_cost(plan.targets_deg),
            "final_target_deg": plan.targets_deg[-1],
            "minimum_target_deg": min(plan.targets_deg),
            "maximum_target_deg": max(plan.targets_deg),
            "change_count": plan_change_count(plan.targets_deg),
            "digest": plan.digest(),
        }
        for plan in LIFE011_PLANS
    }
    exact = all(
        item["steps"] == 32
        and item["command_cost_deg"] == 480.0
        and item["final_target_deg"] == 90.0
        and item["minimum_target_deg"] >= 30.0
        and item["maximum_target_deg"] <= 150.0
        for item in plans.values()
    )
    return exact and complementarity_gate(ramp), {
        "plans": plans,
        "limited_ramp": _serialize_ramp_audit(ramp),
        "complementarity_realized": complementarity_gate(ramp),
        "plans_digest": plans_digest(),
    }


def run_eligibility_preflight(
    parent: Path,
    *,
    organism,
) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    result: dict[str, Any] = {}
    parent.mkdir(parents=True, exist_ok=True)
    for experiment_id in LIFE011_EXPERIMENTS:
        with tempfile.TemporaryDirectory(
            prefix=f"life011-preflight-{organism.seed}-{experiment_id}-",
            dir=parent,
        ) as temporary:
            with Life010Run(
                Path(temporary) / "run",
                organism=organism,
                run_id=f"preflight-{organism.seed}-{experiment_id}",
                **life011_run_options(),
            ) as run:
                run.run_trial(
                    experiment_id,
                    cycle_index=0,
                    decision={"policy": "eligibility_preflight_first_execution"},
                )
                signals = run.current_signals()[experiment_id]
                proposal = run.kernel.propose_experiment(
                    experiment_id,
                    now_ns=3_000_000_000,
                    signals=signals,
                    safety=SAFE_CONTEXT,
                )
                plan = next(
                    item
                    for item in LIFE011_PLANS
                    if item.primitive == LIFE011_PRIMITIVES[experiment_id]
                )
                if proposal.primitive != plan.primitive:
                    raise AssertionError("LIFE-011 preflight primitive changed")
                if (
                    signals.predicted_risk > MAX_PREDICTED_RISK
                    or signals.motor_cost > MAX_MOTOR_COST
                ):
                    raise AssertionError("LIFE-011 preflight guard failed")
                result[experiment_id] = {
                    "eligible_after_own_history": True,
                    "predicted_risk": signals.predicted_risk,
                    "motor_cost": signals.motor_cost,
                    "primitive": proposal.primitive,
                    "plan_digest": plan.digest(),
                    "command_cost_deg": plan_command_cost(plan.targets_deg),
                }
    return result, time.perf_counter() - started


def _trajectory(
    root: Path,
    *,
    organism,
    private_bank,
    policy_name: str,
    learned: ProgressRidgePolicy,
    diagnostic_masks: Mapping[str, tuple[bool, ...]],
) -> Life010Trajectory:
    return run_life010_trajectory(
        root,
        organism=organism,
        private_bank=private_bank,
        policy_name=policy_name,
        learned=learned,
        policy_names=POLICY_NAMES,
        experiments=LIFE011_EXPERIMENTS,
        motif_by_experiment=LIFE011_EXPERIMENT_MOTIF,
        run_options=life011_run_options(),
        temporary_prefix="life011",
        uniform_seed_namespace="life011-uniform-v1",
        learned_policy_name=LEARNED_POLICY,
        command_cost_deg=PLAN_COST_DEG,
        diagnostic_masks=diagnostic_masks,
    )


def _relative_margin(
    baseline: Life010Trajectory,
    oracle: Life010Trajectory,
    subset: str = "complete",
) -> float:
    if subset == "complete":
        baseline_auc = baseline.auc
        oracle_auc = oracle.auc
    else:
        baseline_auc = normalized_auc(baseline.diagnostic_curves[subset])
        oracle_auc = normalized_auc(oracle.diagnostic_curves[subset])
    return (baseline_auc - oracle_auc) / baseline_auc


def _regime_min(
    margins: np.ndarray,
    organisms,
) -> dict[str, float]:
    return {
        regime: float(
            min(
                margins[index]
                for index, organism in enumerate(organisms)
                if organism.regime == regime
            )
        )
        for regime in (
            "speed_dominant",
            "settling_dominant",
            "friction_dominant",
        )
    }


def _margin_diagnostics(
    organisms,
    banks,
    masks,
    trajectories,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for organism in organisms:
        bank = banks[organism.seed]
        mobile_mask = masks[organism.seed]["mobile"]
        subsets = {
            "complete": tuple(True for _ in bank),
            "mobile": mobile_mask,
            "inert": tuple(not value for value in mobile_mask),
        }
        round_robin = trajectories[organism.seed]["round_robin"]
        oracle = trajectories[organism.seed]["oracle"]
        result[str(organism.seed)] = {
            name: {
                "count": sum(mask),
                "prior_mae": prior_mae(
                    [item for item, selected in zip(bank, mask) if selected]
                ),
                "round_robin_final_mae": (
                    round_robin.final_mae
                    if name == "complete"
                    else round_robin.diagnostic_curves[name][-1]
                ),
                "oracle_margin_vs_round_robin": _relative_margin(
                    round_robin,
                    oracle,
                    name,
                ),
            }
            for name, mask in subsets.items()
        }
    return result


def run_life011_smoke(output: str | Path) -> Mapping[str, Any]:
    """Run only reviewed seeds 18491..18496, with the margin plate first."""

    output_path = Path(output)
    final_report = output_path / "smoke_report.json"
    margin_report = output_path / "margin_plate_report.json"
    if final_report.is_file():
        return json.loads(final_report.read_text(encoding="utf-8"))
    if margin_report.is_file():
        previous = json.loads(margin_report.read_text(encoding="utf-8"))
        if not previous["margin_plate_passed"]:
            return previous
        raise RuntimeError("incomplete LIFE-011 timing plate exists; preserve it")
    if output_path.exists() and any(output_path.iterdir()):
        raise RuntimeError("incomplete LIFE-011 smoke directory exists; preserve it")
    output_path.mkdir(parents=True, exist_ok=True)

    plan_gate, plan_audit = _plan_gate()
    if not plan_gate:
        raise AssertionError("LIFE-011 plan construction gate failed before execution")

    organisms = [sample_life011_organism(seed) for seed in SMOKE_SEEDS]
    regime_counts = Counter(organism.regime for organism in organisms)
    organism_gate = regime_counts == {
        "speed_dominant": 2,
        "settling_dominant": 2,
        "friction_dominant": 2,
    }
    if not organism_gate:
        raise AssertionError("LIFE-011 smoke regimes are not balanced")

    preflight: dict[int, dict[str, Any]] = {}
    preflight_seconds: dict[int, float] = {}
    for organism in organisms:
        values, elapsed = run_eligibility_preflight(
            output_path / "preflight",
            organism=organism,
        )
        preflight[organism.seed] = values
        preflight_seconds[organism.seed] = elapsed

    banks = {}
    bank_seconds: dict[int, float] = {}
    masks: dict[int, dict[str, tuple[bool, ...]]] = {}
    for organism in organisms:
        started = time.perf_counter()
        banks[organism.seed] = build_life011_private_bank(organism)
        bank_seconds[organism.seed] = time.perf_counter() - started
        mobile = private_bank_mobile_mask(organism)
        masks[organism.seed] = {
            "mobile": mobile,
            "inert": tuple(not value for value in mobile),
        }

    empty_policy = ProgressRidgePolicy(alpha=POLICY_ALPHA)
    trajectories: dict[int, dict[str, Life010Trajectory]] = {}
    for organism in organisms:
        trajectories[organism.seed] = {}
        for policy_name in MARGIN_POLICIES:
            trajectories[organism.seed][policy_name] = _trajectory(
                output_path / "margin" / str(organism.seed) / policy_name,
                organism=organism,
                private_bank=banks[organism.seed],
                policy_name=policy_name,
                learned=empty_policy,
                diagnostic_masks=masks[organism.seed],
            )

    greedy_auc = np.asarray(
        [
            trajectories[organism.seed]["greedy_public_residual"].auc
            for organism in organisms
        ]
    )
    round_auc = np.asarray(
        [trajectories[organism.seed]["round_robin"].auc for organism in organisms]
    )
    round_co_primary = float(greedy_auc.mean()) > float(round_auc.mean())
    greedy_margins = np.asarray(
        [
            _relative_margin(
                trajectories[organism.seed]["greedy_public_residual"],
                trajectories[organism.seed]["oracle"],
            )
            for organism in organisms
        ]
    )
    round_margins = np.asarray(
        [
            _relative_margin(
                trajectories[organism.seed]["round_robin"],
                trajectories[organism.seed]["oracle"],
            )
            for organism in organisms
        ]
    )
    progress_ratios = {
        organism.seed: (
            trajectories[organism.seed]["round_robin"].final_mae
            / trajectories[organism.seed]["round_robin"].curve[0]
        )
        for organism in organisms
    }
    gate5 = all(value <= 0.80 for value in progress_ratios.values())
    gate6 = (
        float(np.median(greedy_margins)) >= 0.15
        and min(_regime_min(greedy_margins, organisms).values()) >= 0.05
    )
    gate7 = (
        not round_co_primary
        or (
            float(np.median(round_margins)) >= 0.15
            and min(_regime_min(round_margins, organisms).values()) >= 0.05
        )
    )
    margin_diagnostics = _margin_diagnostics(
        organisms,
        banks,
        masks,
        trajectories,
    )
    oracle_preference = {
        regime: dict(
            Counter(
                choice
                for organism in organisms
                if organism.regime == regime
                for choice in trajectories[organism.seed]["oracle"].choices
            )
        )
        for regime in (
            "speed_dominant",
            "settling_dominant",
            "friction_dominant",
        )
    }
    margin_payload: dict[str, Any] = {
        "schema_version": 1,
        "campaign": "life011-smoke-v1",
        "stage": "margin_plate",
        "seeds": list(SMOKE_SEEDS),
        "plan_audit": plan_audit,
        "organisms": [asdict(organism) for organism in organisms],
        "preflight": {str(key): value for key, value in preflight.items()},
        "constant_signals": {
            "predicted_risk": CONSTANT_PREDICTED_RISK,
            "motor_cost": CONSTANT_MOTOR_COST,
            "zero_variance_scale": 1.0,
        },
        "anchor_decision": {
            "condition": "mean_greedy_auc > mean_round_robin_auc",
            "greedy_mean_auc": float(greedy_auc.mean()),
            "round_robin_mean_auc": float(round_auc.mean()),
            "round_robin_is_co_primary": round_co_primary,
            "primary_baselines": (
                ["greedy_public_residual", "round_robin"]
                if round_co_primary
                else ["greedy_public_residual"]
            ),
        },
        "margin": {
            "greedy_by_seed": {
                str(organism.seed): float(greedy_margins[index])
                for index, organism in enumerate(organisms)
            },
            "greedy_median": float(np.median(greedy_margins)),
            "greedy_regime_min": _regime_min(greedy_margins, organisms),
            "round_robin_by_seed": {
                str(organism.seed): float(round_margins[index])
                for index, organism in enumerate(organisms)
            },
            "round_robin_median": float(np.median(round_margins)),
            "round_robin_regime_min": _regime_min(round_margins, organisms),
            "round_robin_final_to_initial_ratio": {
                str(key): value for key, value in progress_ratios.items()
            },
            "oracle_preferred_plan_by_regime": oracle_preference,
        },
        "mobile_inert_decomposition": margin_diagnostics,
        "trajectories": {
            str(seed): {
                name: asdict(value)
                for name, value in by_policy.items()
            }
            for seed, by_policy in trajectories.items()
        },
        "timing": {
            "preflight_seconds_by_seed": preflight_seconds,
            "private_bank_seconds_by_seed": bank_seconds,
        },
        "margin_gates": {
            "5_round_robin_private_improvement_at_least_20pct_each": gate5,
            "6_oracle_margin_vs_greedy": gate6,
            "7_oracle_margin_vs_round_if_co_primary": gate7,
        },
        "margin_plate_passed": gate5 and gate6 and gate7,
    }
    margin_payload["logical_digest"] = canonical_digest(
        {
            key: value
            for key, value in margin_payload.items()
            if key not in {"timing", "logical_digest"}
        }
    )
    _write_json(margin_report, margin_payload)
    if not margin_payload["margin_plate_passed"]:
        return margin_payload

    teacher_results: dict[int, Life010TeacherResult] = {}
    examples = []
    for organism in organisms:
        teacher = build_life010_teacher(
            output_path / "teacher" / str(organism.seed),
            organism=organism,
            private_bank=banks[organism.seed],
            experiments=LIFE011_EXPERIMENTS,
            motif_by_experiment=LIFE011_EXPERIMENT_MOTIF,
            run_options=life011_run_options(),
            temporary_prefix="life011",
        )
        teacher_results[organism.seed] = teacher
        examples.extend(teacher.examples)
    learned = ProgressRidgePolicy(alpha=POLICY_ALPHA)
    learned.fit(examples)
    replay = ProgressRidgePolicy(alpha=POLICY_ALPHA)
    replay.fit(examples)
    weight_gate = learned.digest() == replay.digest()

    for organism in organisms:
        for policy_name in TIMING_POLICIES:
            trajectories[organism.seed][policy_name] = _trajectory(
                output_path / "timing" / str(organism.seed) / policy_name,
                organism=organism,
                private_bank=banks[organism.seed],
                policy_name=policy_name,
                learned=learned,
                diagnostic_masks=masks[organism.seed],
            )

    exact_counts = all(
        trajectory.main_counts == _expected_counts(24)
        for by_policy in trajectories.values()
        for trajectory in by_policy.values()
    ) and all(
        result.main_counts == _expected_counts(24)
        for result in teacher_results.values()
    )
    branch_replay = all(
        result.replay_bit_identical for result in teacher_results.values()
    )
    protection_integrity = all(
        result.protection_integrity for result in teacher_results.values()
    ) and all(
        trajectory.protection_integrity
        for by_policy in trajectories.values()
        for trajectory in by_policy.values()
    )
    average_bank = float(np.mean(list(bank_seconds.values())))
    average_teacher = float(
        np.mean([result.elapsed_seconds for result in teacher_results.values()])
    )
    average_policy_bundle = float(
        np.mean(
            [
                sum(
                    trajectory.elapsed_seconds
                    for trajectory in trajectories[organism.seed].values()
                )
                for organism in organisms
            ]
        )
    )
    projection_seconds = (
        sum(preflight_seconds.values())
        + 40.0 * (average_bank + average_teacher)
        + 24.0 * (average_bank + average_policy_bundle)
    )
    gates = {
        "1_plans_exact_and_realized_complementarity": plan_gate,
        "2_persistent_eligibility_integrity": all(
            value["eligible_after_own_history"]
            for by_plan in preflight.values()
            for value in by_plan.values()
        ),
        "3_organisms_valid_balanced_without_replacement": organism_gate
        and all(len(bank) == 192 for bank in banks.values()),
        "4_branch_replay_and_counts_exact": branch_replay and exact_counts,
        "5_round_robin_private_improvement_at_least_20pct_each": gate5,
        "6_oracle_margin_vs_greedy": gate6,
        "7_oracle_margin_vs_round_if_co_primary": gate7,
        "8_projection_at_most_90min": projection_seconds <= 5400.0,
        "9_weights_bit_identical": weight_gate,
        "10_prior_and_public_protection_integrity": protection_integrity,
    }
    final_payload = dict(margin_payload)
    final_payload.update(
        {
            "stage": "complete_smoke",
            "policy_digest": learned.digest(),
            "teacher": {
                str(seed): asdict(result)
                for seed, result in teacher_results.items()
            },
            "trajectories": {
                str(seed): {
                    name: asdict(value)
                    for name, value in by_policy.items()
                }
                for seed, by_policy in trajectories.items()
            },
            "timing": {
                **margin_payload["timing"],
                "teacher_seconds_by_seed": {
                    str(seed): result.elapsed_seconds
                    for seed, result in teacher_results.items()
                },
                "projected_campaign_seconds": projection_seconds,
            },
            "gates": gates,
            "smoke_passed": all(gates.values()),
        }
    )
    final_payload["logical_digest"] = canonical_digest(
        {
            key: value
            for key, value in final_payload.items()
            if key not in {"timing", "logical_digest"}
        }
    )
    _write_json(final_report, final_payload)
    return final_payload
