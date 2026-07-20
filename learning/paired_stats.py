"""Paired statistics for pre-registered replication gates (DC-003R).

Implements the frozen analysis of docs/research/dc003r_preregistration.md:
exact sign-flip permutation tests, a shifted variant for non-inferiority,
BCa bootstrap confidence intervals, Holm correction, explicit sign counts,
and descriptive paired effect sizes. Pure numpy + stdlib.
"""

from __future__ import annotations

from statistics import NormalDist

import numpy as np

_NORM = NormalDist()
_MAX_EXACT_N = 20
_CHUNK = 1 << 16


def _sign_flip_means(diffs: np.ndarray) -> np.ndarray:
    """Means of the paired differences under every sign assignment (2^n)."""
    n = diffs.size
    if n == 0:
        raise ValueError("empty differences")
    if n > _MAX_EXACT_N:
        raise ValueError(f"exact enumeration limited to n <= {_MAX_EXACT_N}")
    total = 1 << n
    means = np.empty(total)
    exponents = np.arange(n, dtype=np.uint32)
    for start in range(0, total, _CHUNK):
        masks = np.arange(start, min(start + _CHUNK, total), dtype=np.uint32)
        signs = 1.0 - 2.0 * ((masks[:, None] >> exponents) & 1)
        means[start : start + masks.size] = signs @ diffs / n
    return means


def exact_sign_flip_pvalue(diffs, alternative: str = "greater") -> float:
    """Exact one-sided sign-flip permutation p-value for paired differences.

    H0: the differences are symmetric around zero. The identity assignment is
    included in the null distribution, so the smallest possible p is 2^-n.
    """
    d = np.asarray(diffs, dtype=float)
    means = _sign_flip_means(d)
    observed = d.mean()
    tol = 1e-12 * max(1.0, float(np.abs(d).max(initial=0.0)))
    if alternative == "greater":
        count = int(np.sum(means >= observed - tol))
    elif alternative == "less":
        count = int(np.sum(means <= observed + tol))
    else:
        raise ValueError(f"unknown alternative: {alternative}")
    return count / means.size


def noninferiority_sign_flip_pvalue(diffs, margin: float) -> float:
    """Exact sign-flip test of H0: mean(diffs) >= margin against inferiority.

    The differences are shifted by the margin, then tested one-sided ("less").
    With margin = 0 this reduces to the standard one-sided test.
    """
    d = np.asarray(diffs, dtype=float) - float(margin)
    return exact_sign_flip_pvalue(d, alternative="less")


def bca_bootstrap_ci(values, statistic=np.mean, n_boot: int = 10_000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    """Bias-corrected and accelerated bootstrap CI for statistic(values)."""
    x = np.asarray(values, dtype=float)
    n = x.size
    if n < 2:
        raise ValueError("need at least two values")
    rng = np.random.default_rng(seed)
    theta = float(statistic(x))
    indices = rng.integers(0, n, size=(n_boot, n))
    boot = np.array([float(statistic(x[row])) for row in indices])
    proportion = float(np.clip(np.mean(boot < theta), 1 / (n_boot + 1), n_boot / (n_boot + 1)))
    z0 = _NORM.inv_cdf(proportion)
    jackknife = np.array([float(statistic(np.delete(x, i))) for i in range(n)])
    centered = jackknife.mean() - jackknife
    denominator = 6.0 * float(np.sum(centered**2)) ** 1.5
    acceleration = 0.0 if denominator == 0.0 else float(np.sum(centered**3)) / denominator

    def adjusted_quantile(q: float) -> float:
        z = _NORM.inv_cdf(q)
        return _NORM.cdf(z0 + (z0 + z) / (1.0 - acceleration * (z0 + z)))

    lower = float(np.quantile(boot, adjusted_quantile(alpha / 2)))
    upper = float(np.quantile(boot, adjusted_quantile(1.0 - alpha / 2)))
    return lower, upper


def holm_correction(pvalues) -> np.ndarray:
    """Holm step-down adjusted p-values, in the original order."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p, kind="stable")
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (p.size - rank) * p[index])
        adjusted[index] = min(1.0, running)
    return adjusted


def paired_sign_counts(diffs) -> dict[str, int]:
    """Explicit sign counts of the paired differences."""
    d = np.asarray(diffs, dtype=float)
    return {
        "positive": int(np.sum(d > 0)),
        "negative": int(np.sum(d < 0)),
        "zero": int(np.sum(d == 0)),
    }


def cohen_dz(diffs) -> float:
    """Paired Cohen's dz (descriptive only). NaN when the spread is zero."""
    d = np.asarray(diffs, dtype=float)
    spread = float(d.std(ddof=1))
    return float(d.mean() / spread) if spread > 0 else float("nan")


def rank_biserial(diffs) -> float:
    """Matched-pairs rank-biserial correlation (descriptive only)."""
    d = np.asarray(diffs, dtype=float)
    nonzero = d[d != 0]
    if nonzero.size == 0:
        return 0.0
    magnitudes = np.abs(nonzero)
    order = np.argsort(magnitudes, kind="stable")
    sorted_magnitudes = magnitudes[order]
    ranks_sorted = np.arange(1, nonzero.size + 1, dtype=float)
    start = 0
    while start < nonzero.size:
        stop = start
        while stop + 1 < nonzero.size and sorted_magnitudes[stop + 1] == sorted_magnitudes[start]:
            stop += 1
        ranks_sorted[start : stop + 1] = ranks_sorted[start : stop + 1].mean()
        start = stop + 1
    ranks = np.empty(nonzero.size)
    ranks[order] = ranks_sorted
    positive = float(ranks[nonzero > 0].sum())
    negative = float(ranks[nonzero < 0].sum())
    return (positive - negative) / (positive + negative)
