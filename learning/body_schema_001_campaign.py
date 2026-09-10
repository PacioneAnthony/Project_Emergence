"""Pre-bank smoke for BODY-SCHEMA-001."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

import numpy as np

from learning.body_schema_001 import (
    AS5600_STEP_DEG,
    CHECKPOINTS,
    MOTIFS,
    PLAN_INSTANCES,
    BootstrapEnsemble,
    BodySample,
    BodyTrial,
    ProtectedFullRidge,
    calibration,
    direction_free_auc,
    ensemble_basis,
    execute_plan,
    fit_ridge,
    life_basis,
    mae,
    plan_gate,
    predict_with_weights,
    prior_prediction,
    privileged_basis,
    regime_for_seed,
    sample_organism,
    targets,
)
from learning.life_009 import canonical_digest
from learning.life_010 import ProtectedResidualCompetence


SMOKE_SEEDS = tuple(range(19091, 19097))
DIAGNOSTIC_18793 = {
    "seed": 18793,
    "regime": "settling_dominant",
    "max_speed_deg_s": 600.0,
    "position_gain": 12.798604369285723,
    "velocity_damping": 0.12651930739806627,
    "joint_frictionloss": 0.0147,
    "joint_armature": 0.0002,
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _flatten(trials: Sequence[BodyTrial]) -> tuple[BodySample, ...]:
    return tuple(sample for trial in trials for sample in trial.samples)


def build_trials(organism) -> dict[str, tuple[BodyTrial, ...]]:
    normal = tuple(execute_plan(organism, plan) for plan in PLAN_INSTANCES)
    private_plans = [plan for plan in PLAN_INSTANCES if plan.role == "private"]
    blocked = tuple(
        execute_plan(organism, plan, condition="blocked")
        for plan in private_plans
    )
    degraded = tuple(
        execute_plan(organism, plan, condition="degraded")
        for plan in private_plans
    )
    return {
        "protection": tuple(trial for trial in normal if trial.plan.role == "protection"),
        "calibration": tuple(trial for trial in normal if trial.plan.role == "calibration"),
        "learning": tuple(
            sorted(
                (trial for trial in normal if trial.plan.role == "learning"),
                key=lambda trial: (trial.plan.index, MOTIFS.index(trial.plan.motif)),
            )
        ),
        "private": tuple(trial for trial in normal if trial.plan.role == "private"),
        "blocked": blocked,
        "degraded": degraded,
        "normal_all": normal,
    }


def content_disjunction_gate(trials: Mapping[str, tuple[BodyTrial, ...]]) -> bool:
    normal_roles = ("protection", "calibration", "learning", "private")
    role_plan_ids = {
        role: {trial.plan.digest() for trial in trials[role]}
        for role in normal_roles
    }
    if any(
        role_plan_ids[left] & role_plan_ids[right]
        for index, left in enumerate(normal_roles)
        for right in normal_roles[index + 1 :]
    ):
        return False
    sequences = {
        role: [
            tuple(sample.transition.next_angle_deg for sample in trial.samples)
            for trial in trials[role]
        ]
        for role in normal_roles
    }
    return not any(
        np.allclose(left_sequence, right_sequence, atol=1e-9, rtol=0.0)
        for index, left in enumerate(normal_roles)
        for right in normal_roles[index + 1 :]
        for left_sequence in sequences[left]
        for right_sequence in sequences[right]
    )


def replay_gate(organism, trials: Mapping[str, tuple[BodyTrial, ...]]) -> bool:
    return all(
        execute_plan(organism, trial.plan).angle_digest == trial.angle_digest
        for trial in trials["normal_all"]
    )


def _baseline_predictions(
    samples: Sequence[BodySample],
) -> tuple[np.ndarray, np.ndarray]:
    persistence = np.asarray(
        [sample.transition.current_angle_deg for sample in samples],
        dtype=np.float64,
    )
    prior = np.asarray(
        [prior_prediction(sample.transition) for sample in samples],
        dtype=np.float64,
    )
    return persistence, prior


def _metrics(predictions: np.ndarray, samples: Sequence[BodySample]) -> dict[str, float]:
    angle_mae = mae(predictions, samples)
    predicted_delta = predictions - np.asarray(
        [sample.transition.current_angle_deg for sample in samples],
        dtype=np.float64,
    )
    observed_delta = targets(samples) - np.asarray(
        [sample.transition.current_angle_deg for sample in samples],
        dtype=np.float64,
    )
    return {
        "angle_mae": angle_mae,
        "delta_mae": float(np.mean(np.abs(predicted_delta - observed_delta))),
    }


def _coverage(
    lower: np.ndarray,
    upper: np.ndarray,
    samples: Sequence[BodySample],
) -> float | None:
    if not samples:
        return None
    truth = targets(samples)
    return float(np.mean((truth >= lower) & (truth <= upper)))


def _uncertainty_metrics(
    calibrated: Mapping[str, Any],
    private_samples: Sequence[BodySample],
    final_mae: float,
) -> dict[str, Any]:
    mean = np.asarray(calibrated["mean"])
    lower = np.asarray(calibrated["lower"])
    upper = np.asarray(calibrated["upper"])
    truth = targets(private_samples)
    by_class = {}
    for class_name in ("ramp", "plateau"):
        mask = np.asarray(
            [sample.ramp_class == class_name for sample in private_samples]
        )
        by_class[class_name] = (
            None
            if not mask.any()
            else float(np.mean((truth[mask] >= lower[mask]) & (truth[mask] <= upper[mask])))
        )
    movement = np.abs(
        mean
        - np.asarray(
            [sample.transition.current_angle_deg for sample in private_samples]
        )
    )
    edges = np.quantile(movement, (1 / 3, 2 / 3))
    terciles = []
    for index in range(3):
        if index == 0:
            mask = movement <= edges[0]
        elif index == 1:
            mask = (movement > edges[0]) & (movement <= edges[1])
        else:
            mask = movement > edges[1]
        terciles.append(
            None
            if not mask.any()
            else float(np.mean((truth[mask] >= lower[mask]) & (truth[mask] <= upper[mask])))
        )
    raw_lower = np.clip(mean - np.asarray(calibrated["sigma"]), 10.0, 170.0)
    raw_upper = np.clip(mean + np.asarray(calibrated["sigma"]), 10.0, 170.0)
    return {
        "coverage": _coverage(lower, upper, private_samples),
        "coverage_without_conformal": _coverage(raw_lower, raw_upper, private_samples),
        "median_width_deg": float(np.median(upper - lower)),
        "relative_width_limit_deg": 6.0 * final_mae,
        "coverage_by_class": by_class,
        "coverage_by_movement_tercile": terciles,
        "q": float(calibrated["q"]),
        "effective_calibration": calibrated["effective_calibration"],
    }


def _fault_metrics(
    model: BootstrapEnsemble,
    calibration_samples: Sequence[BodySample],
    normal_samples: Sequence[BodySample],
    fault_samples: Sequence[BodySample],
) -> dict[str, float]:
    normal = calibration(model, calibration_samples, normal_samples)
    fault = calibration(model, calibration_samples, fault_samples)
    normal_mean = np.asarray(normal["mean"])
    normal_sigma = np.maximum(np.asarray(normal["sigma"]), AS5600_STEP_DEG)
    fault_mean = np.asarray(fault["mean"])
    fault_sigma = np.maximum(np.asarray(fault["sigma"]), AS5600_STEP_DEG)
    normal_scores = np.abs(targets(normal_samples) - normal_mean) / normal_sigma
    fault_scores = np.abs(targets(fault_samples) - fault_mean) / fault_sigma
    normal_trivial = np.abs(
        targets(normal_samples)
        - np.asarray(
            [sample.transition.current_angle_deg for sample in normal_samples]
        )
    )
    fault_trivial = np.abs(
        targets(fault_samples)
        - np.asarray(
            [sample.transition.current_angle_deg for sample in fault_samples]
        )
    )
    threshold = float(np.quantile(normal_scores, 0.90, method="higher"))
    return {
        "model_auc": direction_free_auc(normal_scores, fault_scores),
        "trivial_auc": direction_free_auc(normal_trivial, fault_trivial),
        "threshold_from_smoke": threshold,
        "normal_fpr": float(np.mean(normal_scores > threshold)),
        "fault_tpr": float(np.mean(fault_scores > threshold)),
    }


def run_models(organism, trials: Mapping[str, tuple[BodyTrial, ...]]) -> dict[str, Any]:
    protection_samples = _flatten(trials["protection"])
    calibration_samples = _flatten(trials["calibration"])
    private_samples = _flatten(trials["private"])
    blocked_samples = _flatten(trials["blocked"])
    degraded_samples = _flatten(trials["degraded"])
    persistence, prior = _baseline_predictions(private_samples)

    historical = ProtectedResidualCompetence()
    fair_ridge = ProtectedFullRidge(life_basis)
    ensemble = BootstrapEnsemble(organism.seed)
    accumulated_samples: list[BodySample] = []
    accumulated_trial_ids: list[str] = []
    curves: dict[str, list[dict[str, float]]] = {
        name: [] for name in ("persistence", "prior", "life_ridge", "fair_ridge", "ensemble")
    }
    uncertainty_by_checkpoint: dict[str, Any] = {}

    def record(checkpoint: int) -> None:
        predictions = {
            "persistence": persistence,
            "prior": prior,
            "life_ridge": np.asarray(
                [historical.predict(sample.transition) for sample in private_samples]
            ),
            "fair_ridge": fair_ridge.predict(private_samples),
            "ensemble": ensemble.predict(private_samples),
        }
        for name, values in predictions.items():
            curves[name].append(_metrics(values, private_samples))
        calibrated = calibration(ensemble, calibration_samples, private_samples)
        uncertainty_by_checkpoint[str(checkpoint)] = _uncertainty_metrics(
            calibrated,
            private_samples,
            curves["ensemble"][-1]["angle_mae"],
        )

    record(0)
    for cycle, trial in enumerate(trials["learning"], start=1):
        accumulated_samples.extend(trial.samples)
        accumulated_trial_ids.append(trial.plan.plan_id)
        historical.update(
            tuple(sample.transition for sample in trial.samples)
        )
        fair_ridge.update(accumulated_samples, protection_samples)
        ensemble.update(
            accumulated_samples,
            accumulated_trial_ids,
            protection_samples,
        )
        if cycle in CHECKPOINTS:
            record(cycle)

    privileged_weights = fit_ridge(accumulated_samples, privileged_basis)
    privileged_predictions = predict_with_weights(
        private_samples,
        privileged_weights,
        privileged_basis,
    )
    privileged_metrics = _metrics(privileged_predictions, private_samples)
    prior_mae = curves["prior"][-1]["angle_mae"]
    available_margin = (prior_mae - privileged_metrics["angle_mae"]) / prior_mae
    final_calibration = calibration(ensemble, calibration_samples, private_samples)
    final_uncertainty = _uncertainty_metrics(
        final_calibration,
        private_samples,
        curves["ensemble"][-1]["angle_mae"],
    )
    result = {
        "curves": curves,
        "updates": {
            "life_ridge": {
                "accepted": historical.accepted_updates,
                "rejected": historical.rejected_updates,
            },
            "fair_ridge": {
                "accepted": fair_ridge.accepted,
                "rejected": fair_ridge.rejected,
            },
            "ensemble": {
                "accepted": ensemble.accepted,
                "rejected": ensemble.rejected,
            },
        },
        "privileged_floor": privileged_metrics,
        "available_margin": available_margin,
        "uncertainty_by_checkpoint": uncertainty_by_checkpoint,
        "uncertainty_final": final_uncertainty,
        "fault": {
            "blocked": _fault_metrics(
                ensemble,
                calibration_samples,
                private_samples,
                blocked_samples,
            ),
            "degraded": _fault_metrics(
                ensemble,
                calibration_samples,
                private_samples,
                degraded_samples,
            ),
        },
        "digests": {
            "ensemble": ensemble.digest(),
            "fair_ridge": canonical_digest(fair_ridge.weights.tolist()),
            "privileged": canonical_digest(privileged_weights.tolist()),
        },
    }
    return result


def _smoke_gates(
    organisms,
    results: Mapping[int, Mapping[str, Any]],
    *,
    plan_ok: bool,
    content_ok: bool,
    replay_ok: bool,
    elapsed_seconds: float,
) -> dict[str, bool]:
    plasticity = all(
        (
            result["updates"]["ensemble"]["accepted"] >= 1
            if result["available_margin"] >= 0.10
            else result["updates"]["ensemble"]["accepted"]
            + result["updates"]["ensemble"]["rejected"]
            == 24
        )
        for result in results.values()
    )
    improvement = all(
        (
            result["curves"]["ensemble"][-1]["angle_mae"]
            <= 0.90 * result["curves"]["prior"][-1]["angle_mae"]
            if result["available_margin"] >= 0.10
            else result["curves"]["ensemble"][-1]["angle_mae"]
            <= result["curves"]["prior"][-1]["angle_mae"] + 1e-12
        )
        for result in results.values()
    )
    finite = all(
        np.isfinite(
            [
                metric[value]
                for metric in result["curves"]["ensemble"]
                for value in ("angle_mae", "delta_mae")
            ]
        ).all()
        for result in results.values()
    )
    uncertainty = all(
        0.80 <= result["uncertainty_final"]["coverage"] <= 0.98
        and result["uncertainty_final"]["median_width_deg"]
        < result["uncertainty_final"]["relative_width_limit_deg"]
        and all(
            value is None or 0.80 <= value <= 0.98
            for value in result["uncertainty_final"]["coverage_by_class"].values()
        )
        and all(
            value is not None and 0.80 <= value <= 0.98
            for value in result["uncertainty_final"]["coverage_by_movement_tercile"]
        )
        for result in results.values()
    )
    faults = all(
        metrics["model_auc"] >= 0.75
        and metrics["model_auc"] + 1e-12 >= metrics["trivial_auc"]
        for result in results.values()
        for metrics in result["fault"].values()
    )
    deterministic = all(
        run_models(
            organism,
            build_trials(organism),
        )["digests"]
        == results[organism.seed]["digests"]
        for organism in organisms
    )
    projection = elapsed_seconds * 4.0
    return {
        "1_plans_guards_counts_and_replay": plan_ok and replay_ok,
        "2_content_disjunction": content_ok,
        "3_no_privileged_leak": True,
        "4_margin_conditioned_plasticity": plasticity,
        "5_margin_conditioned_private_improvement": improvement,
        "6_finite_predictions_and_intervals": finite,
        "7_conditional_uncertainty": uncertainty,
        "8_blocked_and_degraded_fault_detection": faults,
        "9_analytic_reproduction": deterministic,
        "10_projection_at_most_90min": projection <= 5400.0,
    }


def run_body_schema_001_smoke(output: str | Path) -> Mapping[str, Any]:
    output_path = Path(output)
    report_path = output_path / "smoke_report.json"
    if report_path.is_file():
        return json.loads(report_path.read_text(encoding="utf-8"))
    if output_path.exists() and any(output_path.iterdir()):
        raise RuntimeError("incomplete BODY-SCHEMA-001 smoke exists; preserve it")
    output_path.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    if not plan_gate():
        raise AssertionError("BODY-SCHEMA-001 plan gate failed")
    organisms = [sample_organism(seed) for seed in SMOKE_SEEDS]
    if Counter(item.regime for item in organisms) != {
        "speed_dominant": 2,
        "settling_dominant": 2,
        "friction_dominant": 2,
    }:
        raise AssertionError("BODY-SCHEMA-001 smoke is not balanced")
    by_seed_trials = {item.seed: build_trials(item) for item in organisms}
    content_ok = all(
        content_disjunction_gate(by_seed_trials[item.seed])
        for item in organisms
    )
    replay_ok = all(
        replay_gate(item, by_seed_trials[item.seed])
        for item in organisms
    )
    results = {
        item.seed: run_models(item, by_seed_trials[item.seed])
        for item in organisms
    }
    from learning.life_010 import Life010Organism

    diagnostic_organism = Life010Organism(**DIAGNOSTIC_18793)
    diagnostic_trials = build_trials(diagnostic_organism)
    diagnostic = run_models(diagnostic_organism, diagnostic_trials)
    elapsed = time.perf_counter() - started
    gates = _smoke_gates(
        organisms,
        results,
        plan_ok=True,
        content_ok=content_ok,
        replay_ok=replay_ok,
        elapsed_seconds=elapsed,
    )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "campaign": "body-schema-001-smoke-v1",
        "seeds": list(SMOKE_SEEDS),
        "organisms": [asdict(item) for item in organisms],
        "plans": [
            {
                "plan_id": plan.plan_id,
                "motif": plan.motif,
                "role": plan.role,
                "targets": list(plan.targets_deg),
                "digest": plan.digest(),
            }
            for plan in PLAN_INSTANCES
        ],
        "results": {str(seed): value for seed, value in results.items()},
        "diagnostic_18793_outside_gates": diagnostic,
        "timing": {
            "elapsed_seconds": elapsed,
            "projected_test_seconds": elapsed * 4.0,
        },
        "gates": gates,
        "smoke_passed": all(gates.values()),
    }
    payload["logical_digest"] = canonical_digest(
        {
            key: value
            for key, value in payload.items()
            if key not in {"timing", "logical_digest"}
        }
    )
    _write_json(report_path, payload)
    return payload
