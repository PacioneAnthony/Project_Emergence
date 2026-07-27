"""Scientific core for LIFE-009 learned sensorimotor curriculum."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from cognitive.models import ExperimentSignals
from cognitive.needs import NeedActivation, PersistentNeedActivator
from j0.replay import SessionReplay
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig
from sim3d.life_executor import BoundedPrimitivePlan


LIFE009_AMPLITUDES = (0.0, 15.0, 40.0, 70.0, 110.0, 160.0)
LIFE009_REACHABLE_AMPLITUDES = (15.0, 40.0, 70.0)
LIFE009_EXPERIMENTS = ("probe_fine", "probe_medium", "probe_wide")
LIFE009_PRIMITIVES = {
    "probe_fine": "probe_fine_bounded_servo",
    "probe_medium": "probe_medium_bounded_servo",
    "probe_wide": "probe_wide_bounded_servo",
}
LIFE009_PLANS = (
    BoundedPrimitivePlan(
        LIFE009_PRIMITIVES["probe_fine"],
        (75.0, 90.0, 105.0, 90.0) * 3,
    ),
    BoundedPrimitivePlan(
        LIFE009_PRIMITIVES["probe_medium"],
        (50.0, 90.0, 130.0, 90.0) * 3,
    ),
    BoundedPrimitivePlan(
        LIFE009_PRIMITIVES["probe_wide"],
        (20.0, 90.0, 160.0, 90.0) * 3,
    ),
)
EXPERIMENT_AMPLITUDE = {
    "probe_fine": 15.0,
    "probe_medium": 40.0,
    "probe_wide": 70.0,
}
EXPERIMENT_COMMAND_COST = {
    "probe_fine": 180.0,
    "probe_medium": 480.0,
    "probe_wide": 840.0,
}
RIDGE_ALPHA = 1e-3
ASCII_EXPERIMENT_ORDER = tuple(sorted(LIFE009_EXPERIMENTS))


def stable_seed(*parts: object) -> int:
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return int.from_bytes(
        hashlib.sha256(payload.encode("utf-8")).digest()[:4],
        "big",
    )


def canonical_digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class OrganismParameters:
    organism_seed: int
    max_speed_deg_s: float
    position_gain: float
    velocity_damping: float
    joint_frictionloss: float
    joint_armature: float

    def digest(self) -> str:
        return canonical_digest(asdict(self))


def sample_organism_parameters(seed: int) -> OrganismParameters:
    rng = np.random.default_rng(stable_seed("life009-organism-v1", int(seed)))
    return OrganismParameters(
        organism_seed=int(seed),
        max_speed_deg_s=float(rng.uniform(360.0, 720.0)),
        position_gain=float(rng.uniform(8.0, 12.0)),
        velocity_damping=float(rng.uniform(0.12, 0.18)),
        joint_frictionloss=float(rng.uniform(0.012, 0.018)),
        joint_armature=float(rng.uniform(1.6e-4, 2.4e-4)),
    )


def organism_bench_config(
    parameters: OrganismParameters,
    execution_seed: int,
) -> BenchConfig:
    config = BenchConfig(seed=int(execution_seed), randomize_room=False)
    config.servo.max_speed_deg_s = parameters.max_speed_deg_s
    config.servo.position_gain = parameters.position_gain
    config.servo.velocity_damping = parameters.velocity_damping
    config.servo.joint_frictionloss = parameters.joint_frictionloss
    config.servo.joint_armature = parameters.joint_armature
    return config


def organism_config_factory(parameters: OrganismParameters):
    def build(execution_seed: int) -> BenchConfig:
        return organism_bench_config(parameters, execution_seed)

    return build


@dataclass(frozen=True)
class OneStepTransition:
    current_angle_deg: float
    previous_target_deg: float
    next_target_deg: float
    previous_delta_deg: float
    next_angle_deg: float

    @property
    def command_delta_deg(self) -> float:
        return self.next_target_deg - self.previous_target_deg

    @property
    def command_amplitude_deg(self) -> float:
        return round(abs(self.command_delta_deg), 9)


def transitions_from_session(session_dir: str | Path) -> tuple[OneStepTransition, ...]:
    events = [
        event
        for event in SessionReplay(session_dir).events(tolerate_truncated_tail=False)
        if event.event_type == "servo_state"
    ]
    if len(events) != 12:
        raise ValueError("a LIFE-009 primitive must contain exactly 12 servo events")
    transitions: list[OneStepTransition] = []
    previous_angle = 90.0
    angle_before_previous = 90.0
    previous_target = 90.0
    for event in events:
        target = float(event.payload["requested_deg"])
        next_angle = float(event.payload["as5600_deg"])
        transitions.append(
            OneStepTransition(
                current_angle_deg=previous_angle,
                previous_target_deg=previous_target,
                next_target_deg=target,
                previous_delta_deg=previous_angle - angle_before_previous,
                next_angle_deg=next_angle,
            )
        )
        angle_before_previous = previous_angle
        previous_angle = next_angle
        previous_target = target
    return tuple(transitions)


def _basis(transition: OneStepTransition) -> np.ndarray:
    command = transition.command_delta_deg
    magnitude = abs(command)
    values = [
        (transition.current_angle_deg - 90.0) / 80.0,
        (transition.previous_target_deg - 90.0) / 80.0,
        (transition.next_target_deg - 90.0) / 80.0,
        transition.previous_delta_deg / 160.0,
        command / 160.0,
    ]
    for knot in LIFE009_AMPLITUDES:
        values.append(max(command - knot, 0.0) / 160.0)
        values.append(max(-command - knot, 0.0) / 160.0)
    values.append(magnitude / 160.0)
    return np.asarray(values, dtype=np.float64)


@dataclass(frozen=True)
class RidgeSnapshot:
    transitions: tuple[OneStepTransition, ...]


class OneStepRidgeCompetence:
    """Per-organism ridge model predicting the next AS5600 angle."""

    def __init__(self, transitions: Iterable[OneStepTransition] = ()) -> None:
        self.transitions = list(transitions)
        self.feature_mean: np.ndarray | None = None
        self.feature_scale: np.ndarray | None = None
        self.weights: np.ndarray | None = None
        self.inverse_information: np.ndarray | None = None
        self._fit()

    def snapshot(self) -> RidgeSnapshot:
        return RidgeSnapshot(tuple(self.transitions))

    @classmethod
    def from_snapshot(cls, snapshot: RidgeSnapshot) -> "OneStepRidgeCompetence":
        return cls(snapshot.transitions)

    def copy(self) -> "OneStepRidgeCompetence":
        return self.from_snapshot(self.snapshot())

    def update(self, transitions: Iterable[OneStepTransition]) -> None:
        self.transitions.extend(transitions)
        self._fit()

    def _fit(self) -> None:
        if not self.transitions:
            self.feature_mean = None
            self.feature_scale = None
            self.weights = None
            self.inverse_information = None
            return
        raw = np.stack([_basis(item) for item in self.transitions])
        mean = raw.mean(axis=0)
        scale = raw.std(axis=0)
        scale[scale == 0.0] = 1.0
        standardized = (raw - mean) / scale
        design = np.column_stack([np.ones(len(raw)), standardized])
        targets = np.asarray(
            [(item.next_angle_deg - 90.0) / 80.0 for item in self.transitions],
            dtype=np.float64,
        )
        penalty = np.eye(design.shape[1], dtype=np.float64) * RIDGE_ALPHA
        penalty[0, 0] = 0.0
        information = design.T @ design + penalty
        self.feature_mean = mean
        self.feature_scale = scale
        self.weights = np.linalg.solve(information, design.T @ targets)
        self.inverse_information = np.linalg.inv(information)
        if not all(
            np.all(np.isfinite(value))
            for value in (
                self.feature_mean,
                self.feature_scale,
                self.weights,
                self.inverse_information,
            )
        ):
            raise FloatingPointError("non-finite LIFE-009 competence fit")

    def predict(self, transition: OneStepTransition) -> float:
        if self.weights is None:
            return float(transition.current_angle_deg)
        raw = _basis(transition)
        standardized = (raw - self.feature_mean) / self.feature_scale
        design = np.concatenate(([1.0], standardized))
        prediction = 90.0 + 80.0 * float(design @ self.weights)
        if not math.isfinite(prediction):
            raise FloatingPointError("non-finite LIFE-009 prediction")
        return prediction

    def errors(self, evaluation: Sequence[OneStepTransition]) -> np.ndarray:
        return np.asarray(
            [abs(self.predict(item) - item.next_angle_deg) for item in evaluation],
            dtype=np.float64,
        )

    def mae(
        self,
        evaluation: Sequence[OneStepTransition],
        *,
        amplitudes: Sequence[float] = LIFE009_REACHABLE_AMPLITUDES,
    ) -> float:
        allowed = set(float(value) for value in amplitudes)
        selected = [
            item for item in evaluation if item.command_amplitude_deg in allowed
        ]
        if not selected:
            raise ValueError("evaluation subset is empty")
        return float(self.errors(selected).mean())

    def mae_by_amplitude(
        self,
        evaluation: Sequence[OneStepTransition],
    ) -> dict[float, float]:
        return {
            amplitude: self.mae(evaluation, amplitudes=(amplitude,))
            for amplitude in LIFE009_AMPLITUDES
        }

    def amplitude_count(self, amplitude: float) -> int:
        return sum(
            math.isclose(item.command_amplitude_deg, amplitude, abs_tol=1e-9)
            for item in self.transitions
        )

    def amplitude_residual_mean(self, amplitude: float) -> float:
        selected = [
            abs(self.predict(item) - item.next_angle_deg)
            for item in self.transitions
            if math.isclose(item.command_amplitude_deg, amplitude, abs_tol=1e-9)
        ]
        return float(np.mean(selected)) if selected else 0.0

    def amplitude_uncertainty(self, amplitude: float) -> float:
        if self.inverse_information is None:
            return 1.0
        prototypes = []
        for direction in (-1.0, 1.0):
            target = 90.0 + direction * amplitude
            if not 10.0 <= target <= 170.0:
                continue
            transition = OneStepTransition(
                current_angle_deg=90.0,
                previous_target_deg=90.0,
                next_target_deg=target,
                previous_delta_deg=0.0,
                next_angle_deg=90.0,
            )
            raw = _basis(transition)
            standardized = (raw - self.feature_mean) / self.feature_scale
            design = np.concatenate(([1.0], standardized))
            prototypes.append(float(design @ self.inverse_information @ design))
        if not prototypes:
            return 1.0
        return float(max(0.0, np.mean(prototypes)))

    def digest(self) -> str:
        payload = {
            "transitions": [asdict(item) for item in self.transitions],
            "feature_mean": None
            if self.feature_mean is None
            else self.feature_mean.tolist(),
            "feature_scale": None
            if self.feature_scale is None
            else self.feature_scale.tolist(),
            "weights": None if self.weights is None else self.weights.tolist(),
        }
        return canonical_digest(payload)


def _evaluation_pairs(amplitude: float) -> list[tuple[float, float]]:
    if amplitude == 0.0:
        starts = np.linspace(10.0, 170.0, 8)
        return [(float(start), float(start)) for start in starts]
    span = 160.0 - amplitude
    positive_starts = np.linspace(10.0, 10.0 + span, 4)
    negative_starts = np.linspace(170.0, 170.0 - span, 4)
    return [
        *((float(start), float(start + amplitude)) for start in positive_starts),
        *((float(start), float(start - amplitude)) for start in negative_starts),
    ]


def build_private_evaluation_bank(
    parameters: OrganismParameters,
) -> tuple[OneStepTransition, ...]:
    transitions: list[OneStepTransition] = []
    for amplitude in LIFE009_AMPLITUDES:
        for replicate, (start, target) in enumerate(_evaluation_pairs(amplitude)):
            seed = stable_seed(
                "life009-private-evaluation-v1",
                parameters.organism_seed,
                amplitude,
                replicate,
            )
            env = BenchHeadEnv(organism_bench_config(parameters, seed))
            try:
                before_previous = env.reset(seed=seed)
                previous = before_previous
                for _ in range(50):
                    before_previous = previous
                    previous = env.step(start)
                following = env.step(target)
                transitions.append(
                    OneStepTransition(
                        current_angle_deg=previous.as5600_deg,
                        previous_target_deg=start,
                        next_target_deg=target,
                        previous_delta_deg=(
                            previous.as5600_deg - before_previous.as5600_deg
                        ),
                        next_angle_deg=following.as5600_deg,
                    )
                )
            finally:
                env.close()
    order_rng = np.random.default_rng(
        stable_seed("life009-private-order-v1", parameters.organism_seed)
    )
    order = order_rng.permutation(len(transitions))
    result = tuple(transitions[int(index)] for index in order)
    counts = {
        amplitude: sum(
            math.isclose(item.command_amplitude_deg, amplitude, abs_tol=1e-8)
            for item in result
        )
        for amplitude in LIFE009_AMPLITUDES
    }
    if counts != {amplitude: 8 for amplitude in LIFE009_AMPLITUDES}:
        raise AssertionError(f"invalid private evaluation coverage: {counts}")
    return result


@dataclass(frozen=True)
class PolicyHistory:
    chosen: tuple[str, ...] = ()

    def append(self, experiment_id: str) -> "PolicyHistory":
        return PolicyHistory(self.chosen + (experiment_id,))

    @property
    def last(self) -> str | None:
        return self.chosen[-1] if self.chosen else None

    @property
    def consecutive_last(self) -> int:
        if not self.chosen:
            return 0
        last = self.chosen[-1]
        count = 0
        for item in reversed(self.chosen):
            if item != last:
                break
            count += 1
        return count


def policy_feature_vector(
    model: OneStepRidgeCompetence,
    *,
    experiment_id: str,
    cycle_index: int,
    history: PolicyHistory,
    signals: ExperimentSignals,
) -> np.ndarray:
    if experiment_id not in LIFE009_EXPERIMENTS:
        raise KeyError(experiment_id)
    values: list[float] = [
        float(experiment_id == name) for name in ASCII_EXPERIMENT_ORDER
    ]
    values.extend([cycle_index / 24.0, len(model.transitions) / (24.0 * 12.0)])
    for amplitude in LIFE009_AMPLITUDES:
        values.extend(
            [
                model.amplitude_count(amplitude) / (24.0 * 12.0),
                model.amplitude_residual_mean(amplitude) / 160.0,
                model.amplitude_uncertainty(amplitude),
            ]
        )
    amplitude = EXPERIMENT_AMPLITUDE[experiment_id]
    values.extend(
        [
            model.amplitude_count(amplitude) / (24.0 * 12.0),
            model.amplitude_residual_mean(amplitude) / 160.0,
            model.amplitude_uncertainty(amplitude),
        ]
    )
    values.extend(
        [float(history.last == name) for name in ASCII_EXPERIMENT_ORDER]
    )
    values.append(history.consecutive_last / 24.0)
    values.extend(
        [
            signals.epistemic_gain,
            signals.learning_progress,
            signals.novelty,
            signals.controllability,
            signals.predicted_risk,
            signals.motor_cost,
        ]
    )
    values.append(EXPERIMENT_COMMAND_COST[experiment_id] / 1000.0)
    vector = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(vector)):
        raise FloatingPointError("non-finite LIFE-009 policy feature")
    return vector


@dataclass(frozen=True)
class TeacherExample:
    organism_seed: int
    cycle_index: int
    experiment_id: str
    features: tuple[float, ...]
    target_progress: float


class ProgressRidgePolicy:
    def __init__(self) -> None:
        self.feature_mean: np.ndarray | None = None
        self.feature_scale: np.ndarray | None = None
        self.target_mean: float | None = None
        self.target_scale: float | None = None
        self.weights: np.ndarray | None = None

    def fit(self, examples: Sequence[TeacherExample]) -> None:
        if not examples:
            raise ValueError("teacher examples are required")
        raw = np.asarray([item.features for item in examples], dtype=np.float64)
        targets = np.asarray(
            [item.target_progress for item in examples],
            dtype=np.float64,
        )
        mean = raw.mean(axis=0)
        scale = raw.std(axis=0)
        scale[scale == 0.0] = 1.0
        target_mean = float(targets.mean())
        target_scale = float(targets.std())
        if target_scale == 0.0:
            target_scale = 1.0
        design = np.column_stack([np.ones(len(raw)), (raw - mean) / scale])
        standardized_target = (targets - target_mean) / target_scale
        penalty = np.eye(design.shape[1], dtype=np.float64) * RIDGE_ALPHA
        penalty[0, 0] = 0.0
        weights = np.linalg.solve(
            design.T @ design + penalty,
            design.T @ standardized_target,
        )
        if not all(
            np.all(np.isfinite(value))
            for value in (mean, scale, weights)
        ):
            raise FloatingPointError("non-finite LIFE-009 policy fit")
        self.feature_mean = mean
        self.feature_scale = scale
        self.target_mean = target_mean
        self.target_scale = target_scale
        self.weights = weights

    def predict(self, features: Sequence[float]) -> float:
        if self.weights is None:
            raise RuntimeError("policy is not fitted")
        raw = np.asarray(features, dtype=np.float64)
        design = np.concatenate(
            ([1.0], (raw - self.feature_mean) / self.feature_scale)
        )
        value = self.target_mean + self.target_scale * float(design @ self.weights)
        if not math.isfinite(value):
            raise FloatingPointError("non-finite LIFE-009 progress prediction")
        return value

    def choose(self, features: Mapping[str, Sequence[float]]) -> str:
        scored = [
            (self.predict(features[experiment_id]), experiment_id)
            for experiment_id in ASCII_EXPERIMENT_ORDER
        ]
        return sorted(scored, key=lambda item: (-item[0], item[1]))[0][1]

    def digest(self) -> str:
        if self.weights is None:
            raise RuntimeError("policy is not fitted")
        return canonical_digest(
            {
                "feature_mean": self.feature_mean.tolist(),
                "feature_scale": self.feature_scale.tolist(),
                "target_mean": self.target_mean,
                "target_scale": self.target_scale,
                "weights": self.weights.tolist(),
            }
        )


def clipped_progress(before_mae: float, after_mae: float) -> float:
    return float(np.clip((before_mae - after_mae) / max(before_mae, 1e-6), -1.0, 1.0))


def normalized_auc(curve: Sequence[float]) -> float:
    values = np.asarray(curve, dtype=np.float64)
    if len(values) != 25:
        raise ValueError("LIFE-009 curve must contain instants 0..24")
    if values[0] <= 0.0:
        raise ValueError("initial MAE must be strictly positive")
    return float(np.trapezoid(values, dx=1.0) / (24.0 * values[0]))


def transparent_score(signals: ExperimentSignals) -> float:
    return float(
        signals.epistemic_gain
        + signals.learning_progress
        + 0.25 * signals.novelty
        + 0.5 * signals.controllability
        - signals.predicted_risk
        - 0.5 * signals.motor_cost
    )


def choose_greedy_uncertainty(model: OneStepRidgeCompetence) -> str:
    scored = [
        (model.amplitude_uncertainty(EXPERIMENT_AMPLITUDE[name]), name)
        for name in ASCII_EXPERIMENT_ORDER
    ]
    return sorted(scored, key=lambda item: (-item[0], item[1]))[0][1]


def command_cost(experiment_id: str) -> float:
    return EXPERIMENT_COMMAND_COST[experiment_id]


def plan_for_experiment(experiment_id: str) -> BoundedPrimitivePlan:
    primitive = LIFE009_PRIMITIVES[experiment_id]
    return next(plan for plan in LIFE009_PLANS if plan.primitive == primitive)


class ForcedChoiceActivator:
    """Expose all LIFE-006 candidates while making one audited choice win."""

    def __init__(self, base: PersistentNeedActivator) -> None:
        self.base = base
        self.experiment_id: str | None = None
        self.decision: Mapping[str, object] = {}

    def set_choice(
        self,
        experiment_id: str,
        *,
        decision: Mapping[str, object],
    ) -> None:
        if experiment_id not in LIFE009_EXPERIMENTS:
            raise KeyError(experiment_id)
        self.experiment_id = experiment_id
        self.decision = dict(decision)

    def activate(self, kernel) -> NeedActivation:
        activation = self.base.activate(kernel)
        if self.experiment_id is None:
            raise RuntimeError("LIFE-009 choice was not set")
        if self.experiment_id not in activation.candidates:
            raise RuntimeError("LIFE-009 choice is not an active candidate")
        forced: dict[str, ExperimentSignals] = {}
        evidence: dict[str, Mapping[str, object]] = {}
        for experiment_id, original in activation.candidates.items():
            selected = experiment_id == self.experiment_id
            forced[experiment_id] = ExperimentSignals(
                epistemic_gain=1.0 if selected else 0.0,
                learning_progress=1.0 if selected else 0.0,
                novelty=1.0 if selected else 0.0,
                controllability=1.0 if selected else 0.0,
                predicted_risk=original.predicted_risk,
                motor_cost=original.motor_cost,
            )
            evidence[experiment_id] = {
                **dict(activation.signal_evidence[experiment_id]),
                "life009_curriculum": {
                    **dict(self.decision),
                    "selected_experiment_id": self.experiment_id,
                    "candidate_experiment_id": experiment_id,
                },
            }
        audit = {
            **dict(activation.audit),
            "life009_curriculum": {
                **dict(self.decision),
                "selected_experiment_id": self.experiment_id,
                "eligible_experiment_ids": list(sorted(forced)),
            },
        }
        return NeedActivation(
            candidates=forced,
            signal_evidence=evidence,
            urgency=activation.urgency,
            audit=audit,
        )
