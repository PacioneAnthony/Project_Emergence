from __future__ import annotations

import json

import pytest

from cognitive.competence import EXECUTED_TRACKING_METRIC, UpperBoundCriterion
from cognitive.endurance import EnduranceConfig, run_endurance_campaign
from cognitive.experiments import SafeExperimentCatalog
from cognitive.models import ExperimentSignals, ExperimentSpec, SafetyContext
from cognitive.needs import CompetenceNeedRoute, PersistentNeedActivator
from cognitive.supervisor import (
    CompetenceEvaluationRoute,
    DevelopmentCycleRequest,
    PersistentDevelopmentSupervisor,
)
from j0.recorder import QuotaExceededError, QuotaPolicy
from sim3d.life_executor import BoundedMujocoExecutor


COMPETENCE = "bounded_servo_tracking"
EXPERIMENT = "diagnose-servo"


def catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                EXPERIMENT,
                "diagnose_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=100,
            )
        ]
    )


def safety() -> SafetyContext:
    return SafetyContext(
        emergency_stop=False,
        hardware_healthy=True,
        model_update_in_progress=False,
        quota_state="ok",
        allowed_primitives=frozenset({"diagnose_bounded_servo"}),
    )


def supervisor(data_root, *, quota=None) -> PersistentDevelopmentSupervisor:
    prior = ExperimentSignals(
        epistemic_gain=0.9,
        learning_progress=0.2,
        novelty=0.2,
        controllability=0.5,
        predicted_risk=0.0,
        motor_cost=0.1,
    )
    route = CompetenceNeedRoute(
        competence_name=COMPETENCE,
        cold_start_signals={EXPERIMENT: prior},
        unknown_experiments=(EXPERIMENT,),
        learning_experiments=(EXPERIMENT,),
        candidate_experiments=(EXPERIMENT,),
        validated_experiments=(EXPERIMENT,),
        regressed_experiments=(EXPERIMENT,),
    )
    evaluation = CompetenceEvaluationRoute(
        competence_name=COMPETENCE,
        criterion=UpperBoundCriterion(
            EXECUTED_TRACKING_METRIC,
            validation_upper_bound=9.0,
            regression_upper_bound=15.0,
            min_samples=2,
        ),
        window_size=2,
        model_version="analytic-tracking-v1",
    )
    return PersistentDevelopmentSupervisor(
        PersistentNeedActivator((route,)),
        BoundedMujocoExecutor(data_root, quota=quota),
        evaluations={EXPERIMENT: evaluation},
    )


def test_endurance_campaign_covers_fault_matrix_and_is_idempotent(tmp_path) -> None:
    database_path = tmp_path / "endurance.sqlite3"
    data_root = tmp_path / "j0"
    report_path = tmp_path / "report.json"
    config = EnduranceConfig(
        campaign_id="test-endurance",
        session_id="test-endurance-session",
        cycle_count=10,
        seed_start=17891,
        max_database_bytes=2 * 1024 * 1024,
        max_j0_bytes=2 * 1024 * 1024,
        max_mean_combined_bytes_per_cycle=128 * 1024,
    )
    first = run_endurance_campaign(
        database_path,
        data_root,
        catalog=catalog(),
        supervisor=supervisor(data_root),
        safety=safety(),
        config=config,
        report_path=report_path,
    )
    assert all(first.gates.values())
    assert first.counts["complete_cycles"] == 10
    assert first.counts["assessments"] == 9
    assert first.invocation == {
        "restart_count": 8,
        "unsafe_block_count": 2,
        "skipped_complete_cycles": 0,
    }
    assert json.loads(report_path.read_text(encoding="utf-8"))["logical_digest"] == (
        first.logical_digest
    )

    second = run_endurance_campaign(
        database_path,
        data_root,
        catalog=catalog(),
        supervisor=supervisor(data_root),
        safety=safety(),
        config=config,
    )
    assert second.logical_digest == first.logical_digest
    assert second.counts == first.counts
    assert second.invocation["restart_count"] == 0
    assert second.invocation["unsafe_block_count"] == 0
    assert second.invocation["skipped_complete_cycles"] == 10


def test_saturated_quota_leaves_cycle_selected_then_resumes(tmp_path) -> None:
    from cognitive.kernel import CognitiveKernel

    database_path = tmp_path / "quota.sqlite3"
    data_root = tmp_path / "j0"
    data_root.mkdir()
    (data_root / "already-full.bin").write_bytes(b"x" * 100)
    saturated = QuotaPolicy(
        budget_bytes=100,
        warning_bytes=50,
        stop_long_session_bytes=75,
    )
    route_supervisor = supervisor(data_root, quota=saturated)
    cycle_request = DevelopmentCycleRequest(
        cycle_id="quota-cycle",
        execution_id="quota-execution",
        j0_session_id="quota-j0",
        seed=17911,
    )
    life_catalog = catalog()
    with CognitiveKernel(database_path, catalog=life_catalog) as kernel:
        kernel.start_session("quota-session", started_at_ns=0)
        with pytest.raises(QuotaExceededError):
            route_supervisor.advance(
                kernel,
                cycle_request,
                now_ns=1,
                safety=safety(),
            )
        assert kernel.memory.development_cycle("quota-cycle")["status"] == "selected"
        assert kernel.memory.connection.execute(
            "SELECT COUNT(*) FROM experiment_proposals"
        ).fetchone()[0] == 1

        recovered = supervisor(data_root).advance(
            kernel,
            cycle_request,
            now_ns=2,
            safety=safety(),
        )
        assert recovered.status == "complete"
        assert kernel.memory.connection.execute(
            "SELECT COUNT(*) FROM experiment_proposals"
        ).fetchone()[0] == 1
