"""B2 – Active inference / controllability estimator for J0.

Reference: §13.B2 of DEVELOPMENTAL_ARCHITECTURE_REVIEW.md

ControllabilityEstimator  permutation test: how much do actions explain
                          the observed gyro change relative to chance?

SkillScheduler            3-term interest function:
                          interest = controllability × prediction_progress
                                   - habituation - risk
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from learning.efference_copy import EfferenceCopy


class ControllabilityEstimator:
    """Permutation-based controllability score ∈ [0, 1].

    High score: the EfferenceCopy model explains the observed motion much
    better than permuted (random) actions → agent controls its sensor.

    Parameters
    ----------
    n_permutations  Number of action permutations used to build the baseline.
    rng             Optional seeded generator for reproducibility.
    """

    def __init__(
        self,
        *,
        n_permutations: int = 50,
        rng: np.random.Generator | None = None,
    ):
        self._n_permutations = n_permutations
        self._rng = rng if rng is not None else np.random.default_rng()

    def estimate(
        self,
        commands: np.ndarray,
        gyro_deltas: np.ndarray,
        efference_copy: EfferenceCopy,
    ) -> float:
        """Return P(permuted mean residual > actual mean residual)."""
        commands = np.asarray(commands, dtype=float).ravel()
        gyro_deltas = np.asarray(gyro_deltas, dtype=float).ravel()
        if len(commands) < 2:
            return 0.0

        actual_mean = float(np.mean(efference_copy.residuals(commands, gyro_deltas)))

        count_better = sum(
            1
            for _ in range(self._n_permutations)
            if float(np.mean(efference_copy.residuals(self._rng.permutation(commands), gyro_deltas))) > actual_mean
        )
        return count_better / self._n_permutations


@dataclass
class SkillSchedulerConfig:
    habituation_decay: float = 0.95
    habituation_increment: float = 0.2
    risk_threshold: float = 0.05   # metres; below this distance → collision risk
    risk_penalty: float = 1.0


class SkillScheduler:
    """3-term curiosity-driven interest function.

    interest = controllability × prediction_progress - habituation - risk

    ``state_key`` is any hashable identifying the current discretised state
    (e.g. ``(distance_bucket, angle_bucket)``).  Habituation decays
    geometrically toward zero and increments each time the state is visited.
    """

    def __init__(self, config: SkillSchedulerConfig | None = None):
        self._config = config or SkillSchedulerConfig()
        self._habituation: dict[Any, float] = defaultdict(float)

    def interest(
        self,
        *,
        controllability: float,
        prediction_progress: float,
        state_key: Any,
        distance_m: float,
    ) -> float:
        cfg = self._config
        risk = cfg.risk_penalty if distance_m < cfg.risk_threshold else 0.0
        return controllability * prediction_progress - self._habituation[state_key] - risk

    def update_habituation(self, state_key: Any) -> None:
        cfg = self._config
        self._habituation[state_key] = (
            self._habituation[state_key] * cfg.habituation_decay + cfg.habituation_increment
        )

    def decay_all(self) -> None:
        """Apply geometric decay to every tracked state (call once per step)."""
        cfg = self._config
        for key in list(self._habituation):
            self._habituation[key] *= cfg.habituation_decay
