"""Safety-gated, transparent experiment proposal catalog."""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable
import uuid

from cognitive.beliefs import BeliefState, BeliefUnavailableError
from cognitive.memory import EpisodicMemory
from cognitive.models import (
    ExperimentProposal,
    ExperimentSignals,
    ExperimentSpec,
    SafetyContext,
)


class ExperimentBlockedError(RuntimeError):
    def __init__(self, reasons: Iterable[str]) -> None:
        self.reasons = tuple(reasons)
        super().__init__("experiment proposal blocked: " + ", ".join(self.reasons))


class SafeExperimentCatalog:
    def __init__(self, specs: Iterable[ExperimentSpec] = ()) -> None:
        self._specs: dict[str, ExperimentSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: ExperimentSpec) -> None:
        if spec.experiment_id in self._specs:
            raise ValueError(f"duplicate experiment: {spec.experiment_id}")
        self._specs[spec.experiment_id] = spec

    def propose(
        self,
        experiment_id: str,
        *,
        session_id: str,
        now_ns: int,
        signals: ExperimentSignals,
        safety: SafetyContext,
        beliefs: BeliefState,
        memory: EpisodicMemory,
    ) -> ExperimentProposal:
        try:
            spec = self._specs[experiment_id]
        except KeyError as error:
            raise KeyError(f"unknown experiment: {experiment_id}") from error

        reasons: list[str] = []
        if safety.emergency_stop:
            reasons.append("emergency_stop")
        if not safety.hardware_healthy:
            reasons.append("hardware_unhealthy")
        if safety.model_update_in_progress:
            reasons.append("model_update_in_progress")
        if safety.quota_state not in {"ok", "warning"}:
            reasons.append(f"quota:{safety.quota_state}")
        if spec.primitive not in safety.allowed_primitives:
            reasons.append("primitive_not_allowed")
        if signals.predicted_risk > spec.max_predicted_risk:
            reasons.append("predicted_risk")
        if signals.motor_cost > spec.max_motor_cost:
            reasons.append("motor_cost")

        for requirement in spec.required_beliefs:
            try:
                beliefs.require(
                    requirement.name,
                    now_ns=now_ns,
                    max_age_ns=requirement.max_age_ns,
                    max_variance=requirement.max_variance,
                    min_quality=requirement.min_quality,
                )
            except BeliefUnavailableError as error:
                reasons.append(str(error))

        proposal_count = memory.proposal_count(session_id, experiment_id)
        if proposal_count >= spec.max_proposals_per_session:
            reasons.append("session_quota")
        last_proposal = memory.last_proposal_time(session_id, experiment_id)
        if last_proposal is not None and now_ns - last_proposal < spec.min_interval_ns:
            reasons.append("minimum_interval")
        if reasons:
            raise ExperimentBlockedError(reasons)

        components = {
            "epistemic_gain": signals.epistemic_gain,
            "learning_progress": signals.learning_progress,
            "novelty": 0.25 * signals.novelty,
            "controllability": 0.5 * signals.controllability,
            "predicted_risk": -signals.predicted_risk,
            "motor_cost": -0.5 * signals.motor_cost,
        }
        score = sum(components.values())
        rationale = {
            "score_components": components,
            "signals": asdict(signals),
            "limits": {
                "max_predicted_risk": spec.max_predicted_risk,
                "max_motor_cost": spec.max_motor_cost,
                "min_interval_ns": spec.min_interval_ns,
                "max_proposals_per_session": spec.max_proposals_per_session,
            },
            "metadata": dict(spec.metadata),
        }
        return ExperimentProposal(
            proposal_id=f"proposal-{uuid.uuid4().hex}",
            experiment_id=experiment_id,
            primitive=spec.primitive,
            session_id=session_id,
            created_at_ns=now_ns,
            score=score,
            belief_revision=beliefs.revision,
            rationale=rationale,
        )
