"""Teacher, trajectories, and pre-bank smoke qualification for LIFE-010."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping

import numpy as np

from cognitive.experiments import SafeExperimentCatalog
from cognitive.kernel import CognitiveKernel
from cognitive.models import ExperimentSignals, ExperimentSpec, SafetyContext
from cognitive.needs import CompetenceNeedRoute, PersistentNeedActivator
from cognitive.supervisor import DevelopmentCycleRequest, PersistentDevelopmentSupervisor
from learning.life_009 import (
    ForcedChoiceActivator,
    PolicyHistory,
    ProgressRidgePolicy,
    TeacherExample,
    canonical_digest,
    clipped_progress,
    normalized_auc,
    stable_seed,
    transparent_score,
)
from learning.life_010 import (
    CONTROL_DT,
    EXPERIMENT_MOTIF,
    LIFE010_EXPERIMENTS,
    LIFE010_MOTIFS,
    LIFE010_PLANS,
    LIFE010_PRIMITIVES,
    NOMINAL_SPEED_DEG_S,
    PLAN_COST_DEG,
    PLAN_STEPS,
    POLICY_ALPHA,
    PRIOR_STEP_DEG,
    DynamicsTransition,
    Life010Organism,
    ProtectedResidualCompetence,
    ProtectedUpdate,
    build_life010_private_bank,
    choose_greedy_public_residual,
    choose_life010_uncertainty,
    life010_config_factory,
    life010_policy_features,
    plan_change_count,
    plan_command_cost,
    regime_for_seed,
    sample_life010_organism,
    transitions_from_life010_session,
)
from sim3d.life_executor import BoundedMujocoExecutor


POLICY_NAMES = (
    "learned_protected_progress_ridge_v1",
    "greedy_public_residual",
    "greedy_uncertainty",
    "round_robin",
    "life006_transparent_score",
    "uniform_random",
)


def build_life010_catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                experiment_id,
                LIFE010_PRIMITIVES[experiment_id],
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=100,
                metadata={
                    "life010_motif": EXPERIMENT_MOTIF[experiment_id],
                    "command_cost_deg": PLAN_COST_DEG,
                    "plan_steps": PLAN_STEPS,
                },
            )
            for experiment_id in LIFE010_EXPERIMENTS
        ]
    )


def build_life010_base_activator() -> PersistentNeedActivator:
    prior = ExperimentSignals(0.5, 0.5, 0.5, 0.5, 0.1, 0.5)
    priors = {experiment_id: prior for experiment_id in LIFE010_EXPERIMENTS}
    route = CompetenceNeedRoute(
        competence_name="neck_dynamics_residual_prediction",
        cold_start_signals=priors,
        unknown_experiments=LIFE010_EXPERIMENTS,
        learning_experiments=LIFE010_EXPERIMENTS,
        candidate_experiments=LIFE010_EXPERIMENTS,
        regressed_experiments=LIFE010_EXPERIMENTS,
    )
    return PersistentNeedActivator((route,))


SAFE_CONTEXT = SafetyContext(
    emergency_stop=False,
    hardware_healthy=True,
    model_update_in_progress=False,
    quota_state="ok",
    allowed_primitives=frozenset(LIFE010_PRIMITIVES.values()),
)


@dataclass(frozen=True)
class TrialExecution:
    transitions: tuple[DynamicsTransition, ...]
    realized_displacement_deg: float


class Life010Run:
    def __init__(
        self,
        root: str | Path,
        *,
        organism: Life010Organism,
        run_id: str,
        catalog_builder=build_life010_catalog,
        activator_builder=build_life010_base_activator,
        experiments=LIFE010_EXPERIMENTS,
        plans=LIFE010_PLANS,
        primitives=LIFE010_PRIMITIVES,
        motif_by_experiment=EXPERIMENT_MOTIF,
        seed_namespace: str = "life010-primitive-v1",
        protocol_name: str = "life-010-protected-curriculum",
        invariant_limits: tuple[float, float] | None = None,
        safety_context: SafetyContext = SAFE_CONTEXT,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.organism = organism
        self.run_id = run_id
        self.experiments = tuple(experiments)
        self.primitives = dict(primitives)
        self.motif_by_experiment = dict(motif_by_experiment)
        self.seed_namespace = seed_namespace
        self.protocol_name = protocol_name
        self.invariant_limits = invariant_limits
        self.safety_context = safety_context
        self.catalog = catalog_builder()
        self.base_activator = activator_builder()
        self.forced_activator = ForcedChoiceActivator(
            self.base_activator,
            allowed_experiments=self.experiments,
        )
        self.data_root = self.root / "j0"
        self.executor = BoundedMujocoExecutor(
            self.data_root,
            plans=plans,
            bench_config_factory=life010_config_factory(organism),
        )
        self.supervisor = PersistentDevelopmentSupervisor(
            self.forced_activator,
            self.executor,
        )
        self.kernel = CognitiveKernel(self.root / "memory.sqlite3", catalog=self.catalog)
        self.kernel.start_session(
            f"session-{run_id}",
            started_at_ns=1_000_000_000,
            metadata={
                "purpose": protocol_name,
                "organism_seed": organism.seed,
                "organism_digest": organism.digest(),
                "regime": organism.regime,
                "run_id": run_id,
            },
        )
        self.assessments_path = self.root / "plasticity_updates.jsonl"
        self.closed = False

    def current_signals(self) -> Mapping[str, ExperimentSignals]:
        return self.base_activator.activate(self.kernel).candidates

    def run_trial(
        self,
        experiment_id: str,
        *,
        cycle_index: int,
        decision: Mapping[str, object],
    ) -> TrialExecution:
        self.forced_activator.set_choice(experiment_id, decision=decision)
        label = f"{self.run_id}-{cycle_index:02d}"
        request = DevelopmentCycleRequest(
            cycle_id=f"cycle-{label}",
            execution_id=f"execution-{label}",
            j0_session_id=f"j0-{label}",
            seed=stable_seed(
                self.seed_namespace,
                self.organism.seed,
                cycle_index,
                experiment_id,
            ),
        )
        outcome = self.supervisor.advance(
            self.kernel,
            request,
            now_ns=2_000_000_000 + cycle_index * 1_000_000_000,
            safety=self.safety_context,
        )
        if outcome.status != "complete" or outcome.experiment_id != experiment_id:
            raise AssertionError(
                f"{self.protocol_name} cycle did not complete with its selected plan"
            )
        execution = self.kernel.memory.experiment_execution(request.execution_id)
        if execution is None or execution["status"] != "complete":
            raise AssertionError(f"{self.protocol_name} execution is not complete")
        if self.invariant_limits is not None:
            summary = json.loads(execution["result_summary_json"])
            max_risk, max_cost = self.invariant_limits
            if (
                float(summary["boundary_exposure"]) > max_risk
                or float(summary["motor_cost"]) > max_cost
            ):
                raise AssertionError(
                    f"{self.protocol_name} per-trial guard invariant failed"
                )
        transitions = transitions_from_life010_session(
            execution["session_ref"],
            motif=self.motif_by_experiment[experiment_id],
        )
        previous = 90.0
        realized = 0.0
        for item in transitions:
            realized += abs(item.next_angle_deg - previous)
            previous = item.next_angle_deg
        return TrialExecution(transitions, realized)

    def record_plasticity_update(
        self,
        *,
        cycle_index: int,
        experiment_id: str,
        update: ProtectedUpdate,
        model_digest: str,
    ) -> None:
        record = {
            "schema_version": 1,
            "cycle_index": cycle_index,
            "experiment_id": experiment_id,
            "motif": update.motif,
            "accepted": update.accepted,
            "current_public_mae": update.current_public_mae,
            "candidate_public_mae": update.candidate_public_mae,
            "model_digest": model_digest,
        }
        with self.assessments_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )

    def counts(self) -> dict[str, int]:
        connection = self.kernel.memory.connection
        assessment_count = 0
        if self.assessments_path.is_file():
            assessment_count = len(
                self.assessments_path.read_text(encoding="utf-8").splitlines()
            )
        return {
            "proposals": int(connection.execute("SELECT COUNT(*) FROM experiment_proposals").fetchone()[0]),
            "executions": int(connection.execute("SELECT COUNT(*) FROM experiment_executions").fetchone()[0]),
            "j0_sessions": len(list((self.data_root / "sessions").glob("*/manifest.json"))),
            "cycles": int(connection.execute("SELECT COUNT(*) FROM development_cycles").fetchone()[0]),
            "complete_cycles": int(
                connection.execute(
                    "SELECT COUNT(*) FROM development_cycles WHERE status='complete'"
                ).fetchone()[0]
            ),
            "assessments": assessment_count,
            "running_executions": int(
                connection.execute(
                    "SELECT COUNT(*) FROM experiment_executions WHERE status='running'"
                ).fetchone()[0]
            ),
        }

    def close(self) -> None:
        if self.closed:
            return
        if self.counts()["running_executions"]:
            raise RuntimeError("cannot close LIFE-010 run with an active execution")
        self.kernel.end_session(ended_at_ns=30_000_000_000)
        self.kernel.close()
        self.closed = True

    def __enter__(self) -> "Life010Run":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type is None:
            self.close()
        else:
            self.kernel.close()
            self.closed = True


def _expected_counts(cycles: int, *, assessments: int | None = None) -> dict[str, int]:
    return {
        "proposals": cycles,
        "executions": cycles,
        "j0_sessions": cycles,
        "cycles": cycles,
        "complete_cycles": cycles,
        "assessments": cycles if assessments is None else assessments,
        "running_executions": 0,
    }


def run_life010_branch(
    organism: Life010Organism,
    *,
    experiment_id: str,
    cycle_index: int,
    parent: Path,
    run_options: Mapping[str, Any] | None = None,
    temporary_prefix: str = "life010",
) -> TrialExecution:
    with tempfile.TemporaryDirectory(
        prefix=f"{temporary_prefix}-branch-{cycle_index:02d}-{experiment_id}-",
        dir=parent,
    ) as temporary:
        with Life010Run(
            Path(temporary) / "run",
            organism=organism,
            run_id=f"branch-{cycle_index:02d}-{experiment_id}",
            **dict(run_options or {}),
        ) as branch:
            result = branch.run_trial(
                experiment_id,
                cycle_index=cycle_index,
                decision={"policy": "teacher_counterfactual", "temporary_store": True},
            )
            if branch.counts() != _expected_counts(1, assessments=0):
                raise AssertionError(f"invalid LIFE-010 branch counts: {branch.counts()}")
            return result


@dataclass(frozen=True)
class Life010TeacherResult:
    examples: tuple[TeacherExample, ...]
    main_counts: Mapping[str, int]
    replay_bit_identical: bool
    accepted_updates: int
    rejected_updates: int
    protection_integrity: bool
    elapsed_seconds: float


def build_life010_teacher(
    root: str | Path,
    *,
    organism: Life010Organism,
    private_bank: tuple[DynamicsTransition, ...],
    cycles: int = 24,
    experiments=LIFE010_EXPERIMENTS,
    motif_by_experiment=EXPERIMENT_MOTIF,
    run_options: Mapping[str, Any] | None = None,
    temporary_prefix: str = "life010",
) -> Life010TeacherResult:
    started = time.perf_counter()
    parent = Path(root)
    parent.mkdir(parents=True, exist_ok=True)
    model = ProtectedResidualCompetence()
    history = PolicyHistory()
    examples: list[TeacherExample] = []
    bit_identical = True
    protection_integrity = True
    with Life010Run(
        parent / "main",
        organism=organism,
        run_id=f"teacher-{organism.seed}",
        **dict(run_options or {}),
    ) as main:
        for cycle_index in range(cycles):
            signals = main.current_signals()
            before = model.mae(private_bank)
            branches: dict[str, TrialExecution] = {}
            for experiment_id in experiments:
                features = life010_policy_features(
                    model,
                    experiment_id=experiment_id,
                    cycle_index=cycle_index,
                    history=history,
                    signals=signals[experiment_id],
                    experiments=experiments,
                    motif_by_experiment=motif_by_experiment,
                )
                branch = run_life010_branch(
                    organism,
                    experiment_id=experiment_id,
                    cycle_index=cycle_index,
                    parent=parent,
                    run_options=run_options,
                    temporary_prefix=temporary_prefix,
                )
                branches[experiment_id] = branch
                branch_model = model.copy()
                branch_model.update(branch.transitions)
                examples.append(
                    TeacherExample(
                        organism_seed=organism.seed,
                        cycle_index=cycle_index,
                        experiment_id=experiment_id,
                        features=tuple(float(value) for value in features),
                        target_progress=clipped_progress(
                            before,
                            branch_model.mae(private_bank),
                        ),
                    )
                )
            selected = experiments[
                (organism.seed + cycle_index) % len(experiments)
            ]
            replay = main.run_trial(
                selected,
                cycle_index=cycle_index,
                decision={"policy": "latin_square_teacher"},
            )
            if replay.transitions != branches[selected].transitions:
                bit_identical = False
                raise AssertionError("LIFE-010 branch replay is not bit-identical")
            update = model.update(replay.transitions)
            protection_integrity &= (
                not update.accepted
                or update.candidate_public_mae <= update.current_public_mae + 1e-12
            )
            main.record_plasticity_update(
                cycle_index=cycle_index,
                experiment_id=selected,
                update=update,
                model_digest=model.digest(),
            )
            history = history.append(selected)
        counts = main.counts()
        if counts != _expected_counts(cycles):
            raise AssertionError(f"LIFE-010 teacher contamination: {counts}")
    return Life010TeacherResult(
        examples=tuple(examples),
        main_counts=counts,
        replay_bit_identical=bit_identical,
        accepted_updates=model.accepted_updates,
        rejected_updates=model.rejected_updates,
        protection_integrity=protection_integrity,
        elapsed_seconds=time.perf_counter() - started,
    )


@dataclass(frozen=True)
class Life010Trajectory:
    policy: str
    regime: str
    curve: tuple[float, ...]
    public_curve: tuple[float | None, ...]
    auc: float
    final_mae: float
    worst_motif_mae: float
    motif_mae: Mapping[str, float]
    choices: tuple[str, ...]
    accepted_updates: int
    rejected_updates: int
    protection_integrity: bool
    public_private_median_gap: float
    command_cost_deg: float
    realized_displacement_deg: float
    main_counts: Mapping[str, int]
    elapsed_seconds: float
    diagnostic_curves: Mapping[str, tuple[float, ...]]


def _features(
    model: ProtectedResidualCompetence,
    *,
    cycle_index: int,
    history: PolicyHistory,
    signals: Mapping[str, ExperimentSignals],
    experiments=LIFE010_EXPERIMENTS,
    motif_by_experiment=EXPERIMENT_MOTIF,
) -> dict[str, np.ndarray]:
    return {
        experiment_id: life010_policy_features(
            model,
            experiment_id=experiment_id,
            cycle_index=cycle_index,
            history=history,
            signals=signals[experiment_id],
            experiments=experiments,
            motif_by_experiment=motif_by_experiment,
        )
        for experiment_id in experiments
    }


def _choose_policy(
    policy_name: str,
    *,
    model: ProtectedResidualCompetence,
    cycle_index: int,
    history: PolicyHistory,
    signals: Mapping[str, ExperimentSignals],
    learned: ProgressRidgePolicy,
    uniform_rng: np.random.Generator,
    experiments=LIFE010_EXPERIMENTS,
    motif_by_experiment=EXPERIMENT_MOTIF,
    learned_policy_name: str = "learned_protected_progress_ridge_v1",
) -> tuple[str, Mapping[str, Any]]:
    if policy_name == learned_policy_name:
        predictions = {
            name: learned.predict(vector)
            for name, vector in _features(
                model,
                cycle_index=cycle_index,
                history=history,
                signals=signals,
                experiments=experiments,
                motif_by_experiment=motif_by_experiment,
            ).items()
        }
        choice = sorted(predictions, key=lambda name: (-predictions[name], name))[0]
        return choice, {"policy": policy_name, "predictions": predictions}
    if policy_name == "greedy_public_residual":
        choice = choose_greedy_public_residual(
            model,
            experiments=experiments,
            motif_by_experiment=motif_by_experiment,
        )
        return choice, {
            "policy": policy_name,
            "public_mae": {
                motif: model.public_mae(motif) for motif in LIFE010_MOTIFS
            },
        }
    if policy_name == "greedy_uncertainty":
        choice = choose_life010_uncertainty(
            model,
            experiments=experiments,
            motif_by_experiment=motif_by_experiment,
        )
        return choice, {
            "policy": policy_name,
            "uncertainty": {
                motif: model.motif_uncertainty(motif) for motif in LIFE010_MOTIFS
            },
        }
    if policy_name == "round_robin":
        choice = experiments[cycle_index % len(experiments)]
        return choice, {"policy": policy_name}
    if policy_name == "life006_transparent_score":
        scores = {name: transparent_score(signals[name]) for name in experiments}
        choice = sorted(scores, key=lambda name: (-scores[name], name))[0]
        return choice, {"policy": policy_name, "scores": scores}
    if policy_name == "uniform_random":
        choice = str(uniform_rng.choice(experiments))
        return choice, {"policy": policy_name}
    raise KeyError(policy_name)


def run_life010_trajectory(
    root: str | Path,
    *,
    organism: Life010Organism,
    private_bank: tuple[DynamicsTransition, ...],
    policy_name: str,
    learned: ProgressRidgePolicy,
    cycles: int = 24,
    policy_names=POLICY_NAMES,
    experiments=LIFE010_EXPERIMENTS,
    motif_by_experiment=EXPERIMENT_MOTIF,
    run_options: Mapping[str, Any] | None = None,
    temporary_prefix: str = "life010",
    uniform_seed_namespace: str = "life010-uniform-v1",
    learned_policy_name: str = "learned_protected_progress_ridge_v1",
    command_cost_deg: float = PLAN_COST_DEG,
    diagnostic_masks: Mapping[str, tuple[bool, ...]] | None = None,
) -> Life010Trajectory:
    if policy_name not in policy_names and policy_name != "oracle":
        raise KeyError(policy_name)
    started = time.perf_counter()
    model = ProtectedResidualCompetence()
    history = PolicyHistory()
    choices: list[str] = []
    realized = 0.0
    curve = [model.mae(private_bank)]
    selected_diagnostics = dict(diagnostic_masks or {})
    if any(len(mask) != len(private_bank) for mask in selected_diagnostics.values()):
        raise ValueError("diagnostic masks must match the private bank")
    diagnostic_curves: dict[str, list[float]] = {
        name: [
            model.mae(
                [item for item, selected in zip(private_bank, mask) if selected]
            )
        ]
        for name, mask in selected_diagnostics.items()
    }
    public_curve: list[float | None] = [None]
    gaps: list[float] = []
    protection_integrity = True
    uniform_rng = np.random.default_rng(
        stable_seed(uniform_seed_namespace, organism.seed)
    )
    run_root = Path(root)
    run_root.parent.mkdir(parents=True, exist_ok=True)
    with Life010Run(
        run_root,
        organism=organism,
        run_id=f"{policy_name}-{organism.seed}",
        **dict(run_options or {}),
    ) as main:
        for cycle_index in range(cycles):
            signals = main.current_signals()
            if policy_name == "oracle":
                progress: dict[str, float] = {}
                branches: dict[str, TrialExecution] = {}
                for experiment_id in experiments:
                    branch = run_life010_branch(
                        organism,
                        experiment_id=experiment_id,
                        cycle_index=cycle_index,
                        parent=run_root.parent,
                        run_options=run_options,
                        temporary_prefix=temporary_prefix,
                    )
                    branches[experiment_id] = branch
                    candidate = model.copy()
                    candidate.update(branch.transitions)
                    progress[experiment_id] = clipped_progress(
                        curve[-1],
                        candidate.mae(private_bank),
                    )
                selected = sorted(progress, key=lambda name: (-progress[name], name))[0]
                decision: Mapping[str, Any] = {
                    "policy": "oracle_descriptive",
                    "privileged_progress": progress,
                }
            else:
                selected, decision = _choose_policy(
                    policy_name,
                    model=model,
                    cycle_index=cycle_index,
                    history=history,
                    signals=signals,
                    learned=learned,
                    uniform_rng=uniform_rng,
                    experiments=experiments,
                    motif_by_experiment=motif_by_experiment,
                    learned_policy_name=learned_policy_name,
                )
            trial = main.run_trial(
                selected,
                cycle_index=cycle_index,
                decision=decision,
            )
            if policy_name == "oracle" and trial.transitions != branches[selected].transitions:
                raise AssertionError("LIFE-010 oracle replay is not bit-identical")
            update = model.update(trial.transitions)
            protection_integrity &= (
                not update.accepted
                or update.candidate_public_mae <= update.current_public_mae + 1e-12
            )
            main.record_plasticity_update(
                cycle_index=cycle_index,
                experiment_id=selected,
                update=update,
                model_digest=model.digest(),
            )
            current_public = model.public_mae()
            current_private = model.mae(private_bank)
            if current_public is not None:
                gaps.append(current_public - current_private)
            curve.append(current_private)
            for name, mask in selected_diagnostics.items():
                diagnostic_curves[name].append(
                    model.mae(
                        [
                            item
                            for item, selected in zip(private_bank, mask)
                            if selected
                        ]
                    )
                )
            public_curve.append(current_public)
            realized += trial.realized_displacement_deg
            choices.append(selected)
            history = history.append(selected)
        counts = main.counts()
        if counts != _expected_counts(cycles):
            raise AssertionError(f"LIFE-010 policy residue: {counts}")
    motif_mae = model.private_mae_by_motif(private_bank)
    return Life010Trajectory(
        policy=policy_name,
        regime=organism.regime,
        curve=tuple(curve),
        public_curve=tuple(public_curve),
        auc=normalized_auc(curve),
        final_mae=curve[-1],
        worst_motif_mae=max(motif_mae.values()),
        motif_mae=motif_mae,
        choices=tuple(choices),
        accepted_updates=model.accepted_updates,
        rejected_updates=model.rejected_updates,
        protection_integrity=protection_integrity,
        public_private_median_gap=float(np.median(gaps)) if gaps else 0.0,
        command_cost_deg=cycles * command_cost_deg,
        realized_displacement_deg=realized,
        main_counts=counts,
        elapsed_seconds=time.perf_counter() - started,
        diagnostic_curves={
            name: tuple(values) for name, values in diagnostic_curves.items()
        },
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _relative_margin(baseline: Life010Trajectory, oracle: Life010Trajectory) -> float:
    return (baseline.auc - oracle.auc) / baseline.auc


def run_life010_smoke(output: str | Path) -> Mapping[str, Any]:
    """Run only 18191..18196 and decide whether reserved banks may open."""

    output_path = Path(output)
    report_path = output_path / "smoke_report.json"
    if report_path.is_file():
        return json.loads(report_path.read_text(encoding="utf-8"))
    if output_path.exists() and any(output_path.iterdir()):
        raise RuntimeError("incomplete LIFE-010 smoke directory exists; preserve it")
    output_path.mkdir(parents=True, exist_ok=True)

    plan_audit = {
        plan.primitive: {
            "steps": len(plan.targets_deg),
            "command_cost_deg": plan_command_cost(plan.targets_deg),
            "final_target_deg": plan.targets_deg[-1],
            "change_count": plan_change_count(plan.targets_deg),
        }
        for plan in LIFE010_PLANS
    }
    plan_gate = sorted(
        (item["steps"], item["command_cost_deg"], item["final_target_deg"])
        for item in plan_audit.values()
    ) == [(32, 560.0, 90.0)] * 3

    organisms = [sample_life010_organism(seed) for seed in range(18191, 18197)]
    if {regime: sum(item.regime == regime for item in organisms) for regime in (
        "speed_dominant", "settling_dominant", "friction_dominant"
    )} != {
        "speed_dominant": 2,
        "settling_dominant": 2,
        "friction_dominant": 2,
    }:
        raise AssertionError("smoke regimes are not balanced")

    banks: dict[int, tuple[DynamicsTransition, ...]] = {}
    bank_seconds: dict[int, float] = {}
    for organism in organisms:
        started = time.perf_counter()
        banks[organism.seed] = build_life010_private_bank(organism)
        bank_seconds[organism.seed] = time.perf_counter() - started

    teacher_results: dict[int, Life010TeacherResult] = {}
    examples: list[TeacherExample] = []
    for organism in organisms:
        result = build_life010_teacher(
            output_path / "teacher" / str(organism.seed),
            organism=organism,
            private_bank=banks[organism.seed],
        )
        teacher_results[organism.seed] = result
        examples.extend(result.examples)

    learned = ProgressRidgePolicy(alpha=POLICY_ALPHA)
    learned.fit(examples)
    replay = ProgressRidgePolicy(alpha=POLICY_ALPHA)
    replay.fit(examples)
    weight_gate = learned.digest() == replay.digest()

    trajectories: dict[int, dict[str, Life010Trajectory]] = {}
    for organism in organisms:
        by_policy: dict[str, Life010Trajectory] = {}
        for policy_name in POLICY_NAMES + ("oracle",):
            by_policy[policy_name] = run_life010_trajectory(
                output_path / "policies" / str(organism.seed) / policy_name,
                organism=organism,
                private_bank=banks[organism.seed],
                policy_name=policy_name,
                learned=learned,
            )
        trajectories[organism.seed] = by_policy

    greedy_auc = np.asarray(
        [trajectories[item.seed]["greedy_public_residual"].auc for item in organisms]
    )
    round_auc = np.asarray(
        [trajectories[item.seed]["round_robin"].auc for item in organisms]
    )
    round_co_primary = float(greedy_auc.mean()) > float(round_auc.mean())
    anchor = (
        ("greedy_public_residual", "round_robin")
        if round_co_primary
        else ("greedy_public_residual",)
    )
    greedy_margins = np.asarray(
        [
            _relative_margin(
                trajectories[item.seed]["greedy_public_residual"],
                trajectories[item.seed]["oracle"],
            )
            for item in organisms
        ]
    )
    round_margins = np.asarray(
        [
            _relative_margin(
                trajectories[item.seed]["round_robin"],
                trajectories[item.seed]["oracle"],
            )
            for item in organisms
        ]
    )

    def regime_min(margins: np.ndarray) -> dict[str, float]:
        return {
            regime: float(
                min(
                    margins[index]
                    for index, item in enumerate(organisms)
                    if item.regime == regime
                )
            )
            for regime in ("speed_dominant", "settling_dominant", "friction_dominant")
        }

    progress_ratios = {
        item.seed: (
            trajectories[item.seed]["round_robin"].final_mae
            / trajectories[item.seed]["round_robin"].curve[0]
        )
        for item in organisms
    }
    public_integrity = all(
        result.protection_integrity for result in teacher_results.values()
    ) and all(
        trajectory.protection_integrity
        for by_policy in trajectories.values()
        for trajectory in by_policy.values()
    )
    prior_alignment = (
        CONTROL_DT == 0.02
        and PRIOR_STEP_DEG == NOMINAL_SPEED_DEG_S * CONTROL_DT == 12.0
        and all(len(plan.targets_deg) == 32 for plan in LIFE010_PLANS)
    )

    average_bank = float(np.mean(list(bank_seconds.values())))
    average_teacher = float(
        np.mean([result.elapsed_seconds for result in teacher_results.values()])
    )
    average_policy_bundle = float(
        np.mean(
            [
                sum(trajectory.elapsed_seconds for trajectory in trajectories[item.seed].values())
                for item in organisms
            ]
        )
    )
    projection_seconds = (
        40.0 * (average_bank + average_teacher)
        + 24.0 * (average_bank + average_policy_bundle)
    )
    oracle_greedy_gate = (
        float(np.median(greedy_margins)) >= 0.15
        and min(regime_min(greedy_margins).values()) >= 0.05
    )
    oracle_round_gate = (
        not round_co_primary
        or (
            float(np.median(round_margins)) >= 0.15
            and min(regime_min(round_margins).values()) >= 0.05
        )
    )
    exact_counts = all(
        trajectory.main_counts == _expected_counts(24)
        for by_policy in trajectories.values()
        for trajectory in by_policy.values()
    ) and all(result.main_counts == _expected_counts(24) for result in teacher_results.values())
    branch_replay = all(result.replay_bit_identical for result in teacher_results.values())
    all_rejections = sum(
        trajectory.rejected_updates
        for by_policy in trajectories.values()
        for trajectory in by_policy.values()
    )
    gates = {
        "plans_equal_32_steps_560deg_return90": plan_gate,
        "organisms_valid_balanced": all(len(banks[item.seed]) == 192 for item in organisms),
        "branch_replay_and_counts_exact": branch_replay and exact_counts,
        "public_protection_integrity": public_integrity,
        "round_robin_private_improvement_at_least_20pct_each": all(
            ratio <= 0.80 for ratio in progress_ratios.values()
        ),
        "oracle_margin_vs_greedy": oracle_greedy_gate,
        "oracle_margin_vs_round_if_co_primary": oracle_round_gate,
        "projection_at_most_90min": projection_seconds <= 5400.0,
        "weights_bit_identical": weight_gate,
        "prior_alignment": prior_alignment,
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "campaign": "life010-smoke-v1",
        "seeds": [item.seed for item in organisms],
        "organisms": [asdict(item) for item in organisms],
        "plan_audit": plan_audit,
        "policy_digest": learned.digest(),
        "anchor_decision": {
            "greedy_mean_auc": float(greedy_auc.mean()),
            "round_robin_mean_auc": float(round_auc.mean()),
            "round_robin_is_co_primary": round_co_primary,
            "primary_baselines": list(anchor),
        },
        "margin": {
            "greedy_by_seed": {
                str(item.seed): float(greedy_margins[index])
                for index, item in enumerate(organisms)
            },
            "greedy_median": float(np.median(greedy_margins)),
            "greedy_regime_min": regime_min(greedy_margins),
            "round_robin_by_seed": {
                str(item.seed): float(round_margins[index])
                for index, item in enumerate(organisms)
            },
            "round_robin_median": float(np.median(round_margins)),
            "round_robin_regime_min": regime_min(round_margins),
            "round_robin_final_to_initial_ratio": {
                str(seed): value for seed, value in progress_ratios.items()
            },
        },
        "protection": {
            "accepted_updates": {
                str(item.seed): {
                    name: trajectory.accepted_updates
                    for name, trajectory in trajectories[item.seed].items()
                }
                for item in organisms
            },
            "rejected_updates": {
                str(item.seed): {
                    name: trajectory.rejected_updates
                    for name, trajectory in trajectories[item.seed].items()
                }
                for item in organisms
            },
            "total_rejections": all_rejections,
            "protected_plasticity_was_exercised": all_rejections > 0,
            "public_private_median_gap": {
                str(item.seed): {
                    name: trajectory.public_private_median_gap
                    for name, trajectory in trajectories[item.seed].items()
                }
                for item in organisms
            },
        },
        "trajectories": {
            str(seed): {name: asdict(value) for name, value in by_policy.items()}
            for seed, by_policy in trajectories.items()
        },
        "timing": {
            "private_bank_seconds_by_seed": bank_seconds,
            "teacher_seconds_by_seed": {
                str(seed): result.elapsed_seconds for seed, result in teacher_results.items()
            },
            "policy_bundle_seconds_by_seed": {
                str(item.seed): sum(
                    trajectory.elapsed_seconds
                    for trajectory in trajectories[item.seed].values()
                )
                for item in organisms
            },
            "projected_campaign_seconds": projection_seconds,
        },
        "gates": gates,
    }
    payload["logical_digest"] = canonical_digest(
        {
            key: value
            for key, value in payload.items()
            if key not in {"timing", "logical_digest"}
        }
    )
    _write_json(report_path, payload)
    failed = [name for name, passed in gates.items() if not passed]
    if failed:
        raise AssertionError("LIFE-010 smoke gates failed: " + ", ".join(failed))
    return payload
