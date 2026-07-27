"""Transparent competence assessments supplied to the persistent kernel."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterable, Literal, Sequence

from cognitive.observed_signals import ServoTrialSummary


AssessmentOutcome = Literal["validated", "regressed", "inconclusive"]
EXECUTED_TRACKING_METRIC = "mean_absolute_tracking_error_deg"


@dataclass(frozen=True)
class UpperBoundCriterion:
    """Hysteretic criterion for a metric where lower values are better."""

    metric_name: str
    validation_upper_bound: float
    regression_upper_bound: float
    min_samples: int

    def __post_init__(self) -> None:
        if not self.metric_name:
            raise ValueError("metric_name is required")
        if not math.isfinite(self.validation_upper_bound):
            raise ValueError("validation_upper_bound must be finite")
        if not math.isfinite(self.regression_upper_bound):
            raise ValueError("regression_upper_bound must be finite")
        if self.regression_upper_bound < self.validation_upper_bound:
            raise ValueError("regression threshold must not be stricter than validation")
        if self.min_samples < 1:
            raise ValueError("min_samples must be positive")


@dataclass(frozen=True)
class CompetenceAssessment:
    outcome: AssessmentOutcome
    criterion: UpperBoundCriterion
    sample_count: int
    maximum: float
    mean: float
    values_digest: str

    def evidence(self) -> dict[str, object]:
        return {
            "assessment": "upper_bound_hysteresis_v1",
            "outcome": self.outcome,
            "criterion": asdict(self.criterion),
            "sample_count": self.sample_count,
            "maximum": self.maximum,
            "mean": self.mean,
            "values_digest": self.values_digest,
        }

    def evidence_digest(self) -> str:
        payload = json.dumps(
            self.evidence(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExecutedCompetenceAssessment:
    """An upper-bound assessment tied to verified LIFE execution summaries."""

    competence_name: str
    experiment_id: str
    window_size: int
    servo_span_deg: float
    source_sessions: tuple[str, ...]
    source_digests: tuple[str, ...]
    assessment: CompetenceAssessment

    @property
    def outcome(self) -> AssessmentOutcome:
        return self.assessment.outcome

    def evidence(self) -> dict[str, object]:
        return {
            "assessment": "executed_servo_tracking_v1",
            "competence_name": self.competence_name,
            "experiment_id": self.experiment_id,
            "window_size": self.window_size,
            "servo_span_deg": self.servo_span_deg,
            "source_sessions": list(self.source_sessions),
            "source_digests": list(self.source_digests),
            "upper_bound": self.assessment.evidence(),
        }

    def evidence_digest(self) -> str:
        payload = json.dumps(
            self.evidence(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assess_upper_bound(
    values: Iterable[float],
    criterion: UpperBoundCriterion,
) -> CompetenceAssessment:
    """Assess held-out values without silently discarding invalid observations."""

    samples = tuple(float(value) for value in values)
    if len(samples) < criterion.min_samples:
        raise ValueError(
            f"{criterion.metric_name} requires at least {criterion.min_samples} samples"
        )
    if any(not math.isfinite(value) for value in samples):
        raise ValueError(f"{criterion.metric_name} samples must all be finite")

    maximum = max(samples)
    mean = sum(samples) / len(samples)
    if maximum <= criterion.validation_upper_bound:
        outcome: AssessmentOutcome = "validated"
    elif maximum > criterion.regression_upper_bound:
        outcome = "regressed"
    else:
        outcome = "inconclusive"

    canonical_values = json.dumps(
        samples,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return CompetenceAssessment(
        outcome=outcome,
        criterion=criterion,
        sample_count=len(samples),
        maximum=maximum,
        mean=mean,
        values_digest=hashlib.sha256(canonical_values.encode("utf-8")).hexdigest(),
    )


def assess_executed_servo_tracking(
    trials: Sequence[ServoTrialSummary],
    *,
    competence_name: str,
    experiment_id: str,
    criterion: UpperBoundCriterion,
    window_size: int | None = None,
    servo_span_deg: float = 160.0,
) -> ExecutedCompetenceAssessment:
    """Assess the latest explicit window of verified servo trial summaries."""

    if not competence_name or not experiment_id:
        raise ValueError("competence_name and experiment_id are required")
    if criterion.metric_name != EXECUTED_TRACKING_METRIC:
        raise ValueError(
            f"executed servo tracking requires metric {EXECUTED_TRACKING_METRIC!r}"
        )
    if not math.isfinite(servo_span_deg) or servo_span_deg <= 0:
        raise ValueError("servo_span_deg must be finite and positive")
    effective_window = criterion.min_samples if window_size is None else window_size
    if effective_window < criterion.min_samples:
        raise ValueError("window_size must be at least criterion.min_samples")
    if len(trials) < effective_window:
        raise ValueError(
            f"{experiment_id} requires at least {effective_window} completed trials"
        )
    selected = tuple(trials[-effective_window:])
    if any(trial.experiment_id != experiment_id for trial in selected):
        raise ValueError("trial experiment_id does not match competence experiment")

    assessment = assess_upper_bound(
        (trial.mean_absolute_error * servo_span_deg for trial in selected),
        criterion,
    )
    return ExecutedCompetenceAssessment(
        competence_name=competence_name,
        experiment_id=experiment_id,
        window_size=effective_window,
        servo_span_deg=float(servo_span_deg),
        source_sessions=tuple(trial.session_id for trial in selected),
        source_digests=tuple(trial.source_digest for trial in selected),
        assessment=assessment,
    )
