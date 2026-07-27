from __future__ import annotations

import json
import sqlite3

import pytest

from cognitive.competence import EXECUTED_TRACKING_METRIC, UpperBoundCriterion
from cognitive.experiments import ExperimentSelectionBlockedError, SafeExperimentCatalog
from cognitive.kernel import CognitiveKernel
from cognitive.memory import EpisodicMemory, SCHEMA_VERSION
from cognitive.models import ExperimentSignals, ExperimentSpec, SafetyContext
from cognitive.needs import CompetenceNeedRoute, PersistentNeedActivator
from cognitive.supervisor import (
    CompetenceEvaluationRoute,
    CycleRecoveryError,
    DevelopmentCycleRequest,
    PersistentDevelopmentSupervisor,
)
from j0.events import Event
from j0.recorder import SessionRecorder
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
                max_proposals_per_session=20,
            )
        ]
    )


def safety(**overrides) -> SafetyContext:
    values = {
        "emergency_stop": False,
        "hardware_healthy": True,
        "model_update_in_progress": False,
        "quota_state": "ok",
        "allowed_primitives": frozenset({"diagnose_bounded_servo"}),
    }
    values.update(overrides)
    return SafetyContext(**values)


def supervisor(data_root) -> PersistentDevelopmentSupervisor:
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
        BoundedMujocoExecutor(data_root),
        evaluations={EXPERIMENT: evaluation},
    )


def request(label: str, seed: int) -> DevelopmentCycleRequest:
    return DevelopmentCycleRequest(
        cycle_id=f"cycle-{label}",
        execution_id=f"execution-{label}",
        j0_session_id=f"j0-{label}",
        seed=seed,
    )


def test_supervisor_resumes_selection_execution_and_assessment_boundaries(
    tmp_path,
) -> None:
    database_path = tmp_path / "supervisor.sqlite3"
    life_catalog = catalog()
    manager = supervisor(tmp_path / "j0")
    first_request = request("selected", 17701)

    kernel = CognitiveKernel(database_path, catalog=life_catalog)
    kernel.start_session("supervised-session", started_at_ns=0)
    selected = manager.advance(
        kernel,
        first_request,
        now_ns=1_000_000_000,
        safety=safety(),
        stop_after="selected",
    )
    assert selected.status == "selected"
    assert kernel.memory.connection.execute(
        "SELECT COUNT(*) FROM experiment_proposals"
    ).fetchone()[0] == 1
    with pytest.raises(RuntimeError, match="active development cycle"):
        kernel.end_session(ended_at_ns=1_000_000_001)
    kernel.close()

    with CognitiveKernel(database_path, catalog=life_catalog) as restored:
        first_complete = manager.advance(
            restored,
            first_request,
            now_ns=2_000_000_000,
            safety=safety(),
        )
        assert first_complete.status == "complete"
        assert first_complete.result["assessment_status"] == "insufficient_history"
        repeated = manager.advance(
            restored,
            first_request,
            now_ns=3_000_000_000,
            safety=safety(),
        )
        assert repeated == first_complete
        assert restored.memory.connection.execute(
            "SELECT COUNT(*) FROM experiment_proposals"
        ).fetchone()[0] == 1

        second_request = request("executed", 17702)
        executed = manager.advance(
            restored,
            second_request,
            now_ns=4_000_000_000,
            safety=safety(),
            stop_after="executed",
        )
        assert executed.status == "executed"
        restored.close()

    with CognitiveKernel(database_path, catalog=life_catalog) as assessed:
        pending = manager.advance(
            assessed,
            second_request,
            now_ns=5_000_000_000,
            safety=safety(),
            stop_after="assessment_applied",
        )
        assert pending.status == "assessment_applied_pending_cycle_commit"
        assert pending.result["application_was_new"] is True
        assert len(assessed.memory.competence_history(COMPETENCE)) == 3
        assessed.close()

    with CognitiveKernel(database_path, catalog=life_catalog) as final:
        completed = manager.advance(
            final,
            second_request,
            now_ns=6_000_000_000,
            safety=safety(),
        )
        assert completed.status == "complete"
        assert completed.result["application_was_new"] is False
        assert len(final.memory.competence_history(COMPETENCE)) == 3
        assert len(final.memory.competence_assessments(COMPETENCE)) == 1
        assert final.memory.connection.execute(
            "SELECT COUNT(*) FROM experiment_executions"
        ).fetchone()[0] == 2
        with pytest.raises(ValueError, match="identity collision"):
            manager.advance(
                final,
                DevelopmentCycleRequest(
                    cycle_id=second_request.cycle_id,
                    execution_id="changed-execution",
                    j0_session_id=second_request.j0_session_id,
                    seed=second_request.seed,
                ),
                now_ns=7_000_000_000,
                safety=safety(),
            )
        final.end_session(ended_at_ns=8_000_000_000)


def test_unsafe_resume_leaves_selected_cycle_recoverable(tmp_path) -> None:
    database_path = tmp_path / "unsafe.sqlite3"
    manager = supervisor(tmp_path / "j0")
    cycle_request = request("unsafe", 17711)
    with CognitiveKernel(database_path, catalog=catalog()) as kernel:
        kernel.start_session("unsafe-session", started_at_ns=0)
        manager.advance(
            kernel,
            cycle_request,
            now_ns=1,
            safety=safety(),
            stop_after="selected",
        )
        with pytest.raises(RuntimeError, match="emergency_stop"):
            manager.advance(
                kernel,
                cycle_request,
                now_ns=2,
                safety=safety(emergency_stop=True),
            )
        assert kernel.memory.development_cycle(cycle_request.cycle_id)["status"] == "selected"
        recovered = manager.advance(
            kernel,
            cycle_request,
            now_ns=3,
            safety=safety(),
        )
        assert recovered.status == "complete"


def test_partial_execution_is_aborted_instead_of_resumed(tmp_path) -> None:
    database_path = tmp_path / "partial.sqlite3"
    data_root = tmp_path / "j0"
    manager = supervisor(data_root)
    cycle_request = request("partial", 17721)
    with CognitiveKernel(database_path, catalog=catalog()) as kernel:
        kernel.start_session("partial-session", started_at_ns=0)
        selected = manager.advance(
            kernel,
            cycle_request,
            now_ns=1,
            safety=safety(),
            stop_after="selected",
        )
        recorder = SessionRecorder(data_root, session_id=cycle_request.j0_session_id)
        recorder.append(
            Event(
                session_id=cycle_request.j0_session_id,
                event_type="servo_state",
                source_id="bench-head-sim",
                sequence_id=0,
                source_timestamp_ns=2,
                host_receive_timestamp_ns=2,
                payload={"requested_deg": 40.0, "as5600_deg": 89.0},
                quality={"payload_valid": True},
                calibration_version="bench-head-v1",
            )
        )
        kernel.begin_experiment_execution(
            selected.proposal_id,
            execution_id=cycle_request.execution_id,
            session_dir=recorder.session_dir,
            started_at_ns=2,
        )
        # Simulate a dead recorder process without an orderly manifest update.
        recorder._events_file.close()
        recorder._events_file = None
        recorder._closed = True

        with pytest.raises(CycleRecoveryError, match="cannot be resumed"):
            manager.advance(
                kernel,
                cycle_request,
                now_ns=3,
                safety=safety(),
            )
        assert kernel.memory.development_cycle(cycle_request.cycle_id)["status"] == "aborted"
        assert kernel.memory.experiment_execution(cycle_request.execution_id)["status"] == "aborted"
        proposal = kernel.memory.proposal(selected.proposal_id)
        assert proposal["status"] == "cancelled"
        manifest = json.loads(
            (recorder.session_dir / "manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["status"] == "aborted"


def test_selection_block_creates_neither_cycle_nor_proposal(tmp_path) -> None:
    manager = supervisor(tmp_path / "j0")
    with CognitiveKernel(tmp_path / "blocked.sqlite3", catalog=catalog()) as kernel:
        kernel.start_session("blocked-session", started_at_ns=0)
        with pytest.raises(ExperimentSelectionBlockedError):
            manager.advance(
                kernel,
                request("blocked", 17731),
                now_ns=1,
                safety=safety(emergency_stop=True),
            )
        assert kernel.memory.development_cycle("cycle-blocked") is None
        assert kernel.memory.connection.execute(
            "SELECT COUNT(*) FROM experiment_proposals"
        ).fetchone()[0] == 0


def test_schema_v3_migrates_to_v4_without_losing_competence(tmp_path) -> None:
    path = tmp_path / "v3.sqlite3"
    with CognitiveKernel(path, catalog=catalog()) as kernel:
        kernel.start_session("migration-v3", started_at_ns=0)
        kernel.memory.apply_competence_assessment(
            COMPETENCE,
            experiment_id=EXPERIMENT,
            outcome="inconclusive",
            assessed_at_ns=1,
            assessment_digest="migration-assessment",
            evidence={"kind": "migration"},
        )
    connection = sqlite3.connect(path)
    connection.execute("DROP TABLE development_cycles")
    connection.execute("UPDATE kernel_state SET schema_version = 3")
    connection.execute("UPDATE schema_meta SET version = 3")
    connection.commit()
    connection.close()

    with EpisodicMemory(path) as migrated:
        version = migrated.connection.execute(
            "SELECT version FROM schema_meta WHERE singleton = 1"
        ).fetchone()[0]
        assert version == SCHEMA_VERSION == 4
        assert len(migrated.competence_assessments(COMPETENCE)) == 1
        assert migrated.development_cycle("absent") is None
