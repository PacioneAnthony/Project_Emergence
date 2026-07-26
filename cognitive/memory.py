"""Transactional SQLite memory for derived cognitive state and raw-data references."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping
import uuid

from cognitive.models import CompetenceStatus, ExperimentProposal


SCHEMA_VERSION = 1


class SchemaVersionError(RuntimeError):
    pass


class InvalidCompetenceTransition(ValueError):
    pass


_ALLOWED_TRANSITIONS: dict[CompetenceStatus, frozenset[CompetenceStatus]] = {
    CompetenceStatus.UNKNOWN: frozenset({CompetenceStatus.LEARNING, CompetenceStatus.SUSPENDED}),
    CompetenceStatus.LEARNING: frozenset({CompetenceStatus.CANDIDATE, CompetenceStatus.SUSPENDED}),
    CompetenceStatus.CANDIDATE: frozenset(
        {CompetenceStatus.VALIDATED, CompetenceStatus.LEARNING, CompetenceStatus.SUSPENDED}
    ),
    CompetenceStatus.VALIDATED: frozenset({CompetenceStatus.REGRESSED, CompetenceStatus.SUSPENDED}),
    CompetenceStatus.REGRESSED: frozenset({CompetenceStatus.LEARNING, CompetenceStatus.SUSPENDED}),
    CompetenceStatus.SUSPENDED: frozenset({CompetenceStatus.LEARNING}),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class EpisodicMemory:
    """Own the compact derived-state database, never the raw sensor payloads."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self._initialize_or_validate_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "EpisodicMemory":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            yield self.connection
        except Exception:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def _initialize_or_validate_schema(self) -> None:
        table = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'"
        ).fetchone()
        if table is not None:
            row = self.connection.execute("SELECT version FROM schema_meta WHERE singleton = 1").fetchone()
            version = None if row is None else int(row["version"])
            if version != SCHEMA_VERSION:
                self.connection.close()
                raise SchemaVersionError(
                    f"unsupported cognitive memory schema version: {version}; expected {SCHEMA_VERSION}"
                )
            return

        with self.transaction() as db:
            db.executescript(
                """
                CREATE TABLE schema_meta (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    version INTEGER NOT NULL
                );
                INSERT INTO schema_meta(singleton, version) VALUES (1, 1);

                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at_ns INTEGER NOT NULL CHECK(started_at_ns >= 0),
                    ended_at_ns INTEGER CHECK(ended_at_ns IS NULL OR ended_at_ns >= started_at_ns),
                    status TEXT NOT NULL CHECK(status IN ('open', 'closed', 'aborted')),
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE episodes (
                    episode_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(session_id),
                    started_at_ns INTEGER NOT NULL CHECK(started_at_ns >= 0),
                    ended_at_ns INTEGER CHECK(ended_at_ns IS NULL OR ended_at_ns >= started_at_ns),
                    status TEXT NOT NULL CHECK(status IN ('open', 'closed')),
                    boundary_reason TEXT,
                    summary_json TEXT NOT NULL,
                    belief_snapshot_json TEXT
                );
                CREATE INDEX idx_episodes_session_time
                    ON episodes(session_id, started_at_ns);
                CREATE UNIQUE INDEX one_open_episode_per_session
                    ON episodes(session_id) WHERE status = 'open';

                CREATE TABLE event_refs (
                    event_ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
                    session_id TEXT NOT NULL REFERENCES sessions(session_id),
                    event_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    sequence_id INTEGER NOT NULL CHECK(sequence_id >= 0),
                    source_timestamp_ns INTEGER NOT NULL CHECK(source_timestamp_ns >= 0),
                    host_receive_timestamp_ns INTEGER NOT NULL CHECK(host_receive_timestamp_ns >= 0),
                    raw_ref TEXT,
                    event_digest TEXT NOT NULL,
                    out_of_order INTEGER NOT NULL CHECK(out_of_order IN (0, 1)),
                    metadata_json TEXT NOT NULL,
                    UNIQUE(session_id, event_type, source_id, sequence_id)
                );
                CREATE INDEX idx_event_refs_episode ON event_refs(episode_id, event_ref_id);

                CREATE TABLE competencies (
                    name TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    updated_at_ns INTEGER NOT NULL CHECK(updated_at_ns >= 0),
                    model_version TEXT,
                    validation_digest TEXT,
                    evidence_json TEXT NOT NULL
                );

                CREATE TABLE competence_history (
                    transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    changed_at_ns INTEGER NOT NULL CHECK(changed_at_ns >= 0),
                    model_version TEXT,
                    validation_digest TEXT,
                    evidence_json TEXT NOT NULL
                );
                CREATE INDEX idx_competence_history_name
                    ON competence_history(name, transition_id);

                CREATE TABLE model_versions (
                    module TEXT NOT NULL,
                    version TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('registered', 'candidate', 'validated', 'retired')),
                    artifact_ref TEXT NOT NULL,
                    artifact_digest TEXT NOT NULL,
                    created_at_ns INTEGER NOT NULL CHECK(created_at_ns >= 0),
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY(module, version)
                );
                CREATE UNIQUE INDEX one_validated_model_per_module
                    ON model_versions(module) WHERE state = 'validated';

                CREATE TABLE experiment_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(session_id),
                    experiment_id TEXT NOT NULL,
                    primitive TEXT NOT NULL,
                    created_at_ns INTEGER NOT NULL CHECK(created_at_ns >= 0),
                    status TEXT NOT NULL CHECK(status IN ('proposed', 'accepted', 'rejected', 'executed', 'cancelled')),
                    score REAL NOT NULL,
                    belief_revision INTEGER NOT NULL CHECK(belief_revision >= 0),
                    rationale_json TEXT NOT NULL
                );
                CREATE INDEX idx_proposals_session_experiment
                    ON experiment_proposals(session_id, experiment_id, created_at_ns);

                CREATE TABLE kernel_state (
                    state_key TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    updated_at_ns INTEGER NOT NULL CHECK(updated_at_ns >= 0),
                    payload_json TEXT NOT NULL
                );
                """
            )

    def integrity_check(self) -> str:
        row = self.connection.execute("PRAGMA integrity_check").fetchone()
        return str(row[0])

    def start_session(
        self,
        session_id: str,
        *,
        started_at_ns: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO sessions(session_id, started_at_ns, status, metadata_json)
                VALUES (?, ?, 'open', ?)
                """,
                (session_id, started_at_ns, _canonical_json(dict(metadata or {}))),
            )

    def start_session_atomic(
        self,
        session_id: str,
        *,
        started_at_ns: int,
        metadata: Mapping[str, Any],
        kernel_state_key: str,
        kernel_payload: Mapping[str, Any],
    ) -> None:
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO sessions(session_id, started_at_ns, status, metadata_json)
                VALUES (?, ?, 'open', ?)
                """,
                (session_id, started_at_ns, _canonical_json(dict(metadata))),
            )
            db.execute(
                """
                INSERT INTO kernel_state(state_key, schema_version, updated_at_ns, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    updated_at_ns = excluded.updated_at_ns,
                    payload_json = excluded.payload_json
                """,
                (
                    kernel_state_key,
                    SCHEMA_VERSION,
                    started_at_ns,
                    _canonical_json(kernel_payload),
                ),
            )

    def session(self, session_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()

    def close_session(self, session_id: str, *, ended_at_ns: int, status: str = "closed") -> None:
        if status not in {"closed", "aborted"}:
            raise ValueError("session status must be closed or aborted")
        with self.transaction() as db:
            current = db.execute(
                "SELECT started_at_ns, status FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if current is None:
                raise KeyError(f"unknown session: {session_id}")
            if current["status"] != "open":
                raise ValueError(f"session {session_id!r} is not open")
            if ended_at_ns < int(current["started_at_ns"]):
                raise ValueError("session end precedes start")
            db.execute(
                "UPDATE sessions SET ended_at_ns = ?, status = ? WHERE session_id = ?",
                (ended_at_ns, status, session_id),
            )

    def end_session_atomic(
        self,
        session_id: str,
        *,
        episode_id: str | None,
        ended_at_ns: int,
        status: str,
        belief_snapshot: Mapping[str, Any],
        kernel_state_key: str,
        kernel_payload: Mapping[str, Any],
    ) -> None:
        if status not in {"closed", "aborted"}:
            raise ValueError("session status must be closed or aborted")
        with self.transaction() as db:
            session = db.execute(
                "SELECT started_at_ns, status FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if session is None or session["status"] != "open":
                raise ValueError("session is missing or already closed")
            if ended_at_ns < int(session["started_at_ns"]):
                raise ValueError("session end precedes start")
            if episode_id is not None:
                cursor = db.execute(
                    """
                    UPDATE episodes SET
                        ended_at_ns = ?, status = 'closed', boundary_reason = 'session_end',
                        belief_snapshot_json = ?
                    WHERE episode_id = ? AND session_id = ? AND status = 'open'
                    """,
                    (
                        ended_at_ns,
                        _canonical_json(belief_snapshot),
                        episode_id,
                        session_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ValueError("active episode is missing or already closed")
            db.execute(
                "UPDATE sessions SET ended_at_ns = ?, status = ? WHERE session_id = ?",
                (ended_at_ns, status, session_id),
            )
            db.execute(
                """
                INSERT INTO kernel_state(state_key, schema_version, updated_at_ns, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    updated_at_ns = excluded.updated_at_ns,
                    payload_json = excluded.payload_json
                """,
                (
                    kernel_state_key,
                    SCHEMA_VERSION,
                    ended_at_ns,
                    _canonical_json(kernel_payload),
                ),
            )

    def open_episode(
        self,
        session_id: str,
        *,
        started_at_ns: int,
        summary: Mapping[str, Any] | None = None,
        episode_id: str | None = None,
    ) -> str:
        episode_id = episode_id or f"episode-{uuid.uuid4().hex}"
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO episodes(
                    episode_id, session_id, started_at_ns, status, summary_json
                ) VALUES (?, ?, ?, 'open', ?)
                """,
                (episode_id, session_id, started_at_ns, _canonical_json(dict(summary or {}))),
            )
        return episode_id

    def close_episode(
        self,
        episode_id: str,
        *,
        ended_at_ns: int,
        boundary_reason: str,
        belief_snapshot: Mapping[str, Any] | None = None,
    ) -> None:
        with self.transaction() as db:
            row = db.execute(
                "SELECT started_at_ns, status FROM episodes WHERE episode_id = ?", (episode_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown episode: {episode_id}")
            if row["status"] != "open":
                raise ValueError(f"episode {episode_id!r} is not open")
            if ended_at_ns < int(row["started_at_ns"]):
                raise ValueError("episode end precedes start")
            db.execute(
                """
                UPDATE episodes
                SET ended_at_ns = ?, status = 'closed', boundary_reason = ?,
                    belief_snapshot_json = ?
                WHERE episode_id = ?
                """,
                (
                    ended_at_ns,
                    boundary_reason,
                    None if belief_snapshot is None else _canonical_json(belief_snapshot),
                    episode_id,
                ),
            )

    def open_episode_for_session(self, session_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM episodes WHERE session_id = ? AND status = 'open'", (session_id,)
        ).fetchone()

    def episode(self, episode_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM episodes WHERE episode_id = ?", (episode_id,)
        ).fetchone()

    def append_event_ref(
        self,
        *,
        episode_id: str,
        session_id: str,
        event_type: str,
        source_id: str,
        sequence_id: int,
        source_timestamp_ns: int,
        host_receive_timestamp_ns: int,
        event_digest: str,
        raw_ref: str | None = None,
        out_of_order: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> int:
        with self.transaction() as db:
            cursor = db.execute(
                """
                INSERT INTO event_refs(
                    episode_id, session_id, event_type, source_id, sequence_id,
                    source_timestamp_ns, host_receive_timestamp_ns, raw_ref,
                    event_digest, out_of_order, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode_id,
                    session_id,
                    event_type,
                    source_id,
                    sequence_id,
                    source_timestamp_ns,
                    host_receive_timestamp_ns,
                    raw_ref,
                    event_digest,
                    int(out_of_order),
                    _canonical_json(dict(metadata or {})),
                ),
            )
        return int(cursor.lastrowid)

    def event_refs(self, episode_id: str) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM event_refs WHERE episode_id = ? ORDER BY event_ref_id", (episode_id,)
            )
        )

    def event_ref_by_identity(
        self,
        session_id: str,
        event_type: str,
        source_id: str,
        sequence_id: int,
    ) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT * FROM event_refs
            WHERE session_id = ? AND event_type = ? AND source_id = ? AND sequence_id = ?
            """,
            (session_id, event_type, source_id, sequence_id),
        ).fetchone()

    def ingest_event_atomic(
        self,
        *,
        session_id: str,
        current_episode_id: str | None,
        new_episode_id: str | None,
        new_episode_started_at_ns: int | None,
        close_current_at_ns: int | None,
        boundary_reason: str | None,
        closed_belief_snapshot: Mapping[str, Any] | None,
        event_type: str,
        source_id: str,
        sequence_id: int,
        source_timestamp_ns: int,
        host_receive_timestamp_ns: int,
        event_digest: str,
        raw_ref: str | None,
        out_of_order: bool,
        event_metadata: Mapping[str, Any],
        kernel_state_key: str,
        kernel_payload: Mapping[str, Any],
    ) -> str:
        """Rotate an episode, append one reference, and checkpoint in one commit."""

        next_episode_id = current_episode_id
        if new_episode_started_at_ns is not None:
            next_episode_id = new_episode_id or f"episode-{uuid.uuid4().hex}"
        elif new_episode_id is not None:
            raise ValueError("new_episode_id requires a new episode timestamp")
        if next_episode_id is None:
            raise ValueError("event ingestion requires a current or new episode")
        with self.transaction() as db:
            if current_episode_id is not None and boundary_reason is not None:
                if close_current_at_ns is None:
                    raise ValueError("episode rotation requires a closing timestamp")
                cursor = db.execute(
                    """
                    UPDATE episodes SET
                        ended_at_ns = ?, status = 'closed', boundary_reason = ?,
                        belief_snapshot_json = ?
                    WHERE episode_id = ? AND status = 'open'
                    """,
                    (
                        close_current_at_ns,
                        boundary_reason,
                        None
                        if closed_belief_snapshot is None
                        else _canonical_json(closed_belief_snapshot),
                        current_episode_id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ValueError("current episode is missing or already closed")
            if new_episode_started_at_ns is not None:
                db.execute(
                    """
                    INSERT INTO episodes(
                        episode_id, session_id, started_at_ns, status, summary_json
                    ) VALUES (?, ?, ?, 'open', '{}')
                    """,
                    (next_episode_id, session_id, new_episode_started_at_ns),
                )
            db.execute(
                """
                INSERT INTO event_refs(
                    episode_id, session_id, event_type, source_id, sequence_id,
                    source_timestamp_ns, host_receive_timestamp_ns, raw_ref,
                    event_digest, out_of_order, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_episode_id,
                    session_id,
                    event_type,
                    source_id,
                    sequence_id,
                    source_timestamp_ns,
                    host_receive_timestamp_ns,
                    raw_ref,
                    event_digest,
                    int(out_of_order),
                    _canonical_json(dict(event_metadata)),
                ),
            )
            db.execute(
                """
                INSERT INTO kernel_state(state_key, schema_version, updated_at_ns, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    updated_at_ns = excluded.updated_at_ns,
                    payload_json = excluded.payload_json
                """,
                (
                    kernel_state_key,
                    SCHEMA_VERSION,
                    host_receive_timestamp_ns,
                    _canonical_json(kernel_payload),
                ),
            )
        return next_episode_id

    def competence_status(self, name: str) -> CompetenceStatus:
        row = self.connection.execute(
            "SELECT status FROM competencies WHERE name = ?", (name,)
        ).fetchone()
        return CompetenceStatus.UNKNOWN if row is None else CompetenceStatus(row["status"])

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
        if not name:
            raise ValueError("competence name is required")
        with self.transaction() as db:
            row = db.execute(
                "SELECT status FROM competencies WHERE name = ?", (name,)
            ).fetchone()
            from_status = CompetenceStatus.UNKNOWN if row is None else CompetenceStatus(row["status"])
            if to_status not in _ALLOWED_TRANSITIONS[from_status]:
                raise InvalidCompetenceTransition(
                    f"invalid competence transition: {from_status.value} -> {to_status.value}"
                )
            if to_status is CompetenceStatus.VALIDATED and not validation_digest:
                raise InvalidCompetenceTransition("validated competence requires a validation digest")
            evidence_json = _canonical_json(dict(evidence))
            db.execute(
                """
                INSERT INTO competencies(
                    name, status, updated_at_ns, model_version, validation_digest, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    status = excluded.status,
                    updated_at_ns = excluded.updated_at_ns,
                    model_version = excluded.model_version,
                    validation_digest = excluded.validation_digest,
                    evidence_json = excluded.evidence_json
                """,
                (
                    name,
                    to_status.value,
                    changed_at_ns,
                    model_version,
                    validation_digest,
                    evidence_json,
                ),
            )
            db.execute(
                """
                INSERT INTO competence_history(
                    name, from_status, to_status, changed_at_ns, model_version,
                    validation_digest, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    from_status.value,
                    to_status.value,
                    changed_at_ns,
                    model_version,
                    validation_digest,
                    evidence_json,
                ),
            )

    def competence_history(self, name: str) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM competence_history WHERE name = ? ORDER BY transition_id", (name,)
            )
        )

    def register_model(
        self,
        module: str,
        version: str,
        *,
        artifact_ref: str,
        artifact_digest: str,
        created_at_ns: int,
        metadata: Mapping[str, Any] | None = None,
        state: str = "registered",
    ) -> None:
        if state not in {"registered", "candidate"}:
            raise ValueError("new model state must be registered or candidate")
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO model_versions(
                    module, version, state, artifact_ref, artifact_digest,
                    created_at_ns, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    module,
                    version,
                    state,
                    artifact_ref,
                    artifact_digest,
                    created_at_ns,
                    _canonical_json(dict(metadata or {})),
                ),
            )

    def promote_model(self, module: str, version: str) -> None:
        with self.transaction() as db:
            candidate = db.execute(
                "SELECT state FROM model_versions WHERE module = ? AND version = ?",
                (module, version),
            ).fetchone()
            if candidate is None or candidate["state"] != "candidate":
                raise ValueError("only a registered candidate model can be promoted")
            db.execute(
                "UPDATE model_versions SET state = 'retired' WHERE module = ? AND state = 'validated'",
                (module,),
            )
            db.execute(
                "UPDATE model_versions SET state = 'validated' WHERE module = ? AND version = ?",
                (module, version),
            )

    def validated_model(self, module: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM model_versions WHERE module = ? AND state = 'validated'", (module,)
        ).fetchone()

    def save_proposal(self, proposal: ExperimentProposal) -> None:
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO experiment_proposals(
                    proposal_id, session_id, experiment_id, primitive, created_at_ns,
                    status, score, belief_revision, rationale_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.session_id,
                    proposal.experiment_id,
                    proposal.primitive,
                    proposal.created_at_ns,
                    proposal.status,
                    proposal.score,
                    proposal.belief_revision,
                    _canonical_json(dict(proposal.rationale)),
                ),
            )

    def proposal_count(self, session_id: str, experiment_id: str) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS count FROM experiment_proposals
            WHERE session_id = ? AND experiment_id = ?
            """,
            (session_id, experiment_id),
        ).fetchone()
        return int(row["count"])

    def last_proposal_time(self, session_id: str, experiment_id: str) -> int | None:
        row = self.connection.execute(
            """
            SELECT MAX(created_at_ns) AS timestamp FROM experiment_proposals
            WHERE session_id = ? AND experiment_id = ?
            """,
            (session_id, experiment_id),
        ).fetchone()
        return None if row["timestamp"] is None else int(row["timestamp"])

    def set_proposal_status(self, proposal_id: str, status: str) -> None:
        if status not in {"accepted", "rejected", "executed", "cancelled"}:
            raise ValueError("invalid terminal proposal status")
        with self.transaction() as db:
            cursor = db.execute(
                "UPDATE experiment_proposals SET status = ? WHERE proposal_id = ?",
                (status, proposal_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"unknown proposal: {proposal_id}")

    def save_kernel_state(
        self,
        state_key: str,
        payload: Mapping[str, Any],
        *,
        updated_at_ns: int,
    ) -> None:
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO kernel_state(state_key, schema_version, updated_at_ns, payload_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(state_key) DO UPDATE SET
                    schema_version = excluded.schema_version,
                    updated_at_ns = excluded.updated_at_ns,
                    payload_json = excluded.payload_json
                """,
                (state_key, SCHEMA_VERSION, updated_at_ns, _canonical_json(payload)),
            )

    def load_kernel_state(self, state_key: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT schema_version, payload_json FROM kernel_state WHERE state_key = ?",
            (state_key,),
        ).fetchone()
        if row is None:
            return None
        if int(row["schema_version"]) != SCHEMA_VERSION:
            raise SchemaVersionError("unsupported kernel snapshot schema version")
        return dict(json.loads(row["payload_json"]))
