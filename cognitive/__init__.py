"""Persistent, model-agnostic cognitive kernel for Project Emergence."""

from cognitive.beliefs import (
    BeliefState,
    BeliefUnavailableError,
    ClockDomainMismatchError,
    fuse_independent_gaussians,
)
from cognitive.experiments import SafeExperimentCatalog
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
    "CompetenceStatus",
    "EpisodicMemory",
    "ExperimentProposal",
    "ExperimentSignals",
    "ExperimentSpec",
    "SafeExperimentCatalog",
    "SafetyContext",
    "fuse_independent_gaussians",
]
