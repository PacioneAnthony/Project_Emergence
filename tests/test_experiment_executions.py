from __future__ import annotations

import json
import sqlite3

import pytest

from cognitive.experiments import SafeExperimentCatalog
from cognitive.kernel import CognitiveKernel
from cognitive.memory import EpisodicMemory, SCHEMA_VERSION
from cognitive.models import ExperimentSignals, ExperimentSpec, SafetyContext
from cognitive.observed_signals import ObservedSignalEstimator
from j0.events import Event
from j0.recorder import SessionRecorder
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig


def execution_catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                "diagnose-servo",
                "diagnose_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=10,
            ),
            ExperimentSpec(
                "wide-scan",
                "scan_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=10,
            ),
        ]
    )


def safe_context() -> SafetyContext:
    return SafetyContext(
        emergency_stop=False,
        hardware_healthy=True,
        model_update_in_progress=False,
        quota_state="ok",
        allowed_primitives=frozenset(
            {"diagnose_bounded_servo", "scan_bounded_servo"}
        ),
    )


def authorization_signals() -> ExperimentSignals:
    return ExperimentSignals(
        epistemic_gain=0.5,
        learning_progress=0.2,
        novelty=0.1,
        controllability=0.8,
        predicted_risk=0.0,
        motor_cost=0.1,
    )


def append_bench_events(
    recorder: SessionRecorder,
    env: BenchHeadEnv,
    targets: list[float],
    *,
    sequence_offset: int = 0,
) -> None:
    for local_sequence, target in enumerate(targets):
        observation = env.step(target)
        timestamp_ns = int(round(observation.time * 1e9))
        recorder.append(
            Event(
                session_id=recorder.session_id,
                event_type="servo_state",
                source_id="bench-head-sim",
                sequence_id=sequence_offset + local_sequence,
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


def make_complete_log(
    root,
    *,
    session_id: str,
    seed: int,
    targets: list[float],
    max_speed_deg_s: float,
):
    config = BenchConfig(seed=seed)
    config.servo.max_speed_deg_s = max_speed_deg_s
    env = BenchHeadEnv(config)
    try:
        env.reset(seed=seed)
        with SessionRecorder(root, session_id=session_id) as recorder:
            append_bench_events(recorder, env, targets)
        return recorder.session_dir
    finally:
        env.close()


def authorize_and_complete(
    kernel: CognitiveKernel,
    *,
    experiment_id: str,
    execution_id: str,
    session_dir,
    now_ns: int,
):
    proposal = kernel.propose_experiment(
        experiment_id,
        now_ns=now_ns,
        signals=authorization_signals(),
        safety=safe_context(),
    )
    kernel.begin_experiment_execution(
        proposal.proposal_id,
        execution_id=execution_id,
        session_dir=session_dir,
        started_at_ns=now_ns + 1,
    )
    summary = kernel.complete_observed_execution(
        execution_id,
        completed_at_ns=now_ns + 2,
    )
    return proposal, summary


def test_execution_attribution_guards_and_atomic_statuses(tmp_path) -> None:
    session_dir = make_complete_log(
        tmp_path / "j0",
        session_id="j0-one",
        seed=17301,
        targets=[60.0] * 4,
        max_speed_deg_s=600.0,
    )
    with CognitiveKernel(
        tmp_path / "kernel.sqlite3", catalog=execution_catalog()
    ) as kernel:
        kernel.start_session("cognitive-a", started_at_ns=0)
        first = kernel.propose_experiment(
            "diagnose-servo",
            now_ns=10,
            signals=authorization_signals(),
            safety=safe_context(),
        )
        second = kernel.propose_experiment(
            "wide-scan",
            now_ns=11,
            signals=authorization_signals(),
            safety=safe_context(),
        )
        with pytest.raises(ValueError, match="invalid direct"):
            kernel.memory.set_proposal_status(first.proposal_id, "executed")
        kernel.begin_experiment_execution(
            first.proposal_id,
            execution_id="execution-one",
            session_dir=session_dir,
            started_at_ns=12,
        )
        with pytest.raises(RuntimeError, match="running execution"):
            kernel.end_session(ended_at_ns=13)
        with pytest.raises(ValueError, match="running execution"):
            kernel.memory.set_proposal_status(first.proposal_id, "cancelled")
        kernel.begin_experiment_execution(
            first.proposal_id,
            execution_id="execution-one",
            session_dir=session_dir,
            started_at_ns=12,
        )
        with pytest.raises(ValueError, match="already attributed"):
            kernel.begin_experiment_execution(
                second.proposal_id,
                execution_id="execution-two",
                session_dir=session_dir,
                started_at_ns=13,
            )
        with pytest.raises(ValueError, match="does not match execution"):
            kernel.memory.complete_experiment_execution(
                "execution-one",
                completed_at_ns=14,
                experiment_id="wide-scan",
                j0_session_id="j0-one",
                source_digest="a" * 64,
                result_summary={"wrong": True},
            )
        row = kernel.memory.experiment_execution("execution-one")
        assert row["status"] == "running"
        summary = kernel.complete_observed_execution(
            "execution-one", completed_at_ns=15
        )
        kernel.complete_observed_execution("execution-one", completed_at_ns=15)
        row = kernel.memory.experiment_execution("execution-one")
        proposal_status = kernel.memory.connection.execute(
            "SELECT status FROM experiment_proposals WHERE proposal_id = ?",
            (first.proposal_id,),
        ).fetchone()["status"]
        assert row["status"] == "complete"
        assert row["source_digest"] == summary.source_digest
        assert proposal_status == "executed"


def test_life003_rebuilds_histories_after_restart_and_drives_choice(tmp_path) -> None:
    database_path = tmp_path / "life003.sqlite3"
    data_root = tmp_path / "j0"
    catalog = execution_catalog()

    # Start the first attributed trial, then lose and restore the cognitive process.
    slow_config = BenchConfig(seed=17311)
    slow_config.servo.max_speed_deg_s = 20.0
    slow_env = BenchHeadEnv(slow_config)
    slow_env.reset(seed=17311)
    slow_recorder = SessionRecorder(data_root, session_id="diagnose-old")
    append_bench_events(slow_recorder, slow_env, [40.0] * 4)
    kernel = CognitiveKernel(database_path, catalog=catalog)
    kernel.start_session("life003-cycle", started_at_ns=0)
    proposal = kernel.propose_experiment(
        "diagnose-servo",
        now_ns=10,
        signals=authorization_signals(),
        safety=safe_context(),
    )
    kernel.begin_experiment_execution(
        proposal.proposal_id,
        execution_id="exec-diagnose-old",
        session_dir=slow_recorder.session_dir,
        started_at_ns=11,
    )
    with pytest.raises(ValueError, match="log is not complete"):
        kernel.complete_observed_execution(
            "exec-diagnose-old", completed_at_ns=12
        )
    kernel.close()
    append_bench_events(
        slow_recorder,
        slow_env,
        [40.0] * 8,
        sequence_offset=4,
    )
    slow_recorder.close()
    slow_env.close()

    with CognitiveKernel(database_path, catalog=catalog) as restored:
        restored.complete_observed_execution(
            "exec-diagnose-old", completed_at_ns=20
        )
        remaining_logs = [
            (
                "diagnose-recent",
                "diagnose-servo",
                "exec-diagnose-recent",
                17312,
                [40.0] * 12,
                600.0,
            ),
            (
                "wide-old",
                "wide-scan",
                "exec-wide-old",
                17313,
                [40.0, 140.0] * 6,
                600.0,
            ),
            (
                "wide-recent",
                "wide-scan",
                "exec-wide-recent",
                17314,
                [40.0, 140.0] * 6,
                600.0,
            ),
        ]
        for index, (
            session_id,
            experiment_id,
            execution_id,
            seed,
            targets,
            speed,
        ) in enumerate(remaining_logs):
            session_dir = make_complete_log(
                data_root,
                session_id=session_id,
                seed=seed,
                targets=targets,
                max_speed_deg_s=speed,
            )
            authorize_and_complete(
                restored,
                experiment_id=experiment_id,
                execution_id=execution_id,
                session_dir=session_dir,
                now_ns=30 + index * 10,
            )

        histories = {
            experiment_id: restored.recompute_observed_history(experiment_id)
            for experiment_id in ("diagnose-servo", "wide-scan")
        }
        assert [len(history) for history in histories.values()] == [2, 2]
        estimates = ObservedSignalEstimator().estimate_candidates(histories)
        selected = restored.select_experiment(
            {
                experiment_id: estimate.signals
                for experiment_id, estimate in estimates.items()
            },
            now_ns=100,
            safety=safe_context(),
            signal_evidence={
                experiment_id: estimate.audit_record()
                for experiment_id, estimate in estimates.items()
            },
        )
        assert selected.experiment_id == "diagnose-servo"
        expected_digests = {
            experiment_id: [trial.source_digest for trial in history]
            for experiment_id, history in histories.items()
        }
        restored.end_session(ended_at_ns=101)

    with CognitiveKernel(database_path, catalog=catalog) as final:
        rebuilt = {
            experiment_id: final.recompute_observed_history(experiment_id)
            for experiment_id in ("diagnose-servo", "wide-scan")
        }
        assert {
            experiment_id: [trial.source_digest for trial in history]
            for experiment_id, history in rebuilt.items()
        } == expected_digests
        database_text = database_path.read_bytes()
        assert b"requested_deg" not in database_text
        assert b"as5600_deg" not in database_text
        assert b"servo_target" not in database_text


def test_recomputed_history_detects_modified_j0_source(tmp_path) -> None:
    session_dir = make_complete_log(
        tmp_path / "j0",
        session_id="tamper-source",
        seed=17321,
        targets=[80.0] * 4,
        max_speed_deg_s=600.0,
    )
    with CognitiveKernel(
        tmp_path / "kernel.sqlite3", catalog=execution_catalog()
    ) as kernel:
        kernel.start_session("tamper-cycle", started_at_ns=0)
        authorize_and_complete(
            kernel,
            experiment_id="diagnose-servo",
            execution_id="exec-tamper",
            session_dir=session_dir,
            now_ns=10,
        )
        with (session_dir / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(
                Event(
                    session_id="tamper-source",
                    event_type="servo_state",
                    source_id="bench-head-sim",
                    sequence_id=99,
                    source_timestamp_ns=999,
                    host_receive_timestamp_ns=999,
                    payload={"requested_deg": 90.0, "as5600_deg": 90.0},
                    quality={"payload_valid": True},
                    calibration_version="bench-head-v1",
                ).to_json()
                + "\n"
            )
        with pytest.raises(ValueError, match="event count|digest changed"):
            kernel.recompute_observed_history("diagnose-servo")


def test_schema_v1_is_migrated_additively_to_current(tmp_path) -> None:
    path = tmp_path / "migration.sqlite3"
    with CognitiveKernel(path, catalog=execution_catalog()) as kernel:
        kernel.start_session("migration-session", started_at_ns=0)
        proposal = kernel.propose_experiment(
            "diagnose-servo",
            now_ns=1,
            signals=authorization_signals(),
            safety=safe_context(),
        )
    connection = sqlite3.connect(path)
    connection.execute("DROP TABLE development_cycles")
    connection.execute("DROP TABLE competence_assessments")
    connection.execute("DROP TABLE experiment_executions")
    connection.execute("UPDATE kernel_state SET schema_version = 1")
    connection.execute("UPDATE schema_meta SET version = 1")
    connection.commit()
    connection.close()

    with EpisodicMemory(path) as migrated:
        version = migrated.connection.execute(
            "SELECT version FROM schema_meta WHERE singleton = 1"
        ).fetchone()[0]
        proposal_row = migrated.connection.execute(
            "SELECT experiment_id FROM experiment_proposals WHERE proposal_id = ?",
            (proposal.proposal_id,),
        ).fetchone()
        tables = {
            row[0]
            for row in migrated.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert version == SCHEMA_VERSION == 4
        assert proposal_row[0] == "diagnose-servo"
        assert "experiment_executions" in tables
        assert "competence_assessments" in tables
        assert "development_cycles" in tables
