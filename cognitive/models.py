"""Typed contracts for the persistent cognitive kernel."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
from typing import Any, Mapping


@dataclass(frozen=True)
class BeliefEstimate:
    """One scalar estimate with uncertainty, freshness, and provenance."""

    name: str
    mean: float
    variance: float
    observed_at_ns: int
    received_at_ns: int
    source_id: str
    clock_domain: str = "unspecified"
    quality: float = 1.0
    calibration_version: str = "unversioned"
    model_version: str = "unversioned"

    def __post_init__(self) -> None:
        if not self.name or not self.source_id or not self.clock_domain:
            raise ValueError("belief name, source_id, and clock_domain are required")
        if not math.isfinite(self.mean):
            raise ValueError("belief mean must be finite")
        if not math.isfinite(self.variance) or self.variance < 0:
            raise ValueError("belief variance must be finite and non-negative")
        if self.observed_at_ns < 0 or self.received_at_ns < 0:
            raise ValueError("belief timestamps must be non-negative")
        if not math.isfinite(self.quality) or not 0 <= self.quality <= 1:
            raise ValueError("belief quality must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BeliefEstimate":
        return cls(
            name=str(data["name"]),
            mean=float(data["mean"]),
            variance=float(data["variance"]),
            observed_at_ns=int(data["observed_at_ns"]),
            received_at_ns=int(data["received_at_ns"]),
            source_id=str(data["source_id"]),
            clock_domain=str(data.get("clock_domain", "unspecified")),
            quality=float(data.get("quality", 1.0)),
            calibration_version=str(data.get("calibration_version", "unversioned")),
            model_version=str(data.get("model_version", "unversioned")),
        )


@dataclass(frozen=True)
class BeliefRequirement:
    name: str
    max_age_ns: int
    max_variance: float
    min_quality: float = 0.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("belief requirement name is required")
        if self.max_age_ns < 0 or self.max_variance < 0:
            raise ValueError("belief requirement limits must be non-negative")
        if not 0 <= self.min_quality <= 1:
            raise ValueError("min_quality must be in [0, 1]")


class CompetenceStatus(str, Enum):
    UNKNOWN = "unknown"
    LEARNING = "learning"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    REGRESSED = "regressed"
    SUSPENDED = "suspended"


@dataclass(frozen=True)
class ExperimentSignals:
    """Scientific-module estimates consumed by the transparent selector."""

    epistemic_gain: float
    learning_progress: float
    novelty: float = 0.0
    controllability: float = 0.0
    predicted_risk: float = 0.0
    motor_cost: float = 0.0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and in [0, 1]")


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    primitive: str
    required_beliefs: tuple[BeliefRequirement, ...] = ()
    max_predicted_risk: float = 0.25
    max_motor_cost: float = 0.5
    min_interval_ns: int = 0
    max_proposals_per_session: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.primitive:
            raise ValueError("experiment_id and primitive are required")
        if not 0 <= self.max_predicted_risk <= 1 or not 0 <= self.max_motor_cost <= 1:
            raise ValueError("risk and cost limits must be in [0, 1]")
        if self.min_interval_ns < 0 or self.max_proposals_per_session < 1:
            raise ValueError("cadence and session quota must be positive")


@dataclass(frozen=True)
class SafetyContext:
    emergency_stop: bool
    hardware_healthy: bool
    model_update_in_progress: bool
    quota_state: str
    allowed_primitives: frozenset[str]


@dataclass(frozen=True)
class ExperimentProposal:
    """A reviewable proposal. It deliberately has no actuator command."""

    proposal_id: str
    experiment_id: str
    primitive: str
    session_id: str
    created_at_ns: int
    score: float
    belief_revision: int
    rationale: Mapping[str, Any]
    status: str = "proposed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
