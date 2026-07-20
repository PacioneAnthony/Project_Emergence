"""DC-005: aggregate-then-clip variant of the fractional scheduler.

Single mechanism change against the DC-003 freeze, motivated by
docs/research/dc005_design_review.md: per-observation gains stay signed, the
regional kernel average is computed first, the fractional ratio uses the
aggregated before-error as denominator, and the clip is applied last. All
other components (coverage pressure, familiarity, habituation, persistent
unproductivity, frontier, coefficients, epsilon) are copied verbatim from
FractionalInterventionalCuriosity. developmental_curiosity.py is untouched.
"""

from __future__ import annotations

import numpy as np

from learning.developmental_curiosity import FractionalInterventionalCuriosity


class PooledFractionalCuriosity(FractionalInterventionalCuriosity):
    """Fractional scheduler scoring pooled signed gains, clipped after averaging."""

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
        raw = before - after  # signed: evaluation noise cancels in the mean
        distance_sq = np.sum(np.square(candidates[:, None, :] - descriptors[None, :, :]), axis=2)
        kernel = np.exp(-0.5 * distance_sq / (self.bandwidth * self.bandwidth))
        evidence = kernel.sum(axis=1)
        familiarity = 1.0 - np.exp(-evidence / self.min_evidence)
        age = np.arange(len(raw) - 1, -1, -1, dtype=np.float64)
        weights = kernel * np.exp(-age / 64.0)[None, :]
        total = weights.sum(axis=1)
        mean_raw = np.divide(
            weights @ raw,
            total,
            out=np.full(count, float(np.mean(raw))),
            where=total > 1e-10,
        )
        second_raw = np.divide(
            weights @ np.square(raw),
            total,
            out=np.full(count, float(np.mean(np.square(raw)))),
            where=total > 1e-10,
        )
        raw_std = np.sqrt(np.maximum(second_raw - np.square(mean_raw), 0.0))
        mean_before = np.divide(
            weights @ before,
            total,
            out=np.full(count, float(np.mean(before))),
            where=total > 1e-10,
        )
        denominator = np.maximum(mean_before, 1e-8)
        ratio = mean_raw / denominator
        stderr = raw_std / np.sqrt(np.maximum(total, 1.0)) / denominator
        confirmed = np.maximum(ratio - 0.5 * stderr, 0.0)
        productive = confirmed / np.sqrt(1.0 + evidence / 8.0)

        mean_after = np.divide(
            weights @ after,
            total,
            out=np.full(count, float(np.mean(after))),
            where=total > 1e-10,
        )
        error_scale = max(self._initial_error_scale or float(np.median(after)), 1e-8)
        low_error = np.exp(-mean_after / error_scale)
        low_gain = np.exp(-np.maximum(ratio, 0.0) / 0.02)
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
