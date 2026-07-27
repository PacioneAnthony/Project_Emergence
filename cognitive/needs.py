"""Declarative activation of experiment candidates from competence needs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any, Mapping

from cognitive.kernel import CognitiveKernel
from cognitive.models import (
    CompetenceStatus,
    ExperimentProposal,
    ExperimentSignals,
    SafetyContext,
)
from cognitive.observed_signals import ObservedSignalEstimator


NEED_URGENCY: Mapping[CompetenceStatus, int] = MappingProxyType({
    CompetenceStatus.REGRESSED: 4,
    CompetenceStatus.UNKNOWN: 3,
    CompetenceStatus.LEARNING: 2,
    CompetenceStatus.CANDIDATE: 1,
    CompetenceStatus.VALIDATED: 0,
})


class NoActiveNeedError(RuntimeError):
    def __init__(self, audit: Mapping[str, Any]) -> None:
        self.audit = dict(audit)
        super().__init__("no active competence need has a routed experiment")


@dataclass(frozen=True)
class CompetenceNeedRoute:
    competence_name: str
    cold_start_signals: Mapping[str, ExperimentSignals]
    unknown_experiments: tuple[str, ...] = ()
    learning_experiments: tuple[str, ...] = ()
    candidate_experiments: tuple[str, ...] = ()
    validated_experiments: tuple[str, ...] = ()
    regressed_experiments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.competence_name:
            raise ValueError("competence_name is required")
        routed = (
            self.unknown_experiments
            + self.learning_experiments
            + self.candidate_experiments
            + self.validated_experiments
            + self.regressed_experiments
        )
        if any(not experiment_id for experiment_id in routed):
            raise ValueError("routed experiment identifiers must be non-empty")
        for experiments in (
            self.unknown_experiments,
            self.learning_experiments,
            self.candidate_experiments,
            self.validated_experiments,
            self.regressed_experiments,
        ):
            if len(set(experiments)) != len(experiments):
                raise ValueError("an experiment may appear only once per competence state")
        routed_set = set(routed)
        prior_set = set(self.cold_start_signals)
        if prior_set != routed_set:
            missing = sorted(routed_set - prior_set)
            extra = sorted(prior_set - routed_set)
            raise ValueError(
                f"cold-start prior keys must match routed experiments; "
                f"missing={missing}, extra={extra}"
            )
        object.__setattr__(
            self,
            "cold_start_signals",
            MappingProxyType(dict(self.cold_start_signals)),
        )

    def experiments_for(self, status: CompetenceStatus) -> tuple[str, ...]:
        return {
            CompetenceStatus.UNKNOWN: self.unknown_experiments,
            CompetenceStatus.LEARNING: self.learning_experiments,
            CompetenceStatus.CANDIDATE: self.candidate_experiments,
            CompetenceStatus.VALIDATED: self.validated_experiments,
            CompetenceStatus.REGRESSED: self.regressed_experiments,
            CompetenceStatus.SUSPENDED: (),
        }[status]


@dataclass(frozen=True)
class NeedActivation:
    candidates: Mapping[str, ExperimentSignals]
    signal_evidence: Mapping[str, Mapping[str, Any]]
    urgency: int
    audit: Mapping[str, Any]


class PersistentNeedActivator:
    """Build selector inputs from persisted competence states and verified histories."""

    def __init__(
        self,
        routes: tuple[CompetenceNeedRoute, ...],
        *,
        estimator: ObservedSignalEstimator | None = None,
    ) -> None:
        if not routes:
            raise ValueError("at least one competence need route is required")
        names = [route.competence_name for route in routes]
        if len(set(names)) != len(names):
            raise ValueError("competence need route names must be unique")
        priors_by_experiment: dict[str, ExperimentSignals] = {}
        for route in routes:
            for experiment_id, prior in route.cold_start_signals.items():
                existing = priors_by_experiment.get(experiment_id)
                if existing is not None and existing != prior:
                    raise ValueError(
                        f"conflicting cold-start priors for {experiment_id}"
                    )
                priors_by_experiment[experiment_id] = prior
        self.routes = tuple(sorted(routes, key=lambda route: route.competence_name))
        self.estimator = estimator or ObservedSignalEstimator()

    def activate(self, kernel: CognitiveKernel) -> NeedActivation:
        route_records: list[dict[str, Any]] = []
        routed: list[tuple[int, CompetenceNeedRoute, CompetenceStatus, tuple[str, ...]]] = []
        for route in self.routes:
            status = kernel.memory.competence_status(route.competence_name)
            experiments = route.experiments_for(status)
            if status is CompetenceStatus.SUSPENDED:
                record_status = "excluded_suspended"
                urgency = None
            elif not experiments:
                record_status = "no_route_for_status"
                urgency = NEED_URGENCY[status]
            else:
                record_status = "routable"
                urgency = NEED_URGENCY[status]
                routed.append((urgency, route, status, experiments))
            route_records.append(
                {
                    "competence_name": route.competence_name,
                    "competence_status": status.value,
                    "status": record_status,
                    "urgency": urgency,
                    "experiments": list(experiments),
                }
            )

        base_audit: dict[str, Any] = {
            "schema_version": 1,
            "policy": "highest_nonempty_need_urgency",
            "routes": route_records,
        }
        if not routed:
            base_audit["active_urgency"] = None
            base_audit["active_competences"] = []
            raise NoActiveNeedError(base_audit)

        active_urgency = max(item[0] for item in routed)
        active = [item for item in routed if item[0] == active_urgency]
        for record in route_records:
            if record["status"] == "routable":
                record["status"] = (
                    "active"
                    if record["urgency"] == active_urgency
                    else "deferred_lower_urgency"
                )
        active_competences = [
            {
                "competence_name": route.competence_name,
                "competence_status": status.value,
                "urgency": urgency,
                "experiments": list(experiments),
            }
            for urgency, route, status, experiments in active
        ]
        base_audit["active_urgency"] = active_urgency
        base_audit["active_competences"] = active_competences

        activators_by_experiment: dict[str, list[dict[str, Any]]] = {}
        prior_by_experiment: dict[str, ExperimentSignals] = {}
        for urgency, route, status, experiments in active:
            for experiment_id in experiments:
                if not kernel.catalog.has_experiment(experiment_id):
                    raise KeyError(f"need route references unknown experiment: {experiment_id}")
                activators_by_experiment.setdefault(experiment_id, []).append(
                    {
                        "competence_name": route.competence_name,
                        "competence_status": status.value,
                        "urgency": urgency,
                    }
                )
                prior_by_experiment[experiment_id] = route.cold_start_signals[
                    experiment_id
                ]

        candidates: dict[str, ExperimentSignals] = {}
        evidence: dict[str, Mapping[str, Any]] = {}
        for experiment_id in sorted(activators_by_experiment):
            history = kernel.recompute_observed_history(experiment_id)
            if history:
                estimate = self.estimator.estimate(experiment_id, history)
                candidates[experiment_id] = estimate.signals
                signal_source: dict[str, Any] = {
                    "kind": "observed_history",
                    **estimate.audit_record(),
                }
            else:
                prior = prior_by_experiment[experiment_id]
                candidates[experiment_id] = prior
                signal_source = {
                    "kind": "cold_start_prior",
                    "signals": asdict(prior),
                    "observation_count": 0,
                }
            evidence[experiment_id] = {
                "signal_source": signal_source,
                "need_activation": {
                    "policy": base_audit["policy"],
                    "active_urgency": active_urgency,
                    "activating_needs": activators_by_experiment[experiment_id],
                    "route_audit": route_records,
                },
            }

        return NeedActivation(
            candidates=candidates,
            signal_evidence=evidence,
            urgency=active_urgency,
            audit=base_audit,
        )

    def select(
        self,
        kernel: CognitiveKernel,
        *,
        now_ns: int,
        safety: SafetyContext,
    ) -> tuple[ExperimentProposal, NeedActivation]:
        activation = self.activate(kernel)
        proposal = kernel.select_experiment(
            activation.candidates,
            now_ns=now_ns,
            safety=safety,
            signal_evidence=activation.signal_evidence,
        )
        return proposal, activation
