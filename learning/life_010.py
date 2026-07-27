"""Protected residual competence and policy features for LIFE-010."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from cognitive.models import ExperimentSignals
from j0.replay import SessionReplay
from learning.life_009 import (
    PolicyHistory,
    canonical_digest,
    stable_seed,
)
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig
from sim3d.life_executor import BoundedPrimitivePlan


LIFE010_EXPERIMENTS = (
    "probe_micro",
    "probe_reversal",
    "probe_step_hold",
)
LIFE010_PRIMITIVES = {
    "probe_micro": "probe_micro_bounded_servo",
    "probe_reversal": "probe_reversal_bounded_servo",
    "probe_step_hold": "probe_step_hold_bounded_servo",
}
LIFE010_MOTIFS = ("micro", "reversal", "step_hold")
EXPERIMENT_MOTIF = {
    "probe_micro": "micro",
    "probe_reversal": "reversal",
    "probe_step_hold": "step_hold",
}
PLAN_COST_DEG = 560.0
PLAN_STEPS = 32
CONTROL_DT = 0.02
NOMINAL_SPEED_DEG_S = 600.0
PRIOR_STEP_DEG = NOMINAL_SPEED_DEG_S * CONTROL_DT
COMPETENCE_ALPHA = 1.0
POLICY_ALPHA = 1e-2

STEP_HOLD_TARGETS = (160.0,) * 6 + (20.0,) * 6 + (160.0,) * 6 + (20.0,) * 6 + (90.0,) * 8
REVERSAL_TARGETS = (
    (50.0, 50.0, 90.0, 90.0, 130.0, 130.0, 90.0, 90.0) * 3
    + (50.0, 50.0, 90.0, 90.0)
    + (90.0, 90.0, 90.0, 90.0)
)
MICRO_TARGETS = (70.0, 90.0, 110.0, 90.0) * 7 + (90.0,) * 4
LIFE010_PLANS = (
    BoundedPrimitivePlan(LIFE010_PRIMITIVES["probe_micro"], MICRO_TARGETS),
    BoundedPrimitivePlan(LIFE010_PRIMITIVES["probe_reversal"], REVERSAL_TARGETS),
    BoundedPrimitivePlan(LIFE010_PRIMITIVES["probe_step_hold"], STEP_HOLD_TARGETS),
)


def plan_command_cost(targets: Sequence[float]) -> float:
    previous = 90.0
    cost = 0.0
    for target in targets:
        cost += abs(float(target) - previous)
        previous = float(target)
    return cost


def plan_change_count(targets: Sequence[float]) -> int:
    previous = 90.0
    changes = 0
    for target in targets:
        changes += float(target) != previous
        previous = float(target)
    return changes


@dataclass(frozen=True)
class Life010Organism:
    seed: int
    regime: str
    max_speed_deg_s: float = 600.0
    position_gain: float = 10.0
    velocity_damping: float = 0.15
    joint_frictionloss: float = 0.0147
    joint_armature: float = 2e-4

    def digest(self) -> str:
        return canonical_digest(asdict(self))


def regime_for_seed(seed: int) -> str:
    return ("speed_dominant", "settling_dominant", "friction_dominant")[seed % 3]


def sample_life010_organism(seed: int) -> Life010Organism:
    regime = regime_for_seed(seed)
    rng = np.random.default_rng(stable_seed("life010-organism-v1", int(seed)))
    values: dict[str, float | int | str] = {"seed": int(seed), "regime": regime}
    if regime == "speed_dominant":
        values["max_speed_deg_s"] = float(rng.uniform(240.0, 720.0))
    elif regime == "settling_dominant":
        values["position_gain"] = float(rng.uniform(7.0, 13.0))
        values["velocity_damping"] = float(rng.uniform(0.08, 0.24))
    else:
        values["joint_frictionloss"] = float(rng.uniform(0.006, 0.030))
        values["joint_armature"] = float(rng.uniform(1e-4, 4e-4))
    return Life010Organism(**values)


def life010_bench_config(
    organism: Life010Organism,
    execution_seed: int,
) -> BenchConfig:
    config = BenchConfig(seed=int(execution_seed), randomize_room=False)
    config.servo.max_speed_deg_s = organism.max_speed_deg_s
    config.servo.position_gain = organism.position_gain
    config.servo.velocity_damping = organism.velocity_damping
    config.servo.joint_frictionloss = organism.joint_frictionloss
    config.servo.joint_armature = organism.joint_armature
    return config


def life010_config_factory(organism: Life010Organism):
    return lambda execution_seed: life010_bench_config(organism, execution_seed)


@dataclass(frozen=True)
class DynamicsTransition:
    current_angle_deg: float
    previous_target_deg: float
    next_target_deg: float
    previous_angle_delta_deg: float
    previous_command_delta_deg: float
    next_angle_deg: float
    sequence_id: int
    motif: str

    @property
    def command_delta_deg(self) -> float:
        return self.next_target_deg - self.previous_target_deg


def transitions_from_life010_session(
    session_dir: str | Path,
    *,
    motif: str,
) -> tuple[DynamicsTransition, ...]:
    if motif not in LIFE010_MOTIFS:
        raise KeyError(motif)
    events = [
        event
        for event in SessionReplay(session_dir).events(tolerate_truncated_tail=False)
        if event.event_type == "servo_state"
    ]
    if len(events) != PLAN_STEPS:
        raise ValueError("a LIFE-010 primitive must contain exactly 32 servo events")
    result: list[DynamicsTransition] = []
    previous_angle = 90.0
    angle_before_previous = 90.0
    previous_target = 90.0
    target_before_previous = 90.0
    for event in events:
        target = float(event.payload["requested_deg"])
        next_angle = float(event.payload["as5600_deg"])
        result.append(
            DynamicsTransition(
                current_angle_deg=previous_angle,
                previous_target_deg=previous_target,
                next_target_deg=target,
                previous_angle_delta_deg=previous_angle - angle_before_previous,
                previous_command_delta_deg=previous_target - target_before_previous,
                next_angle_deg=next_angle,
                sequence_id=int(event.sequence_id),
                motif=motif,
            )
        )
        angle_before_previous = previous_angle
        previous_angle = next_angle
        target_before_previous = previous_target
        previous_target = target
    return tuple(result)


def prior_prediction(transition: DynamicsTransition) -> float:
    error = transition.next_target_deg - transition.current_angle_deg
    limited = float(np.clip(error, -PRIOR_STEP_DEG, PRIOR_STEP_DEG))
    return float(np.clip(transition.current_angle_deg + limited, 10.0, 170.0))


def residual_basis(transition: DynamicsTransition) -> np.ndarray:
    error = transition.next_target_deg - transition.current_angle_deg
    command_delta = transition.command_delta_deg
    previous_command = transition.previous_command_delta_deg
    hold = float(abs(command_delta) < 1e-9)
    reversal = float(
        command_delta * previous_command < 0.0
        and abs(command_delta) >= 1e-9
        and abs(previous_command) >= 1e-9
    )
    return np.asarray(
        [
            1.0,
            error / 160.0,
            float(np.clip(error, -12.0, 12.0)) / 12.0,
            transition.previous_angle_delta_deg / 12.0,
            command_delta / 160.0,
            previous_command / 160.0,
            hold,
            reversal,
            abs(error) / 160.0,
            error * abs(error) / (160.0**2),
            (transition.current_angle_deg - 90.0) / 80.0,
            hold * transition.previous_angle_delta_deg / 12.0,
            reversal * transition.previous_angle_delta_deg / 12.0,
        ],
        dtype=np.float64,
    )


@dataclass(frozen=True)
class ProtectedUpdate:
    accepted: bool
    current_public_mae: float
    candidate_public_mae: float
    motif: str


class ProtectedResidualCompetence:
    def __init__(self) -> None:
        self.fit_data: list[DynamicsTransition] = []
        self.public_data: list[DynamicsTransition] = []
        self.weights = np.zeros(13, dtype=np.float64)
        self.inverse_information = np.eye(13, dtype=np.float64)
        self.accepted_updates = 0
        self.rejected_updates = 0
        self.updates: list[ProtectedUpdate] = []
        self.trial_counts = {motif: 0 for motif in LIFE010_MOTIFS}
        self.first_public_mae: dict[str, float] = {}

    def copy(self) -> "ProtectedResidualCompetence":
        restored = ProtectedResidualCompetence()
        restored.fit_data = list(self.fit_data)
        restored.public_data = list(self.public_data)
        restored.weights = self.weights.copy()
        restored.inverse_information = self.inverse_information.copy()
        restored.accepted_updates = self.accepted_updates
        restored.rejected_updates = self.rejected_updates
        restored.updates = list(self.updates)
        restored.trial_counts = dict(self.trial_counts)
        restored.first_public_mae = dict(self.first_public_mae)
        return restored

    def predict(self, transition: DynamicsTransition) -> float:
        value = prior_prediction(transition) + float(residual_basis(transition) @ self.weights)
        if not math.isfinite(value):
            raise FloatingPointError("non-finite LIFE-010 competence prediction")
        return float(np.clip(value, 10.0, 170.0))

    def mae(self, transitions: Sequence[DynamicsTransition]) -> float:
        if not transitions:
            raise ValueError("MAE requires transitions")
        return float(
            np.mean(
                [
                    abs(self.predict(item) - item.next_angle_deg)
                    for item in transitions
                ]
            )
        )

    def private_mae_by_motif(
        self,
        transitions: Sequence[DynamicsTransition],
    ) -> dict[str, float]:
        return {
            motif: self.mae([item for item in transitions if item.motif == motif])
            for motif in LIFE010_MOTIFS
        }

    def _candidate_weights(self, fit_data: Sequence[DynamicsTransition]) -> tuple[np.ndarray, np.ndarray]:
        design = np.stack([residual_basis(item) for item in fit_data])
        targets = np.asarray(
            [item.next_angle_deg - prior_prediction(item) for item in fit_data],
            dtype=np.float64,
        )
        penalty = np.eye(design.shape[1], dtype=np.float64) * COMPETENCE_ALPHA
        penalty[0, 0] = 0.0
        information = design.T @ design + penalty
        weights = np.linalg.solve(information, design.T @ targets)
        inverse = np.linalg.inv(information)
        if not np.all(np.isfinite(weights)) or not np.all(np.isfinite(inverse)):
            raise FloatingPointError("non-finite LIFE-010 competence fit")
        return weights, inverse

    @staticmethod
    def _mae_with_weights(
        weights: np.ndarray,
        transitions: Sequence[DynamicsTransition],
    ) -> float:
        errors = []
        for item in transitions:
            value = prior_prediction(item) + float(residual_basis(item) @ weights)
            errors.append(abs(float(np.clip(value, 10.0, 170.0)) - item.next_angle_deg))
        return float(np.mean(errors))

    def update(self, trial: Sequence[DynamicsTransition]) -> ProtectedUpdate:
        if len(trial) != PLAN_STEPS:
            raise ValueError("protected update requires one 32-transition trial")
        motifs = {item.motif for item in trial}
        if len(motifs) != 1:
            raise ValueError("one trial must have one motif")
        motif = next(iter(motifs))
        even = [item for item in trial if item.sequence_id % 2 == 0]
        odd = [item for item in trial if item.sequence_id % 2 == 1]
        if len(even) != 16 or len(odd) != 16:
            raise AssertionError("pair/impair split must be 16/16")
        candidate_fit = self.fit_data + even
        candidate_public = self.public_data + odd
        candidate_weights, candidate_inverse = self._candidate_weights(candidate_fit)
        current_mae = self._mae_with_weights(self.weights, candidate_public)
        candidate_mae = self._mae_with_weights(candidate_weights, candidate_public)
        accepted = candidate_mae <= current_mae + 1e-12
        self.fit_data = candidate_fit
        self.public_data = candidate_public
        self.inverse_information = candidate_inverse
        self.trial_counts[motif] += 1
        if motif not in self.first_public_mae:
            motif_public = [item for item in candidate_public if item.motif == motif]
            self.first_public_mae[motif] = self._mae_with_weights(
                self.weights,
                motif_public,
            )
        if accepted:
            self.weights = candidate_weights
            self.accepted_updates += 1
        else:
            self.rejected_updates += 1
        result = ProtectedUpdate(accepted, current_mae, candidate_mae, motif)
        self.updates.append(result)
        return result

    def public_mae(self, motif: str | None = None) -> float | None:
        selected = self.public_data
        if motif is not None:
            selected = [item for item in selected if item.motif == motif]
        return None if not selected else self.mae(selected)

    def motif_uncertainty(self, motif: str) -> float:
        selected = [item for item in self.fit_data if item.motif == motif]
        if not selected:
            return 1.0
        values = [
            float(residual_basis(item) @ self.inverse_information @ residual_basis(item))
            for item in selected
        ]
        return float(max(0.0, np.mean(values)))

    def digest(self) -> str:
        return canonical_digest(
            {
                "fit_data": [asdict(item) for item in self.fit_data],
                "public_data": [asdict(item) for item in self.public_data],
                "weights": self.weights.tolist(),
                "accepted": self.accepted_updates,
                "rejected": self.rejected_updates,
                "trial_counts": self.trial_counts,
                "first_public_mae": self.first_public_mae,
            }
        )


def execute_direct_plan(
    organism: Life010Organism,
    *,
    experiment_id: str,
    execution_seed: int,
    plans: Sequence[BoundedPrimitivePlan] = LIFE010_PLANS,
    primitives: Mapping[str, str] = LIFE010_PRIMITIVES,
    motif_by_experiment: Mapping[str, str] = EXPERIMENT_MOTIF,
) -> tuple[DynamicsTransition, ...]:
    plan = next(
        plan for plan in plans
        if plan.primitive == primitives[experiment_id]
    )
    env = BenchHeadEnv(life010_bench_config(organism, execution_seed))
    try:
        previous_angle = 90.0
        angle_before_previous = 90.0
        previous_target = 90.0
        target_before_previous = 90.0
        result = []
        for sequence_id, target in enumerate(plan.targets_deg):
            observation = env.step(target)
            result.append(
                DynamicsTransition(
                    current_angle_deg=previous_angle,
                    previous_target_deg=previous_target,
                    next_target_deg=target,
                    previous_angle_delta_deg=previous_angle - angle_before_previous,
                    previous_command_delta_deg=previous_target - target_before_previous,
                    next_angle_deg=observation.as5600_deg,
                    sequence_id=sequence_id,
                    motif=motif_by_experiment[experiment_id],
                )
            )
            angle_before_previous = previous_angle
            previous_angle = observation.as5600_deg
            target_before_previous = previous_target
            previous_target = target
        return tuple(result)
    finally:
        env.close()


def build_life010_private_bank(
    organism: Life010Organism,
    *,
    experiments: Sequence[str] = LIFE010_EXPERIMENTS,
    plans: Sequence[BoundedPrimitivePlan] = LIFE010_PLANS,
    primitives: Mapping[str, str] = LIFE010_PRIMITIVES,
    motif_by_experiment: Mapping[str, str] = EXPERIMENT_MOTIF,
    seed_namespace: str = "life010-private-bank-v1",
) -> tuple[DynamicsTransition, ...]:
    result: list[DynamicsTransition] = []
    for repetition in range(2):
        for experiment_id in experiments:
            result.extend(
                execute_direct_plan(
                    organism,
                    experiment_id=experiment_id,
                    execution_seed=stable_seed(
                        seed_namespace,
                        organism.seed,
                        repetition,
                        experiment_id,
                    ),
                    plans=plans,
                    primitives=primitives,
                    motif_by_experiment=motif_by_experiment,
                )
            )
    if len(result) != 192:
        raise AssertionError("LIFE-010 private bank must contain 192 transitions")
    return tuple(result)


def life010_policy_features(
    model: ProtectedResidualCompetence,
    *,
    experiment_id: str,
    cycle_index: int,
    history: PolicyHistory,
    signals: ExperimentSignals,
    experiments: Sequence[str] = LIFE010_EXPERIMENTS,
    motif_by_experiment: Mapping[str, str] = EXPERIMENT_MOTIF,
) -> np.ndarray:
    motif = motif_by_experiment[experiment_id]
    public_global = model.public_mae()
    values: list[float] = [
        float(experiment_id == name) for name in experiments
    ]
    values.extend(
        [
            cycle_index / 24.0,
            (len(model.fit_data) + len(model.public_data)) / (24.0 * 32.0),
            model.accepted_updates / 24.0,
            model.rejected_updates / 24.0,
            0.0 if public_global is None else public_global / 160.0,
            float(public_global is None),
        ]
    )
    for name in LIFE010_MOTIFS:
        mae = model.public_mae(name)
        initial_public = model.first_public_mae.get(name)
        values.extend(
            [
                model.trial_counts[name] / 24.0,
                0.0 if mae is None else mae / 160.0,
                float(mae is None),
                0.0 if mae is None or initial_public is None else (initial_public - mae) / 160.0,
                model.motif_uncertainty(name),
            ]
        )
    motif_mae = model.public_mae(motif)
    values.extend(
        [
            model.trial_counts[motif] / 24.0,
            0.0 if motif_mae is None else motif_mae / 160.0,
            float(motif_mae is None),
            model.motif_uncertainty(motif),
        ]
    )
    values.extend([float(history.last == name) for name in experiments])
    values.append(history.consecutive_last / 24.0)
    values.extend(
        [
            signals.epistemic_gain,
            signals.learning_progress,
            signals.novelty,
            signals.controllability,
            signals.predicted_risk,
            signals.motor_cost,
            1.0,
        ]
    )
    vector = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(vector)):
        raise FloatingPointError("non-finite LIFE-010 policy feature")
    return vector


def choose_greedy_public_residual(
    model: ProtectedResidualCompetence,
    *,
    experiments: Sequence[str] = LIFE010_EXPERIMENTS,
    motif_by_experiment: Mapping[str, str] = EXPERIMENT_MOTIF,
) -> str:
    missing = [
        experiment_id
        for experiment_id in experiments
        if model.public_mae(motif_by_experiment[experiment_id]) is None
    ]
    if missing:
        return sorted(missing)[0]
    return sorted(
        experiments,
        key=lambda experiment_id: (
            -float(model.public_mae(motif_by_experiment[experiment_id])),
            experiment_id,
        ),
    )[0]


def choose_life010_uncertainty(
    model: ProtectedResidualCompetence,
    *,
    experiments: Sequence[str] = LIFE010_EXPERIMENTS,
    motif_by_experiment: Mapping[str, str] = EXPERIMENT_MOTIF,
) -> str:
    return sorted(
        experiments,
        key=lambda experiment_id: (
            -model.motif_uncertainty(motif_by_experiment[experiment_id]),
            experiment_id,
        ),
    )[0]
