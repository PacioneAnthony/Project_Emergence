"""Persistent, restartable orchestration of one developmental simulation cycle."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Literal, Mapping

from cognitive.competence import UpperBoundCriterion
from cognitive.development import evaluate_and_apply_executed_competence
from cognitive.kernel import CognitiveKernel
from cognitive.models import ExperimentProposal, SafetyContext
from cognitive.needs import NeedActivation, PersistentNeedActivator
from j0.recorder import abort_abandoned_session
from j0.replay import SessionReplay
from sim3d.life_executor import BoundedMujocoExecutor


SupervisorCheckpoint = Literal[
    "selected",
    "executed",
    "assessment_applied",
]


class CycleRecoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class DevelopmentCycleRequest:
    cycle_id: str
    execution_id: str
    j0_session_id: str
    seed: int

    def __post_init__(self) -> None:
        if not self.cycle_id or not self.execution_id or not self.j0_session_id:
            raise ValueError("cycle and execution identities are required")
        if not 0 <= self.seed <= 0xFFFFFFFF:
            raise ValueError("cycle seed must be in [0, 2^32-1]")


@dataclass(frozen=True)
class CompetenceEvaluationRoute:
    competence_name: str
    criterion: UpperBoundCriterion
    window_size: int
    servo_span_deg: float = 160.0
    model_version: str | None = None

    def __post_init__(self) -> None:
        if not self.competence_name:
            raise ValueError("competence_name is required")
        if self.window_size < self.criterion.min_samples:
            raise ValueError("evaluation window is smaller than criterion minimum")


@dataclass(frozen=True)
class DevelopmentCycleOutcome:
    cycle_id: str
    status: str
    proposal_id: str
    experiment_id: str
    execution_id: str
    result: Mapping[str, object]


class PersistentDevelopmentSupervisor:
    """Compose LIFE-003..006 without introducing a new decision policy."""

    def __init__(
        self,
        activator: PersistentNeedActivator,
        executor: BoundedMujocoExecutor,
        *,
        evaluations: Mapping[str, CompetenceEvaluationRoute] | None = None,
    ) -> None:
        self.activator = activator
        self.executor = executor
        self.evaluations = dict(evaluations or {})

    @staticmethod
    def _proposal_from_row(row) -> ExperimentProposal:
        return ExperimentProposal(
            proposal_id=str(row["proposal_id"]),
            experiment_id=str(row["experiment_id"]),
            primitive=str(row["primitive"]),
            session_id=str(row["session_id"]),
            created_at_ns=int(row["created_at_ns"]),
            score=float(row["score"]),
            belief_revision=int(row["belief_revision"]),
            rationale=json.loads(row["rationale_json"]),
            status=str(row["status"]),
        )

    @staticmethod
    def _outcome(kernel: CognitiveKernel, cycle_id: str) -> DevelopmentCycleOutcome:
        cycle = kernel.memory.development_cycle(cycle_id)
        if cycle is None:
            raise KeyError(f"unknown development cycle: {cycle_id}")
        return DevelopmentCycleOutcome(
            cycle_id=cycle_id,
            status=str(cycle["status"]),
            proposal_id=str(cycle["proposal_id"]),
            experiment_id=str(cycle["experiment_id"]),
            execution_id=str(cycle["execution_id"]),
            result=json.loads(cycle["result_json"]),
        )

    @staticmethod
    def _verify_request(cycle, request: DevelopmentCycleRequest) -> None:
        expected = (
            request.execution_id,
            request.j0_session_id,
            request.seed,
        )
        actual = (
            cycle["execution_id"],
            cycle["j0_session_id"],
            int(cycle["seed"]),
        )
        if actual != expected:
            raise ValueError("development cycle request identity collision")

    def _select_atomic(
        self,
        kernel: CognitiveKernel,
        request: DevelopmentCycleRequest,
        *,
        now_ns: int,
        safety: SafetyContext,
    ) -> tuple[ExperimentProposal, NeedActivation]:
        if kernel.session_id is None:
            raise RuntimeError("an active cognitive session is required")
        activation = self.activator.activate(kernel)
        cycle_evidence = {
            experiment_id: {
                **dict(evidence),
                "supervised_cycle": {
                    "cycle_id": request.cycle_id,
                    "execution_id": request.execution_id,
                    "j0_session_id": request.j0_session_id,
                    "seed": request.seed,
                },
            }
            for experiment_id, evidence in activation.signal_evidence.items()
        }
        proposal = kernel.catalog.propose_best(
            activation.candidates,
            session_id=kernel.session_id,
            now_ns=now_ns,
            safety=safety,
            beliefs=kernel.beliefs,
            memory=kernel.memory,
            evidence_by_experiment=cycle_evidence,
        )
        kernel.memory.save_proposal_and_cycle(
            proposal,
            cycle_id=request.cycle_id,
            execution_id=request.execution_id,
            j0_session_id=request.j0_session_id,
            seed=request.seed,
            activation=activation.audit,
        )
        return proposal, activation

    def _abort_partial_execution(
        self,
        kernel: CognitiveKernel,
        cycle,
        *,
        now_ns: int,
    ) -> None:
        execution = kernel.memory.experiment_execution(cycle["execution_id"])
        if execution is not None and execution["status"] == "running":
            replay = SessionReplay(execution["session_ref"])
            manifest = replay.manifest()
            if manifest.get("status") == "recording":
                abort_abandoned_session(
                    execution["session_ref"],
                    notes="LIFE-007 abandoned after process loss during MuJoCo execution",
                )
            kernel.abort_experiment_execution(cycle["execution_id"])
        kernel.memory.advance_development_cycle(
            cycle["cycle_id"],
            expected_status="selected",
            to_status="aborted",
            changed_at_ns=now_ns,
            result={"reason": "partial_execution_not_resumable"},
        )

    def advance(
        self,
        kernel: CognitiveKernel,
        request: DevelopmentCycleRequest,
        *,
        now_ns: int,
        safety: SafetyContext,
        stop_after: SupervisorCheckpoint | None = None,
    ) -> DevelopmentCycleOutcome:
        if stop_after not in {None, "selected", "executed", "assessment_applied"}:
            raise ValueError("unsupported supervisor checkpoint")

        cycle = kernel.memory.development_cycle(request.cycle_id)
        if cycle is None:
            self._select_atomic(
                kernel,
                request,
                now_ns=now_ns,
                safety=safety,
            )
            cycle = kernel.memory.development_cycle(request.cycle_id)
            if stop_after == "selected":
                return self._outcome(kernel, request.cycle_id)
        self._verify_request(cycle, request)
        if cycle["status"] in {"complete", "aborted"}:
            return self._outcome(kernel, request.cycle_id)

        proposal_row = kernel.memory.proposal(cycle["proposal_id"])
        if proposal_row is None:
            raise CycleRecoveryError("cycle proposal disappeared")
        execution = kernel.memory.experiment_execution(request.execution_id)

        if cycle["status"] == "selected":
            if execution is None:
                if proposal_row["status"] in {"rejected", "cancelled"}:
                    kernel.memory.advance_development_cycle(
                        request.cycle_id,
                        expected_status="selected",
                        to_status="aborted",
                        changed_at_ns=now_ns,
                        result={"reason": "proposal_no_longer_executable"},
                    )
                    raise CycleRecoveryError("cycle proposal is no longer executable")
                proposal = self._proposal_from_row(proposal_row)
                try:
                    self.executor.execute(
                        kernel,
                        proposal,
                        execution_id=request.execution_id,
                        j0_session_id=request.j0_session_id,
                        seed=request.seed,
                        started_at_ns=max(now_ns, proposal.created_at_ns),
                        safety=safety,
                    )
                except Exception:
                    execution = kernel.memory.experiment_execution(request.execution_id)
                    if execution is not None and execution["status"] == "aborted":
                        kernel.memory.advance_development_cycle(
                            request.cycle_id,
                            expected_status="selected",
                            to_status="aborted",
                            changed_at_ns=now_ns,
                            result={"reason": "execution_failed"},
                        )
                    raise
                execution = kernel.memory.experiment_execution(request.execution_id)
            elif execution["status"] == "running":
                manifest = SessionReplay(execution["session_ref"]).manifest()
                if manifest.get("status") == "complete":
                    kernel.complete_observed_execution(
                        request.execution_id,
                        completed_at_ns=max(now_ns, int(execution["started_at_ns"])),
                    )
                    execution = kernel.memory.experiment_execution(request.execution_id)
                else:
                    self._abort_partial_execution(kernel, cycle, now_ns=now_ns)
                    raise CycleRecoveryError(
                        "partial MuJoCo execution was aborted and cannot be resumed"
                    )
            elif execution["status"] == "aborted":
                kernel.memory.advance_development_cycle(
                    request.cycle_id,
                    expected_status="selected",
                    to_status="aborted",
                    changed_at_ns=now_ns,
                    result={"reason": "execution_was_aborted"},
                )
                raise CycleRecoveryError("cycle execution was already aborted")
            if execution is None or execution["status"] != "complete":
                raise CycleRecoveryError("cycle execution is not complete")
            kernel.memory.advance_development_cycle(
                request.cycle_id,
                expected_status="selected",
                to_status="executed",
                changed_at_ns=int(execution["completed_at_ns"]),
                result={
                    "execution_status": "complete",
                    "source_digest": execution["source_digest"],
                },
            )
            cycle = kernel.memory.development_cycle(request.cycle_id)
            if stop_after == "executed":
                return self._outcome(kernel, request.cycle_id)

        if cycle["status"] == "executed":
            evaluation = self.evaluations.get(str(cycle["experiment_id"]))
            assessment_digest: str | None = None
            if evaluation is None:
                result: dict[str, object] = {"assessment_status": "no_evaluator"}
            else:
                history = kernel.recompute_observed_history(str(cycle["experiment_id"]))
                if len(history) < evaluation.window_size:
                    result = {
                        "assessment_status": "insufficient_history",
                        "history_count": len(history),
                        "required_count": evaluation.window_size,
                    }
                else:
                    update = evaluate_and_apply_executed_competence(
                        kernel,
                        competence_name=evaluation.competence_name,
                        experiment_id=str(cycle["experiment_id"]),
                        criterion=evaluation.criterion,
                        assessed_at_ns=max(now_ns, int(cycle["executed_at_ns"])),
                        window_size=evaluation.window_size,
                        servo_span_deg=evaluation.servo_span_deg,
                        model_version=evaluation.model_version,
                    )
                    assessment_digest = update.assessment.evidence_digest()
                    result = {
                        "assessment_status": "applied",
                        "assessment_digest": assessment_digest,
                        "assessment_outcome": update.assessment.outcome,
                        "application_was_new": update.applied,
                        "from_status": update.from_status.value,
                        "to_status": update.to_status.value,
                        "transition_path": [
                            status.value for status in update.transition_path
                        ],
                    }
                    if stop_after == "assessment_applied":
                        return DevelopmentCycleOutcome(
                            cycle_id=request.cycle_id,
                            status="assessment_applied_pending_cycle_commit",
                            proposal_id=str(cycle["proposal_id"]),
                            experiment_id=str(cycle["experiment_id"]),
                            execution_id=request.execution_id,
                            result=result,
                        )
            kernel.memory.advance_development_cycle(
                request.cycle_id,
                expected_status="executed",
                to_status="complete",
                changed_at_ns=max(now_ns, int(cycle["executed_at_ns"])),
                result=result,
                assessment_digest=assessment_digest,
            )
        return self._outcome(kernel, request.cycle_id)
