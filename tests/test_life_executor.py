from __future__ import annotations

from dataclasses import replace
import inspect
import json

import pytest

from cognitive.experiments import SafeExperimentCatalog
from cognitive.kernel import CognitiveKernel
from cognitive.models import ExperimentSignals, ExperimentSpec, SafetyContext
from cognitive.observed_signals import ObservedSignalEstimator
from sim3d.bench_env import BenchHeadEnv
from sim3d.life_executor import (
    BoundedMujocoExecutor,
    BoundedPrimitivePlan,
)


def life4_catalog(*, include_unknown: bool = False) -> SafeExperimentCatalog:
    specs = [
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
    if include_unknown:
        specs.append(
            ExperimentSpec(
                "unknown-experiment",
                "unregistered_sim_primitive",
                max_proposals_per_session=20,
            )
        )
    return SafeExperimentCatalog(specs)


def life4_safety(**overrides) -> SafetyContext:
    values = {
        "emergency_stop": False,
        "hardware_healthy": True,
        "model_update_in_progress": False,
        "quota_state": "ok",
        "allowed_primitives": frozenset(
            {
                "diagnose_bounded_servo",
                "scan_bounded_servo",
                "unregistered_sim_primitive",
            }
        ),
    }
    values.update(overrides)
    return SafetyContext(**values)


def bootstrap_signals() -> ExperimentSignals:
    return ExperimentSignals(
        epistemic_gain=0.5,
        learning_progress=0.2,
        novelty=0.1,
        controllability=0.8,
        predicted_risk=0.0,
        motor_cost=0.1,
    )


def propose(kernel: CognitiveKernel, experiment_id: str, now_ns: int):
    return kernel.propose_experiment(
        experiment_id,
        now_ns=now_ns,
        signals=bootstrap_signals(),
        safety=life4_safety(),
    )


def test_bounded_plan_contract_and_executor_has_no_free_target_input(tmp_path) -> None:
    with pytest.raises(ValueError, match="1 to 64"):
        BoundedPrimitivePlan("empty", ())
    with pytest.raises(ValueError, match="inside"):
        BoundedPrimitivePlan("unsafe", (171.0,))
    with pytest.raises(ValueError, match="duplicate"):
        BoundedMujocoExecutor(
            tmp_path,
            plans=(
                BoundedPrimitivePlan("same", (90.0,)),
                BoundedPrimitivePlan("same", (100.0,)),
            ),
        )
    parameters = inspect.signature(BoundedMujocoExecutor.execute).parameters
    assert not {"target", "target_deg", "targets", "servo_target"} & set(parameters)


def test_execution_rechecks_safety_registry_and_persisted_identity(tmp_path) -> None:
    database_path = tmp_path / "kernel.sqlite3"
    executor = BoundedMujocoExecutor(tmp_path / "j0")
    with CognitiveKernel(
        database_path, catalog=life4_catalog(include_unknown=True)
    ) as kernel:
        kernel.start_session("life4-guards", started_at_ns=0)
        blocked = propose(kernel, "diagnose-servo", 1)
        with pytest.raises(RuntimeError, match="emergency_stop"):
            executor.execute(
                kernel,
                blocked,
                execution_id="blocked-execution",
                j0_session_id="blocked-j0",
                seed=17401,
                started_at_ns=10,
                safety=life4_safety(emergency_stop=True),
            )
        assert kernel.memory.experiment_execution("blocked-execution") is None

        forged = replace(blocked, primitive="scan_bounded_servo")
        with pytest.raises(ValueError, match="persisted identity"):
            executor.execute(
                kernel,
                forged,
                execution_id="forged-execution",
                j0_session_id="forged-j0",
                seed=17402,
                started_at_ns=20,
                safety=life4_safety(),
            )

        unknown = propose(kernel, "unknown-experiment", 2)
        with pytest.raises(ValueError, match="unsupported bounded primitive"):
            executor.execute(
                kernel,
                unknown,
                execution_id="unknown-execution",
                j0_session_id="unknown-j0",
                seed=17403,
                started_at_ns=30,
                safety=life4_safety(),
            )
        assert not (tmp_path / "j0" / "sessions").exists()


def test_simulator_failure_aborts_log_execution_and_proposal(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "kernel.sqlite3"
    executor = BoundedMujocoExecutor(tmp_path / "j0")
    with CognitiveKernel(database_path, catalog=life4_catalog()) as kernel:
        kernel.start_session("life4-failure", started_at_ns=0)
        proposal = propose(kernel, "diagnose-servo", 1)

        original_step = BenchHeadEnv.step
        calls = 0

        def failing_step(self, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected MuJoCo failure")
            return original_step(self, target)

        monkeypatch.setattr(BenchHeadEnv, "step", failing_step)
        with pytest.raises(RuntimeError, match="injected MuJoCo failure"):
            executor.execute(
                kernel,
                proposal,
                execution_id="failed-execution",
                j0_session_id="failed-j0",
                seed=17411,
                started_at_ns=10,
                safety=life4_safety(),
            )

        execution = kernel.memory.experiment_execution("failed-execution")
        persisted = kernel.memory.proposal(proposal.proposal_id)
        manifest = json.loads(
            (
                tmp_path
                / "j0"
                / "sessions"
                / "failed-j0"
                / "manifest.json"
            ).read_text(encoding="utf-8")
        )
        assert execution["status"] == "aborted"
        assert persisted["status"] == "cancelled"
        assert manifest["status"] == "aborted"
        kernel.end_session(ended_at_ns=20)


def test_life004_closes_observation_selection_execution_loop(tmp_path) -> None:
    database_path = tmp_path / "life004.sqlite3"
    executor = BoundedMujocoExecutor(tmp_path / "j0")
    catalog = life4_catalog()

    with CognitiveKernel(database_path, catalog=catalog) as kernel:
        kernel.start_session("life4-loop", started_at_ns=0)
        bootstrap = (
            ("diagnose-servo", "diagnose-a", 17421),
            ("diagnose-servo", "diagnose-b", 17422),
            ("wide-scan", "wide-a", 17423),
            ("wide-scan", "wide-b", 17424),
        )
        for index, (experiment_id, label, seed) in enumerate(bootstrap):
            proposal = propose(kernel, experiment_id, 1_000_000_000 * (index + 1))
            outcome = executor.execute(
                kernel,
                proposal,
                execution_id=f"execution-{label}",
                j0_session_id=f"j0-{label}",
                seed=seed,
                started_at_ns=1_000_000_000 * (index + 1) + 1,
                safety=life4_safety(),
            )
            assert outcome.summary.experiment_id == experiment_id
            manifest = json.loads(
                (outcome.session_dir / "manifest.json").read_text(encoding="utf-8")
            )
            assert manifest["status"] == "complete"
            assert manifest["event_count"] == 12
            assert manifest["metadata"]["plan_digest"] == outcome.plan_digest

        histories = {
            experiment_id: kernel.recompute_observed_history(experiment_id)
            for experiment_id in ("diagnose-servo", "wide-scan")
        }
        estimates = ObservedSignalEstimator().estimate_candidates(histories)
        selected = kernel.select_experiment(
            {
                experiment_id: estimate.signals
                for experiment_id, estimate in estimates.items()
            },
            now_ns=5_000_000_000,
            safety=life4_safety(),
            signal_evidence={
                experiment_id: estimate.audit_record()
                for experiment_id, estimate in estimates.items()
            },
        )
        assert selected.experiment_id == "diagnose-servo"
        closed_loop = executor.execute(
            kernel,
            selected,
            execution_id="execution-observed-choice",
            j0_session_id="j0-observed-choice",
            seed=17425,
            started_at_ns=5_000_000_001,
            safety=life4_safety(),
        )
        assert closed_loop.summary.experiment_id == selected.experiment_id
        expected_counts = {
            "diagnose-servo": 3,
            "wide-scan": 2,
        }
        kernel.end_session(ended_at_ns=6_000_000_000)

    with CognitiveKernel(database_path, catalog=catalog) as restored:
        for experiment_id, expected_count in expected_counts.items():
            history = restored.recompute_observed_history(experiment_id)
            assert len(history) == expected_count
        database_bytes = database_path.read_bytes()
        assert b"requested_deg" not in database_bytes
        assert b"as5600_deg" not in database_bytes
        assert b"targets_deg" not in database_bytes
        assert b"servo_target" not in database_bytes
