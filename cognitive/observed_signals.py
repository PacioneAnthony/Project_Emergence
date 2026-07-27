"""Deterministic experiment signals derived from J0 servo observations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from statistics import fmean, pstdev
from typing import Any, Iterable, Mapping, Sequence

from cognitive.models import ExperimentSignals
from j0.events import Event


OBSERVED_SIGNAL_SCHEMA_VERSION = 1


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ServoSignalConfig:
    min_deg: float = 10.0
    max_deg: float = 170.0
    neutral_deg: float = 90.0
    boundary_margin_deg: float = 10.0
    bin_count: int = 8

    def __post_init__(self) -> None:
        values = (self.min_deg, self.max_deg, self.neutral_deg, self.boundary_margin_deg)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("servo signal configuration must be finite")
        if self.max_deg <= self.min_deg:
            raise ValueError("max_deg must be greater than min_deg")
        if not self.min_deg <= self.neutral_deg <= self.max_deg:
            raise ValueError("neutral_deg must be inside servo bounds")
        if not 0 <= self.boundary_margin_deg <= (self.max_deg - self.min_deg) / 2:
            raise ValueError("boundary_margin_deg is invalid")
        if self.bin_count < 2:
            raise ValueError("bin_count must be at least 2")

    @property
    def span_deg(self) -> float:
        return self.max_deg - self.min_deg

    def bin_for(self, angle_deg: float) -> int:
        position = (angle_deg - self.min_deg) / self.span_deg
        return min(self.bin_count - 1, max(0, int(position * self.bin_count)))


@dataclass(frozen=True)
class ServoTrialSummary:
    """Compact evidence for one trial; no raw event payload is retained."""

    experiment_id: str
    session_id: str
    source_id: str
    calibration_version: str
    event_count: int
    mean_absolute_error: float
    error_uncertainty: float
    coverage_bins: tuple[int, ...]
    boundary_exposure: float
    motor_cost: float
    source_digest: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["coverage_bins"] = list(self.coverage_bins)
        return value


@dataclass(frozen=True)
class ObservedExperimentEstimate:
    signals: ExperimentSignals
    evidence: Mapping[str, Any]
    evidence_digest: str

    def audit_record(self) -> dict[str, Any]:
        return {
            "evidence_digest": self.evidence_digest,
            "evidence": dict(self.evidence),
        }


def summarize_servo_trial(
    events: Iterable[Event],
    *,
    experiment_id: str,
    config: ServoSignalConfig | None = None,
) -> ServoTrialSummary:
    """Summarize the public servo observation contract from one J0 trial."""

    if not experiment_id:
        raise ValueError("experiment_id is required")
    signal_config = config or ServoSignalConfig()
    selected = [event for event in events if event.event_type == "servo_state"]
    if not selected:
        raise ValueError("at least one servo_state event is required")

    session_ids = {event.session_id for event in selected}
    source_ids = {event.source_id for event in selected}
    calibrations = {event.calibration_version for event in selected}
    if len(session_ids) != 1:
        raise ValueError("a servo trial must belong to exactly one session")
    if len(source_ids) != 1:
        raise ValueError("a servo trial must belong to exactly one source")
    if len(calibrations) != 1:
        raise ValueError("a servo trial must use exactly one calibration version")

    identities: set[tuple[str, str, int]] = set()
    errors: list[float] = []
    requested_angles: list[float] = []
    observed_angles: list[float] = []
    projection: list[dict[str, Any]] = []
    for event in selected:
        identity = (event.session_id, event.source_id, event.sequence_id)
        if identity in identities:
            raise ValueError("duplicate servo event identity")
        identities.add(identity)
        if event.quality.get("payload_valid") is not True:
            raise ValueError("servo event payload must be explicitly valid")
        try:
            requested_deg = float(event.payload["requested_deg"])
            observed_deg = float(event.payload["as5600_deg"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("servo event requires numeric requested_deg and as5600_deg") from error
        if not math.isfinite(requested_deg) or not math.isfinite(observed_deg):
            raise ValueError("servo angles must be finite")
        if not signal_config.min_deg <= requested_deg <= signal_config.max_deg:
            raise ValueError("requested_deg is outside configured servo bounds")
        if not signal_config.min_deg <= observed_deg <= signal_config.max_deg:
            raise ValueError("as5600_deg is outside configured servo bounds")

        requested_angles.append(requested_deg)
        observed_angles.append(observed_deg)
        errors.append(_clip01(abs(requested_deg - observed_deg) / signal_config.span_deg))
        projection.append(
            {
                "session_id": event.session_id,
                "source_id": event.source_id,
                "sequence_id": event.sequence_id,
                "source_timestamp_ns": event.source_timestamp_ns,
                "host_receive_timestamp_ns": event.host_receive_timestamp_ns,
                "requested_deg": requested_deg,
                "as5600_deg": observed_deg,
                "calibration_version": event.calibration_version,
            }
        )

    margin = signal_config.boundary_margin_deg
    lower = signal_config.min_deg + margin
    upper = signal_config.max_deg - margin
    boundary_count = sum(
        requested <= lower
        or requested >= upper
        or observed <= lower
        or observed >= upper
        for requested, observed in zip(requested_angles, observed_angles)
    )
    previous = signal_config.neutral_deg
    total_motion = 0.0
    for requested in requested_angles:
        total_motion += abs(requested - previous)
        previous = requested

    source_envelope = {
        "schema_version": OBSERVED_SIGNAL_SCHEMA_VERSION,
        "event_projection": projection,
    }
    return ServoTrialSummary(
        experiment_id=experiment_id,
        session_id=next(iter(session_ids)),
        source_id=next(iter(source_ids)),
        calibration_version=next(iter(calibrations)),
        event_count=len(selected),
        mean_absolute_error=_clip01(fmean(errors)),
        error_uncertainty=_clip01(pstdev(errors)),
        coverage_bins=tuple(sorted({signal_config.bin_for(value) for value in requested_angles})),
        boundary_exposure=_clip01(boundary_count / len(selected)),
        motor_cost=_clip01(
            total_motion / (signal_config.span_deg * len(requested_angles))
        ),
        source_digest=_digest(source_envelope),
    )


class ObservedSignalEstimator:
    """Map ordered trial summaries to transparent selector signals."""

    def __init__(self, config: ServoSignalConfig | None = None) -> None:
        self.config = config or ServoSignalConfig()

    def estimate(
        self,
        experiment_id: str,
        trials: Sequence[ServoTrialSummary],
    ) -> ObservedExperimentEstimate:
        if not experiment_id:
            raise ValueError("experiment_id is required")
        if not trials:
            raise ValueError("at least one trial summary is required")
        if any(trial.experiment_id != experiment_id for trial in trials):
            raise ValueError("trial experiment_id does not match estimate experiment_id")

        split = len(trials) // 2
        older = trials[:split]
        recent = trials[split:]
        recent_error = fmean(trial.mean_absolute_error for trial in recent)
        recent_uncertainty = fmean(trial.error_uncertainty for trial in recent)
        older_error = (
            fmean(trial.mean_absolute_error for trial in older)
            if older
            else recent_error
        )
        older_bins = {item for trial in older for item in trial.coverage_bins}
        recent_bins = {item for trial in recent for item in trial.coverage_bins}

        signals = ExperimentSignals(
            epistemic_gain=_clip01(recent_error + recent_uncertainty),
            learning_progress=_clip01(older_error - recent_error) if older else 0.0,
            novelty=_clip01(len(recent_bins - older_bins) / self.config.bin_count),
            controllability=_clip01(1.0 - recent_error),
            predicted_risk=max(trial.boundary_exposure for trial in recent),
            motor_cost=_clip01(fmean(trial.motor_cost for trial in recent)),
        )
        evidence: dict[str, Any] = {
            "schema_version": OBSERVED_SIGNAL_SCHEMA_VERSION,
            "kind": "j0_servo_observation_summary",
            "experiment_id": experiment_id,
            "limitations": {
                "predicted_risk": "empirical_boundary_exposure_proxy",
                "causal_claim": False,
            },
            "config": asdict(self.config),
            "partition": {
                "older_trial_count": len(older),
                "recent_trial_count": len(recent),
            },
            "source_sessions": [trial.session_id for trial in trials],
            "source_digests": [trial.source_digest for trial in trials],
            "trial_summaries": [trial.to_dict() for trial in trials],
            "signals": asdict(signals),
        }
        return ObservedExperimentEstimate(
            signals=signals,
            evidence=evidence,
            evidence_digest=_digest(evidence),
        )

    def estimate_candidates(
        self,
        histories: Mapping[str, Sequence[ServoTrialSummary]],
    ) -> dict[str, ObservedExperimentEstimate]:
        if not histories:
            raise ValueError("at least one experiment history is required")
        return {
            experiment_id: self.estimate(experiment_id, histories[experiment_id])
            for experiment_id in sorted(histories)
        }
