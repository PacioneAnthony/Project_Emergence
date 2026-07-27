from __future__ import annotations

import sqlite3

import pytest

from cognitive.competence import (
    EXECUTED_TRACKING_METRIC,
    UpperBoundCriterion,
    assess_executed_servo_tracking,
)
from cognitive.development import evaluate_and_apply_executed_competence
from cognitive.experiments import SafeExperimentCatalog
from cognitive.kernel import CognitiveKernel
from cognitive.memory import EpisodicMemory, InvalidCompetenceTransition, SCHEMA_VERSION
from cognitive.models import (
    CompetenceStatus,
    ExperimentSignals,
    ExperimentSpec,
    SafetyContext,
)
from cognitive.observed_signals import ServoTrialSummary
from j0.events import Event
from j0.recorder import SessionRecorder
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig
from sim3d.life_executor import BoundedMujocoExecutor


COMPETENCE = "bounded_servo_tracking"
EXPERIMENT = "diagnose-servo"


def criterion() -> UpperBoundCriterion:
    return UpperBoundCriterion(
        metric_name=EXECUTED_TRACKING_METRIC,
        validation_upper_bound=9.0,
        regression_upper_bound=15.0,
        min_samples=2,
    )


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


def safety() -> SafetyContext:
    return SafetyContext(
        emergency_stop=False,
        hardware_healthy=True,
        model_update_in_progress=False,
        quota_state="ok",
        allowed_primitives=frozenset({"diagnose_bounded_servo"}),
    )


def signals() -> ExperimentSignals:
    return ExperimentSignals(
        epistemic_gain=0.5,
        learning_progress=0.2,
        novelty=0.1,
        controllability=0.8,
        predicted_risk=0.0,
        motor_cost=0.1,
    )


def summary(session_id: str, error_deg: float) -> ServoTrialSummary:
    return ServoTrialSummary(
        experiment_id=EXPERIMENT,
        session_id=session_id,
        source_id="test",
        calibration_version="test-v1",
        event_count=12,
        mean_absolute_error=error_deg / 160.0,
        error_uncertainty=0.0,
        coverage_bins=(1,),
        boundary_exposure=0.0,
        motor_cost=0.1,
        source_digest=(session_id.encode("utf-8").hex() + "0" * 64)[:64],
    )


def propose(kernel: CognitiveKernel, now_ns: int):
    return kernel.propose_experiment(
        EXPERIMENT,
        now_ns=now_ns,
        signals=signals(),
        safety=safety(),
    )


def make_slow_log(root, *, session_id: str, seed: int):
    config = BenchConfig(seed=seed)
    config.servo.max_speed_deg_s = 20.0
    env = BenchHeadEnv(config)
    try:
        env.reset(seed=seed)
        with SessionRecorder(root, session_id=session_id) as recorder:
            for sequence_id in range(12):
                observation = env.step(40.0)
                timestamp_ns = int(round(observation.time * 1e9))
                recorder.append(
                    Event(
                        session_id=session_id,
                        event_type="servo_state",
                        source_id="bench-head-sim",
                        sequence_id=sequence_id,
                        source_timestamp_ns=timestamp_ns,
                        host_receive_timestamp_ns=timestamp_ns,
                        payload={
                            "requested_deg": observation.requested_deg,
                            "as5600_deg": observation.as5600_deg,
                        },
                        quality={"payload_valid": True, "simulation": True},
                        calibration_version="bench-head-v1",
                    )
                )
        return recorder.session_dir
    finally:
        env.close()


def attribute_slow_trial(
    kernel: CognitiveKernel,
    root,
    *,
    label: str,
    seed: int,
    now_ns: int,
) -> None:
    session_dir = make_slow_log(root, session_id=label, seed=seed)
    proposal = propose(kernel, now_ns)
    kernel.begin_experiment_execution(
        proposal.proposal_id,
        execution_id=f"execution-{label}",
        session_dir=session_dir,
        started_at_ns=now_ns + 1,
    )
    kernel.complete_observed_execution(
        f"execution-{label}",
        completed_at_ns=now_ns + 2,
    )


def test_executed_assessment_uses_explicit_latest_window() -> None:
    trials = (
        summary("obsolete-bad", 40.0),
        summary("recent-a", 4.0),
        summary("recent-b", 6.0),
    )
    assessment = assess_executed_servo_tracking(
        trials,
        competence_name=COMPETENCE,
        experiment_id=EXPERIMENT,
        criterion=criterion(),
        window_size=2,
    )
    assert assessment.outcome == "validated"
    assert assessment.source_sessions == ("recent-a", "recent-b")
    assert assessment.assessment.maximum == pytest.approx(6.0)
    assert assessment.evidence_digest() == assessment.evidence_digest()

    with pytest.raises(ValueError, match="requires metric"):
        assess_executed_servo_tracking(
            trials,
            competence_name=COMPETENCE,
            experiment_id=EXPERIMENT,
            criterion=UpperBoundCriterion("other", 9.0, 15.0, 2),
        )
    with pytest.raises(ValueError, match="at least criterion"):
        assess_executed_servo_tracking(
            trials,
            competence_name=COMPETENCE,
            experiment_id=EXPERIMENT,
            criterion=criterion(),
            window_size=1,
        )


def test_assessment_application_is_idempotent_ordered_and_respects_suspension(
    tmp_path,
) -> None:
    with EpisodicMemory(tmp_path / "memory.sqlite3") as memory:
        evidence = {"kind": "test"}
        first = memory.apply_competence_assessment(
            "unknown-skill",
            experiment_id=EXPERIMENT,
            outcome="inconclusive",
            assessed_at_ns=10,
            assessment_digest="inconclusive-digest",
            evidence=evidence,
        )
        replay = memory.apply_competence_assessment(
            "unknown-skill",
            experiment_id=EXPERIMENT,
            outcome="inconclusive",
            assessed_at_ns=99,
            assessment_digest="inconclusive-digest",
            evidence=evidence,
        )
        assert first[0] is True and replay[0] is False
        assert memory.competence_status("unknown-skill") is CompetenceStatus.UNKNOWN
        assert memory.competence_history("unknown-skill") == []
        with pytest.raises(ValueError, match="older"):
            memory.apply_competence_assessment(
                "unknown-skill",
                experiment_id=EXPERIMENT,
                outcome="validated",
                assessed_at_ns=9,
                assessment_digest="older-digest",
                evidence={"kind": "older"},
            )

        memory.transition_competence(
            "suspended-skill",
            CompetenceStatus.SUSPENDED,
            changed_at_ns=1,
            evidence={"authority": "manual"},
        )
        with pytest.raises(InvalidCompetenceTransition, match="explicit"):
            memory.apply_competence_assessment(
                "suspended-skill",
                experiment_id=EXPERIMENT,
                outcome="validated",
                assessed_at_ns=2,
                assessment_digest="suspended-digest",
                evidence={"kind": "blocked"},
            )


def test_life005_acquisition_regression_recovery_and_replay(tmp_path) -> None:
    database_path = tmp_path / "life005.sqlite3"
    data_root = tmp_path / "j0"
    executor = BoundedMujocoExecutor(data_root)
    life_catalog = catalog()

    with CognitiveKernel(database_path, catalog=life_catalog) as kernel:
        kernel.start_session("life005-acquire-regress", started_at_ns=0)
        for index, seed in enumerate((17501, 17502)):
            proposal = propose(kernel, 1_000_000_000 * (index + 1))
            executor.execute(
                kernel,
                proposal,
                execution_id=f"execution-nominal-{seed}",
                j0_session_id=f"nominal-{seed}",
                seed=seed,
                started_at_ns=1_000_000_000 * (index + 1) + 1,
                safety=safety(),
            )
        acquisition = evaluate_and_apply_executed_competence(
            kernel,
            competence_name=COMPETENCE,
            experiment_id=EXPERIMENT,
            criterion=criterion(),
            assessed_at_ns=3_000_000_000,
            window_size=2,
            model_version="analytic-tracking-v1",
        )
        assert acquisition.assessment.outcome == "validated"
        assert acquisition.transition_path == (
            CompetenceStatus.LEARNING,
            CompetenceStatus.CANDIDATE,
            CompetenceStatus.VALIDATED,
        )

        attribute_slow_trial(
            kernel,
            data_root,
            label="slow-17503",
            seed=17503,
            now_ns=4_000_000_000,
        )
        attribute_slow_trial(
            kernel,
            data_root,
            label="slow-17504",
            seed=17504,
            now_ns=5_000_000_000,
        )
        regression = evaluate_and_apply_executed_competence(
            kernel,
            competence_name=COMPETENCE,
            experiment_id=EXPERIMENT,
            criterion=criterion(),
            assessed_at_ns=6_000_000_000,
            window_size=2,
            model_version="analytic-tracking-v1",
        )
        assert regression.assessment.outcome == "regressed"
        assert regression.transition_path == (CompetenceStatus.REGRESSED,)
        kernel.end_session(ended_at_ns=7_000_000_000)

    with CognitiveKernel(database_path, catalog=life_catalog) as restored:
        assert restored.memory.competence_status(COMPETENCE) is CompetenceStatus.REGRESSED
        restored.start_session("life005-recovery", started_at_ns=8_000_000_000)
        for index, seed in enumerate((17505, 17506)):
            proposal = propose(restored, 9_000_000_000 + index * 1_000_000_000)
            executor.execute(
                restored,
                proposal,
                execution_id=f"execution-recovery-{seed}",
                j0_session_id=f"recovery-{seed}",
                seed=seed,
                started_at_ns=9_000_000_001 + index * 1_000_000_000,
                safety=safety(),
            )
        recovery = evaluate_and_apply_executed_competence(
            restored,
            competence_name=COMPETENCE,
            experiment_id=EXPERIMENT,
            criterion=criterion(),
            assessed_at_ns=11_000_000_000,
            window_size=2,
            model_version="analytic-tracking-v1",
        )
        assert recovery.assessment.outcome == "validated"
        assert recovery.transition_path == (
            CompetenceStatus.LEARNING,
            CompetenceStatus.CANDIDATE,
            CompetenceStatus.VALIDATED,
        )
        replay = evaluate_and_apply_executed_competence(
            restored,
            competence_name=COMPETENCE,
            experiment_id=EXPERIMENT,
            criterion=criterion(),
            assessed_at_ns=12_000_000_000,
            window_size=2,
            model_version="analytic-tracking-v1",
        )
        assert replay.applied is False
        assert len(restored.memory.competence_assessments(COMPETENCE)) == 3
        assert [
            row["to_status"]
            for row in restored.memory.competence_history(COMPETENCE)
        ] == [
            "learning",
            "candidate",
            "validated",
            "regressed",
            "learning",
            "candidate",
            "validated",
        ]
        restored.end_session(ended_at_ns=13_000_000_000)

    with CognitiveKernel(database_path, catalog=life_catalog) as final:
        assert final.memory.competence_status(COMPETENCE) is CompetenceStatus.VALIDATED
        database_bytes = database_path.read_bytes()
        assert b"requested_deg" not in database_bytes
        assert b"as5600_deg" not in database_bytes


def test_schema_v2_migrates_to_v3_without_losing_executions(tmp_path) -> None:
    path = tmp_path / "v2.sqlite3"
    with CognitiveKernel(path, catalog=catalog()) as kernel:
        kernel.start_session("migration-v2", started_at_ns=0)
        proposal = propose(kernel, 1)
    connection = sqlite3.connect(path)
    connection.execute("DROP TABLE development_cycles")
    connection.execute("DROP TABLE competence_assessments")
    connection.execute("UPDATE kernel_state SET schema_version = 2")
    connection.execute("UPDATE schema_meta SET version = 2")
    connection.commit()
    connection.close()

    with EpisodicMemory(path) as migrated:
        version = migrated.connection.execute(
            "SELECT version FROM schema_meta WHERE singleton = 1"
        ).fetchone()[0]
        persisted = migrated.proposal(proposal.proposal_id)
        assert version == SCHEMA_VERSION == 4
        assert persisted["experiment_id"] == EXPERIMENT
