"""B1 – Efference copy / corollary discharge for the J0 neck-servo axis.

Reference: §13.B1 of DEVELOPMENTAL_ARCHITECTURE_REVIEW.md

The model learns:
    Δgyro_z ≈ gain × Δservo_cmd + bias          (OLS, calibration window)

Residual = |Δgyro_z_observed − Δgyro_z_predicted| is large when an external
perturbation caused the motion, small when the servo itself caused it.

J2.5 graduation criterion: AUROC ≥ 0.80 on held-out J0 sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class EfferenceCopy:
    """One-axis OLS efference copy model (servo command → gyro_z)."""

    gain: float = 0.0
    bias: float = 0.0
    _fitted: bool = field(default=False, repr=False)

    def fit(self, commands: np.ndarray, gyro_deltas: np.ndarray) -> None:
        commands = np.asarray(commands, dtype=float).ravel()
        gyro_deltas = np.asarray(gyro_deltas, dtype=float).ravel()
        if len(commands) != len(gyro_deltas):
            raise ValueError("commands and gyro_deltas must have the same length")
        if len(commands) < 2:
            raise ValueError("need at least 2 samples to fit")
        A = np.column_stack([commands, np.ones_like(commands)])
        result = np.linalg.lstsq(A, gyro_deltas, rcond=None)
        self.gain, self.bias = float(result[0][0]), float(result[0][1])
        self._fitted = True

    def predict(self, command_delta_deg: float) -> float:
        return self.gain * command_delta_deg + self.bias

    def residual(self, predicted: float, observed: float) -> float:
        return abs(observed - predicted)

    def residuals(self, commands: np.ndarray, gyro_deltas: np.ndarray) -> np.ndarray:
        commands = np.asarray(commands, dtype=float).ravel()
        gyro_deltas = np.asarray(gyro_deltas, dtype=float).ravel()
        predicted = self.gain * commands + self.bias
        return np.abs(gyro_deltas - predicted).astype(np.float32)


@dataclass
class EfferenceCopyReport:
    n_samples: int
    auroc: float
    gain: float
    bias: float
    mean_residual: float
    std_residual: float
    threshold_auroc: float = 0.80

    @property
    def passed(self) -> bool:
        return self.auroc >= self.threshold_auroc


def evaluate_efference_copy(
    commands: np.ndarray,
    gyro_deltas: np.ndarray,
    external_labels: np.ndarray,
    *,
    train_fraction: float = 0.5,
) -> EfferenceCopyReport:
    """Fit on the first half, compute AUROC on the second half.

    Parameters
    ----------
    commands        1-D array of servo command deltas (degrees)
    gyro_deltas     1-D array of observed Δgyro_z (rad/s)
    external_labels 1-D bool array: True where motion was externally caused
    train_fraction  fraction of data used for OLS fitting
    """
    n = len(commands)
    if n < 4:
        raise ValueError("need at least 4 samples")
    split = max(2, int(n * train_fraction))

    ec = EfferenceCopy()
    ec.fit(commands[:split], gyro_deltas[:split])

    res = ec.residuals(commands[split:], gyro_deltas[split:])
    labels = np.asarray(external_labels[split:], dtype=bool)

    return EfferenceCopyReport(
        n_samples=len(res),
        auroc=_auroc(res, labels),
        gain=ec.gain,
        bias=ec.bias,
        mean_residual=float(np.mean(res)),
        std_residual=float(np.std(res)),
    )


def _auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    pos = scores[labels]
    neg = scores[~labels]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    u = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return u / (len(pos) * len(neg))
