"""Transactional SQLite memory for derived cognitive state and raw-data references."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping
import uuid

from cognitive.models import CompetenceStatus, ExperimentProposal


SCHEMA_VERSION = 4


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
            if version == 1:
                self._migrate_v1_to_v2()
                version = 2
            if version == 2:
                self._migrate_v2_to_v3()
                version = 3
            if version == 3:
                self._migrate_v3_to_v4()
                version = 4
            if version == SCHEMA_VERSION:
                return
            self.connection.close()
            raise SchemaVersionError(
                f"unsupported cognitive memory schema version: {version}; expected {SCHEMA_VERSION}"
            )

        with self.transaction() as db:
            db.executescript(
                """
                CREATE TABLE schema_meta (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    version INTEGER NOT NULL
                );
                INSERT INTO schema_meta(singleton, version) VALUES (1, 4);

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

                CREATE TABLE competence_assessments (
                    competence_name TEXT NOT NULL,
                    assessment_digest TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    outcome TEXT NOT NULL CHECK(
                        outcome IN ('validated', 'regressed', 'inconclusive')
                    ),
                    assessed_at_ns INTEGER NOT NULL CHECK(assessed_at_ns >= 0),
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    transition_path_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    model_version TEXT,
                    PRIMARY KEY(competence_name, assessment_digest)
                );
                CREATE INDEX idx_competence_assessments_time
                    ON competence_assessments(competence_name, assessed_at_ns);

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

                CREATE TABLE experiment_executions (
                    execution_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL UNIQUE REFERENCES experiment_proposals(proposal_id),
                    experiment_id TEXT NOT NULL,
                    j0_session_id TEXT NOT NULL UNIQUE,
                    session_ref TEXT NOT NULL,
                    started_at_ns INTEGER NOT NULL CHECK(started_at_ns >= 0),
                    completed_at_ns INTEGER CHECK(
                        completed_at_ns IS NULL OR completed_at_ns >= started_at_ns
                    ),
                    status TEXT NOT NULL CHECK(status IN ('running', 'complete', 'aborted')),
                    source_digest TEXT,
                    result_summary_json TEXT,
                    CHECK(
                        (status = 'complete' AND completed_at_ns IS NOT NULL
                            AND source_digest IS NOT NULL AND result_summary_json IS NOT NULL)
                        OR status != 'complete'
                    )
                );
                CREATE INDEX idx_executions_experiment_time
                    ON experiment_executions(experiment_id, completed_at_ns, execution_id);

                CREATE TABLE development_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL UNIQUE REFERENCES experiment_proposals(proposal_id),
                    execution_id TEXT NOT NULL UNIQUE,
                    j0_session_id TEXT NOT NULL UNIQUE,
                    seed INTEGER NOT NULL CHECK(seed >= 0 AND seed <= 4294967295),
                    experiment_id TEXT NOT NULL,
                    primitive TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(
                        status IN ('selected', 'executed', 'complete', 'aborted')
                    ),
                    created_at_ns INTEGER NOT NULL CHECK(created_at_ns >= 0),
                    executed_at_ns INTEGER,
                    completed_at_ns INTEGER,
                    activation_json TEXT NOT NULL,
                    assessment_digest TEXT,
                    result_json TEXT NOT NULL
                );
                CREATE INDEX idx_development_cycles_status
                    ON development_cycles(status, created_at_ns);

                CREATE TABLE kernel_state (
                    state_key TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    updated_at_ns INTEGER NOT NULL CHECK(updated_at_ns >= 0),
                    payload_json TEXT NOT NULL
                );
                """
            )

    def _migrate_v1_to_v2(self) -> None:
        """Apply the sole supported additive migration."""

        with self.transaction() as db:
            db.execute(
                """
                CREATE TABLE experiment_executions (
                    execution_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL UNIQUE REFERENCES experiment_proposals(proposal_id),
                    experiment_id TEXT NOT NULL,
                    j0_session_id TEXT NOT NULL UNIQUE,
                    session_ref TEXT NOT NULL,
                    started_at_ns INTEGER NOT NULL CHECK(started_at_ns >= 0),
                    completed_at_ns INTEGER CHECK(
                        completed_at_ns IS NULL OR completed_at_ns >= started_at_ns
                    ),
                    status TEXT NOT NULL CHECK(status IN ('running', 'complete', 'aborted')),
                    source_digest TEXT,
                    result_summary_json TEXT,
                    CHECK(
                        (status = 'complete' AND completed_at_ns IS NOT NULL
                            AND source_digest IS NOT NULL AND result_summary_json IS NOT NULL)
                        OR status != 'complete'
                    )
                )
                """
            )
            db.execute(
                """
                CREATE INDEX idx_executions_experiment_time
                ON experiment_executions(experiment_id, completed_at_ns, execution_id)
                """
            )
            db.execute("UPDATE kernel_state SET schema_version = 2")
            db.execute("UPDATE schema_meta SET version = 2 WHERE singleton = 1")

    def _migrate_v2_to_v3(self) -> None:
        """Add idempotent competence assessment applications."""

        with self.transaction() as db:
            db.execute(
                """
                CREATE TABLE competence_assessments (
                    competence_name TEXT NOT NULL,
                    assessment_digest TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    outcome TEXT NOT NULL CHECK(
                        outcome IN ('validated', 'regressed', 'inconclusive')
                    ),
                    assessed_at_ns INTEGER NOT NULL CHECK(assessed_at_ns >= 0),
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    transition_path_json TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    model_version TEXT,
                    PRIMARY KEY(competence_name, assessment_digest)
                )
                """
            )
            db.execute(
                """
                CREATE INDEX idx_competence_assessments_time
                ON competence_assessments(competence_name, assessed_at_ns)
                """
            )
            db.execute("UPDATE kernel_state SET schema_version = 3")
            db.execute("UPDATE schema_meta SET version = 3 WHERE singleton = 1")

    def _migrate_v3_to_v4(self) -> None:
        """Add the persistent developmental cycle supervisor journal."""

        with self.transaction() as db:
            db.execute(
                """
                CREATE TABLE development_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    proposal_id TEXT NOT NULL UNIQUE REFERENCES experiment_proposals(proposal_id),
                    execution_id TEXT NOT NULL UNIQUE,
                    j0_session_id TEXT NOT NULL UNIQUE,
                    seed INTEGER NOT NULL CHECK(seed >= 0 AND seed <= 4294967295),
                    experiment_id TEXT NOT NULL,
                    primitive TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(
                        status IN ('selected', 'executed', 'complete', 'aborted')
                    ),
                    created_at_ns INTEGER NOT NULL CHECK(created_at_ns >= 0),
                    executed_at_ns INTEGER,
                    completed_at_ns INTEGER,
                    activation_json TEXT NOT NULL,
                    assessment_digest TEXT,
                    result_json TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE INDEX idx_development_cycles_status
                ON development_cycles(status, created_at_ns)
                """
            )
            db.execute("UPDATE kernel_state SET schema_version = 4")
            db.execute("UPDATE schema_meta SET version = 4 WHERE singleton = 1")

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

    def apply_competence_assessment(
        self,
        name: str,
        *,
        experiment_id: str,
        outcome: str,
        assessed_at_ns: int,
        assessment_digest: str,
        evidence: Mapping[str, Any],
        model_version: str | None = None,
    ) -> tuple[bool, CompetenceStatus, CompetenceStatus, tuple[CompetenceStatus, ...]]:
        """Apply one assessment and its full transition path atomically."""

        if not name or not experiment_id or not assessment_digest:
            raise ValueError("competence, experiment, and assessment digest are required")
        if outcome not in {"validated", "regressed", "inconclusive"}:
            raise ValueError("invalid competence assessment outcome")
        if assessed_at_ns < 0:
            raise ValueError("assessment timestamp must be non-negative")
        evidence_json = _canonical_json(dict(evidence))

        with self.transaction() as db:
            existing = db.execute(
                """
                SELECT * FROM competence_assessments
                WHERE competence_name = ? AND assessment_digest = ?
                """,
                (name, assessment_digest),
            ).fetchone()
            if existing is not None:
                if (
                    existing["experiment_id"] != experiment_id
                    or existing["outcome"] != outcome
                    or existing["evidence_json"] != evidence_json
                    or existing["model_version"] != model_version
                ):
                    raise ValueError("competence assessment digest collision")
                path = tuple(
                    CompetenceStatus(value)
                    for value in json.loads(existing["transition_path_json"])
                )
                return (
                    False,
                    CompetenceStatus(existing["from_status"]),
                    CompetenceStatus(existing["to_status"]),
                    path,
                )

            last_assessment = db.execute(
                """
                SELECT MAX(assessed_at_ns) AS timestamp
                FROM competence_assessments WHERE competence_name = ?
                """,
                (name,),
            ).fetchone()
            if (
                last_assessment["timestamp"] is not None
                and assessed_at_ns < int(last_assessment["timestamp"])
            ):
                raise ValueError("competence assessment is older than persisted evidence")
            row = db.execute(
                "SELECT status, updated_at_ns FROM competencies WHERE name = ?",
                (name,),
            ).fetchone()
            if row is not None and assessed_at_ns < int(row["updated_at_ns"]):
                raise ValueError("competence assessment precedes the current state")
            from_status = (
                CompetenceStatus.UNKNOWN
                if row is None
                else CompetenceStatus(row["status"])
            )
            if from_status is CompetenceStatus.SUSPENDED:
                raise InvalidCompetenceTransition(
                    "a suspended competence requires explicit reactivation authority"
                )

            if outcome == "validated":
                paths = {
                    CompetenceStatus.UNKNOWN: (
                        CompetenceStatus.LEARNING,
                        CompetenceStatus.CANDIDATE,
                        CompetenceStatus.VALIDATED,
                    ),
                    CompetenceStatus.LEARNING: (
                        CompetenceStatus.CANDIDATE,
                        CompetenceStatus.VALIDATED,
                    ),
                    CompetenceStatus.CANDIDATE: (CompetenceStatus.VALIDATED,),
                    CompetenceStatus.VALIDATED: (),
                    CompetenceStatus.REGRESSED: (
                        CompetenceStatus.LEARNING,
                        CompetenceStatus.CANDIDATE,
                        CompetenceStatus.VALIDATED,
                    ),
                }
            elif outcome == "regressed":
                paths = {
                    CompetenceStatus.UNKNOWN: (CompetenceStatus.LEARNING,),
                    CompetenceStatus.LEARNING: (),
                    CompetenceStatus.CANDIDATE: (CompetenceStatus.LEARNING,),
                    CompetenceStatus.VALIDATED: (CompetenceStatus.REGRESSED,),
                    CompetenceStatus.REGRESSED: (),
                }
            else:
                paths = {
                    status: ()
                    for status in (
                        CompetenceStatus.UNKNOWN,
                        CompetenceStatus.LEARNING,
                        CompetenceStatus.CANDIDATE,
                        CompetenceStatus.VALIDATED,
                        CompetenceStatus.REGRESSED,
                    )
                }
            path = paths[from_status]
            current = from_status
            transition_evidence = {
                **dict(evidence),
                "assessment_digest": assessment_digest,
                "automatic_application": "life_005_v1",
            }
            transition_evidence_json = _canonical_json(transition_evidence)
            for target in path:
                if target not in _ALLOWED_TRANSITIONS[current]:
                    raise InvalidCompetenceTransition(
                        f"invalid automatic competence transition: "
                        f"{current.value} -> {target.value}"
                    )
                validation_digest = (
                    assessment_digest
                    if target is CompetenceStatus.VALIDATED
                    else None
                )
                db.execute(
                    """
                    INSERT INTO competencies(
                        name, status, updated_at_ns, model_version,
                        validation_digest, evidence_json
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
                        target.value,
                        assessed_at_ns,
                        model_version,
                        validation_digest,
                        transition_evidence_json,
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
                        current.value,
                        target.value,
                        assessed_at_ns,
                        model_version,
                        validation_digest,
                        transition_evidence_json,
                    ),
                )
                current = target

            db.execute(
                """
                INSERT INTO competence_assessments(
                    competence_name, assessment_digest, experiment_id, outcome,
                    assessed_at_ns, from_status, to_status, transition_path_json,
                    evidence_json, model_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    assessment_digest,
                    experiment_id,
                    outcome,
                    assessed_at_ns,
                    from_status.value,
                    current.value,
                    _canonical_json([status.value for status in path]),
                    evidence_json,
                    model_version,
                ),
            )
            return True, from_status, current, path

    def competence_assessments(self, name: str) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT * FROM competence_assessments
                WHERE competence_name = ?
                ORDER BY assessed_at_ns, assessment_digest
                """,
                (name,),
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

    def proposal(self, proposal_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM experiment_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()

    def save_proposal_and_cycle(
        self,
        proposal: ExperimentProposal,
        *,
        cycle_id: str,
        execution_id: str,
        j0_session_id: str,
        seed: int,
        activation: Mapping[str, Any],
    ) -> None:
        """Persist one supervised proposal and its cycle atomically."""

        if not cycle_id or not execution_id or not j0_session_id:
            raise ValueError("cycle and execution identities are required")
        if not 0 <= seed <= 0xFFFFFFFF:
            raise ValueError("cycle seed must be in [0, 2^32-1]")
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
            db.execute(
                """
                INSERT INTO development_cycles(
                    cycle_id, proposal_id, execution_id, j0_session_id, seed,
                    experiment_id, primitive, status, created_at_ns,
                    activation_json, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'selected', ?, ?, '{}')
                """,
                (
                    cycle_id,
                    proposal.proposal_id,
                    execution_id,
                    j0_session_id,
                    seed,
                    proposal.experiment_id,
                    proposal.primitive,
                    proposal.created_at_ns,
                    _canonical_json(dict(activation)),
                ),
            )

    def development_cycle(self, cycle_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM development_cycles WHERE cycle_id = ?",
            (cycle_id,),
        ).fetchone()

    def active_development_cycle_count(self, cognitive_session_id: str) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM development_cycles AS cycle
            JOIN experiment_proposals AS proposal
                ON proposal.proposal_id = cycle.proposal_id
            WHERE proposal.session_id = ?
                AND cycle.status IN ('selected', 'executed')
            """,
            (cognitive_session_id,),
        ).fetchone()
        return int(row["count"])

    def advance_development_cycle(
        self,
        cycle_id: str,
        *,
        expected_status: str,
        to_status: str,
        changed_at_ns: int,
        result: Mapping[str, Any],
        assessment_digest: str | None = None,
    ) -> None:
        allowed = {
            "selected": {"executed", "aborted"},
            "executed": {"complete", "aborted"},
        }
        if to_status not in allowed.get(expected_status, set()):
            raise ValueError("invalid development cycle transition")
        if changed_at_ns < 0:
            raise ValueError("cycle transition timestamp must be non-negative")
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM development_cycles WHERE cycle_id = ?",
                (cycle_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown development cycle: {cycle_id}")
            if row["status"] != expected_status:
                raise ValueError(
                    f"development cycle is {row['status']}, expected {expected_status}"
                )
            previous_time = (
                row["executed_at_ns"]
                if expected_status == "executed"
                else row["created_at_ns"]
            )
            if changed_at_ns < int(previous_time):
                raise ValueError("cycle transition precedes its previous phase")
            executed_at_ns = (
                changed_at_ns if to_status == "executed" else row["executed_at_ns"]
            )
            completed_at_ns = (
                changed_at_ns if to_status in {"complete", "aborted"} else None
            )
            db.execute(
                """
                UPDATE development_cycles SET
                    status = ?, executed_at_ns = ?, completed_at_ns = ?,
                    assessment_digest = ?, result_json = ?
                WHERE cycle_id = ?
                """,
                (
                    to_status,
                    executed_at_ns,
                    completed_at_ns,
                    assessment_digest,
                    _canonical_json(dict(result)),
                    cycle_id,
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
        if status not in {"accepted", "rejected", "cancelled"}:
            raise ValueError("invalid direct proposal status")
        with self.transaction() as db:
            running = db.execute(
                """
                SELECT 1 FROM experiment_executions
                WHERE proposal_id = ? AND status = 'running'
                """,
                (proposal_id,),
            ).fetchone()
            if running is not None:
                raise ValueError("a proposal with a running execution cannot be changed directly")
            cursor = db.execute(
                "UPDATE experiment_proposals SET status = ? WHERE proposal_id = ?",
                (status, proposal_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"unknown proposal: {proposal_id}")

    def begin_experiment_execution(
        self,
        execution_id: str,
        *,
        proposal_id: str,
        cognitive_session_id: str,
        j0_session_id: str,
        session_ref: str,
        started_at_ns: int,
    ) -> None:
        if not execution_id or not proposal_id or not j0_session_id or not session_ref:
            raise ValueError("execution, proposal, J0 session, and session reference are required")
        if started_at_ns < 0:
            raise ValueError("execution start must be non-negative")
        with self.transaction() as db:
            proposal = db.execute(
                """
                SELECT session_id, experiment_id, status
                FROM experiment_proposals WHERE proposal_id = ?
                """,
                (proposal_id,),
            ).fetchone()
            if proposal is None:
                raise KeyError(f"unknown proposal: {proposal_id}")
            if proposal["session_id"] != cognitive_session_id:
                raise ValueError("proposal does not belong to the active cognitive session")
            existing = db.execute(
                "SELECT * FROM experiment_executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
            if existing is not None:
                expected = (
                    proposal_id,
                    j0_session_id,
                    session_ref,
                    started_at_ns,
                )
                actual = (
                    existing["proposal_id"],
                    existing["j0_session_id"],
                    existing["session_ref"],
                    int(existing["started_at_ns"]),
                )
                if actual != expected:
                    raise ValueError("execution identity collision")
                return

            if proposal["status"] not in {"proposed", "accepted"}:
                raise ValueError("proposal is not executable")
            try:
                db.execute(
                    """
                    INSERT INTO experiment_executions(
                        execution_id, proposal_id, experiment_id, j0_session_id,
                        session_ref, started_at_ns, status
                    ) VALUES (?, ?, ?, ?, ?, ?, 'running')
                    """,
                    (
                        execution_id,
                        proposal_id,
                        proposal["experiment_id"],
                        j0_session_id,
                        session_ref,
                        started_at_ns,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError("proposal or J0 session is already attributed") from error
            db.execute(
                "UPDATE experiment_proposals SET status = 'accepted' WHERE proposal_id = ?",
                (proposal_id,),
            )

    def complete_experiment_execution(
        self,
        execution_id: str,
        *,
        completed_at_ns: int,
        experiment_id: str,
        j0_session_id: str,
        source_digest: str,
        result_summary: Mapping[str, Any],
    ) -> None:
        if completed_at_ns < 0 or not source_digest:
            raise ValueError("completion time and source digest are required")
        summary_json = _canonical_json(dict(result_summary))
        with self.transaction() as db:
            execution = db.execute(
                "SELECT * FROM experiment_executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
            if execution is None:
                raise KeyError(f"unknown execution: {execution_id}")
            if execution["status"] == "complete":
                expected = (
                    completed_at_ns,
                    experiment_id,
                    j0_session_id,
                    source_digest,
                    summary_json,
                )
                actual = (
                    int(execution["completed_at_ns"]),
                    execution["experiment_id"],
                    execution["j0_session_id"],
                    execution["source_digest"],
                    execution["result_summary_json"],
                )
                if actual != expected:
                    raise ValueError("completed execution collision")
                return
            if execution["status"] != "running":
                raise ValueError("execution is not running")
            if execution["experiment_id"] != experiment_id:
                raise ValueError("result experiment does not match execution")
            if execution["j0_session_id"] != j0_session_id:
                raise ValueError("result J0 session does not match execution")
            if completed_at_ns < int(execution["started_at_ns"]):
                raise ValueError("execution completion precedes start")
            db.execute(
                """
                UPDATE experiment_executions SET
                    completed_at_ns = ?, status = 'complete', source_digest = ?,
                    result_summary_json = ?
                WHERE execution_id = ?
                """,
                (completed_at_ns, source_digest, summary_json, execution_id),
            )
            db.execute(
                "UPDATE experiment_proposals SET status = 'executed' WHERE proposal_id = ?",
                (execution["proposal_id"],),
            )

    def abort_experiment_execution(self, execution_id: str) -> None:
        with self.transaction() as db:
            execution = db.execute(
                "SELECT proposal_id, status FROM experiment_executions WHERE execution_id = ?",
                (execution_id,),
            ).fetchone()
            if execution is None:
                raise KeyError(f"unknown execution: {execution_id}")
            if execution["status"] == "aborted":
                return
            if execution["status"] != "running":
                raise ValueError("only a running execution can be aborted")
            db.execute(
                "UPDATE experiment_executions SET status = 'aborted' WHERE execution_id = ?",
                (execution_id,),
            )
            db.execute(
                "UPDATE experiment_proposals SET status = 'cancelled' WHERE proposal_id = ?",
                (execution["proposal_id"],),
            )

    def experiment_execution(self, execution_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM experiment_executions WHERE execution_id = ?",
            (execution_id,),
        ).fetchone()

    def completed_experiment_executions(self, experiment_id: str) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                """
                SELECT * FROM experiment_executions
                WHERE experiment_id = ? AND status = 'complete'
                ORDER BY completed_at_ns, execution_id
                """,
                (experiment_id,),
            ).fetchall()
        )

    def running_execution_count(self, cognitive_session_id: str) -> int:
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM experiment_executions AS execution
            JOIN experiment_proposals AS proposal
                ON proposal.proposal_id = execution.proposal_id
            WHERE proposal.session_id = ? AND execution.status = 'running'
            """,
            (cognitive_session_id,),
        ).fetchone()
        return int(row["count"])

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
