"""Deterministic bridges from verified executions to competence state."""

from __future__ import annotations

from dataclasses import dataclass

from cognitive.competence import (
    ExecutedCompetenceAssessment,
    UpperBoundCriterion,
    assess_executed_servo_tracking,
)
from cognitive.kernel import CognitiveKernel
from cognitive.models import CompetenceStatus


@dataclass(frozen=True)
class CompetenceUpdate:
    assessment: ExecutedCompetenceAssessment
    applied: bool
    from_status: CompetenceStatus
    to_status: CompetenceStatus
    transition_path: tuple[CompetenceStatus, ...]


def evaluate_and_apply_executed_competence(
    kernel: CognitiveKernel,
    *,
    competence_name: str,
    experiment_id: str,
    criterion: UpperBoundCriterion,
    assessed_at_ns: int,
    window_size: int | None = None,
    servo_span_deg: float = 160.0,
    model_version: str | None = None,
) -> CompetenceUpdate:
    """Rebuild source logs, assess the latest window, and apply it atomically."""

    trials = kernel.recompute_observed_history(experiment_id)
    assessment = assess_executed_servo_tracking(
        trials,
        competence_name=competence_name,
        experiment_id=experiment_id,
        criterion=criterion,
        window_size=window_size,
        servo_span_deg=servo_span_deg,
    )
    applied, from_status, to_status, path = kernel.memory.apply_competence_assessment(
        competence_name,
        experiment_id=experiment_id,
        outcome=assessment.outcome,
        assessed_at_ns=assessed_at_ns,
        assessment_digest=assessment.evidence_digest(),
        evidence=assessment.evidence(),
        model_version=model_version,
    )
    return CompetenceUpdate(
        assessment=assessment,
        applied=applied,
        from_status=from_status,
        to_status=to_status,
        transition_path=path,
    )
