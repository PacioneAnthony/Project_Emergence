from __future__ import annotations

import json

import pytest

from cognitive.experiments import SafeExperimentCatalog
from cognitive.kernel import CognitiveKernel
from cognitive.models import (
    CompetenceStatus,
    ExperimentSignals,
    ExperimentSpec,
    SafetyContext,
)
from cognitive.needs import (
    CompetenceNeedRoute,
    NoActiveNeedError,
    PersistentNeedActivator,
)
from sim3d.life_executor import BoundedMujocoExecutor


SERVO_COMPETENCE = "bounded_servo_tracking"
VISUAL_COMPETENCE = "visual_scan_coverage"


def cold_prior(*, epistemic_gain: float) -> ExperimentSignals:
    return ExperimentSignals(
        epistemic_gain=epistemic_gain,
        learning_progress=0.2,
        novelty=0.2,
        controllability=0.5,
        predicted_risk=0.0,
        motor_cost=0.1,
    )


def catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                "diagnose-servo",
                "diagnose_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=20,
            ),
            ExperimentSpec(
                "wide-scan",
                "scan_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=20,
            ),
        ]
    )


def safety() -> SafetyContext:
    return SafetyContext(
        emergency_stop=False,
        hardware_healthy=True,
        model_update_in_progress=False,
        quota_state="ok",
        allowed_primitives=frozenset(
            {"diagnose_bounded_servo", "scan_bounded_servo"}
        ),
    )


def routes() -> tuple[CompetenceNeedRoute, ...]:
    return (
        CompetenceNeedRoute(
            competence_name=SERVO_COMPETENCE,
            cold_start_signals={"diagnose-servo": cold_prior(epistemic_gain=0.9)},
            unknown_experiments=("diagnose-servo",),
            learning_experiments=("diagnose-servo",),
            candidate_experiments=("diagnose-servo",),
            validated_experiments=("diagnose-servo",),
            regressed_experiments=("diagnose-servo",),
        ),
        CompetenceNeedRoute(
            competence_name=VISUAL_COMPETENCE,
            cold_start_signals={"wide-scan": cold_prior(epistemic_gain=0.1)},
            unknown_experiments=("wide-scan",),
            learning_experiments=("wide-scan",),
            candidate_experiments=("wide-scan",),
            regressed_experiments=("wide-scan",),
        ),
    )


def apply_status_assessment(
    kernel: CognitiveKernel,
    *,
    competence_name: str,
    outcome: str,
    digest: str,
    timestamp: int,
) -> None:
    kernel.memory.apply_competence_assessment(
        competence_name,
        experiment_id="routing-fixture",
        outcome=outcome,
        assessed_at_ns=timestamp,
        assessment_digest=digest,
        evidence={"kind": "life006-routing-fixture", "outcome": outcome},
    )


def test_need_route_validation_and_conflicting_priors() -> None:
    with pytest.raises(ValueError, match="prior keys"):
        CompetenceNeedRoute(
            competence_name="missing-prior",
            cold_start_signals={},
            unknown_experiments=("experiment",),
        )
    shared_a = CompetenceNeedRoute(
        competence_name="a",
        cold_start_signals={"shared": cold_prior(epistemic_gain=0.2)},
        unknown_experiments=("shared",),
    )
    shared_b = CompetenceNeedRoute(
        competence_name="b",
        cold_start_signals={"shared": cold_prior(epistemic_gain=0.8)},
        unknown_experiments=("shared",),
    )
    with pytest.raises(ValueError, match="conflicting"):
        PersistentNeedActivator((shared_a, shared_b))


def test_cold_start_candidates_and_need_audit_are_persisted(tmp_path) -> None:
    activator = PersistentNeedActivator(routes())
    with CognitiveKernel(tmp_path / "kernel.sqlite3", catalog=catalog()) as kernel:
        kernel.start_session("needs-cold", started_at_ns=0)
        proposal, activation = activator.select(
            kernel,
            now_ns=1,
            safety=safety(),
        )
        assert activation.urgency == 3
        assert set(activation.candidates) == {"diagnose-servo", "wide-scan"}
        assert proposal.experiment_id == "diagnose-servo"
        for evidence in activation.signal_evidence.values():
            assert evidence["signal_source"]["kind"] == "cold_start_prior"
        row = kernel.memory.proposal(proposal.proposal_id)
        persisted = json.loads(row["rationale_json"])
        source = persisted["selection"]["candidates"]["diagnose-servo"][
            "signal_evidence"
        ]
        assert source["need_activation"]["active_urgency"] == 3
        assert source["signal_source"]["kind"] == "cold_start_prior"


def test_regressed_preempts_unknown_and_suspended_never_activates(tmp_path) -> None:
    activator = PersistentNeedActivator(routes())
    with CognitiveKernel(tmp_path / "kernel.sqlite3", catalog=catalog()) as kernel:
        kernel.start_session("needs-priority", started_at_ns=0)
        apply_status_assessment(
            kernel,
            competence_name=SERVO_COMPETENCE,
            outcome="validated",
            digest="servo-validated",
            timestamp=1,
        )
        after_validation = activator.activate(kernel)
        assert set(after_validation.candidates) == {"wide-scan"}
        assert after_validation.urgency == 3

        apply_status_assessment(
            kernel,
            competence_name=SERVO_COMPETENCE,
            outcome="regressed",
            digest="servo-regressed",
            timestamp=2,
        )
        after_regression = activator.activate(kernel)
        assert set(after_regression.candidates) == {"diagnose-servo"}
        assert after_regression.urgency == 4

        kernel.transition_competence(
            SERVO_COMPETENCE,
            CompetenceStatus.SUSPENDED,
            changed_at_ns=3,
            evidence={"authority": "test-suspension"},
        )
        after_suspension = activator.activate(kernel)
        assert set(after_suspension.candidates) == {"wide-scan"}
        servo_audit = next(
            item
            for item in after_suspension.audit["routes"]
            if item["competence_name"] == SERVO_COMPETENCE
        )
        assert servo_audit["status"] == "excluded_suspended"


def test_no_active_need_writes_no_proposal(tmp_path) -> None:
    empty_route = CompetenceNeedRoute(
        competence_name="no-monitoring",
        cold_start_signals={},
    )
    activator = PersistentNeedActivator((empty_route,))
    with CognitiveKernel(tmp_path / "kernel.sqlite3", catalog=catalog()) as kernel:
        kernel.start_session("needs-empty", started_at_ns=0)
        with pytest.raises(NoActiveNeedError) as error:
            activator.select(kernel, now_ns=1, safety=safety())
        assert error.value.audit["active_urgency"] is None
        count = kernel.memory.connection.execute(
            "SELECT COUNT(*) FROM experiment_proposals"
        ).fetchone()[0]
        assert count == 0


def test_life006_observed_activation_survives_restart_and_routes_state(tmp_path) -> None:
    database_path = tmp_path / "life006.sqlite3"
    data_root = tmp_path / "j0"
    activator = PersistentNeedActivator(routes())
    executor = BoundedMujocoExecutor(data_root)
    life_catalog = catalog()

    kernel = CognitiveKernel(database_path, catalog=life_catalog)
    kernel.start_session("life006-loop", started_at_ns=0)
    first, cold_activation = activator.select(kernel, now_ns=1, safety=safety())
    assert first.experiment_id == "diagnose-servo"
    executor.execute(
        kernel,
        first,
        execution_id="life006-first-diagnose",
        j0_session_id="life006-diagnose-17601",
        seed=17601,
        started_at_ns=2,
        safety=safety(),
    )
    observed_activation = activator.activate(kernel)
    assert set(observed_activation.candidates) == {
        "diagnose-servo",
        "wide-scan",
    }
    assert (
        observed_activation.signal_evidence["diagnose-servo"]["signal_source"][
            "kind"
        ]
        == "observed_history"
    )
    assert (
        observed_activation.signal_evidence["wide-scan"]["signal_source"]["kind"]
        == "cold_start_prior"
    )
    kernel.close()  # Crash-style restart with the cognitive session open.

    with CognitiveKernel(database_path, catalog=life_catalog) as restored:
        replayed_activation = activator.activate(restored)
        assert replayed_activation == observed_activation

        apply_status_assessment(
            restored,
            competence_name=SERVO_COMPETENCE,
            outcome="validated",
            digest="life006-servo-validated",
            timestamp=1_000_000_000,
        )
        visual_need = activator.activate(restored)
        assert set(visual_need.candidates) == {"wide-scan"}
        wide, _ = activator.select(
            restored,
            now_ns=1_000_000_001,
            safety=safety(),
        )
        assert wide.experiment_id == "wide-scan"
        executor.execute(
            restored,
            wide,
            execution_id="life006-wide",
            j0_session_id="life006-wide-17602",
            seed=17602,
            started_at_ns=1_000_000_002,
            safety=safety(),
        )

        apply_status_assessment(
            restored,
            competence_name=SERVO_COMPETENCE,
            outcome="regressed",
            digest="life006-servo-regressed",
            timestamp=2_000_000_000,
        )
        recovery_need = activator.activate(restored)
        assert set(recovery_need.candidates) == {"diagnose-servo"}
        assert recovery_need.urgency == 4
        assert (
            recovery_need.signal_evidence["diagnose-servo"]["signal_source"]["kind"]
            == "observed_history"
        )
        restored.end_session(ended_at_ns=3_000_000_000)
