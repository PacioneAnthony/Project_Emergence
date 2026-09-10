"""Probabilistic J1 body-schema qualification primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Mapping, Sequence

import numpy as np

from learning.life_009 import canonical_digest, stable_seed
from learning.life_010 import (
    DynamicsTransition,
    Life010Organism,
    ProtectedResidualCompetence,
    life010_bench_config,
    prior_prediction,
    residual_basis,
)
from sim3d.bench_env import BenchHeadEnv


AS5600_STEP_DEG = 360.0 / 4096.0
ALPHA = 1.0
ENSEMBLE_SIZE = 16
PLAN_STEPS = 32
PLAN_COST_DEG = 240.0
CHECKPOINTS = tuple(range(0, 25, 3))
MOTIFS = ("impulse", "reversal", "micro")
ROLES = {
    0: "protection",
    1: "calibration",
    **{index: "learning" for index in range(2, 10)},
    10: "private",
    11: "private",
}

IMPULSE_WAYPOINTS = (150.0, 90.0, 30.0, 90.0)
IMPULSE_DURATIONS = (
    (8, 8, 8, 8),
    (5, 11, 7, 9),
    (6, 10, 6, 10),
    (7, 9, 5, 11),
    (9, 7, 11, 5),
    (10, 6, 10, 6),
    (11, 5, 9, 7),
    (4, 12, 8, 8),
    (9, 4, 11, 8),
    (8, 8, 4, 12),
    (12, 8, 8, 4),
    (6, 8, 12, 6),
)
REVERSAL_WAYPOINTS = (60.0, 90.0, 120.0, 90.0, 60.0, 90.0, 120.0, 90.0)
_REVERSAL_PATTERN = (2, 3, 4, 5, 6, 5, 4, 3)
REVERSAL_DURATIONS = (
    (4,) * 8,
    *tuple(
        _REVERSAL_PATTERN[offset:] + _REVERSAL_PATTERN[:offset]
        for offset in range(8)
    ),
    (1, 7, 1, 7, 1, 7, 1, 7),
    (7, 1, 7, 1, 7, 1, 7, 1),
    (2, 6, 2, 6, 2, 6, 2, 6),
)
MICRO_WAYPOINTS = (75.0, 90.0, 105.0, 90.0) * 4
_micro_durations: list[tuple[int, ...]] = [(2,) * 16]
for _index in range(11):
    _values = [2] * 16
    _values[_index] = 3
    _values[(_index + 5) % 16] = 1
    _micro_durations.append(tuple(_values))
MICRO_DURATIONS = tuple(_micro_durations)


@dataclass(frozen=True)
class PlanInstance:
    motif: str
    index: int
    role: str
    targets_deg: tuple[float, ...]

    @property
    def plan_id(self) -> str:
        return f"{self.motif}-{self.index:02d}"

    def digest(self) -> str:
        return canonical_digest(asdict(self))


def _expand(waypoints: Sequence[float], durations: Sequence[int]) -> tuple[float, ...]:
    return tuple(
        target
        for target, duration in zip(waypoints, durations)
        for _ in range(duration)
    )


def build_plan_instances() -> tuple[PlanInstance, ...]:
    definitions = {
        "impulse": (IMPULSE_WAYPOINTS, IMPULSE_DURATIONS),
        "reversal": (REVERSAL_WAYPOINTS, REVERSAL_DURATIONS),
        "micro": (MICRO_WAYPOINTS, MICRO_DURATIONS),
    }
    result = tuple(
        PlanInstance(
            motif=motif,
            index=index,
            role=ROLES[index],
            targets_deg=_expand(waypoints, durations),
        )
        for motif, (waypoints, by_instance) in definitions.items()
        for index, durations in enumerate(by_instance)
    )
    if len(result) != 36:
        raise AssertionError("BODY-SCHEMA-001 requires 36 plan instances")
    return result


PLAN_INSTANCES = build_plan_instances()


def command_cost(targets: Sequence[float]) -> float:
    previous = 90.0
    total = 0.0
    for target in targets:
        total += abs(float(target) - previous)
        previous = float(target)
    return total


def plan_gate() -> bool:
    return (
        len({plan.digest() for plan in PLAN_INSTANCES}) == 36
        and all(
            len(plan.targets_deg) == 32
            and plan.targets_deg[-1] == 90.0
            and min(plan.targets_deg) >= 30.0
            and max(plan.targets_deg) <= 150.0
            and command_cost(plan.targets_deg) == PLAN_COST_DEG
            for plan in PLAN_INSTANCES
        )
        and all(
            sum(plan.motif == motif and plan.role == role for plan in PLAN_INSTANCES)
            == expected
            for motif in MOTIFS
            for role, expected in (
                ("protection", 1),
                ("calibration", 1),
                ("learning", 8),
                ("private", 2),
            )
        )
    )


def regime_for_seed(seed: int) -> str:
    return ("speed_dominant", "settling_dominant", "friction_dominant")[seed % 3]


def sample_organism(seed: int) -> Life010Organism:
    regime = regime_for_seed(seed)
    rng = np.random.default_rng(stable_seed("body-schema-001-organism-v1", seed))
    values: dict[str, float | int | str] = {"seed": seed, "regime": regime}
    if regime == "speed_dominant":
        values["max_speed_deg_s"] = float(rng.uniform(240.0, 720.0))
    elif regime == "settling_dominant":
        values["position_gain"] = float(rng.uniform(7.0, 13.0))
        values["velocity_damping"] = float(rng.uniform(0.08, 0.24))
    else:
        values["joint_frictionloss"] = float(rng.uniform(0.006, 0.030))
        values["joint_armature"] = float(rng.uniform(1e-4, 4e-4))
    return Life010Organism(**values)


@dataclass(frozen=True)
class BodySample:
    transition: DynamicsTransition
    plan_id: str
    role: str
    ramp_class: str
    limited_deg: float
    joint_velocity_deg_s: float


@dataclass(frozen=True)
class BodyTrial:
    plan: PlanInstance
    condition: str
    samples: tuple[BodySample, ...]
    angle_digest: str


def _ramp_class(
    delta_limited: float,
    steps_after_arrival: int | None,
) -> tuple[str, int | None]:
    if abs(delta_limited) > 1e-12:
        return "ramp", steps_after_arrival
    next_count = 1 if steps_after_arrival is None else steps_after_arrival + 1
    return ("plateau" if next_count <= 3 else "dead_time"), next_count


def execute_plan(
    organism: Life010Organism,
    plan: PlanInstance,
    *,
    condition: str = "normal",
) -> BodyTrial:
    if condition not in {"normal", "blocked", "degraded"}:
        raise KeyError(condition)
    config = life010_bench_config(
        organism,
        stable_seed("body-schema-001-execution-v1", organism.seed, plan.plan_id, condition),
    )
    if condition == "blocked":
        config.servo.max_speed_deg_s = 0.0
    elif condition == "degraded":
        config.servo.max_speed_deg_s /= 3.0
    env = BenchHeadEnv(config)
    try:
        previous_angle = 90.0
        angle_before_previous = 90.0
        previous_target = 90.0
        target_before_previous = 90.0
        previous_limited = 90.0
        steps_after_arrival: int | None = None
        samples: list[BodySample] = []
        for sequence_id, target in enumerate(plan.targets_deg):
            current_limited = float(env._limited_deg)
            current_joint_velocity = math.degrees(
                float(env.data.qvel[env._qvel_servo])
            )
            observation = env.step(target)
            limited = float(env._limited_deg)
            delta_limited = limited - previous_limited
            if abs(delta_limited) > 1e-12:
                ramp_class = "ramp"
                steps_after_arrival = (
                    0 if abs(limited - target) <= 1e-12 else None
                )
            else:
                ramp_class, steps_after_arrival = _ramp_class(
                    delta_limited,
                    steps_after_arrival,
                )
            transition = DynamicsTransition(
                current_angle_deg=previous_angle,
                previous_target_deg=previous_target,
                next_target_deg=float(target),
                previous_angle_delta_deg=previous_angle - angle_before_previous,
                previous_command_delta_deg=previous_target - target_before_previous,
                next_angle_deg=observation.as5600_deg,
                sequence_id=sequence_id,
                motif={
                    "impulse": "step_hold",
                    "reversal": "reversal",
                    "micro": "micro",
                }[plan.motif],
            )
            samples.append(
                BodySample(
                    transition=transition,
                    plan_id=plan.plan_id,
                    role=plan.role,
                    ramp_class=ramp_class,
                    limited_deg=current_limited,
                    joint_velocity_deg_s=current_joint_velocity,
                )
            )
            angle_before_previous = previous_angle
            previous_angle = observation.as5600_deg
            target_before_previous = previous_target
            previous_target = float(target)
            previous_limited = limited
        angle_digest = canonical_digest(
            {
                "plan_id": plan.plan_id,
                "condition": condition,
                "angles": [item.transition.next_angle_deg for item in samples],
            }
        )
        return BodyTrial(plan, condition, tuple(samples), angle_digest)
    finally:
        env.close()


def life_basis(sample: BodySample) -> np.ndarray:
    return residual_basis(sample.transition)


def ensemble_basis(sample: BodySample) -> np.ndarray:
    base = list(life_basis(sample))
    transition = sample.transition
    previous_delta = transition.previous_angle_delta_deg / 12.0
    error = transition.next_target_deg - transition.current_angle_deg
    command_delta = transition.command_delta_deg
    base.extend(
        [
            previous_delta**2,
            error * transition.previous_angle_delta_deg / (160.0 * 12.0),
            command_delta * transition.previous_angle_delta_deg / (160.0 * 12.0),
            abs(transition.previous_angle_delta_deg) / 12.0,
            float(np.clip(error, -12.0, 12.0)) / 12.0 * previous_delta,
        ]
    )
    return np.asarray(base, dtype=np.float64)


def privileged_basis(sample: BodySample) -> np.ndarray:
    return np.concatenate(
        [
            ensemble_basis(sample),
            np.asarray(
                [
                    (sample.limited_deg - 90.0) / 80.0,
                    sample.joint_velocity_deg_s / 600.0,
                ],
                dtype=np.float64,
            ),
        ]
    )


def fit_ridge(
    samples: Sequence[BodySample],
    basis,
    *,
    trial_weights: Mapping[str, float] | None = None,
) -> np.ndarray:
    width = len(basis(samples[0])) if samples else 18
    if not samples:
        return np.zeros(width, dtype=np.float64)
    row_weights = np.asarray(
        [
            1.0 if trial_weights is None else trial_weights.get(sample.plan_id, 0.0)
            for sample in samples
        ],
        dtype=np.float64,
    )
    if float(row_weights.sum()) <= 0.0:
        return np.zeros(width, dtype=np.float64)
    design = np.stack([basis(sample) for sample in samples])
    targets = np.asarray(
        [
            sample.transition.next_angle_deg - prior_prediction(sample.transition)
            for sample in samples
        ],
        dtype=np.float64,
    )
    root_weights = np.sqrt(row_weights)
    weighted_design = design * root_weights[:, None]
    weighted_targets = targets * root_weights
    penalty = np.eye(design.shape[1], dtype=np.float64) * ALPHA
    penalty[0, 0] = 0.0
    return np.linalg.solve(
        weighted_design.T @ weighted_design + penalty,
        weighted_design.T @ weighted_targets,
    )


def predict_with_weights(
    samples: Sequence[BodySample],
    weights: np.ndarray,
    basis,
) -> np.ndarray:
    if not samples:
        return np.asarray([], dtype=np.float64)
    values = np.asarray(
        [
            prior_prediction(sample.transition) + float(basis(sample) @ weights)
            for sample in samples
        ],
        dtype=np.float64,
    )
    return np.clip(values, 10.0, 170.0)


def targets(samples: Sequence[BodySample]) -> np.ndarray:
    return np.asarray(
        [sample.transition.next_angle_deg for sample in samples],
        dtype=np.float64,
    )


def mae(predictions: np.ndarray, samples: Sequence[BodySample]) -> float:
    if not samples:
        raise ValueError("MAE requires samples")
    return float(np.mean(np.abs(predictions - targets(samples))))


class ProtectedFullRidge:
    def __init__(self, basis=life_basis) -> None:
        self.basis = basis
        self.weights = np.zeros(13 if basis is life_basis else 18, dtype=np.float64)
        self.accepted = 0
        self.rejected = 0

    def predict(self, samples: Sequence[BodySample]) -> np.ndarray:
        return predict_with_weights(samples, self.weights, self.basis)

    def update(
        self,
        learning_samples: Sequence[BodySample],
        protection_samples: Sequence[BodySample],
    ) -> bool:
        candidate = fit_ridge(learning_samples, self.basis)
        current_mae = mae(self.predict(protection_samples), protection_samples)
        candidate_mae = mae(
            predict_with_weights(protection_samples, candidate, self.basis),
            protection_samples,
        )
        accepted = candidate_mae <= current_mae + 1e-12
        if accepted:
            self.weights = candidate
            self.accepted += 1
        else:
            self.rejected += 1
        return accepted


class BootstrapEnsemble:
    def __init__(self, organism_seed: int) -> None:
        self.organism_seed = organism_seed
        self.members = np.zeros((ENSEMBLE_SIZE, 18), dtype=np.float64)
        self.accepted = 0
        self.rejected = 0

    def member_predictions(self, samples: Sequence[BodySample]) -> np.ndarray:
        if not samples:
            return np.empty((ENSEMBLE_SIZE, 0), dtype=np.float64)
        design = np.stack([ensemble_basis(sample) for sample in samples])
        prior = np.asarray(
            [prior_prediction(sample.transition) for sample in samples],
            dtype=np.float64,
        )
        return np.clip(prior[None, :] + self.members @ design.T, 10.0, 170.0)

    def predict(self, samples: Sequence[BodySample]) -> np.ndarray:
        return self.member_predictions(samples).mean(axis=0)

    def _candidate(
        self,
        samples: Sequence[BodySample],
        trial_ids: Sequence[str],
    ) -> np.ndarray:
        result = []
        for member in range(ENSEMBLE_SIZE):
            weights = {
                trial_id: float(
                    np.random.default_rng(
                        stable_seed(
                            "body-schema-001-bootstrap-v1",
                            self.organism_seed,
                            member,
                            trial_id,
                        )
                    ).poisson(1.0)
                )
                for trial_id in trial_ids
            }
            result.append(
                fit_ridge(samples, ensemble_basis, trial_weights=weights)
            )
        return np.stack(result)

    def update(
        self,
        learning_samples: Sequence[BodySample],
        learning_trial_ids: Sequence[str],
        protection_samples: Sequence[BodySample],
    ) -> bool:
        candidate = self._candidate(learning_samples, learning_trial_ids)
        current_mae = mae(self.predict(protection_samples), protection_samples)
        previous = self.members
        self.members = candidate
        candidate_mae = mae(self.predict(protection_samples), protection_samples)
        accepted = candidate_mae <= current_mae + 1e-12
        if accepted:
            self.accepted += 1
        else:
            self.members = previous
            self.rejected += 1
        return accepted

    def digest(self) -> str:
        return canonical_digest(
            {
                "members": self.members.tolist(),
                "accepted": self.accepted,
                "rejected": self.rejected,
            }
        )


def calibration(
    model: BootstrapEnsemble,
    calibration_samples: Sequence[BodySample],
    evaluation_samples: Sequence[BodySample],
) -> dict[str, np.ndarray | float | dict[str, int]]:
    calibration_members = model.member_predictions(calibration_samples)
    calibration_mean = calibration_members.mean(axis=0)
    calibration_residuals = targets(calibration_samples) - calibration_mean
    class_sigmas: dict[str, float] = {}
    effective: dict[str, int] = {}
    global_mad = float(np.median(np.abs(calibration_residuals - np.median(calibration_residuals))))
    global_sigma = max(AS5600_STEP_DEG, 1.4826 * global_mad)
    for class_name in ("ramp", "plateau"):
        selected = np.asarray(
            [sample.ramp_class == class_name for sample in calibration_samples]
        )
        effective[class_name] = int(selected.sum())
        if selected.any():
            values = calibration_residuals[selected]
            mad = float(np.median(np.abs(values - np.median(values))))
            class_sigmas[class_name] = max(AS5600_STEP_DEG, 1.4826 * mad)
        else:
            class_sigmas[class_name] = global_sigma
    calibration_inter = calibration_members.var(axis=0)
    calibration_sigma = np.sqrt(
        calibration_inter
        + np.asarray(
            [
                class_sigmas.get(sample.ramp_class, global_sigma) ** 2
                for sample in calibration_samples
            ]
        )
    )
    scores = np.abs(calibration_residuals) / calibration_sigma
    q = float(np.quantile(scores, 0.90, method="higher"))
    evaluation_members = model.member_predictions(evaluation_samples)
    evaluation_mean = evaluation_members.mean(axis=0)
    evaluation_sigma = np.sqrt(
        evaluation_members.var(axis=0)
        + np.asarray(
            [
                class_sigmas.get(sample.ramp_class, global_sigma) ** 2
                for sample in evaluation_samples
            ]
        )
    )
    return {
        "mean": evaluation_mean,
        "sigma": evaluation_sigma,
        "lower": np.clip(evaluation_mean - q * evaluation_sigma, 10.0, 170.0),
        "upper": np.clip(evaluation_mean + q * evaluation_sigma, 10.0, 170.0),
        "q": q,
        "effective_calibration": effective,
    }


def direction_free_auc(normal_scores: Sequence[float], fault_scores: Sequence[float]) -> float:
    normal = np.asarray(normal_scores, dtype=np.float64)
    fault = np.asarray(fault_scores, dtype=np.float64)
    comparisons = (
        (fault[:, None] > normal[None, :]).mean()
        + 0.5 * (fault[:, None] == normal[None, :]).mean()
    )
    return float(max(comparisons, 1.0 - comparisons))
