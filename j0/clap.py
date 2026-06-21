"""Offline peak alignment for the visible/audible J0 synchronization gesture."""

from __future__ import annotations

from array import array
import json
import math
from pathlib import Path
import sys
from typing import Iterable

from j0.events import Event
from j0.replay import SessionReplay


def _blob_bytes(session_dir: Path, event: Event) -> bytes:
    path = session_dir / str(event.payload["blob_path"])
    offset = int(event.payload.get("blob_offset", 0))
    size = int(event.payload["blob_size"])
    with path.open("rb") as stream:
        stream.seek(offset)
        return stream.read(size)


def _audio_rms(data: bytes) -> float:
    samples = array("h")
    samples.frombytes(data)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return 0.0
    return math.sqrt(sum(value * value for value in samples) / len(samples))


def _audio_impulse(event: Event, data: bytes) -> tuple[int, float]:
    samples = array("h")
    samples.frombytes(data)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return event.source_timestamp_ns, 0.0

    score = math.sqrt(sum(value * value for value in samples) / len(samples))
    sample_rate_hz = int(event.payload.get("sample_rate_hz", 0))
    if sample_rate_hz <= 0:
        return event.source_timestamp_ns, score

    peak_index = max(range(len(samples)), key=lambda index: abs(samples[index]))
    timestamp_source = event.quality.get("timestamp_source")
    if timestamp_source == "host_callback":
        samples_after_peak = len(samples) - peak_index
        timestamp_ns = event.source_timestamp_ns - round(samples_after_peak / sample_rate_hz * 1_000_000_000)
    elif timestamp_source in {
        "portaudio_adc_first_sample",
        "host_callback_estimated_first_sample",
        "sample_count_anchored_to_host_callback",
        "sample_count_anchored_to_portaudio_adc",
    }:
        timestamp_ns = event.source_timestamp_ns + round(peak_index / sample_rate_hz * 1_000_000_000)
    else:
        timestamp_ns = event.source_timestamp_ns
    return timestamp_ns, score


def _peak(items: list[tuple[int, float]]) -> dict | None:
    if not items:
        return None
    timestamp_ns, score = max(items, key=lambda item: item[1])
    return {"timestamp_ns": timestamp_ns, "score": score}


def _peak_near(items: list[tuple[int, float]], center_ns: int | None, window_ns: int = 1_000_000_000) -> dict | None:
    if center_ns is None:
        return _peak(items)
    return _peak([item for item in items if abs(item[0] - center_ns) <= window_ns])


def _local_peaks(items: list[tuple[int, float]]) -> list[tuple[int, float]]:
    if len(items) < 3:
        return items
    peaks = []
    for index in range(1, len(items) - 1):
        previous_score = items[index - 1][1]
        timestamp_ns, score = items[index]
        next_score = items[index + 1][1]
        if score >= previous_score and score >= next_score:
            peaks.append((timestamp_ns, score))
    return peaks


def _audio_impacts(items: list[tuple[int, float]]) -> list[tuple[int, float]]:
    if not items:
        return []
    strongest = max(items, key=lambda item: item[1])
    threshold = strongest[1] * 0.10
    nearby = [
        item
        for item in _local_peaks(items)
        if abs(item[0] - strongest[0]) <= 750_000_000 and item[1] >= threshold
    ]
    selected: list[tuple[int, float]] = []
    for candidate in sorted(nearby, key=lambda item: item[1], reverse=True):
        if all(abs(candidate[0] - existing[0]) >= 80_000_000 for existing in selected):
            selected.append(candidate)
        if len(selected) >= 5:
            break
    return sorted(selected)


def _match_peak(items: list[tuple[int, float]], center_ns: int, window_ns: int = 50_000_000) -> dict | None:
    candidates = [item for item in _local_peaks(items) if abs(item[0] - center_ns) <= window_ns]
    if not candidates:
        return None

    distance_scale_ns = 20_000_000
    timestamp_ns, score = max(
        candidates,
        key=lambda item: item[1] / (1.0 + ((item[0] - center_ns) / distance_scale_ns) ** 2),
    )
    return {
        "timestamp_ns": timestamp_ns,
        "score": score,
        "offset_from_audio_ms": (timestamp_ns - center_ns) / 1_000_000,
    }


def analyze_clap(session_dir: str | Path, *, write_report: bool = True) -> dict:
    session_path = Path(session_dir)
    events = list(SessionReplay(session_path).events())

    sync_path = session_path / "reports" / "sync.json"
    sync = json.loads(sync_path.read_text(encoding="utf-8")) if sync_path.exists() else {}
    device_offset_ns = sync.get("median_offset_ns")

    audio_scores: list[tuple[int, float]] = []
    for event in events:
        if event.event_type == "audio_chunk" and event.payload.get("blob_path"):
            audio_scores.append(_audio_impulse(event, _blob_bytes(session_path, event)))

    imu_scores: list[tuple[int, float]] = []
    previous_magnitude: float | None = None
    for event in events:
        if event.event_type != "imu_sample":
            continue
        raw = event.payload.get("accel_raw")
        if not raw or len(raw) != 3:
            continue
        magnitude = math.sqrt(sum(float(value) ** 2 for value in raw))
        score = abs(magnitude - previous_magnitude) if previous_magnitude is not None else 0.0
        timestamp_ns = event.source_timestamp_ns + int(device_offset_ns or 0)
        imu_scores.append((timestamp_ns, score))
        previous_magnitude = magnitude

    video_scores: list[tuple[int, float]] = []
    try:
        import cv2
        import numpy as np

        previous = None
        for event in events:
            if event.event_type != "video_frame" or not event.payload.get("blob_path"):
                continue
            encoded = np.frombuffer(_blob_bytes(session_path, event), dtype=np.uint8)
            frame = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
            if frame is None:
                continue
            frame = cv2.resize(frame, (64, 48))
            score = float(cv2.absdiff(frame, previous).mean()) if previous is not None else 0.0
            video_scores.append((event.source_timestamp_ns, score))
            previous = frame
    except ImportError:
        pass

    impacts = []
    for impact_index, (audio_timestamp_ns, audio_score) in enumerate(_audio_impacts(audio_scores), start=1):
        matches = {
            "video": _match_peak(video_scores, audio_timestamp_ns),
            "imu": _match_peak(imu_scores, audio_timestamp_ns),
        }
        impacts.append(
            {
                "impact": impact_index,
                "audio": {"timestamp_ns": audio_timestamp_ns, "score": audio_score},
                **matches,
            }
        )

    primary_impact = max(impacts, key=lambda impact: impact["audio"]["score"], default=None)
    audio_peak = primary_impact["audio"] if primary_impact else _peak(audio_scores)
    reference = audio_peak["timestamp_ns"] if audio_peak else None
    peaks = {
        "audio": audio_peak,
        "video": primary_impact["video"] if primary_impact else _peak_near(video_scores, reference),
        "imu": primary_impact["imu"] if primary_impact else _peak_near(imu_scores, reference),
    }
    offsets_ms = {
        name: ((peak["timestamp_ns"] - reference) / 1_000_000 if peak and reference is not None else None)
        for name, peak in peaks.items()
    }
    impact_offsets = [
        abs(match["offset_from_audio_ms"])
        for impact in impacts
        for name in ("video", "imu")
        if (match := impact.get(name)) is not None
    ]
    available_offsets = impact_offsets or [
        abs(value) for name, value in offsets_ms.items() if name != "audio" and value is not None
    ]
    report = {
        "schema_version": 1,
        "method": "audio sample-level impulses, then nearby video-frame and IMU local peaks for each impact",
        "device_clock_offset_ns": device_offset_ns,
        "impact_count": len(impacts),
        "impacts": impacts,
        "peaks": peaks,
        "offsets_from_audio_ms": offsets_ms,
        "max_absolute_offset_ms": max(available_offsets) if available_offsets else None,
        "passes_20ms_target": bool(available_offsets and max(available_offsets) <= 20.0),
        "limitations": [
            "The gesture must be visible to the camera, audible to the microphone, and mechanically coupled to the head.",
            "Peak association must be inspected when multiple strong events occur in the same session.",
        ],
    }
    if write_report:
        output = session_path / "reports" / "clap_sync.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
