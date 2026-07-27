"""Transparent competence assessments supplied to the persistent kernel."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterable, Literal


AssessmentOutcome = Literal["validated", "regressed", "inconclusive"]


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
