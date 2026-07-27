"""Persistent, model-agnostic cognitive kernel for Project Emergence."""

from cognitive.beliefs import (
    BeliefState,
    BeliefUnavailableError,
    ClockDomainMismatchError,
    fuse_independent_gaussians,
)
from cognitive.competence import (
    CompetenceAssessment,
    ExecutedCompetenceAssessment,
    UpperBoundCriterion,
    assess_executed_servo_tracking,
    assess_upper_bound,
)
from cognitive.development import (
    CompetenceUpdate,
    evaluate_and_apply_executed_competence,
)
from cognitive.experiments import (
    ExperimentSelectionBlockedError,
    SafeExperimentCatalog,
)
from cognitive.endurance import (
    EnduranceConfig,
    EnduranceReport,
    run_endurance_campaign,
)
from cognitive.kernel import CognitiveKernel
from cognitive.memory import EpisodicMemory
from cognitive.models import (
    BeliefEstimate,
    BeliefRequirement,
    CompetenceStatus,
    ExperimentProposal,
    ExperimentSignals,
    ExperimentSpec,
    SafetyContext,
)
from cognitive.needs import (
    CompetenceNeedRoute,
    NeedActivation,
    NoActiveNeedError,
    PersistentNeedActivator,
)
from cognitive.observed_signals import (
    ObservedExperimentEstimate,
    ObservedSignalEstimator,
    ServoSignalConfig,
    ServoTrialSummary,
    summarize_servo_trial,
)
from cognitive.supervisor import (
    CompetenceEvaluationRoute,
    CycleRecoveryError,
    DevelopmentCycleOutcome,
    DevelopmentCycleRequest,
    PersistentDevelopmentSupervisor,
)

__all__ = [
    "BeliefEstimate",
    "BeliefRequirement",
    "BeliefState",
    "BeliefUnavailableError",
    "ClockDomainMismatchError",
    "CognitiveKernel",
    "CompetenceAssessment",
    "CompetenceUpdate",
    "CompetenceStatus",
    "CompetenceNeedRoute",
    "CompetenceEvaluationRoute",
    "EpisodicMemory",
    "EnduranceConfig",
    "EnduranceReport",
    "ExperimentProposal",
    "ExperimentSelectionBlockedError",
    "ExperimentSignals",
    "ExperimentSpec",
    "CycleRecoveryError",
    "DevelopmentCycleOutcome",
    "DevelopmentCycleRequest",
    "ExecutedCompetenceAssessment",
    "ObservedExperimentEstimate",
    "ObservedSignalEstimator",
    "NeedActivation",
    "NoActiveNeedError",
    "PersistentNeedActivator",
    "PersistentDevelopmentSupervisor",
    "SafeExperimentCatalog",
    "SafetyContext",
    "ServoSignalConfig",
    "ServoTrialSummary",
    "UpperBoundCriterion",
    "assess_executed_servo_tracking",
    "assess_upper_bound",
    "evaluate_and_apply_executed_competence",
    "fuse_independent_gaussians",
    "run_endurance_campaign",
    "summarize_servo_trial",
]
