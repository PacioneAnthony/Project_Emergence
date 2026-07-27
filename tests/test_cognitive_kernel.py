from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from cognitive.beliefs import (
    BeliefState,
    BeliefUnavailableError,
    ClockDomainMismatchError,
    fuse_independent_gaussians,
)
from cognitive.boundaries import BoundaryConfig
from cognitive.competence import UpperBoundCriterion, assess_upper_bound
from cognitive.experiments import (
    ExperimentBlockedError,
    ExperimentSelectionBlockedError,
    SafeExperimentCatalog,
)
from cognitive.kernel import CognitiveKernel
from cognitive.memory import (
    EpisodicMemory,
    InvalidCompetenceTransition,
    SchemaVersionError,
)
from cognitive.models import (
    BeliefEstimate,
    BeliefRequirement,
    CompetenceStatus,
    ExperimentSignals,
    ExperimentSpec,
    SafetyContext,
)
from j0.events import Event
from j0.recorder import SessionRecorder
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig


def belief(
    name: str = "free_space",
    *,
    mean: float = 0.8,
    variance: float = 0.02,
    observed_at_ns: int = 100,
    received_at_ns: int = 110,
    source_id: str = "range-model",
    clock_domain: str = "boot-a:host-monotonic",
    quality: float = 0.9,
) -> BeliefEstimate:
    return BeliefEstimate(
        name=name,
        mean=mean,
        variance=variance,
        observed_at_ns=observed_at_ns,
        received_at_ns=received_at_ns,
        source_id=source_id,
        clock_domain=clock_domain,
        quality=quality,
        calibration_version="range-cal-v1",
        model_version="range-v1",
    )


def event(
    session_id: str,
    sequence_id: int,
    timestamp_ns: int,
    *,
    event_type: str = "range_sample",
    payload: dict[str, object] | None = None,
) -> Event:
    return Event(
        session_id=session_id,
        event_type=event_type,
        source_id="sim",
        sequence_id=sequence_id,
        source_timestamp_ns=timestamp_ns,
        host_receive_timestamp_ns=timestamp_ns,
        payload=payload or {"large_sensor_value": "must-not-enter-sqlite"},
        quality={"payload_valid": True},
        calibration_version="sim-v1",
    )


def safe_context(**overrides: object) -> SafetyContext:
    values: dict[str, object] = {
        "emergency_stop": False,
        "hardware_healthy": True,
        "model_update_in_progress": False,
        "quota_state": "ok",
        "allowed_primitives": frozenset({"look_left"}),
    }
    values.update(overrides)
    return SafetyContext(**values)  # type: ignore[arg-type]


def catalog(*, quota: int = 2, interval_ns: int = 10) -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                experiment_id="scan-left",
                primitive="look_left",
                required_beliefs=(
                    BeliefRequirement(
                        "free_space",
                        max_age_ns=1_000,
                        max_variance=0.1,
                        min_quality=0.8,
                    ),
                ),
                max_predicted_risk=0.2,
                max_motor_cost=0.4,
                min_interval_ns=interval_ns,
                max_proposals_per_session=quota,
            )
        ]
    )


def signals(**overrides: float) -> ExperimentSignals:
    values = {
        "epistemic_gain": 0.7,
        "learning_progress": 0.5,
        "novelty": 0.2,
        "controllability": 0.8,
        "predicted_risk": 0.1,
        "motor_cost": 0.2,
    }
    values.update(overrides)
    return ExperimentSignals(**values)


def bench_target_error(
    *,
    seed: int,
    target_deg: float,
    max_speed_deg_s: float = 600.0,
) -> float:
    config = BenchConfig(seed=seed)
    config.servo.max_speed_deg_s = max_speed_deg_s
    env = BenchHeadEnv(config)
    try:
        observation = env.reset(seed=seed)
        for _ in range(20):
            observation = env.step(target_deg)
        return abs(observation.as5600_deg - target_deg)
    finally:
        env.close()


def test_beliefs_reject_out_of_order_and_apply_constraints() -> None:
    state = BeliefState()
    assert state.update(belief())
    assert not state.update(belief(mean=9.0, observed_at_ns=99, received_at_ns=120))
    assert state.get("free_space").mean == 0.8  # type: ignore[union-attr]
    assert state.require(
        "free_space", now_ns=150, max_age_ns=100, max_variance=0.1, min_quality=0.8
    ).mean == 0.8
    with pytest.raises(BeliefUnavailableError, match="stale"):
        state.require("free_space", now_ns=10_000, max_age_ns=100, max_variance=1)


def test_clock_domain_change_requires_explicit_session_authority() -> None:
    state = BeliefState()
    state.update(belief(observed_at_ns=10_000, received_at_ns=10_010))
    after_reboot = belief(
        mean=0.7,
        observed_at_ns=10,
        received_at_ns=20,
        clock_domain="boot-b:host-monotonic",
    )
    with pytest.raises(ClockDomainMismatchError):
        state.update(after_reboot)
    assert state.update(after_reboot, allow_clock_change=True)
    assert state.get("free_space").clock_domain == "boot-b:host-monotonic"


def test_belief_snapshot_round_trip_is_bit_identical() -> None:
    state = BeliefState()
    state.update(belief("z"))
    state.update(belief("a", observed_at_ns=200, received_at_ns=210))
    restored = BeliefState.from_snapshot(state.snapshot())
    assert restored.canonical_json() == state.canonical_json()
    assert restored.revision == 2


def test_gaussian_fusion_is_explicit_and_tracks_provenance() -> None:
    fused = fuse_independent_gaussians(
        "heading",
        [
            belief("heading", mean=0, variance=1, source_id="imu"),
            belief("heading", mean=2, variance=1, source_id="vision"),
        ],
        received_at_ns=120,
        source_id="fusion:imu+vision",
    )
    assert fused.mean == pytest.approx(1)
    assert fused.variance == pytest.approx(0.5)
    assert fused.source_id == "fusion:imu+vision"


def test_unknown_database_schema_is_refused(tmp_path) -> None:
    path = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE schema_meta(singleton INTEGER PRIMARY KEY, version INTEGER)")
    connection.execute("INSERT INTO schema_meta VALUES (1, 99)")
    connection.commit()
    connection.close()
    with pytest.raises(SchemaVersionError, match="99"):
        EpisodicMemory(path)


def test_event_ingestion_stores_reference_and_digest_not_payload(tmp_path) -> None:
    path = tmp_path / "kernel.sqlite3"
    with CognitiveKernel(path) as kernel:
        kernel.start_session("s1", started_at_ns=0)
        episode_id = kernel.ingest_event(
            event("s1", 0, 100),
            raw_ref="sessions/s1/events.jsonl#L1",
        )
        row = kernel.memory.event_refs(episode_id)[0]
        assert row["raw_ref"] == "sessions/s1/events.jsonl#L1"
        assert len(row["event_digest"]) == 64
        columns = {item["name"] for item in kernel.memory.connection.execute("PRAGMA table_info(event_refs)")}
        assert "payload" not in columns and "payload_json" not in columns
        database_bytes = path.read_bytes()
        assert b"must-not-enter-sqlite" not in database_bytes


def test_duplicate_event_is_idempotent_but_identity_collision_is_refused(tmp_path) -> None:
    with CognitiveKernel(tmp_path / "kernel.sqlite3") as kernel:
        kernel.start_session("s1", started_at_ns=0)
        original = event("s1", 0, 100)
        episode_id = kernel.ingest_event(original)
        assert kernel.ingest_event(original) == episode_id
        assert len(kernel.memory.event_refs(episode_id)) == 1
        with pytest.raises(ValueError, match="identity collision"):
            kernel.ingest_event(event("s1", 0, 100, payload={"changed": True}))


def test_j0_replay_bridge_is_deterministic_and_restartable(tmp_path) -> None:
    session_dir = tmp_path / "sessions" / "s1"
    session_dir.mkdir(parents=True)
    events = [event("s1", 0, 100), event("s1", 1, 110)]
    (session_dir / "events.jsonl").write_text(
        "".join(item.to_json() + "\n" for item in events),
        encoding="utf-8",
    )
    (session_dir / "manifest.json").write_text(
        json.dumps({"session_id": "s1"}),
        encoding="utf-8",
    )
    path = tmp_path / "kernel.sqlite3"
    with CognitiveKernel(path) as kernel:
        kernel.start_session("s1", started_at_ns=0)
        first_stats = kernel.ingest_replay(session_dir)
        episode_id = kernel.episode_id
    with CognitiveKernel(path) as restored:
        second_stats = restored.ingest_replay(session_dir)
        assert second_stats == first_stats
        rows = restored.memory.event_refs(episode_id)
        assert len(rows) == 2
        assert rows[0]["raw_ref"].endswith("events.jsonl#L1")


def test_causal_boundaries_are_online_and_late_events_do_not_rewrite(tmp_path) -> None:
    config = BoundaryConfig(
        silence_ns=10,
        max_episode_ns=100,
        explicit_event_types=frozenset({"collision"}),
    )
    with CognitiveKernel(tmp_path / "kernel.sqlite3", boundary_config=config) as kernel:
        kernel.start_session("s1", started_at_ns=0)
        first = kernel.ingest_event(event("s1", 0, 10))
        assert kernel.ingest_event(event("s1", 1, 20)) == first
        second = kernel.ingest_event(event("s1", 2, 31))
        assert second != first
        assert kernel.memory.episode(first)["boundary_reason"] == "silence"
        third = kernel.ingest_event(event("s1", 3, 40, event_type="collision"))
        assert third != second
        late_episode = kernel.ingest_event(event("s1", 4, 25))
        assert late_episode == third
        late_row = kernel.memory.event_refs(third)[-1]
        assert late_row["out_of_order"] == 1
        assert kernel.last_event_at_ns == 40


def test_competence_requires_candidate_and_validation_digest(tmp_path) -> None:
    with EpisodicMemory(tmp_path / "memory.sqlite3") as memory:
        with pytest.raises(InvalidCompetenceTransition):
            memory.transition_competence(
                "avoidance",
                CompetenceStatus.VALIDATED,
                changed_at_ns=1,
                evidence={},
            )
        memory.transition_competence(
            "avoidance", CompetenceStatus.LEARNING, changed_at_ns=1, evidence={"runs": 1}
        )
        memory.transition_competence(
            "avoidance", CompetenceStatus.CANDIDATE, changed_at_ns=2, evidence={"runs": 10}
        )
        with pytest.raises(InvalidCompetenceTransition, match="digest"):
            memory.transition_competence(
                "avoidance",
                CompetenceStatus.VALIDATED,
                changed_at_ns=3,
                evidence={"held_out": True},
            )
        memory.transition_competence(
            "avoidance",
            CompetenceStatus.VALIDATED,
            changed_at_ns=3,
            evidence={"held_out": True},
            model_version="avoid-v2",
            validation_digest="sha256:validation",
        )
        assert memory.competence_status("avoidance") is CompetenceStatus.VALIDATED
        assert [row["to_status"] for row in memory.competence_history("avoidance")] == [
            "learning",
            "candidate",
            "validated",
        ]


def test_upper_bound_assessment_has_hysteresis_and_auditable_digest() -> None:
    criterion = UpperBoundCriterion(
        metric_name="absolute_error_deg",
        validation_upper_bound=2.0,
        regression_upper_bound=4.0,
        min_samples=2,
    )
    validated = assess_upper_bound([0.5, 1.5], criterion)
    inconclusive = assess_upper_bound([1.5, 3.0], criterion)
    regressed = assess_upper_bound([1.5, 4.1], criterion)

    assert validated.outcome == "validated"
    assert inconclusive.outcome == "inconclusive"
    assert regressed.outcome == "regressed"
    assert len(validated.values_digest) == 64
    assert len(validated.evidence_digest()) == 64
    assert validated.evidence_digest() == assess_upper_bound([0.5, 1.5], criterion).evidence_digest()
    with pytest.raises(ValueError, match="at least 2"):
        assess_upper_bound([0.5], criterion)
    with pytest.raises(ValueError, match="finite"):
        assess_upper_bound([0.5, float("nan")], criterion)


def test_model_promotion_is_explicit_and_unique(tmp_path) -> None:
    with EpisodicMemory(tmp_path / "memory.sqlite3") as memory:
        memory.register_model(
            "reafference",
            "v1",
            artifact_ref="models/r1",
            artifact_digest="abc",
            created_at_ns=1,
            state="candidate",
        )
        memory.promote_model("reafference", "v1")
        assert memory.validated_model("reafference")["version"] == "v1"
        memory.register_model(
            "reafference",
            "v2",
            artifact_ref="models/r2",
            artifact_digest="def",
            created_at_ns=2,
            state="candidate",
        )
        memory.promote_model("reafference", "v2")
        assert memory.validated_model("reafference")["version"] == "v2"


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"emergency_stop": True}, "emergency_stop"),
        ({"hardware_healthy": False}, "hardware_unhealthy"),
        ({"model_update_in_progress": True}, "model_update_in_progress"),
        ({"quota_state": "long_session_blocked"}, "quota:long_session_blocked"),
        ({"allowed_primitives": frozenset()}, "primitive_not_allowed"),
    ],
)
def test_safety_guards_block_experiment_proposals(tmp_path, override, reason) -> None:
    with CognitiveKernel(tmp_path / "kernel.sqlite3", catalog=catalog()) as kernel:
        kernel.start_session("s1", started_at_ns=0)
        kernel.update_belief(belief(), checkpoint=True)
        with pytest.raises(ExperimentBlockedError) as error:
            kernel.propose_experiment(
                "scan-left",
                now_ns=200,
                signals=signals(),
                safety=safe_context(**override),
            )
        assert reason in error.value.reasons


def test_belief_risk_and_cost_constraints_block_proposal(tmp_path) -> None:
    with CognitiveKernel(tmp_path / "kernel.sqlite3", catalog=catalog()) as kernel:
        kernel.start_session("s1", started_at_ns=0)
        with pytest.raises(ExperimentBlockedError, match="missing"):
            kernel.propose_experiment(
                "scan-left", now_ns=200, signals=signals(), safety=safe_context()
            )
        kernel.update_belief(belief(), checkpoint=True)
        with pytest.raises(ExperimentBlockedError) as error:
            kernel.propose_experiment(
                "scan-left",
                now_ns=200,
                signals=signals(predicted_risk=0.3, motor_cost=0.6),
                safety=safe_context(),
            )
        assert {"predicted_risk", "motor_cost"} <= set(error.value.reasons)


def test_proposal_has_no_actuator_command_and_persistent_cadence(tmp_path) -> None:
    path = tmp_path / "kernel.sqlite3"
    with CognitiveKernel(path, catalog=catalog(quota=2, interval_ns=10)) as kernel:
        kernel.start_session("s1", started_at_ns=0)
        kernel.update_belief(belief(), checkpoint=True)
        proposal = kernel.propose_experiment(
            "scan-left", now_ns=200, signals=signals(), safety=safe_context()
        )
        assert proposal.primitive == "look_left"
        assert not {"v_cmd", "omega_cmd", "servo_target"} & proposal.to_dict().keys()
    with CognitiveKernel(path, catalog=catalog(quota=2, interval_ns=10)) as restored:
        with pytest.raises(ExperimentBlockedError) as error:
            restored.propose_experiment(
                "scan-left", now_ns=205, signals=signals(), safety=safe_context()
            )
        assert "minimum_interval" in error.value.reasons
        restored.propose_experiment(
            "scan-left", now_ns=210, signals=signals(), safety=safe_context()
        )
        with pytest.raises(ExperimentBlockedError) as error:
            restored.propose_experiment(
                "scan-left", now_ns=220, signals=signals(), safety=safe_context()
            )
        assert "session_quota" in error.value.reasons


def test_selector_chooses_best_eligible_candidate_and_persists_full_audit(tmp_path) -> None:
    selection_catalog = SafeExperimentCatalog(
        [
            ExperimentSpec(
                experiment_id="diagnose-servo",
                primitive="look_left",
                required_beliefs=(
                    BeliefRequirement(
                        "free_space",
                        max_age_ns=1_000,
                        max_variance=0.1,
                        min_quality=0.8,
                    ),
                ),
                max_predicted_risk=0.2,
                max_motor_cost=0.4,
                max_proposals_per_session=1,
            ),
            ExperimentSpec(
                experiment_id="wide-scan",
                primitive="look_wide",
                max_predicted_risk=0.2,
                max_motor_cost=0.4,
            ),
        ]
    )
    path = tmp_path / "selection.sqlite3"
    with CognitiveKernel(path, catalog=selection_catalog) as kernel:
        kernel.start_session("selection", started_at_ns=0)
        kernel.update_belief(belief(), checkpoint=True)
        proposal = kernel.select_experiment(
            {
                "diagnose-servo": signals(epistemic_gain=0.5, learning_progress=0.6),
                "wide-scan": signals(
                    epistemic_gain=1.0,
                    learning_progress=1.0,
                    predicted_risk=0.3,
                ),
            },
            now_ns=200,
            safety=SafetyContext(
                emergency_stop=False,
                hardware_healthy=True,
                model_update_in_progress=False,
                quota_state="ok",
                allowed_primitives=frozenset({"look_left", "look_wide"}),
            ),
        )
        assert proposal.experiment_id == "diagnose-servo"
        selection = proposal.rationale["selection"]
        assert selection["policy"] == "highest_score_then_experiment_id"
        assert selection["candidates"]["wide-scan"] == {
            "status": "blocked",
            "reasons": ["predicted_risk"],
        }
        row = kernel.memory.connection.execute(
            "SELECT rationale_json FROM experiment_proposals WHERE proposal_id = ?",
            (proposal.proposal_id,),
        ).fetchone()
        assert json.loads(row["rationale_json"])["selection"] == selection

        with pytest.raises(ExperimentSelectionBlockedError) as error:
            kernel.select_experiment(
                {
                    "diagnose-servo": signals(),
                    "wide-scan": signals(),
                },
                now_ns=210,
                safety=SafetyContext(
                    emergency_stop=True,
                    hardware_healthy=True,
                    model_update_in_progress=False,
                    quota_state="ok",
                    allowed_primitives=frozenset({"look_left", "look_wide"}),
                ),
            )
        assert "emergency_stop" in error.value.blocked_by_experiment["wide-scan"]
        assert "session_quota" in error.value.blocked_by_experiment["diagnose-servo"]


def test_selector_tie_break_is_stable_and_only_selected_candidate_uses_quota(tmp_path) -> None:
    selection_catalog = SafeExperimentCatalog(
        [
            ExperimentSpec("beta", "look_left", max_proposals_per_session=1),
            ExperimentSpec("alpha", "look_left", max_proposals_per_session=1),
        ]
    )
    with CognitiveKernel(tmp_path / "tie.sqlite3", catalog=selection_catalog) as kernel:
        kernel.start_session("tie", started_at_ns=0)
        first = kernel.select_experiment(
            {"beta": signals(), "alpha": signals()},
            now_ns=1,
            safety=safe_context(),
        )
        assert first.experiment_id == "alpha"
        second = kernel.select_experiment(
            {"beta": signals(), "alpha": signals()},
            now_ns=2,
            safety=safe_context(),
        )
        assert second.experiment_id == "beta"


def test_life_regression_recovery_and_experiment_choice_survive_restart(tmp_path) -> None:
    path = tmp_path / "life-recovery.sqlite3"
    criterion = UpperBoundCriterion(
        metric_name="absolute_error_deg",
        validation_upper_bound=2.0,
        regression_upper_bound=4.0,
        min_samples=2,
    )
    recovery_catalog = SafeExperimentCatalog(
        [
            ExperimentSpec("recalibrate-servo", "look_left", max_proposals_per_session=1),
            ExperimentSpec("explore-room", "look_left", max_proposals_per_session=1),
        ]
    )

    validation = assess_upper_bound(
        [
            bench_target_error(seed=17101, target_deg=75.0),
            bench_target_error(seed=17102, target_deg=105.0),
        ],
        criterion,
    )
    regression = assess_upper_bound(
        [
            bench_target_error(seed=17103, target_deg=75.0, max_speed_deg_s=10.0),
            bench_target_error(seed=17104, target_deg=105.0, max_speed_deg_s=10.0),
        ],
        criterion,
    )
    assert validation.outcome == "validated"
    assert regression.outcome == "regressed"

    with CognitiveKernel(path, catalog=recovery_catalog) as kernel:
        kernel.start_session("life-validation", started_at_ns=0)
        kernel.transition_competence(
            "bounded_head_orientation",
            CompetenceStatus.LEARNING,
            changed_at_ns=1,
            evidence={"phase": "acquisition"},
        )
        kernel.transition_competence(
            "bounded_head_orientation",
            CompetenceStatus.CANDIDATE,
            changed_at_ns=2,
            evidence=validation.evidence(),
            model_version="servo-cal-v1",
        )
        kernel.transition_competence(
            "bounded_head_orientation",
            CompetenceStatus.VALIDATED,
            changed_at_ns=3,
            evidence=validation.evidence(),
            model_version="servo-cal-v1",
            validation_digest=validation.evidence_digest(),
        )
        kernel.end_session(ended_at_ns=4)

    with CognitiveKernel(path, catalog=recovery_catalog) as restored:
        restored.start_session("life-regression", started_at_ns=10)
        restored.transition_competence(
            "bounded_head_orientation",
            CompetenceStatus.REGRESSED,
            changed_at_ns=11,
            evidence=regression.evidence(),
            model_version="servo-cal-v1",
        )
        proposal = restored.select_experiment(
            {
                "explore-room": signals(epistemic_gain=0.4, learning_progress=0.1),
                "recalibrate-servo": signals(epistemic_gain=0.8, learning_progress=0.9),
            },
            now_ns=12,
            safety=safe_context(),
        )
        assert proposal.experiment_id == "recalibrate-servo"
        restored.end_session(ended_at_ns=13)

    recovery = assess_upper_bound(
        [
            bench_target_error(seed=17105, target_deg=70.0),
            bench_target_error(seed=17106, target_deg=110.0),
        ],
        criterion,
    )
    with CognitiveKernel(path, catalog=recovery_catalog) as recovered:
        assert recovered.memory.competence_status(
            "bounded_head_orientation"
        ) is CompetenceStatus.REGRESSED
        recovered.start_session("life-recovery", started_at_ns=20)
        recovered.transition_competence(
            "bounded_head_orientation",
            CompetenceStatus.LEARNING,
            changed_at_ns=21,
            evidence={"selected_proposal": proposal.proposal_id},
            model_version="servo-cal-v2",
        )
        recovered.transition_competence(
            "bounded_head_orientation",
            CompetenceStatus.CANDIDATE,
            changed_at_ns=22,
            evidence=recovery.evidence(),
            model_version="servo-cal-v2",
        )
        recovered.transition_competence(
            "bounded_head_orientation",
            CompetenceStatus.VALIDATED,
            changed_at_ns=23,
            evidence=recovery.evidence(),
            model_version="servo-cal-v2",
            validation_digest=recovery.evidence_digest(),
        )
        recovered.end_session(ended_at_ns=24)

    with CognitiveKernel(path, catalog=recovery_catalog) as final:
        assert final.memory.competence_status(
            "bounded_head_orientation"
        ) is CompetenceStatus.VALIDATED
        assert [row["to_status"] for row in final.memory.competence_history(
            "bounded_head_orientation"
        )] == [
            "learning",
            "candidate",
            "validated",
            "regressed",
            "learning",
            "candidate",
            "validated",
        ]


def test_crash_restart_restores_beliefs_session_and_open_episode(tmp_path) -> None:
    path = tmp_path / "kernel.sqlite3"
    kernel = CognitiveKernel(path)
    kernel.start_session("s1", started_at_ns=0)
    kernel.update_belief(belief(), checkpoint=True)
    episode_id = kernel.ingest_event(event("s1", 0, 100))
    expected_beliefs = kernel.beliefs.canonical_json()
    kernel.close()  # Simulated process loss: no orderly end_session call.

    with CognitiveKernel(path) as restored:
        assert restored.session_id == "s1"
        assert restored.episode_id == episode_id
        assert restored.last_event_at_ns == 100
        assert restored.beliefs.canonical_json() == expected_beliefs
        assert restored.memory.open_episode_for_session("s1")["episode_id"] == episode_id
        assert restored.memory.integrity_check() == "ok"


def test_orderly_session_end_closes_episode_and_clears_resume_state(tmp_path) -> None:
    path = tmp_path / "kernel.sqlite3"
    with CognitiveKernel(path) as kernel:
        kernel.start_session("s1", started_at_ns=0)
        episode_id = kernel.ingest_event(event("s1", 0, 100))
        kernel.end_session(ended_at_ns=150)
        assert kernel.memory.episode(episode_id)["boundary_reason"] == "session_end"
    with CognitiveKernel(path) as restored:
        assert restored.session_id is None
        assert restored.episode_id is None


def test_snapshot_json_is_canonical_in_database(tmp_path) -> None:
    with CognitiveKernel(tmp_path / "kernel.sqlite3") as kernel:
        kernel.start_session("s1", started_at_ns=0, metadata={"b": 2, "a": 1})
        row = kernel.memory.connection.execute(
            "SELECT payload_json FROM kernel_state WHERE state_key = 'cognitive_kernel'"
        ).fetchone()
        payload = json.loads(row["payload_json"])
        assert row["payload_json"] == json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )


def test_life_smoke_spans_two_bench_sessions_and_validates_a_primitive(tmp_path) -> None:
    """Engineering smoke only: certify one bounded simulator primitive across restarts."""

    database_path = tmp_path / "life.sqlite3"
    data_root = tmp_path / "j0"
    targets_by_session = (("life-a", 17001, 75.0), ("life-b", 17002, 105.0))
    errors: list[float] = []

    for session_index, (session_id, seed, target_deg) in enumerate(targets_by_session):
        clock_base = session_index * 10_000_000_000
        env = BenchHeadEnv()
        observation = env.reset(seed=seed)
        with CognitiveKernel(database_path) as kernel, SessionRecorder(
            data_root,
            session_id=session_id,
            metadata={"purpose": "life-001-engineering-smoke", "seed": seed},
        ) as recorder:
            kernel.start_session(
                session_id,
                started_at_ns=clock_base,
                metadata={"clock_domain": "life-smoke-logical-v1"},
            )
            if session_index == 0:
                kernel.transition_competence(
                    "bounded_head_orientation",
                    CompetenceStatus.LEARNING,
                    changed_at_ns=clock_base,
                    evidence={"kind": "engineering_smoke"},
                )
            for sequence_id in range(20):
                observation = env.step(target_deg)
                timestamp_ns = clock_base + int(round(observation.time * 1e9))
                observed_event = Event(
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
                    quality={"simulation": True},
                    calibration_version="bench-head-v1",
                )
                recorder.append(observed_event)
                kernel.ingest_event(
                    observed_event,
                    raw_ref=f"{recorder.events_path.resolve()}#L{sequence_id + 1}",
                )
            error_deg = abs(observation.as5600_deg - target_deg)
            errors.append(error_deg)
            kernel.update_belief(
                BeliefEstimate(
                    name="head_target_error_deg",
                    mean=error_deg,
                    variance=(360.0 / 4096.0) ** 2 / 12.0,
                    observed_at_ns=timestamp_ns,
                    received_at_ns=timestamp_ns,
                    source_id="life-001-analytic-evaluator",
                    clock_domain="life-smoke-logical-v1",
                    quality=1.0,
                    calibration_version="as5600-12bit",
                    model_version="analytic-v1",
                )
            )
            if session_index == 0:
                kernel.transition_competence(
                    "bounded_head_orientation",
                    CompetenceStatus.CANDIDATE,
                    changed_at_ns=timestamp_ns,
                    evidence={"absolute_error_deg": error_deg, "target_deg": target_deg},
                    model_version="bench-servo-analytic-v1",
                )
            else:
                evidence = {
                    "absolute_errors_deg": errors,
                    "seeds": [17001, 17002],
                    "criterion_deg": 2.0,
                }
                validation_digest = hashlib.sha256(
                    json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                assert max(errors) <= 2.0
                kernel.transition_competence(
                    "bounded_head_orientation",
                    CompetenceStatus.VALIDATED,
                    changed_at_ns=timestamp_ns,
                    evidence=evidence,
                    model_version="bench-servo-analytic-v1",
                    validation_digest=validation_digest,
                )
            kernel.end_session(ended_at_ns=timestamp_ns)
        env.close()

    with CognitiveKernel(database_path) as restored:
        assert restored.session_id is None
        assert restored.memory.competence_status(
            "bounded_head_orientation"
        ) is CompetenceStatus.VALIDATED
        assert restored.beliefs.get("head_target_error_deg").mean == pytest.approx(errors[-1])
