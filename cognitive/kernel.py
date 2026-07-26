"""Model-agnostic orchestration of beliefs, episode references, and proposals."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping
import uuid

from cognitive.beliefs import BeliefState
from cognitive.boundaries import BoundaryConfig, CausalBoundaryPolicy
from cognitive.experiments import SafeExperimentCatalog
from cognitive.memory import EpisodicMemory
from cognitive.models import (
    BeliefEstimate,
    CompetenceStatus,
    ExperimentProposal,
    ExperimentSignals,
    SafetyContext,
)
from j0.events import Event
from j0.replay import ReplayStats, SessionReplay


KERNEL_STATE_KEY = "cognitive_kernel"
KERNEL_SNAPSHOT_VERSION = 1


class CognitiveKernel:
    """Persistent cognitive plumbing; never an actuator or scientific model."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        catalog: SafeExperimentCatalog | None = None,
        boundary_config: BoundaryConfig | None = None,
    ) -> None:
        self.memory = EpisodicMemory(database_path)
        self.catalog = catalog or SafeExperimentCatalog()
        self.boundary_policy = CausalBoundaryPolicy(boundary_config)
        self.beliefs = BeliefState()
        self.session_id: str | None = None
        self.episode_id: str | None = None
        self.episode_started_at_ns: int | None = None
        self.last_event_at_ns: int | None = None
        self._restore()

    def close(self) -> None:
        self.memory.close()

    def __enter__(self) -> "CognitiveKernel":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _restore(self) -> None:
        snapshot = self.memory.load_kernel_state(KERNEL_STATE_KEY)
        if snapshot is None:
            return
        version = int(snapshot.get("schema_version", -1))
        if version != KERNEL_SNAPSHOT_VERSION:
            raise ValueError(f"unsupported cognitive kernel snapshot version: {version}")
        self.beliefs = BeliefState.from_snapshot(snapshot["belief_state"])
        self.session_id = snapshot.get("session_id")
        self.episode_id = snapshot.get("episode_id")
        self.episode_started_at_ns = snapshot.get("episode_started_at_ns")
        self.last_event_at_ns = snapshot.get("last_event_at_ns")
        if self.session_id is not None:
            session = self.memory.session(self.session_id)
            if session is None or session["status"] != "open":
                raise RuntimeError("kernel snapshot points to a non-open session")
        if self.episode_id is not None:
            episode = self.memory.episode(self.episode_id)
            if episode is None or episode["status"] != "open":
                raise RuntimeError("kernel snapshot points to a non-open episode")

    def _snapshot(
        self,
        *,
        episode_id: str | None = None,
        episode_started_at_ns: int | None = None,
        last_event_at_ns: int | None = None,
    ) -> dict[str, Any]:
        return {
            "schema_version": KERNEL_SNAPSHOT_VERSION,
            "belief_state": self.beliefs.snapshot(),
            "session_id": self.session_id,
            "episode_id": self.episode_id if episode_id is None else episode_id,
            "episode_started_at_ns": (
                self.episode_started_at_ns
                if episode_started_at_ns is None
                else episode_started_at_ns
            ),
            "last_event_at_ns": self.last_event_at_ns if last_event_at_ns is None else last_event_at_ns,
        }

    def checkpoint(self, *, now_ns: int) -> None:
        self.memory.save_kernel_state(KERNEL_STATE_KEY, self._snapshot(), updated_at_ns=now_ns)

    def start_session(
        self,
        session_id: str,
        *,
        started_at_ns: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if self.session_id is not None:
            raise RuntimeError(f"session {self.session_id!r} is already active")
        self.session_id = session_id
        try:
            self.memory.start_session_atomic(
                session_id,
                started_at_ns=started_at_ns,
                metadata=dict(metadata or {}),
                kernel_state_key=KERNEL_STATE_KEY,
                kernel_payload=self._snapshot(),
            )
        except Exception:
            self.session_id = None
            raise

    def update_belief(
        self,
        estimate: BeliefEstimate,
        *,
        checkpoint: bool = True,
        allow_clock_change: bool = False,
    ) -> bool:
        updated = self.beliefs.update(estimate, allow_clock_change=allow_clock_change)
        if updated and checkpoint:
            self.checkpoint(now_ns=estimate.received_at_ns)
        return updated

    def ingest_event(
        self,
        event: Event,
        *,
        raw_ref: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        if self.session_id is None:
            raise RuntimeError("an active session is required")
        if event.session_id != self.session_id:
            raise ValueError("event session does not match the active kernel session")

        event_digest = hashlib.sha256(event.to_json().encode("utf-8")).hexdigest()
        existing = self.memory.event_ref_by_identity(
            event.session_id,
            event.event_type,
            event.source_id,
            event.sequence_id,
        )
        if existing is not None:
            if existing["event_digest"] != event_digest:
                raise ValueError("event identity collision with a different digest")
            return str(existing["episode_id"])

        timestamp_ns = event.host_receive_timestamp_ns
        out_of_order = self.last_event_at_ns is not None and timestamp_ns < self.last_event_at_ns
        reason = self.boundary_policy.boundary_before(
            event_type=event.event_type,
            timestamp_ns=timestamp_ns,
            episode_started_at_ns=self.episode_started_at_ns,
            last_event_at_ns=self.last_event_at_ns,
        )
        if out_of_order:
            reason = None

        old_episode_id = self.episode_id
        new_episode_started_at_ns: int | None = None
        new_episode_id: str | None = None
        close_current_at_ns: int | None = None
        if old_episode_id is None:
            new_episode_started_at_ns = timestamp_ns
            new_episode_id = f"episode-{uuid.uuid4().hex}"
        elif reason is not None:
            new_episode_started_at_ns = timestamp_ns
            new_episode_id = f"episode-{uuid.uuid4().hex}"
            close_current_at_ns = self.last_event_at_ns

        effective_episode_id = new_episode_id or old_episode_id
        effective_start = (
            new_episode_started_at_ns
            if new_episode_started_at_ns is not None
            else self.episode_started_at_ns
        )
        effective_last = self.last_event_at_ns if out_of_order else timestamp_ns
        snapshot = self._snapshot(
            episode_id=effective_episode_id,
            episode_started_at_ns=effective_start,
            last_event_at_ns=effective_last,
        )
        stored_episode_id = self.memory.ingest_event_atomic(
            session_id=self.session_id,
            current_episode_id=old_episode_id,
            new_episode_id=new_episode_id,
            new_episode_started_at_ns=new_episode_started_at_ns,
            close_current_at_ns=close_current_at_ns,
            boundary_reason=None if old_episode_id is None else reason,
            closed_belief_snapshot=self.beliefs.snapshot(),
            event_type=event.event_type,
            source_id=event.source_id,
            sequence_id=event.sequence_id,
            source_timestamp_ns=event.source_timestamp_ns,
            host_receive_timestamp_ns=event.host_receive_timestamp_ns,
            event_digest=event_digest,
            raw_ref=raw_ref,
            out_of_order=out_of_order,
            event_metadata={
                "quality": dict(event.quality),
                "calibration_version": event.calibration_version,
                **dict(metadata or {}),
            },
            kernel_state_key=KERNEL_STATE_KEY,
            kernel_payload=snapshot,
        )
        self.episode_id = stored_episode_id
        self.episode_started_at_ns = effective_start
        self.last_event_at_ns = effective_last
        return stored_episode_id

    def ingest_replay(self, session_dir: str | Path) -> ReplayStats:
        """Ingest a J0 log in file order with durable line references."""

        replay = SessionReplay(session_dir)
        events_path = replay.events_path.resolve()
        digest = hashlib.sha256()
        count = 0
        for line_number, replayed_event in enumerate(replay.events(), start=1):
            self.ingest_event(
                replayed_event,
                raw_ref=f"{events_path}#L{line_number}",
                metadata={"ingestion": "j0_replay"},
            )
            digest.update(replayed_event.to_json().encode("utf-8"))
            digest.update(b"\n")
            count += 1
        return ReplayStats(count, digest.hexdigest(), replay.ignored_trailing_bytes)

    def propose_experiment(
        self,
        experiment_id: str,
        *,
        now_ns: int,
        signals: ExperimentSignals,
        safety: SafetyContext,
    ) -> ExperimentProposal:
        if self.session_id is None:
            raise RuntimeError("an active session is required")
        proposal = self.catalog.propose(
            experiment_id,
            session_id=self.session_id,
            now_ns=now_ns,
            signals=signals,
            safety=safety,
            beliefs=self.beliefs,
            memory=self.memory,
        )
        self.memory.save_proposal(proposal)
        return proposal

    def transition_competence(
        self,
        name: str,
        to_status: CompetenceStatus,
        *,
        changed_at_ns: int,
        evidence: Mapping[str, Any],
        model_version: str | None = None,
        validation_digest: str | None = None,
    ) -> None:
        self.memory.transition_competence(
            name,
            to_status,
            changed_at_ns=changed_at_ns,
            evidence=evidence,
            model_version=model_version,
            validation_digest=validation_digest,
        )

    def end_session(self, *, ended_at_ns: int, status: str = "closed") -> None:
        if self.session_id is None:
            raise RuntimeError("no active session")
        session_id = self.session_id
        if self.last_event_at_ns is not None and ended_at_ns < self.last_event_at_ns:
            raise ValueError("session end precedes the last observed event")
        terminal_snapshot = {
            "schema_version": KERNEL_SNAPSHOT_VERSION,
            "belief_state": self.beliefs.snapshot(),
            "session_id": None,
            "episode_id": None,
            "episode_started_at_ns": None,
            "last_event_at_ns": None,
        }
        self.memory.end_session_atomic(
            session_id,
            episode_id=self.episode_id,
            ended_at_ns=ended_at_ns,
            status=status,
            belief_snapshot=self.beliefs.snapshot(),
            kernel_state_key=KERNEL_STATE_KEY,
            kernel_payload=terminal_snapshot,
        )
        self.session_id = None
        self.episode_id = None
        self.episode_started_at_ns = None
        self.last_event_at_ns = None
