"""Online-only causal episode boundary policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundaryConfig:
    silence_ns: int = 2_000_000_000
    max_episode_ns: int = 30_000_000_000
    explicit_event_types: frozenset[str] = frozenset(
        {"emergency_stop", "collision", "goal_reached", "manual_episode_boundary"}
    )

    def __post_init__(self) -> None:
        if self.silence_ns <= 0 or self.max_episode_ns <= 0:
            raise ValueError("episode boundary durations must be positive")


class CausalBoundaryPolicy:
    def __init__(self, config: BoundaryConfig | None = None) -> None:
        self.config = config or BoundaryConfig()

    def boundary_before(
        self,
        *,
        event_type: str,
        timestamp_ns: int,
        episode_started_at_ns: int | None,
        last_event_at_ns: int | None,
    ) -> str | None:
        if timestamp_ns < 0:
            raise ValueError("event timestamp must be non-negative")
        if episode_started_at_ns is None or last_event_at_ns is None:
            return "first_observation"
        if timestamp_ns < last_event_at_ns:
            return None
        if event_type in self.config.explicit_event_types:
            return f"explicit:{event_type}"
        if timestamp_ns - last_event_at_ns > self.config.silence_ns:
            return "silence"
        if timestamp_ns - episode_started_at_ns >= self.config.max_episode_ns:
            return "max_duration"
        return None
