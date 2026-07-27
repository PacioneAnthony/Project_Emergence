"""Persistent, model-agnostic cognitive kernel for Project Emergence."""

from cognitive.beliefs import (
    BeliefState,
    BeliefUnavailableError,
    ClockDomainMismatchError,
    fuse_independent_gaussians,
)
from cognitive.competence import (
    CompetenceAssessment,
    UpperBoundCriterion,
    assess_upper_bound,
)
from cognitive.experiments import (
    ExperimentSelectionBlockedError,
    SafeExperimentCatalog,
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

__all__ = [
    "BeliefEstimate",
    "BeliefRequirement",
    "BeliefState",
    "BeliefUnavailableError",
    "ClockDomainMismatchError",
    "CognitiveKernel",
    "CompetenceAssessment",
    "CompetenceStatus",
    "EpisodicMemory",
    "ExperimentProposal",
    "ExperimentSelectionBlockedError",
    "ExperimentSignals",
    "ExperimentSpec",
    "SafeExperimentCatalog",
    "SafetyContext",
    "UpperBoundCriterion",
    "assess_upper_bound",
    "fuse_independent_gaussians",
]
