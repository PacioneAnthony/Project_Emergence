"""Two-stage reviewed smoke for LIFE-012."""

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
from learning.life_009 import ProgressRidgePolicy, canonical_digest, normalized_auc
from learning.life_010 import POLICY_ALPHA, prior_prediction
from learning.life_010_campaign import (
    Life010Run,
    Life010TeacherResult,
    Life010Trajectory,
    _expected_counts,
    build_life010_teacher,
    run_life010_trajectory,
)
from learning.life_012 import (
    CONSTANT_MOTOR_COST,
    CONSTANT_PREDICTED_RISK,
    CRITICAL_STEP_DEG,
    CRITICAL_SPEED_DEG_S,
    LIFE012_EXPERIMENT_MOTIF,
    LIFE012_EXPERIMENTS,
    LIFE012_PLANS,
    LIFE012_PRIMITIVES,
    MAX_MOTOR_COST,
    MAX_PREDICTED_RISK,
    PLAN_COST_DEG,
    PLAN_STEPS,
    build_life012_private_bank,
    plan_construction_gate,
    plans_audit,
    plans_digest,
    private_bank_classes,
    prior_mae_or_none,
    sample_life012_organism,
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
SMOKE_SEEDS = tuple(range(18791, 18797))


def build_life012_catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                experiment_id,
                LIFE012_PRIMITIVES[experiment_id],
                max_predicted_risk=MAX_PREDICTED_RISK,
                max_motor_cost=MAX_MOTOR_COST,
                max_proposals_per_session=100,
                metadata={
                    "life012_motif": LIFE012_EXPERIMENT_MOTIF[experiment_id],
                    "command_cost_deg": PLAN_COST_DEG,
                    "plan_steps": PLAN_STEPS,
                    "plans_digest": plans_digest(),
                    "b1_path": "B",
                },
            )
            for experiment_id in LIFE012_EXPERIMENTS
        ]
    )


def build_life012_base_activator() -> PersistentNeedActivator:
    prior = ExperimentSignals(0.5, 0.5, 0.5, 0.5, 0.1, 0.5)
    priors = {name: prior for name in LIFE012_EXPERIMENTS}
    return PersistentNeedActivator(
        (
            CompetenceNeedRoute(
                competence_name="neck_dynamics_residual_prediction_v2",
                cold_start_signals=priors,
                unknown_experiments=LIFE012_EXPERIMENTS,
                learning_experiments=LIFE012_EXPERIMENTS,
                candidate_experiments=LIFE012_EXPERIMENTS,
                regressed_experiments=LIFE012_EXPERIMENTS,
            ),
        )
    )


SAFE_CONTEXT = SafetyContext(
    emergency_stop=False,
    hardware_healthy=True,
    model_update_in_progress=False,
    quota_state="ok",
    allowed_primitives=frozenset(LIFE012_PRIMITIVES.values()),
)


def life012_run_options() -> dict[str, Any]:
    return {
        "catalog_builder": build_life012_catalog,
        "activator_builder": build_life012_base_activator,
        "experiments": LIFE012_EXPERIMENTS,
        "plans": LIFE012_PLANS,
        "primitives": LIFE012_PRIMITIVES,
        "motif_by_experiment": LIFE012_EXPERIMENT_MOTIF,
        "seed_namespace": "life012-primitive-v1",
        "protocol_name": "life-012-protected-curriculum",
        "invariant_limits": (MAX_PREDICTED_RISK, MAX_MOTOR_COST),
        "safety_context": SAFE_CONTEXT,
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_eligibility_preflight(parent: Path, *, organism) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    result: dict[str, Any] = {}
    parent.mkdir(parents=True, exist_ok=True)
    for experiment_id in LIFE012_EXPERIMENTS:
        with tempfile.TemporaryDirectory(
            prefix=f"life012-preflight-{organism.seed}-{experiment_id}-",
            dir=parent,
        ) as temporary:
            with Life010Run(
                Path(temporary) / "run",
                organism=organism,
                run_id=f"preflight-{organism.seed}-{experiment_id}",
                **life012_run_options(),
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
                if proposal.primitive != LIFE012_PRIMITIVES[experiment_id]:
                    raise AssertionError("LIFE-012 preflight primitive changed")
                if (
                    signals.predicted_risk > MAX_PREDICTED_RISK
                    or signals.motor_cost > MAX_MOTOR_COST
                ):
                    raise AssertionError("LIFE-012 preflight guard failed")
                result[experiment_id] = {
                    "eligible_after_own_history": True,
                    "predicted_risk": signals.predicted_risk,
                    "motor_cost": signals.motor_cost,
                    "primitive": proposal.primitive,
                }
    return result, time.perf_counter() - started


def _taxonomy_masks(organism) -> dict[str, tuple[bool, ...]]:
    classes = private_bank_classes(organism)
    result = {
        name: tuple(value == name for value in classes)
        for name in ("ramp", "plateau", "dead_time")
    }
    for repetition in range(2):
        for plan_index, experiment_id in enumerate(LIFE012_EXPERIMENTS):
            start = (repetition * len(LIFE012_EXPERIMENTS) + plan_index) * PLAN_STEPS
            stop = start + PLAN_STEPS
            for class_name in ("ramp", "plateau", "dead_time"):
                key = f"{experiment_id}:{class_name}"
                previous = list(result.get(key, (False,) * len(classes)))
                for index in range(start, stop):
                    previous[index] = classes[index] == class_name
                result[key] = tuple(previous)
    return result


def _trajectory(
    root: Path,
    *,
    organism,
    private_bank,
    policy_name: str,
    learned: ProgressRidgePolicy,
    diagnostic_masks,
) -> Life010Trajectory:
    return run_life010_trajectory(
        root,
        organism=organism,
        private_bank=private_bank,
        policy_name=policy_name,
        learned=learned,
        policy_names=POLICY_NAMES,
        experiments=LIFE012_EXPERIMENTS,
        motif_by_experiment=LIFE012_EXPERIMENT_MOTIF,
        run_options=life012_run_options(),
        temporary_prefix="life012",
        uniform_seed_namespace="life012-uniform-v1",
        learned_policy_name=LEARNED_POLICY,
        command_cost_deg=PLAN_COST_DEG,
        diagnostic_masks=diagnostic_masks,
    )


def _relative_margin(
    baseline: Life010Trajectory,
    oracle: Life010Trajectory,
    subset: str | None = None,
) -> float | None:
    if subset is None:
        baseline_auc = baseline.auc
        oracle_auc = oracle.auc
    else:
        baseline_curve = baseline.diagnostic_curves[subset]
        oracle_curve = oracle.diagnostic_curves[subset]
        if not baseline_curve or not oracle_curve:
            return None
        baseline_auc = normalized_auc(baseline_curve)
        oracle_auc = normalized_auc(oracle_curve)
    return (baseline_auc - oracle_auc) / baseline_auc


def _regime_min(values: np.ndarray, organisms) -> dict[str, float]:
    return {
        regime: float(
            min(
                values[index]
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


def _diagnostics_for_organism(
    organism,
    bank,
    masks,
    round_robin: Life010Trajectory,
    oracle: Life010Trajectory,
) -> dict[str, Any]:
    full_prior = prior_mae_or_none(bank)
    if full_prior is None:
        raise AssertionError("LIFE-012 complete bank cannot be empty")
    result: dict[str, Any] = {
        "cadence_deg_per_step": organism.max_speed_deg_s * 0.02,
        "plateau_available": organism.max_speed_deg_s * 0.02 > CRITICAL_STEP_DEG,
        "critical_speed_deg_s": CRITICAL_SPEED_DEG_S,
        "by_plan_and_class": {},
    }
    for key, mask in masks.items():
        selected = [item for item, include in zip(bank, mask) if include]
        count = len(selected)
        prior_value = prior_mae_or_none(selected)
        final_value = (
            round_robin.diagnostic_curves[key][-1]
            if round_robin.diagnostic_curves[key]
            else None
        )
        prior_mass = (
            None
            if count == 0
            else prior_value * count / (full_prior * len(bank))
        )
        final_mass = (
            None
            if count == 0
            else final_value * count / (round_robin.final_mae * len(bank))
        )
        result["by_plan_and_class"][key] = {
            "count": count,
            "prior_mae": prior_value,
            "round_robin_final_mae": final_value,
            "prior_error_mass_fraction": prior_mass,
            "round_robin_final_error_mass_fraction": final_mass,
            "oracle_margin": _relative_margin(round_robin, oracle, key),
        }
    plateau_mask = masks["plateau"]
    result["plateau_prior_residual_sequence"] = [
        item.next_angle_deg - prior_prediction(item)
        for item, include in zip(bank, plateau_mask)
        if include
    ]
    if result["by_plan_and_class"]["dead_time"]["count"] != 0:
        raise AssertionError("LIFE-012 dead_time diagnostic is not zero")
    return result


def run_life012_smoke(output: str | Path) -> Mapping[str, Any]:
    output_path = Path(output)
    manifest_path = output_path / "protocol_manifest.json"
    margin_path = output_path / "margin_plate_report.json"
    final_path = output_path / "smoke_report.json"
    if final_path.is_file():
        return json.loads(final_path.read_text(encoding="utf-8"))
    if margin_path.is_file():
        previous = json.loads(margin_path.read_text(encoding="utf-8"))
        if not previous["margin_plate_passed"]:
            return previous
        raise RuntimeError("incomplete LIFE-012 final plate exists; preserve it")
    if output_path.exists() and any(output_path.iterdir()):
        raise RuntimeError("incomplete LIFE-012 smoke directory exists; preserve it")
    output_path.mkdir(parents=True, exist_ok=True)

    protocol_manifest = {
        "schema_version": 1,
        "campaign": "life012-smoke-v1",
        "b1_path": "B",
        "plans_digest": plans_digest(),
        "critical_step_deg": CRITICAL_STEP_DEG,
        "critical_speed_deg_s": CRITICAL_SPEED_DEG_S,
        "speed_family_fraction_below_critical": 0.28125,
        "smoke_probability_at_least_one_below_critical": 0.4833984375,
        "test_probability_at_least_one_below_critical": 1.0 - 0.71875**8,
        "seeds": list(SMOKE_SEEDS),
    }
    protocol_manifest["logical_digest"] = canonical_digest(protocol_manifest)
    _write_json(manifest_path, protocol_manifest)

    construction_gate = plan_construction_gate()
    if not construction_gate:
        raise AssertionError("LIFE-012 construction gate failed before simulation")
    organisms = [sample_life012_organism(seed) for seed in SMOKE_SEEDS]
    regime_counts = Counter(item.regime for item in organisms)
    organism_gate = regime_counts == {
        "speed_dominant": 2,
        "settling_dominant": 2,
        "friction_dominant": 2,
    }
    if not organism_gate:
        raise AssertionError("LIFE-012 regimes are not balanced")

    preflight = {}
    preflight_seconds = {}
    for organism in organisms:
        values, elapsed = run_eligibility_preflight(
            output_path / "preflight",
            organism=organism,
        )
        preflight[organism.seed] = values
        preflight_seconds[organism.seed] = elapsed

    banks = {}
    masks = {}
    bank_seconds = {}
    for organism in organisms:
        started = time.perf_counter()
        banks[organism.seed] = build_life012_private_bank(organism)
        bank_seconds[organism.seed] = time.perf_counter() - started
        masks[organism.seed] = _taxonomy_masks(organism)

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
            trajectories[item.seed]["greedy_public_residual"].auc
            for item in organisms
        ]
    )
    round_auc = np.asarray(
        [trajectories[item.seed]["round_robin"].auc for item in organisms]
    )
    co_primary = float(greedy_auc.mean()) > float(round_auc.mean())
    greedy_margins = np.asarray(
        [
            _relative_margin(
                trajectories[item.seed]["greedy_public_residual"],
                trajectories[item.seed]["oracle"],
            )
            for item in organisms
        ],
        dtype=np.float64,
    )
    round_margins = np.asarray(
        [
            _relative_margin(
                trajectories[item.seed]["round_robin"],
                trajectories[item.seed]["oracle"],
            )
            for item in organisms
        ],
        dtype=np.float64,
    )
    progress_ratios = {
        item.seed: (
            trajectories[item.seed]["round_robin"].final_mae
            / trajectories[item.seed]["round_robin"].curve[0]
        )
        for item in organisms
    }
    gate4 = all(value <= 0.80 for value in progress_ratios.values())
    gate5 = (
        float(np.median(greedy_margins)) >= 0.15
        and min(_regime_min(greedy_margins, organisms).values()) >= 0.05
    )
    gate6 = (
        not co_primary
        or (
            float(np.median(round_margins)) >= 0.15
            and min(_regime_min(round_margins, organisms).values()) >= 0.05
        )
    )
    eligibility_gate = all(
        value["eligible_after_own_history"]
        for by_plan in preflight.values()
        for value in by_plan.values()
    ) and all(
        masks[item.seed]["dead_time"].count(True) == 0
        for item in organisms
    )
    diagnostics = {
        str(item.seed): _diagnostics_for_organism(
            item,
            banks[item.seed],
            masks[item.seed],
            trajectories[item.seed]["round_robin"],
            trajectories[item.seed]["oracle"],
        )
        for item in organisms
    }
    margin_gates = {
        "1_plans_and_complementarity": construction_gate,
        "2_eligibility_invariant_and_zero_dead_time": eligibility_gate,
        "3_organisms_balanced_without_replacement": organism_gate
        and all(len(bank) == 192 for bank in banks.values()),
        "4_round_robin_improvement_at_least_20pct_each": gate4,
        "5_oracle_margin_vs_greedy": gate5,
        "6_oracle_margin_vs_round_if_co_primary": gate6,
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "campaign": "life012-smoke-v1",
        "stage": "margin_plate",
        "protocol_manifest": protocol_manifest,
        "plan_audit": plans_audit(),
        "organisms": [asdict(item) for item in organisms],
        "preflight": {str(key): value for key, value in preflight.items()},
        "constant_signals": {
            "predicted_risk": CONSTANT_PREDICTED_RISK,
            "motor_cost": CONSTANT_MOTOR_COST,
            "zero_variance_scale": 1.0,
            "transparent_score_active_terms": [
                "epistemic_gain",
                "learning_progress",
                "0.25*novelty",
                "0.5*controllability",
            ],
        },
        "anchor_decision": {
            "condition": "mean_greedy_auc > mean_round_robin_auc",
            "greedy_mean_auc": float(greedy_auc.mean()),
            "round_robin_mean_auc": float(round_auc.mean()),
            "round_robin_is_co_primary": co_primary,
        },
        "margin": {
            "greedy_by_seed": {
                str(item.seed): float(greedy_margins[index])
                for index, item in enumerate(organisms)
            },
            "greedy_median": float(np.median(greedy_margins)),
            "greedy_regime_min": _regime_min(greedy_margins, organisms),
            "round_robin_by_seed": {
                str(item.seed): float(round_margins[index])
                for index, item in enumerate(organisms)
            },
            "round_robin_median": float(np.median(round_margins)),
            "round_robin_regime_min": _regime_min(round_margins, organisms),
            "round_robin_final_to_initial_ratio": {
                str(key): value for key, value in progress_ratios.items()
            },
            "oracle_preferred_plan_by_regime": {
                regime: dict(
                    Counter(
                        choice
                        for item in organisms
                        if item.regime == regime
                        for choice in trajectories[item.seed]["oracle"].choices
                    )
                )
                for regime in (
                    "speed_dominant",
                    "settling_dominant",
                    "friction_dominant",
                )
            },
        },
        "taxonomy_diagnostics": diagnostics,
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
        "margin_gates": margin_gates,
        "margin_plate_passed": all(margin_gates.values()),
    }
    payload["logical_digest"] = canonical_digest(
        {
            key: value
            for key, value in payload.items()
            if key not in {"timing", "logical_digest"}
        }
    )
    _write_json(margin_path, payload)
    if not payload["margin_plate_passed"]:
        return payload

    teacher_results: dict[int, Life010TeacherResult] = {}
    examples = []
    for organism in organisms:
        result = build_life010_teacher(
            output_path / "teacher" / str(organism.seed),
            organism=organism,
            private_bank=banks[organism.seed],
            experiments=LIFE012_EXPERIMENTS,
            motif_by_experiment=LIFE012_EXPERIMENT_MOTIF,
            run_options=life012_run_options(),
            temporary_prefix="life012",
        )
        teacher_results[organism.seed] = result
        examples.extend(result.examples)
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
        item.main_counts == _expected_counts(24)
        for by_policy in trajectories.values()
        for item in by_policy.values()
    ) and all(
        item.main_counts == _expected_counts(24)
        for item in teacher_results.values()
    )
    replay_gate = all(item.replay_bit_identical for item in teacher_results.values())
    protection_gate = all(
        item.protection_integrity for item in teacher_results.values()
    ) and all(
        item.protection_integrity
        for by_policy in trajectories.values()
        for item in by_policy.values()
    )
    average_bank = float(np.mean(list(bank_seconds.values())))
    average_teacher = float(
        np.mean([item.elapsed_seconds for item in teacher_results.values()])
    )
    average_bundle = float(
        np.mean(
            [
                sum(value.elapsed_seconds for value in trajectories[item.seed].values())
                for item in organisms
            ]
        )
    )
    projection = (
        sum(preflight_seconds.values())
        + 40.0 * (average_bank + average_teacher)
        + 24.0 * (average_bank + average_bundle)
    )
    final_gates = {
        "1_plans_and_complementarity": construction_gate,
        "2_eligibility_invariant_and_zero_dead_time": eligibility_gate,
        "3_organisms_balanced_without_replacement": organism_gate,
        "4_branch_replay_and_counts_exact": replay_gate and exact_counts,
        "5_round_robin_improvement_at_least_20pct_each": gate4,
        "6_oracle_margin_vs_greedy": gate5,
        "7_oracle_margin_vs_round_if_co_primary": gate6,
        "8_projection_at_most_90min": projection <= 5400.0,
        "9_weights_bit_identical": weight_gate,
        "10_prior_and_public_protection_integrity": protection_gate,
    }
    final = dict(payload)
    final.update(
        {
            "stage": "complete_smoke",
            "policy_digest": learned.digest(),
            "teacher": {
                str(seed): asdict(value)
                for seed, value in teacher_results.items()
            },
            "trajectories": {
                str(seed): {
                    name: asdict(value)
                    for name, value in by_policy.items()
                }
                for seed, by_policy in trajectories.items()
            },
            "timing": {
                **payload["timing"],
                "teacher_seconds_by_seed": {
                    str(seed): value.elapsed_seconds
                    for seed, value in teacher_results.items()
                },
                "projected_campaign_seconds": projection,
            },
            "gates": final_gates,
            "smoke_passed": all(final_gates.values()),
        }
    )
    final["logical_digest"] = canonical_digest(
        {
            key: value
            for key, value in final.items()
            if key not in {"timing", "logical_digest"}
        }
    )
    _write_json(final_path, final)
    return final
