"""Auditable teacher, policy trajectories, and smoke gate for LIFE-009."""

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
    ASCII_EXPERIMENT_ORDER,
    EXPERIMENT_AMPLITUDE,
    LIFE009_EXPERIMENTS,
    LIFE009_PLANS,
    LIFE009_PRIMITIVES,
    ForcedChoiceActivator,
    OneStepRidgeCompetence,
    OneStepTransition,
    OrganismParameters,
    PolicyHistory,
    ProgressRidgePolicy,
    TeacherExample,
    build_private_evaluation_bank,
    canonical_digest,
    choose_greedy_uncertainty,
    clipped_progress,
    command_cost,
    normalized_auc,
    organism_config_factory,
    policy_feature_vector,
    sample_organism_parameters,
    stable_seed,
    transitions_from_session,
    transparent_score,
)
from sim3d.life_executor import BoundedMujocoExecutor


POLICY_NAMES = (
    "learned_progress_ridge_v1",
    "greedy_uncertainty",
    "life006_transparent_score",
    "round_robin",
    "uniform_random",
)


def build_life009_catalog() -> SafeExperimentCatalog:
    return SafeExperimentCatalog(
        [
            ExperimentSpec(
                experiment_id,
                LIFE009_PRIMITIVES[experiment_id],
                max_predicted_risk=0.5,
                max_motor_cost=0.8,
                max_proposals_per_session=100,
                metadata={"life009_command_amplitude_deg": EXPERIMENT_AMPLITUDE[experiment_id]},
            )
            for experiment_id in LIFE009_EXPERIMENTS
        ]
    )


def build_life009_base_activator() -> PersistentNeedActivator:
    prior = ExperimentSignals(
        epistemic_gain=0.5,
        learning_progress=0.5,
        novelty=0.5,
        controllability=0.5,
        predicted_risk=0.1,
        motor_cost=0.5,
    )
    priors = {experiment_id: prior for experiment_id in LIFE009_EXPERIMENTS}
    route = CompetenceNeedRoute(
        competence_name="neck_one_step_prediction",
        cold_start_signals=priors,
        unknown_experiments=LIFE009_EXPERIMENTS,
        learning_experiments=LIFE009_EXPERIMENTS,
        candidate_experiments=LIFE009_EXPERIMENTS,
        regressed_experiments=LIFE009_EXPERIMENTS,
    )
    return PersistentNeedActivator((route,))


SAFE_CONTEXT = SafetyContext(
    emergency_stop=False,
    hardware_healthy=True,
    model_update_in_progress=False,
    quota_state="ok",
    allowed_primitives=frozenset(LIFE009_PRIMITIVES.values()),
)


class OrganismRun:
    """One isolated persistent LIFE trajectory for one organism and policy."""

    def __init__(
        self,
        root: str | Path,
        *,
        parameters: OrganismParameters,
        run_id: str,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.parameters = parameters
        self.run_id = run_id
        self.catalog = build_life009_catalog()
        self.base_activator = build_life009_base_activator()
        self.forced_activator = ForcedChoiceActivator(self.base_activator)
        self.data_root = self.root / "j0"
        self.executor = BoundedMujocoExecutor(
            self.data_root,
            plans=LIFE009_PLANS,
            bench_config_factory=organism_config_factory(parameters),
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
                "purpose": "life-009-curriculum",
                "organism_seed": parameters.organism_seed,
                "organism_digest": parameters.digest(),
                "run_id": run_id,
            },
        )
        self.closed = False

    def current_signals(self) -> Mapping[str, ExperimentSignals]:
        return self.base_activator.activate(self.kernel).candidates

    def run_trial(
        self,
        experiment_id: str,
        *,
        cycle_index: int,
        decision: Mapping[str, object],
    ) -> tuple[OneStepTransition, ...]:
        self.forced_activator.set_choice(experiment_id, decision=decision)
        label = f"{self.run_id}-{cycle_index:02d}"
        request = DevelopmentCycleRequest(
            cycle_id=f"cycle-{label}",
            execution_id=f"execution-{label}",
            j0_session_id=f"j0-{label}",
            seed=stable_seed(
                "life009-primitive-noise-v1",
                self.parameters.organism_seed,
                cycle_index,
                experiment_id,
            ),
        )
        outcome = self.supervisor.advance(
            self.kernel,
            request,
            now_ns=2_000_000_000 + cycle_index * 1_000_000_000,
            safety=SAFE_CONTEXT,
        )
        if outcome.status != "complete":
            raise AssertionError("LIFE-009 cycle did not complete")
        if outcome.experiment_id != experiment_id:
            raise AssertionError("LIFE-009 forced choice was not selected")
        execution = self.kernel.memory.experiment_execution(request.execution_id)
        if execution is None or execution["status"] != "complete":
            raise AssertionError("LIFE-009 execution did not complete")
        return transitions_from_session(execution["session_ref"])

    def counts(self) -> dict[str, int]:
        connection = self.kernel.memory.connection
        return {
            "proposals": int(
                connection.execute("SELECT COUNT(*) FROM experiment_proposals").fetchone()[0]
            ),
            "executions": int(
                connection.execute("SELECT COUNT(*) FROM experiment_executions").fetchone()[0]
            ),
            "cycles": int(
                connection.execute("SELECT COUNT(*) FROM development_cycles").fetchone()[0]
            ),
            "complete_cycles": int(
                connection.execute(
                    "SELECT COUNT(*) FROM development_cycles WHERE status='complete'"
                ).fetchone()[0]
            ),
            "running_executions": int(
                connection.execute(
                    "SELECT COUNT(*) FROM experiment_executions WHERE status='running'"
                ).fetchone()[0]
            ),
        }

    def close(self) -> None:
        if self.closed:
            return
        counts = self.counts()
        if counts["running_executions"]:
            raise RuntimeError("cannot close LIFE-009 run with an active execution")
        self.kernel.end_session(
            ended_at_ns=30_000_000_000,
        )
        self.kernel.close()
        self.closed = True

    def __enter__(self) -> "OrganismRun":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if exc_type is None:
            self.close()
        else:
            self.kernel.close()
            self.closed = True


def run_isolated_branch(
    parameters: OrganismParameters,
    *,
    experiment_id: str,
    cycle_index: int,
    parent: Path,
) -> tuple[OneStepTransition, ...]:
    """Execute a counterfactual with disposable SQLite and J0 stores."""

    with tempfile.TemporaryDirectory(
        prefix=f"life009-branch-{cycle_index:02d}-{experiment_id}-",
        dir=parent,
    ) as temporary:
        branch_root = Path(temporary) / "run"
        with OrganismRun(
            branch_root,
            parameters=parameters,
            run_id=f"branch-{cycle_index:02d}-{experiment_id}",
        ) as branch:
            transitions = branch.run_trial(
                experiment_id,
                cycle_index=cycle_index,
                decision={
                    "policy": "teacher_counterfactual",
                    "temporary_store": True,
                },
            )
            counts = branch.counts()
            if counts != {
                "proposals": 1,
                "executions": 1,
                "cycles": 1,
                "complete_cycles": 1,
                "running_executions": 0,
            }:
                raise AssertionError(f"invalid branch counts: {counts}")
            return transitions


@dataclass(frozen=True)
class TeacherResult:
    examples: tuple[TeacherExample, ...]
    final_model_digest: str
    main_counts: Mapping[str, int]
    replay_bit_identical: bool
    elapsed_seconds: float


def build_teacher_trajectory(
    root: str | Path,
    *,
    parameters: OrganismParameters,
    evaluation: tuple[OneStepTransition, ...],
    cycles: int = 24,
) -> TeacherResult:
    started = time.perf_counter()
    parent = Path(root)
    parent.mkdir(parents=True, exist_ok=True)
    model = OneStepRidgeCompetence()
    history = PolicyHistory()
    examples: list[TeacherExample] = []
    replay_bit_identical = True
    with OrganismRun(
        parent / "main",
        parameters=parameters,
        run_id=f"teacher-{parameters.organism_seed}",
    ) as main:
        for cycle_index in range(cycles):
            signals = main.current_signals()
            before_mae = model.mae(evaluation)
            branch_trials: dict[str, tuple[OneStepTransition, ...]] = {}
            for experiment_id in ASCII_EXPERIMENT_ORDER:
                features = policy_feature_vector(
                    model,
                    experiment_id=experiment_id,
                    cycle_index=cycle_index,
                    history=history,
                    signals=signals[experiment_id],
                )
                transitions = run_isolated_branch(
                    parameters,
                    experiment_id=experiment_id,
                    cycle_index=cycle_index,
                    parent=parent,
                )
                branch_trials[experiment_id] = transitions
                branch_model = model.copy()
                branch_model.update(transitions)
                examples.append(
                    TeacherExample(
                        organism_seed=parameters.organism_seed,
                        cycle_index=cycle_index,
                        experiment_id=experiment_id,
                        features=tuple(float(value) for value in features),
                        target_progress=clipped_progress(
                            before_mae,
                            branch_model.mae(evaluation),
                        ),
                    )
                )
            selected = ASCII_EXPERIMENT_ORDER[
                (parameters.organism_seed + cycle_index) % len(ASCII_EXPERIMENT_ORDER)
            ]
            replayed = main.run_trial(
                selected,
                cycle_index=cycle_index,
                decision={
                    "policy": "latin_square_teacher",
                    "selected_index": ASCII_EXPERIMENT_ORDER.index(selected),
                },
            )
            replay_bit_identical &= replayed == branch_trials[selected]
            if replayed != branch_trials[selected]:
                raise AssertionError("counterfactual branch replay was not bit-identical")
            model.update(replayed)
            history = history.append(selected)
        counts = main.counts()
        expected = {
            "proposals": cycles,
            "executions": cycles,
            "cycles": cycles,
            "complete_cycles": cycles,
            "running_executions": 0,
        }
        if counts != expected:
            raise AssertionError(f"teacher main-store contamination: {counts}")
    return TeacherResult(
        examples=tuple(examples),
        final_model_digest=model.digest(),
        main_counts=counts,
        replay_bit_identical=replay_bit_identical,
        elapsed_seconds=time.perf_counter() - started,
    )


@dataclass(frozen=True)
class TrajectoryResult:
    policy: str
    curve: tuple[float, ...]
    auc: float
    final_mae: float
    worst_reachable_mae: float
    out_of_domain_mae: Mapping[str, float]
    command_cost_deg: float
    choices: tuple[str, ...]
    main_counts: Mapping[str, int]
    evaluation_seconds: float
    elapsed_seconds: float


def _feature_map(
    model: OneStepRidgeCompetence,
    *,
    cycle_index: int,
    history: PolicyHistory,
    signals: Mapping[str, ExperimentSignals],
) -> dict[str, np.ndarray]:
    return {
        experiment_id: policy_feature_vector(
            model,
            experiment_id=experiment_id,
            cycle_index=cycle_index,
            history=history,
            signals=signals[experiment_id],
        )
        for experiment_id in ASCII_EXPERIMENT_ORDER
    }


def _choose_non_oracle(
    policy_name: str,
    *,
    cycle_index: int,
    model: OneStepRidgeCompetence,
    history: PolicyHistory,
    signals: Mapping[str, ExperimentSignals],
    learned_policy: ProgressRidgePolicy,
    uniform_rng: np.random.Generator,
) -> tuple[str, Mapping[str, Any]]:
    features = _feature_map(
        model,
        cycle_index=cycle_index,
        history=history,
        signals=signals,
    )
    if policy_name == "learned_progress_ridge_v1":
        predictions = {
            name: learned_policy.predict(vector)
            for name, vector in features.items()
        }
        selected = sorted(
            predictions,
            key=lambda name: (-predictions[name], name),
        )[0]
        return selected, {"policy": policy_name, "predictions": predictions}
    if policy_name == "greedy_uncertainty":
        selected = choose_greedy_uncertainty(model)
        return selected, {
            "policy": policy_name,
            "uncertainties": {
                name: model.amplitude_uncertainty(EXPERIMENT_AMPLITUDE[name])
                for name in ASCII_EXPERIMENT_ORDER
            },
        }
    if policy_name == "life006_transparent_score":
        scores = {
            name: transparent_score(signals[name])
            for name in ASCII_EXPERIMENT_ORDER
        }
        selected = sorted(scores, key=lambda name: (-scores[name], name))[0]
        return selected, {"policy": policy_name, "scores": scores}
    if policy_name == "round_robin":
        selected = ASCII_EXPERIMENT_ORDER[cycle_index % len(ASCII_EXPERIMENT_ORDER)]
        return selected, {"policy": policy_name, "cycle_index": cycle_index}
    if policy_name == "uniform_random":
        selected = str(uniform_rng.choice(ASCII_EXPERIMENT_ORDER))
        return selected, {"policy": policy_name, "cycle_index": cycle_index}
    raise KeyError(policy_name)


def run_policy_trajectory(
    root: str | Path,
    *,
    parameters: OrganismParameters,
    evaluation: tuple[OneStepTransition, ...],
    policy_name: str,
    learned_policy: ProgressRidgePolicy,
    cycles: int = 24,
) -> TrajectoryResult:
    if policy_name not in POLICY_NAMES and policy_name != "oracle":
        raise KeyError(policy_name)
    started = time.perf_counter()
    evaluation_seconds = 0.0
    model = OneStepRidgeCompetence()
    history = PolicyHistory()
    choices: list[str] = []
    cost = 0.0
    eval_started = time.perf_counter()
    curve = [model.mae(evaluation)]
    evaluation_seconds += time.perf_counter() - eval_started
    uniform_rng = np.random.default_rng(
        stable_seed("life009-uniform-random-v1", parameters.organism_seed)
    )
    run_root = Path(root)
    run_root.parent.mkdir(parents=True, exist_ok=True)
    with OrganismRun(
        run_root,
        parameters=parameters,
        run_id=f"{policy_name}-{parameters.organism_seed}",
    ) as main:
        for cycle_index in range(cycles):
            signals = main.current_signals()
            if policy_name == "oracle":
                before_mae = curve[-1]
                progress: dict[str, float] = {}
                branches: dict[str, tuple[OneStepTransition, ...]] = {}
                for experiment_id in ASCII_EXPERIMENT_ORDER:
                    transitions = run_isolated_branch(
                        parameters,
                        experiment_id=experiment_id,
                        cycle_index=cycle_index,
                        parent=run_root.parent,
                    )
                    branches[experiment_id] = transitions
                    candidate_model = model.copy()
                    candidate_model.update(transitions)
                    progress[experiment_id] = clipped_progress(
                        before_mae,
                        candidate_model.mae(evaluation),
                    )
                selected = sorted(
                    progress,
                    key=lambda name: (-progress[name], name),
                )[0]
                decision: Mapping[str, Any] = {
                    "policy": "oracle_descriptive",
                    "privileged_progress": progress,
                }
            else:
                selected, decision = _choose_non_oracle(
                    policy_name,
                    cycle_index=cycle_index,
                    model=model,
                    history=history,
                    signals=signals,
                    learned_policy=learned_policy,
                    uniform_rng=uniform_rng,
                )
            transitions = main.run_trial(
                selected,
                cycle_index=cycle_index,
                decision=decision,
            )
            if policy_name == "oracle" and transitions != branches[selected]:
                raise AssertionError("oracle branch replay was not bit-identical")
            model.update(transitions)
            history = history.append(selected)
            choices.append(selected)
            cost += command_cost(selected)
            eval_started = time.perf_counter()
            curve.append(model.mae(evaluation))
            evaluation_seconds += time.perf_counter() - eval_started
        counts = main.counts()
        expected = {
            "proposals": cycles,
            "executions": cycles,
            "cycles": cycles,
            "complete_cycles": cycles,
            "running_executions": 0,
        }
        if counts != expected:
            raise AssertionError(f"policy main-store residue: {counts}")
    by_amplitude = model.mae_by_amplitude(evaluation)
    reachable = [by_amplitude[value] for value in (15.0, 40.0, 70.0)]
    out_of_domain = {
        str(int(value)): by_amplitude[value] for value in (0.0, 110.0, 160.0)
    }
    return TrajectoryResult(
        policy=policy_name,
        curve=tuple(curve),
        auc=normalized_auc(curve),
        final_mae=float(curve[-1]),
        worst_reachable_mae=float(max(reachable)),
        out_of_domain_mae=out_of_domain,
        command_cost_deg=cost,
        choices=tuple(choices),
        main_counts=counts,
        evaluation_seconds=evaluation_seconds,
        elapsed_seconds=time.perf_counter() - started,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_life009_smoke(output: str | Path) -> Mapping[str, Any]:
    """Run only seed 17991 and decide whether reserved banks may be opened."""

    output_path = Path(output)
    report_path = output_path / "smoke_report.json"
    if report_path.is_file():
        return json.loads(report_path.read_text(encoding="utf-8"))
    if output_path.exists() and any(output_path.iterdir()):
        raise RuntimeError("incomplete LIFE-009 smoke directory exists; preserve it for audit")
    output_path.mkdir(parents=True, exist_ok=True)
    parameters = sample_organism_parameters(17991)

    bank_started = time.perf_counter()
    evaluation = build_private_evaluation_bank(parameters)
    bank_seconds = time.perf_counter() - bank_started

    teacher = build_teacher_trajectory(
        output_path / "teacher",
        parameters=parameters,
        evaluation=evaluation,
    )
    learned = ProgressRidgePolicy()
    learned.fit(teacher.examples)
    learned_replay = ProgressRidgePolicy()
    learned_replay.fit(teacher.examples)
    weights_bit_identical = learned.digest() == learned_replay.digest()

    trajectories: dict[str, TrajectoryResult] = {}
    test_started = time.perf_counter()
    for policy_name in POLICY_NAMES:
        trajectories[policy_name] = run_policy_trajectory(
            output_path / "policies" / policy_name,
            parameters=parameters,
            evaluation=evaluation,
            policy_name=policy_name,
            learned_policy=learned,
        )
    five_policy_seconds = time.perf_counter() - test_started
    oracle_started = time.perf_counter()
    oracle = run_policy_trajectory(
        output_path / "policies" / "oracle",
        parameters=parameters,
        evaluation=evaluation,
        policy_name="oracle",
        learned_policy=learned,
    )
    oracle_seconds = time.perf_counter() - oracle_started
    trajectories["oracle"] = oracle

    analysis_started = time.perf_counter()
    greedy = trajectories["greedy_uncertainty"]
    round_robin = trajectories["round_robin"]
    oracle_margin = (greedy.auc - oracle.auc) / greedy.auc
    curve_seconds = sum(
        trajectory.evaluation_seconds
        for trajectory in trajectories.values()
    )
    test_without_curve = max(0.0, five_policy_seconds - sum(
        trajectories[name].evaluation_seconds for name in POLICY_NAMES
    ))
    analysis_seconds = time.perf_counter() - analysis_started
    protocol_projection_seconds = (
        40.0 * (bank_seconds + teacher.elapsed_seconds)
        + 24.0 * (bank_seconds + test_without_curve + curve_seconds)
        + analysis_seconds
    )
    conservative_projection_seconds = (
        protocol_projection_seconds + 24.0 * oracle_seconds
    )
    gates = {
        "private_bank_48": len(evaluation) == 48,
        "teacher_examples_72": len(teacher.examples) == 72,
        "branch_replay_bit_identical": teacher.replay_bit_identical,
        "weights_bit_identical": weights_bit_identical,
        "round_robin_progress_12_to_24": round_robin.curve[12] > round_robin.curve[24],
        "oracle_margin_at_least_10pct": oracle_margin >= 0.10,
        "projection_at_most_60min": conservative_projection_seconds <= 3600.0,
        "all_main_counts_exact": all(
            trajectory.main_counts
            == {
                "proposals": 24,
                "executions": 24,
                "cycles": 24,
                "complete_cycles": 24,
                "running_executions": 0,
            }
            for trajectory in trajectories.values()
        ),
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "campaign": "life009-smoke-v1",
        "seed": 17991,
        "organism": asdict(parameters),
        "organism_digest": parameters.digest(),
        "policy_digest": learned.digest(),
        "private_bank_digest": canonical_digest(
            [asdict(item) for item in evaluation]
        ),
        "teacher": {
            "example_count": len(teacher.examples),
            "final_model_digest": teacher.final_model_digest,
            "main_counts": dict(teacher.main_counts),
            "replay_bit_identical": teacher.replay_bit_identical,
        },
        "trajectories": {
            name: asdict(result) for name, result in trajectories.items()
        },
        "margin": {
            "oracle_relative_improvement_vs_greedy": oracle_margin,
            "round_robin_mae_cycle_12": round_robin.curve[12],
            "round_robin_mae_cycle_24": round_robin.curve[24],
        },
        "timing": {
            "private_bank_seconds": bank_seconds,
            "teacher_organism_seconds": teacher.elapsed_seconds,
            "five_policy_organism_seconds": five_policy_seconds,
            "five_policy_without_curve_seconds": test_without_curve,
            "curve_seconds": curve_seconds,
            "oracle_seconds": oracle_seconds,
            "analysis_seconds": analysis_seconds,
            "protocol_projection_seconds": protocol_projection_seconds,
            "conservative_projection_seconds": conservative_projection_seconds,
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
        raise AssertionError("LIFE-009 smoke gates failed: " + ", ".join(failed))
    return payload

