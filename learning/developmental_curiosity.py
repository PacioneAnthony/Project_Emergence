"""Continuous developmental curiosity without hand-authored difficulty levels.

The scheduler treats difficulty as a relation between the learner and a
state-action descriptor.  It combines local learning progress, reducible
uncertainty from a bootstrapped kernel ensemble, habituation, persistent
unpredictability, controllability and risk.  A competence-dependent frontier
keeps early exploration close to a safe home descriptor and expands as the
global prediction error decreases.

This module is deliberately model-agnostic and CPU-only.  The controlled
probe and promotion criteria are documented in
``docs/research/developmental_curiosity_probe.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CuriosityWeights:
    progress: float = 1.0
    epistemic: float = 0.8
    novelty: float = 0.15
    habituation: float = 0.45
    irreducible: float = 0.8
    risk: float = 1.0


class DevelopmentalCuriosity:
    """Score continuous candidate experiences from online prediction errors.

    Descriptors must be normalized to roughly ``[0, 1]`` per dimension.  No
    semantic region or fixed difficulty label is required.  Bootstrap members
    carry different smooth priors; their predictions converge where evidence
    accumulates, making their disagreement a cheap estimate of reducible
    uncertainty.  Local residual variance and stable high error are treated as
    evidence of irreducible unpredictability instead of as permanent novelty.
    """

    def __init__(
        self,
        descriptor_dim: int,
        home_descriptor: np.ndarray,
        *,
        bandwidth: float = 0.18,
        ensemble_size: int = 7,
        min_evidence: float = 8.0,
        initial_frontier: float = 0.12,
        max_frontier: float = 0.75,
        epsilon: float = 0.05,
        prior_strength: float = 2.0,
        max_observations: int = 2048,
        seed: int = 0,
        weights: CuriosityWeights | None = None,
    ):
        if descriptor_dim <= 0:
            raise ValueError("descriptor_dim must be positive")
        home = np.asarray(home_descriptor, dtype=np.float64)
        if home.shape != (descriptor_dim,):
            raise ValueError(f"home_descriptor must have shape ({descriptor_dim},)")
        if bandwidth <= 0 or ensemble_size < 2 or min_evidence <= 0 or max_observations < 2:
            raise ValueError("bandwidth/min_evidence must be positive, ensemble_size/max_observations >= 2")
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")

        self.descriptor_dim = descriptor_dim
        self.home_descriptor = home
        self.bandwidth = float(bandwidth)
        self.ensemble_size = int(ensemble_size)
        self.min_evidence = float(min_evidence)
        self.initial_frontier = float(initial_frontier)
        self.max_frontier = float(max_frontier)
        self.epsilon = float(epsilon)
        self.prior_strength = float(prior_strength)
        self.max_observations = int(max_observations)
        self.weights = weights or CuriosityWeights()

        rng = np.random.default_rng(seed)
        self._prior_vectors = rng.normal(size=(ensemble_size, descriptor_dim))
        self._prior_bias = rng.normal(size=ensemble_size)
        self._bootstrap_rng = np.random.default_rng(seed + 1)
        self._descriptors: list[np.ndarray] = []
        self._errors: list[float] = []
        self._controllability: list[float] = []
        self._bootstrap_counts: list[np.ndarray] = []
        self._initial_error_scale: float | None = None

    @property
    def observation_count(self) -> int:
        return len(self._errors)

    def observe(self, descriptor: np.ndarray, error: float, *, controllability: float = 1.0) -> None:
        descriptor = self._validate_descriptors(descriptor, single=True)[0]
        if not np.isfinite(error) or error < 0:
            raise ValueError("error must be finite and non-negative")
        if not np.isfinite(controllability):
            raise ValueError("controllability must be finite")

        self._descriptors.append(descriptor)
        self._errors.append(float(error))
        self._controllability.append(float(np.clip(controllability, 0.0, 1.0)))
        self._bootstrap_counts.append(self._bootstrap_rng.poisson(1.0, self.ensemble_size).astype(np.float64))

        if len(self._errors) > self.max_observations:
            self._descriptors.pop(0)
            self._errors.pop(0)
            self._controllability.pop(0)
            self._bootstrap_counts.pop(0)

        if self._initial_error_scale is None and len(self._errors) >= max(4, int(self.min_evidence // 2)):
            self._initial_error_scale = max(float(np.median(self._errors)), 1e-8)

    def mastery(self) -> float:
        """Global error reduction used only to widen the safe frontier."""

        if self._initial_error_scale is None or not self._errors:
            return 0.0
        tail = self._errors[-max(4, min(32, len(self._errors) // 2)) :]
        recent = float(np.median(tail))
        return float(np.clip(1.0 - recent / self._initial_error_scale, 0.0, 1.0))

    def score_components(
        self,
        candidates: np.ndarray,
        *,
        controllability: np.ndarray | None = None,
        risk: np.ndarray | None = None,
    ) -> dict[str, np.ndarray]:
        candidates = self._validate_descriptors(candidates)
        count = len(candidates)
        candidate_control = self._candidate_vector(controllability, count, default=1.0, name="controllability")
        candidate_control = np.clip(candidate_control, 0.0, 1.0)
        candidate_risk = self._candidate_vector(risk, count, default=0.0, name="risk")
        candidate_risk = np.maximum(candidate_risk, 0.0)

        if not self._errors:
            distance = np.linalg.norm(candidates - self.home_descriptor[None, :], axis=1)
            reachability = np.exp(-0.5 * np.square(distance / self.initial_frontier))
            zeros = np.zeros(count, dtype=np.float64)
            score = self.weights.novelty * reachability - self.weights.risk * candidate_risk
            return {
                "score": score,
                "progress": zeros,
                "epistemic": zeros,
                "familiarity": zeros,
                "habituation": zeros,
                "irreducible": zeros,
                "reachability": reachability,
            }

        descriptors = np.stack(self._descriptors)
        errors = np.asarray(self._errors, dtype=np.float64)
        controls = np.asarray(self._controllability, dtype=np.float64)
        distance_sq = np.sum(np.square(candidates[:, None, :] - descriptors[None, :, :]), axis=2)
        kernel = np.exp(-0.5 * distance_sq / (self.bandwidth * self.bandwidth))
        evidence = kernel.sum(axis=1)
        familiarity = 1.0 - np.exp(-evidence / self.min_evidence)

        scale = max(float(np.median(errors)), self._initial_error_scale or 0.0, 1e-8)
        recent_mask = np.zeros(len(errors), dtype=np.float64)
        recent_mask[len(errors) // 2 :] = 1.0
        old_mask = 1.0 - recent_mask
        old_mean, old_weight = self._weighted_mean(kernel, errors, old_mask)
        recent_mean, recent_weight = self._weighted_mean(kernel, errors, recent_mask)
        progress = np.maximum(old_mean - recent_mean, 0.0) / scale
        progress *= np.minimum(old_weight, recent_weight) / (np.minimum(old_weight, recent_weight) + self.min_evidence)
        progress = np.clip(progress, 0.0, 2.0)

        local_mean, _ = self._weighted_mean(kernel, errors, np.ones(len(errors)))
        local_second, _ = self._weighted_mean(kernel, np.square(errors), np.ones(len(errors)))
        residual_std = np.sqrt(np.maximum(local_second - np.square(local_mean), 0.0)) / scale

        bootstrap = np.stack(self._bootstrap_counts)
        prior_phase = candidates @ self._prior_vectors.T + self._prior_bias[None, :]
        prior = scale * (1.0 + 0.35 * np.tanh(prior_phase))
        weighted = kernel[:, :, None] * bootstrap[None, :, :]
        member_evidence = weighted.sum(axis=1)
        member_prediction = (
            np.einsum("cnm,n->cm", weighted, errors) + self.prior_strength * prior
        ) / (member_evidence + self.prior_strength)
        epistemic = np.std(member_prediction, axis=1) / scale

        known = np.vstack([self.home_descriptor[None, :], descriptors])
        nearest = np.sqrt(np.min(np.sum(np.square(candidates[:, None, :] - known[None, :, :]), axis=2), axis=1))
        frontier = self.initial_frontier + self.mastery() * (self.max_frontier - self.initial_frontier)
        reachability = np.exp(-0.5 * np.square(nearest / max(frontier, 1e-8)))

        local_control, _ = self._weighted_mean(kernel, controls, np.ones(len(errors)))
        effective_control = np.clip(0.5 * candidate_control + 0.5 * local_control, 0.0, 1.0)
        normalized_error = np.clip(recent_mean / scale, 0.0, 3.0)
        habituation = familiarity * np.exp(-normalized_error)
        irreducible = familiarity * (residual_std + normalized_error * (1.0 - np.clip(progress, 0.0, 1.0)))
        irreducible *= 1.0 / (1.0 + 4.0 * epistemic)
        novelty = 1.0 - familiarity

        learnable = self.weights.progress * progress + self.weights.epistemic * epistemic
        positive = reachability * effective_control * (learnable + self.weights.novelty * novelty)
        score = positive - self.weights.habituation * habituation
        score -= self.weights.irreducible * irreducible + self.weights.risk * candidate_risk
        return {
            "score": score,
            "progress": progress,
            "epistemic": epistemic,
            "familiarity": familiarity,
            "habituation": habituation,
            "irreducible": irreducible,
            "reachability": reachability,
        }

    def choose(
        self,
        candidates: np.ndarray,
        rng: np.random.Generator,
        *,
        controllability: np.ndarray | None = None,
        risk: np.ndarray | None = None,
    ) -> int:
        candidates = self._validate_descriptors(candidates)
        if rng.random() < self.epsilon:
            return int(rng.integers(0, len(candidates)))
        scores = self.score_components(candidates, controllability=controllability, risk=risk)["score"]
        best = np.flatnonzero(np.isclose(scores, np.max(scores)))
        return int(rng.choice(best))

    def diagnostics(self) -> dict[str, float | int]:
        return {
            "observations": self.observation_count,
            "mastery": self.mastery(),
            "frontier": self.initial_frontier + self.mastery() * (self.max_frontier - self.initial_frontier),
        }

    def _validate_descriptors(self, descriptors: np.ndarray, *, single: bool = False) -> np.ndarray:
        value = np.asarray(descriptors, dtype=np.float64)
        if single:
            if value.shape != (self.descriptor_dim,):
                raise ValueError(f"descriptor must have shape ({self.descriptor_dim},)")
            value = value[None, :]
        elif value.ndim == 1:
            value = value[None, :]
        if value.ndim != 2 or value.shape[1] != self.descriptor_dim or len(value) == 0:
            raise ValueError(f"descriptors must have shape (N, {self.descriptor_dim})")
        if not np.all(np.isfinite(value)):
            raise ValueError("descriptors must be finite")
        return value

    @staticmethod
    def _candidate_vector(value: np.ndarray | None, count: int, *, default: float, name: str) -> np.ndarray:
        if value is None:
            return np.full(count, default, dtype=np.float64)
        vector = np.asarray(value, dtype=np.float64)
        if vector.ndim == 0:
            vector = np.full(count, float(vector), dtype=np.float64)
        if vector.shape != (count,) or not np.all(np.isfinite(vector)):
            raise ValueError(f"{name} must be finite with shape ({count},)")
        return vector

    @staticmethod
    def _weighted_mean(kernel: np.ndarray, values: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        weights = kernel * mask[None, :]
        total = weights.sum(axis=1)
        fallback = float(np.mean(values))
        mean = np.divide(weights @ values, total, out=np.full(len(kernel), fallback), where=total > 1e-10)
        return mean, total


class InterventionalCuriosity:
    """Continuous scheduler driven by measured before/after learning gains.

    Unlike :class:`DevelopmentalCuriosity`, this scheduler never infers
    reducibility from a stable high error.  It observes the causal reduction of
    a fixed anchor error after a bounded learning intervention.  Persistent
    high error is penalized only after repeated interventions produce no gain.
    """

    def __init__(
        self,
        descriptor_dim: int,
        home_descriptor: np.ndarray,
        *,
        bandwidth: float = 0.08,
        min_evidence: float = 5.0,
        frontier: float = 0.09,
        epsilon: float = 0.05,
        max_observations: int = 512,
    ):
        home = np.asarray(home_descriptor, dtype=np.float64)
        if descriptor_dim <= 0 or home.shape != (descriptor_dim,):
            raise ValueError("invalid descriptor_dim/home_descriptor")
        if bandwidth <= 0 or min_evidence <= 0 or frontier <= 0 or max_observations < 2:
            raise ValueError("bandwidth/min_evidence/frontier must be positive")
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")
        self.descriptor_dim = descriptor_dim
        self.home_descriptor = home
        self.bandwidth = float(bandwidth)
        self.min_evidence = float(min_evidence)
        self.frontier = float(frontier)
        self.epsilon = float(epsilon)
        self.max_observations = int(max_observations)
        self._descriptors: list[np.ndarray] = []
        self._before: list[float] = []
        self._after: list[float] = []
        self._gains: list[float] = []
        self._initial_error_scale: float | None = None

    @property
    def observation_count(self) -> int:
        return len(self._gains)

    def observe(self, descriptor: np.ndarray, error_before: float, error_after: float) -> None:
        descriptor = self._validate(descriptor, single=True)[0]
        if min(error_before, error_after) < 0 or not np.isfinite(error_before + error_after):
            raise ValueError("anchor errors must be finite and non-negative")
        gain = max(float(error_before - error_after), 0.0)
        self._descriptors.append(descriptor)
        self._before.append(float(error_before))
        self._after.append(float(error_after))
        self._gains.append(gain)
        if self._initial_error_scale is None and len(self._before) >= 4:
            self._initial_error_scale = max(float(np.median(self._before)), 1e-8)
        if len(self._gains) > self.max_observations:
            self._descriptors.pop(0)
            self._before.pop(0)
            self._after.pop(0)
            self._gains.pop(0)

    def score_components(self, candidates: np.ndarray) -> dict[str, np.ndarray]:
        candidates = self._validate(candidates)
        count = len(candidates)
        zeros = np.zeros(count, dtype=np.float64)
        if not self._gains:
            distance = np.linalg.norm(candidates - self.home_descriptor[None, :], axis=1)
            reachability = np.exp(-0.5 * np.square(distance / self.frontier))
            return {
                "score": 0.25 * reachability,
                "confirmed_gain": zeros,
                "familiarity": zeros,
                "habituation": zeros,
                "unproductive": zeros,
                "reachability": reachability,
            }

        descriptors = np.stack(self._descriptors)
        gains = np.asarray(self._gains, dtype=np.float64)
        after = np.asarray(self._after, dtype=np.float64)
        distance_sq = np.sum(np.square(candidates[:, None, :] - descriptors[None, :, :]), axis=2)
        kernel = np.exp(-0.5 * distance_sq / (self.bandwidth * self.bandwidth))
        evidence = kernel.sum(axis=1)
        familiarity = 1.0 - np.exp(-evidence / self.min_evidence)

        age = np.arange(len(gains) - 1, -1, -1, dtype=np.float64)
        recency = np.exp(-age / 64.0)
        weights = kernel * recency[None, :]
        total = weights.sum(axis=1)
        fallback_gain = float(np.mean(gains))
        mean_gain = np.divide(weights @ gains, total, out=np.full(count, fallback_gain), where=total > 1e-10)
        second_gain = np.divide(
            weights @ np.square(gains),
            total,
            out=np.full(count, float(np.mean(np.square(gains)))),
            where=total > 1e-10,
        )
        gain_std = np.sqrt(np.maximum(second_gain - np.square(mean_gain), 0.0))
        stderr = gain_std / np.sqrt(np.maximum(total, 1.0))
        gain_scale = max(float(np.percentile(gains, 75)), 1e-8)
        confirmed_gain = np.maximum(mean_gain - 0.5 * stderr, 0.0) / gain_scale
        confirmed_gain = np.clip(confirmed_gain, 0.0, 3.0)

        mean_after = np.divide(
            weights @ after,
            total,
            out=np.full(count, float(np.mean(after))),
            where=total > 1e-10,
        )
        error_scale = max(self._initial_error_scale or float(np.median(after)), 1e-8)
        low_error = np.exp(-mean_after / error_scale)
        low_gain = np.exp(-np.clip(mean_gain / gain_scale, 0.0, 10.0))
        habituation = familiarity * low_error * low_gain
        high_error = 1.0 - low_error
        evidence_gate = evidence / (evidence + self.min_evidence)
        unproductive = familiarity * high_error * low_gain * evidence_gate

        known = np.vstack([self.home_descriptor[None, :], descriptors])
        nearest = np.sqrt(np.min(np.sum(np.square(candidates[:, None, :] - known[None, :, :]), axis=2), axis=1))
        reachability = np.exp(-0.5 * np.square(nearest / self.frontier))
        novelty = 1.0 - familiarity
        uncertainty = np.clip(stderr / gain_scale, 0.0, 2.0)
        score = reachability * (1.5 * confirmed_gain + 0.25 * novelty + 0.10 * uncertainty)
        score -= 0.45 * habituation + 0.80 * unproductive
        return {
            "score": score,
            "confirmed_gain": confirmed_gain,
            "familiarity": familiarity,
            "habituation": habituation,
            "unproductive": unproductive,
            "reachability": reachability,
        }

    def choose(self, candidates: np.ndarray, rng: np.random.Generator) -> int:
        candidates = self._validate(candidates)
        if rng.random() < self.epsilon:
            return int(rng.integers(0, len(candidates)))
        scores = self.score_components(candidates)["score"]
        best = np.flatnonzero(np.isclose(scores, np.max(scores)))
        return int(rng.choice(best))

    def diagnostics(self) -> dict[str, float | int]:
        return {
            "observations": self.observation_count,
            "mean_gain": float(np.mean(self._gains)) if self._gains else 0.0,
            "positive_gain_fraction": float(np.mean(np.asarray(self._gains) > 1e-8)) if self._gains else 0.0,
        }

    def _validate(self, descriptors: np.ndarray, *, single: bool = False) -> np.ndarray:
        value = np.asarray(descriptors, dtype=np.float64)
        if single:
            if value.shape != (self.descriptor_dim,):
                raise ValueError(f"descriptor must have shape ({self.descriptor_dim},)")
            value = value[None, :]
        elif value.ndim == 1:
            value = value[None, :]
        if value.ndim != 2 or value.shape[1] != self.descriptor_dim or len(value) == 0:
            raise ValueError(f"descriptors must have shape (N, {self.descriptor_dim})")
        if not np.all(np.isfinite(value)):
            raise ValueError("descriptors must be finite")
        return value


class FractionalInterventionalCuriosity(InterventionalCuriosity):
    """DC-003 scheduler with absolute fractional gain and coverage pressure."""

    def score_components(self, candidates: np.ndarray) -> dict[str, np.ndarray]:
        candidates = self._validate(candidates)
        count = len(candidates)
        zeros = np.zeros(count, dtype=np.float64)
        if not self._gains:
            distance = np.linalg.norm(candidates - self.home_descriptor[None, :], axis=1)
            reachability = np.exp(-0.5 * np.square(distance / self.frontier))
            return {
                "score": 0.08 * reachability,
                "fractional_gain": zeros,
                "familiarity": zeros,
                "habituation": zeros,
                "unproductive": zeros,
                "reachability": reachability,
            }

        descriptors = np.stack(self._descriptors)
        before = np.asarray(self._before, dtype=np.float64)
        after = np.asarray(self._after, dtype=np.float64)
        fractional = np.maximum(before - after, 0.0) / np.maximum(before, 1e-8)
        distance_sq = np.sum(np.square(candidates[:, None, :] - descriptors[None, :, :]), axis=2)
        kernel = np.exp(-0.5 * distance_sq / (self.bandwidth * self.bandwidth))
        evidence = kernel.sum(axis=1)
        familiarity = 1.0 - np.exp(-evidence / self.min_evidence)
        age = np.arange(len(fractional) - 1, -1, -1, dtype=np.float64)
        weights = kernel * np.exp(-age / 64.0)[None, :]
        total = weights.sum(axis=1)
        mean_gain = np.divide(
            weights @ fractional,
            total,
            out=np.full(count, float(np.mean(fractional))),
            where=total > 1e-10,
        )
        second = np.divide(
            weights @ np.square(fractional),
            total,
            out=np.full(count, float(np.mean(np.square(fractional)))),
            where=total > 1e-10,
        )
        stderr = np.sqrt(np.maximum(second - np.square(mean_gain), 0.0)) / np.sqrt(np.maximum(total, 1.0))
        confirmed = np.maximum(mean_gain - 0.5 * stderr, 0.0)
        productive = confirmed / np.sqrt(1.0 + evidence / 8.0)

        mean_after = np.divide(
            weights @ after,
            total,
            out=np.full(count, float(np.mean(after))),
            where=total > 1e-10,
        )
        error_scale = max(self._initial_error_scale or float(np.median(after)), 1e-8)
        low_error = np.exp(-mean_after / error_scale)
        low_gain = np.exp(-mean_gain / 0.02)
        evidence_gate = evidence / (evidence + self.min_evidence)
        habituation = familiarity * low_error * low_gain
        unproductive = familiarity * (1.0 - low_error) * low_gain * evidence_gate

        known = np.vstack([self.home_descriptor[None, :], descriptors])
        nearest = np.sqrt(np.min(np.sum(np.square(candidates[:, None, :] - known[None, :, :]), axis=2), axis=1))
        reachability = np.exp(-0.5 * np.square(nearest / self.frontier))
        novelty = 1.0 - familiarity
        score = reachability * (2.0 * productive + 0.08 * novelty + 0.05 * np.clip(stderr, 0.0, 0.2))
        score -= 0.30 * habituation + 0.50 * unproductive
        return {
            "score": score,
            "fractional_gain": confirmed,
            "familiarity": familiarity,
            "habituation": habituation,
            "unproductive": unproductive,
            "reachability": reachability,
        }
