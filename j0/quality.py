"""Automatic integrity and rate report for J0 sessions."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Iterable

from j0.events import Event
from j0.recorder import directory_size
from j0.replay import SessionReplay


@dataclass(frozen=True)
class SourceQuality:
    source_id: str
    event_type: str
    count: int
    duration_s: float
    rate_hz: float
    max_gap_ms: float
    median_gap_ms: float
    sequence_gaps: int
    duplicate_or_reversed_sequences: int
    reversed_source_timestamps: int
    reversed_host_timestamps: int


RATE_RULES = {
    "imu_sample": {"minimum_hz": 95.0, "maximum_gap_ms": 50.0},
    "range_sample": {"minimum_hz": 18.0, "maximum_gap_ms": 250.0},
    "video_frame": {"minimum_hz": 27.0, "maximum_gap_ms": 250.0},
    "audio_chunk": {"minimum_hz": 10.0, "maximum_gap_ms": 200.0},
}
REQUIRED_J0_EVENT_TYPES = {"imu_sample", "range_sample", "video_frame", "audio_chunk", "servo_state"}


def _analyze_group(source_id: str, event_type: str, events: list[Event]) -> SourceQuality:
    source_times = [event.source_timestamp_ns for event in events]
    host_times = [event.host_receive_timestamp_ns for event in events]
    sequences = [event.sequence_id for event in events]
    gaps = [max(0, current - previous) for previous, current in zip(source_times, source_times[1:])]
    duration_ns = max(0, source_times[-1] - source_times[0]) if len(source_times) > 1 else 0
    rate_hz = (len(events) - 1) / (duration_ns / 1_000_000_000) if duration_ns > 0 else 0.0
    sequence_gaps = sum(max(0, current - previous - 1) for previous, current in zip(sequences, sequences[1:]))

    return SourceQuality(
        source_id=source_id,
        event_type=event_type,
        count=len(events),
        duration_s=duration_ns / 1_000_000_000,
        rate_hz=rate_hz,
        max_gap_ms=(max(gaps) / 1_000_000) if gaps else 0.0,
        median_gap_ms=(median(gaps) / 1_000_000) if gaps else 0.0,
        sequence_gaps=sequence_gaps,
        duplicate_or_reversed_sequences=sum(
            current <= previous for previous, current in zip(sequences, sequences[1:])
        ),
        reversed_source_timestamps=sum(
            current < previous for previous, current in zip(source_times, source_times[1:])
        ),
        reversed_host_timestamps=sum(current < previous for previous, current in zip(host_times, host_times[1:])),
    )


def analyze_events(events: Iterable[Event]) -> dict:
    event_list = list(events)
    groups: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in event_list:
        groups[(event.source_id, event.event_type)].append(event)

    sources = [_analyze_group(source_id, event_type, grouped) for (source_id, event_type), grouped in groups.items()]
    violations: list[dict] = []
    for source in sources:
        rule = RATE_RULES.get(source.event_type)
        if not rule or source.count < 2:
            continue
        if source.rate_hz < rule["minimum_hz"]:
            violations.append(
                {"kind": "low_rate", "source_id": source.source_id, "event_type": source.event_type, "value": source.rate_hz}
            )
        if source.max_gap_ms > rule["maximum_gap_ms"]:
            violations.append(
                {"kind": "large_gap", "source_id": source.source_id, "event_type": source.event_type, "value": source.max_gap_ms}
            )
        if source.sequence_gaps:
            violations.append(
                {"kind": "sequence_gap", "source_id": source.source_id, "event_type": source.event_type, "value": source.sequence_gaps}
            )

    first_host = min((event.host_receive_timestamp_ns for event in event_list), default=0)
    last_host = max((event.host_receive_timestamp_ns for event in event_list), default=0)
    duration_s = max(0, last_host - first_host) / 1_000_000_000
    event_type_counts = Counter(event.event_type for event in event_list)
    missing_event_types = sorted(REQUIRED_J0_EVENT_TYPES - set(event_type_counts))
    for event_type in missing_event_types:
        violations.append({"kind": "missing_modality", "event_type": event_type, "value": 0})
    return {
        "schema_version": 1,
        "event_count": len(event_list),
        "duration_s": duration_s,
        "event_types": dict(event_type_counts),
        "missing_event_types": missing_event_types,
        "explicit_drop_notices": sum(
            int(event.payload.get("count", 1)) for event in event_list if event.event_type == "drop_notice"
        ),
        "sources": [asdict(source) for source in sorted(sources, key=lambda item: (item.source_id, item.event_type))],
        "violations": violations,
        "passes_integrity_rules": not violations,
    }


def analyze_session(session_dir: str | Path, *, write_report: bool = True) -> dict:
    replay = SessionReplay(session_dir)
    replay_stats = replay.stats()
    session_path = Path(session_dir)
    events = list(replay.events())
    report = analyze_events(events)
    blob_errors: list[dict] = []
    blob_max_ends: dict[str, int] = defaultdict(int)
    blob_handles = {}
    try:
        for event in events:
            blob_path = event.payload.get("blob_path")
            if not blob_path:
                continue
            offset = int(event.payload.get("blob_offset", 0))
            size = int(event.payload.get("blob_size", -1))
            expected_hash = event.payload.get("blob_sha256")
            target = session_path / str(blob_path)
            if size < 0 or not target.is_file():
                blob_errors.append({"event_type": event.event_type, "sequence_id": event.sequence_id, "error": "missing_blob"})
                continue
            handle = blob_handles.get(str(target))
            if handle is None:
                handle = target.open("rb")
                blob_handles[str(target)] = handle
            handle.seek(offset)
            data = handle.read(size)
            blob_max_ends[str(target)] = max(blob_max_ends[str(target)], offset + size)
            if len(data) != size:
                blob_errors.append({"event_type": event.event_type, "sequence_id": event.sequence_id, "error": "truncated_blob"})
            elif expected_hash and hashlib.sha256(data).hexdigest() != expected_hash:
                blob_errors.append({"event_type": event.event_type, "sequence_id": event.sequence_id, "error": "blob_hash_mismatch"})
    finally:
        for handle in blob_handles.values():
            handle.close()

    unreferenced_blob_tail_bytes = 0
    for target_text, maximum_end in blob_max_ends.items():
        unreferenced_blob_tail_bytes += max(0, Path(target_text).stat().st_size - maximum_end)

    report["blob_errors"] = blob_errors
    report["unreferenced_blob_tail_bytes"] = unreferenced_blob_tail_bytes
    report["passes_integrity_rules"] = bool(report["passes_integrity_rules"] and not blob_errors)
    size_bytes = directory_size(session_path)
    duration_minutes = report["duration_s"] / 60
    bytes_per_minute = size_bytes / duration_minutes if duration_minutes > 0 else 0.0
    report.update(
        logical_sha256=replay_stats.logical_sha256,
        ignored_trailing_bytes=replay_stats.ignored_trailing_bytes,
        session_size_bytes=size_bytes,
        bytes_per_minute=bytes_per_minute,
        projected_gb_per_week_continuous=bytes_per_minute * 60 * 24 * 7 / 1_000_000_000,
        qualifies_30_minutes=report["duration_s"] >= 1800.0,
    )
    report["passes_j0_automatic_checks"] = bool(
        report["passes_integrity_rules"] and report["qualifies_30_minutes"] and not replay_stats.ignored_trailing_bytes
    )

    if write_report:
        output = session_path / "reports" / "quality.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
