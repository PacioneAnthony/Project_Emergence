"""Append-only J0 session recorder with explicit storage quotas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import uuid
from typing import Any, Mapping

from j0.clock import host_time_ns
from j0.events import Event


GB = 1_000_000_000


class QuotaExceededError(RuntimeError):
    pass


@dataclass(frozen=True)
class QuotaPolicy:
    budget_bytes: int = 200 * GB
    warning_bytes: int = 160 * GB
    stop_long_session_bytes: int = 180 * GB

    def __post_init__(self) -> None:
        if not 0 < self.warning_bytes < self.stop_long_session_bytes <= self.budget_bytes:
            raise ValueError("quota thresholds must satisfy warning < stop <= budget")

    def state(self, used_bytes: int) -> str:
        if used_bytes >= self.budget_bytes:
            return "budget_exceeded"
        if used_bytes >= self.stop_long_session_bytes:
            return "long_session_blocked"
        if used_bytes >= self.warning_bytes:
            return "warning"
        return "ok"

    def allows_start(self, used_bytes: int, *, long_session: bool) -> bool:
        limit = self.stop_long_session_bytes if long_session else self.budget_bytes
        return used_bytes < limit


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except FileNotFoundError:
            continue
    return total


def generate_session_id(prefix: str = "j0") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


class SessionRecorder:
    """Write one immutable session directory.

    Event lines are flushed after every append. Manifest updates use atomic
    replacement and never rewrite the event stream.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        session_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        quota: QuotaPolicy | None = None,
        long_session: bool = False,
        fsync_every_events: int = 1,
    ) -> None:
        self.root = Path(root)
        self.sessions_root = self.root / "sessions"
        self.quota = quota or QuotaPolicy()
        self.long_session = long_session
        if fsync_every_events < 0:
            raise ValueError("fsync_every_events must be non-negative")
        self.fsync_every_events = fsync_every_events
        self.session_id = session_id or generate_session_id()
        self.session_dir = self.sessions_root / self.session_id
        self.events_path = self.session_dir / "events.jsonl"
        self.manifest_path = self.session_dir / "manifest.json"
        self._lock = threading.Lock()
        self._event_count = 0
        self._closed = False
        self._events_file: Any = None
        self._blob_streams: dict[tuple[str, str], Any] = {}

        self.sessions_root.mkdir(parents=True, exist_ok=True)
        used_bytes = directory_size(self.root)
        if not self.quota.allows_start(used_bytes, long_session=long_session):
            kind = "long" if long_session else "short"
            raise QuotaExceededError(
                f"cannot start {kind} session: {used_bytes} bytes used, quota state {self.quota.state(used_bytes)}"
            )
        if self.session_dir.exists():
            raise FileExistsError(f"session already exists: {self.session_dir}")

        (self.session_dir / "blobs" / "video").mkdir(parents=True)
        (self.session_dir / "blobs" / "audio").mkdir(parents=True)
        (self.session_dir / "reports").mkdir(parents=True)
        self._events_file = self.events_path.open("x", encoding="utf-8", newline="\n")
        self._manifest: dict[str, Any] = {
            "schema_version": 1,
            "session_id": self.session_id,
            "status": "recording",
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "started_monotonic_ns": host_time_ns(),
            "ended_at_utc": None,
            "event_count": 0,
            "quota": asdict(self.quota),
            "quota_state_at_start": self.quota.state(used_bytes),
            "metadata": dict(metadata or {}),
        }
        self._write_manifest()

    def _write_manifest(self) -> None:
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.manifest_path)

    def _ensure_open(self) -> None:
        if self._closed or self._events_file is None:
            raise RuntimeError("session recorder is closed")

    def append(self, event: Event) -> None:
        self._ensure_open()
        if event.session_id != self.session_id:
            raise ValueError(f"event belongs to {event.session_id}, expected {self.session_id}")

        line = event.to_json() + "\n"
        with self._lock:
            self._events_file.write(line)
            self._events_file.flush()
            if self.fsync_every_events and (self._event_count + 1) % self.fsync_every_events == 0:
                os.fsync(self._events_file.fileno())
            self._event_count += 1

    def write_blob(
        self,
        *,
        kind: str,
        data: bytes,
        suffix: str,
        event: Event,
    ) -> Event:
        """Persist a blob atomically, then append its referencing event."""

        self._ensure_open()
        if kind not in {"video", "audio"}:
            raise ValueError("blob kind must be video or audio")
        clean_suffix = suffix.lstrip(".")
        digest = hashlib.sha256(data).hexdigest()
        relative = Path("blobs") / kind / f"{event.sequence_id:010d}-{digest[:12]}.{clean_suffix}"
        target = self.session_dir / relative
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)

        payload = dict(event.payload)
        payload.update({"blob_path": relative.as_posix(), "blob_size": len(data), "blob_sha256": digest})
        blob_event = Event(
            session_id=event.session_id,
            event_type=event.event_type,
            source_id=event.source_id,
            sequence_id=event.sequence_id,
            source_timestamp_ns=event.source_timestamp_ns,
            host_receive_timestamp_ns=event.host_receive_timestamp_ns,
            payload=payload,
            quality=dict(event.quality),
            calibration_version=event.calibration_version,
            schema_version=event.schema_version,
        )
        self.append(blob_event)
        return blob_event

    def append_blob_stream(
        self,
        *,
        kind: str,
        stream_name: str,
        data: bytes,
        event: Event,
    ) -> Event:
        """Append bytes to one durable blob stream and record offset metadata."""

        self._ensure_open()
        if kind not in {"video", "audio"}:
            raise ValueError("blob kind must be video or audio")
        if Path(stream_name).name != stream_name:
            raise ValueError("stream_name must be a plain file name")

        key = (kind, stream_name)
        with self._lock:
            stream = self._blob_streams.get(key)
            if stream is None:
                target = self.session_dir / "blobs" / kind / stream_name
                stream = target.open("xb")
                self._blob_streams[key] = stream
            offset = stream.tell()
            stream.write(data)
            stream.flush()

        relative = Path("blobs") / kind / stream_name
        payload = dict(event.payload)
        payload.update(
            {
                "blob_path": relative.as_posix(),
                "blob_offset": offset,
                "blob_size": len(data),
                "blob_sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        stream_event = Event(
            session_id=event.session_id,
            event_type=event.event_type,
            source_id=event.source_id,
            sequence_id=event.sequence_id,
            source_timestamp_ns=event.source_timestamp_ns,
            host_receive_timestamp_ns=event.host_receive_timestamp_ns,
            payload=payload,
            quality=dict(event.quality),
            calibration_version=event.calibration_version,
            schema_version=event.schema_version,
        )
        self.append(stream_event)
        return stream_event

    def close(self, *, status: str = "complete", notes: str | None = None) -> None:
        if self._closed:
            return
        with self._lock:
            for stream in self._blob_streams.values():
                stream.flush()
                os.fsync(stream.fileno())
                stream.close()
            self._blob_streams.clear()
            self._events_file.flush()
            os.fsync(self._events_file.fileno())
            self._events_file.close()
            self._closed = True

        used_bytes = directory_size(self.root)
        self._manifest.update(
            status=status,
            ended_at_utc=datetime.now(timezone.utc).isoformat(),
            ended_monotonic_ns=host_time_ns(),
            event_count=self._event_count,
            session_size_bytes=directory_size(self.session_dir),
            project_size_bytes=used_bytes,
            quota_state_at_end=self.quota.state(used_bytes),
        )
        if notes:
            self._manifest["notes"] = notes
        self._write_manifest()

    def abort(self, notes: str) -> None:
        self.close(status="aborted", notes=notes)

    def __enter__(self) -> "SessionRecorder":
        return self

    def __exit__(self, exc_type: Any, exc: BaseException | None, traceback: Any) -> None:
        if exc is None:
            self.close()
        else:
            self.abort(f"{exc_type.__name__}: {exc}")
