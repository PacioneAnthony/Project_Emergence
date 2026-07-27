from __future__ import annotations

import json

import pytest

from cognitive.experiments import SafeExperimentCatalog
from cognitive.kernel import CognitiveKernel
from cognitive.models import ExperimentSpec, SafetyContext
from cognitive.observed_signals import (
    ObservedSignalEstimator,
    ServoSignalConfig,
    summarize_servo_trial,
)
from j0.events import Event
from j0.recorder import SessionRecorder
from j0.replay import SessionReplay
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig


def servo_event(
    sequence_id: int,
    requested_deg: float,
    observed_deg: float,
    *,
    session_id: str = "trial-a",
) -> Event:
    return Event(
        session_id=session_id,
        event_type="servo_state",
        source_id="bench-head-sim",
        sequence_id=sequence_id,
        source_timestamp_ns=sequence_id * 20_000_000,
        host_receive_timestamp_ns=sequence_id * 20_000_000,
        payload={"requested_deg": requested_deg, "as5600_deg": observed_deg},
        quality={"payload_valid": True, "simulation": True},
        calibration_version="bench-head-v1",
    )


def record_bench_trial(
    root,
    *,
    session_id: str,
    experiment_id: str,
    seed: int,
    targets: list[float],
    max_speed_deg_s: float = 600.0,
):
    config = BenchConfig(seed=seed)
    config.servo.max_speed_deg_s = max_speed_deg_s
    env = BenchHeadEnv(config)
    try:
        env.reset(seed=seed)
        with SessionRecorder(
            root,
            session_id=session_id,
            metadata={"experiment_id": experiment_id, "seed": seed},
        ) as recorder:
            for sequence_id, target in enumerate(targets):
                observation = env.step(target)
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


def test_servo_trial_summary_is_deterministic_and_contains_no_raw_payload() -> None:
    events = [
        servo_event(0, 90.0, 88.0),
        servo_event(1, 130.0, 120.0),
        servo_event(2, 170.0, 160.0),
    ]
    first = summarize_servo_trial(events, experiment_id="scan")
    second = summarize_servo_trial(events, experiment_id="scan")

    assert first == second
    assert first.event_count == 3
    assert first.mean_absolute_error == pytest.approx(22.0 / 3.0 / 160.0)
    assert first.coverage_bins == (4, 6, 7)
    assert first.boundary_exposure == pytest.approx(1 / 3)
    assert first.motor_cost == pytest.approx(80.0 / (160.0 * 3.0))
    serialized = json.dumps(first.to_dict(), sort_keys=True)
    assert "requested_deg" not in serialized
    assert "as5600_deg" not in serialized


@pytest.mark.parametrize(
    ("events", "message"),
    [
        ([servo_event(0, 90.0, 90.0), servo_event(0, 90.0, 90.0)], "duplicate"),
        (
            [
                Event(
                    **{
                        **servo_event(0, 90.0, 90.0).to_dict(),
                        "quality": {"payload_valid": False},
                    }
                )
            ],
            "explicitly valid",
        ),
        ([servo_event(0, 171.0, 90.0)], "outside"),
    ],
)
def test_servo_trial_summary_rejects_invalid_evidence(events, message) -> None:
    with pytest.raises(ValueError, match=message):
        summarize_servo_trial(events, experiment_id="scan")


def test_observed_estimator_measures_progress_novelty_and_digest() -> None:
    config = ServoSignalConfig(bin_count=8)
    old = summarize_servo_trial(
        [servo_event(0, 40.0, 90.0), servo_event(1, 40.0, 80.0)],
        experiment_id="diagnose",
        config=config,
    )
    recent = summarize_servo_trial(
        [
            servo_event(0, 40.0, 42.0, session_id="trial-b"),
            servo_event(1, 120.0, 116.0, session_id="trial-b"),
        ],
        experiment_id="diagnose",
        config=config,
    )
    estimator = ObservedSignalEstimator(config)
    first = estimator.estimate("diagnose", [old, recent])
    second = estimator.estimate("diagnose", [old, recent])

    assert first == second
    assert first.signals.learning_progress > 0
    assert first.signals.novelty == pytest.approx(1 / 8)
    assert first.signals.controllability > 0.95
    assert first.evidence_digest == second.evidence_digest
    assert first.audit_record()["evidence_digest"] == first.evidence_digest
    assert first.evidence["limitations"]["causal_claim"] is False


def test_selector_requires_signal_evidence_to_match_candidates(tmp_path) -> None:
    catalog = SafeExperimentCatalog(
        [ExperimentSpec("alpha", "look"), ExperimentSpec("beta", "look")]
    )
    estimator = ObservedSignalEstimator()
    summary = summarize_servo_trial(
        [servo_event(0, 90.0, 90.0)], experiment_id="alpha"
    )
    estimate = estimator.estimate("alpha", [summary])
    with CognitiveKernel(tmp_path / "kernel.sqlite3", catalog=catalog) as kernel:
        kernel.start_session("selection", started_at_ns=0)
        with pytest.raises(ValueError, match="keys must match"):
            kernel.select_experiment(
                {"alpha": estimate.signals, "beta": estimate.signals},
                now_ns=1,
                safety=SafetyContext(
                    emergency_stop=False,
                    hardware_healthy=True,
                    model_update_in_progress=False,
                    quota_state="ok",
                    allowed_primitives=frozenset({"look"}),
                ),
                signal_evidence={"alpha": estimate.audit_record()},
            )


def test_life002_observation_choice_and_evidence_survive_restart(tmp_path) -> None:
    """MuJoCo/J0 histories, not scripted scores, drive a persistent safe choice."""

    data_root = tmp_path / "j0"
    trials = [
        (
            "diagnose-old",
            "diagnose-servo",
            17201,
            [40.0] * 12,
            20.0,
        ),
        (
            "diagnose-recent",
            "diagnose-servo",
            17202,
            [40.0] * 12,
            600.0,
        ),
        (
            "wide-old",
            "wide-scan",
            17203,
            [40.0, 140.0] * 6,
            600.0,
        ),
        (
            "wide-recent",
            "wide-scan",
            17204,
            [40.0, 140.0] * 6,
            600.0,
        ),
    ]
    session_dirs = {
        session_id: record_bench_trial(
            data_root,
            session_id=session_id,
            experiment_id=experiment_id,
            seed=seed,
            targets=targets,
            max_speed_deg_s=max_speed,
        )
        for session_id, experiment_id, seed, targets, max_speed in trials
    }

    def recompute():
        summaries = {
            "diagnose-servo": [
                summarize_servo_trial(
                    SessionReplay(session_dirs[session_id]).events(),
                    experiment_id="diagnose-servo",
                )
                for session_id in ("diagnose-old", "diagnose-recent")
            ],
            "wide-scan": [
                summarize_servo_trial(
                    SessionReplay(session_dirs[session_id]).events(),
                    experiment_id="wide-scan",
                )
                for session_id in ("wide-old", "wide-recent")
            ],
        }
        return ObservedSignalEstimator().estimate_candidates(summaries)

    first_estimates = recompute()
    database_path = tmp_path / "life002.sqlite3"
    catalog = SafeExperimentCatalog(
        [
            ExperimentSpec(
                "diagnose-servo",
                "diagnose_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
            ),
            ExperimentSpec(
                "wide-scan",
                "scan_bounded_servo",
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
            ),
        ]
    )
    safety = SafetyContext(
        emergency_stop=False,
        hardware_healthy=True,
        model_update_in_progress=False,
        quota_state="ok",
        allowed_primitives=frozenset(
            {"diagnose_bounded_servo", "scan_bounded_servo"}
        ),
    )
    kernel = CognitiveKernel(database_path, catalog=catalog)
    kernel.start_session("life002-selection", started_at_ns=1_000_000_000)
    proposal = kernel.select_experiment(
        {
            experiment_id: estimate.signals
            for experiment_id, estimate in first_estimates.items()
        },
        now_ns=1_000_000_001,
        safety=safety,
        signal_evidence={
            experiment_id: estimate.audit_record()
            for experiment_id, estimate in first_estimates.items()
        },
    )
    kernel.close()  # Simulated process restart with an open persistent session.

    assert proposal.experiment_id == "diagnose-servo"
    assert not {"servo_target", "v_cmd", "omega_cmd"} & proposal.to_dict().keys()
    assert set(proposal.rationale["selection"]["candidates"]) == {
        "diagnose-servo",
        "wide-scan",
    }

    with CognitiveKernel(database_path, catalog=catalog) as restored:
        second_estimates = recompute()
        assert second_estimates == first_estimates
        row = restored.memory.connection.execute(
            "SELECT rationale_json FROM experiment_proposals WHERE proposal_id = ?",
            (proposal.proposal_id,),
        ).fetchone()
        rationale_json = row["rationale_json"]
        persisted = json.loads(rationale_json)
        for experiment_id, estimate in second_estimates.items():
            record = persisted["selection"]["candidates"][experiment_id][
                "signal_evidence"
            ]
            assert record["evidence_digest"] == estimate.evidence_digest
            assert record["evidence"] == estimate.evidence
        assert "requested_deg" not in rationale_json
        assert "as5600_deg" not in rationale_json
        assert "servo_target" not in rationale_json
        restored.end_session(ended_at_ns=1_000_000_002)
