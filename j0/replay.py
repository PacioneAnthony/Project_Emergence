"""Deterministic replay for append-only J0 event logs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Callable, Iterator

from j0.events import Event


@dataclass(frozen=True)
class ReplayStats:
    event_count: int
    logical_sha256: str
    ignored_trailing_bytes: int


class SessionReplay:
    def __init__(self, session_dir: str | Path):
        self.session_dir = Path(session_dir)
        self.events_path = self.session_dir / "events.jsonl"
        self.manifest_path = self.session_dir / "manifest.json"
        if not self.events_path.is_file():
            raise FileNotFoundError(self.events_path)
        self.ignored_trailing_bytes = 0

    def manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def events(self, *, tolerate_truncated_tail: bool = True) -> Iterator[Event]:
        self.ignored_trailing_bytes = 0
        with self.events_path.open("rb") as stream:
            line_number = 0
            while True:
                line = stream.readline()
                if not line:
                    break
                line_number += 1
                if not line.endswith(b"\n"):
                    if tolerate_truncated_tail:
                        self.ignored_trailing_bytes = len(line)
                        break
                    raise ValueError(f"truncated final event line {line_number}")
                try:
                    yield Event.from_json(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"invalid event at line {line_number}: {error}") from error

    def stats(self) -> ReplayStats:
        digest = hashlib.sha256()
        count = 0
        for event in self.events():
            digest.update(event.to_json().encode("utf-8"))
            digest.update(b"\n")
            count += 1
        return ReplayStats(count, digest.hexdigest(), self.ignored_trailing_bytes)

    def play(
        self,
        callback: Callable[[Event], None],
        *,
        speed: float = 0.0,
        clock: str = "host_receive_timestamp_ns",
        sleep: Callable[[float], None] = time.sleep,
    ) -> ReplayStats:
        """Replay in file order; speed=0 disables waiting without changing order."""

        if speed < 0:
            raise ValueError("speed must be non-negative")
        if clock not in {"host_receive_timestamp_ns", "source_timestamp_ns"}:
            raise ValueError("unsupported replay clock")

        digest = hashlib.sha256()
        count = 0
        previous_timestamp: int | None = None
        for event in self.events():
            timestamp = getattr(event, clock)
            if speed > 0 and previous_timestamp is not None:
                delay_seconds = max(0, timestamp - previous_timestamp) / 1_000_000_000 / speed
                if delay_seconds:
                    sleep(delay_seconds)
            callback(event)
            encoded = event.to_json().encode("utf-8") + b"\n"
            digest.update(encoded)
            count += 1
            previous_timestamp = timestamp
        return ReplayStats(count, digest.hexdigest(), self.ignored_trailing_bytes)
