"""The C1 margin probe: two witnesses against a perceptual oracle (D-060, step 3).

Every definition and threshold used here was fixed in docs/research/c1_journal.md,
entry 1, and committed in 6cc7252 before this module existed. The constants below
transcribe that entry, `verdict` applies it, and nothing else decides. Changing a
constant after seeing a number would turn the gate into the soft gate D-060
exists to remove.

After exploration, delay and designation, three policies play the *same* episode,
so every comparison is paired:

* the perceptual oracle, the upper bound, knows every placed object's cell and
  exact pixels but must still recognise the designated one -- recognition alone,
  no search and no memory. Its success rate is the feasibility;
* the "last angle seen" witness answers from its exploration memory and never
  checks;
* the "exhaustive scan" witness revisits the fifteen cells and answers the best
  fresh match.

No policy learns and none has a cognitive mechanism. They share one deliberately
simple matcher, and that choice protects itself: a matcher too weak to work makes
the oracle fail as well, and the probe stops instead of accepting a margin
manufactured by weak witnesses.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

import numpy as np
from matplotlib.colors import rgb_to_hsv

from learning import paired_stats
from learning.c1_task import C1Config, C1Episode

NAMESPACE = "c1-margin-probe/v1"

# The matcher -- journal, entry 1.
SATURATION_MIN = 0.45
VALUE_MIN = 0.25
HUE_BINS = 24
MIN_OBJECT_PIXELS = 20
EMPTY_DISTANCE = 2.0

# The thresholds -- journal, entry 1.
FEASIBILITY_MIN = 0.90
FEASIBILITY_WILSON_LOW_MIN = 0.80
REJECTED_ROOMS_MAX = 0.10
SUCCESS_MARGIN_MIN = 0.10
COST_MARGIN_MIN = 3.0
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 0

ORACLE = "oracle_perceptif"
WITNESSES = ("dernier_angle", "balayage")
POLICIES = (ORACLE,) + WITNESSES


def probe_seeds(subspace: str, count: int) -> list[int]:
    """The journal's recipe: first four bytes, big-endian, of SHA-256 of [namespace, subspace, i]."""

    seeds = []
    for i in range(count):
        blob = json.dumps([NAMESPACE, subspace, i], separators=(",", ":"), ensure_ascii=False)
        seeds.append(int.from_bytes(hashlib.sha256(blob.encode()).digest()[:4], "big"))
    return seeds


def wilson(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """95 % Wilson score interval for a success rate.

    Honest at the extremes, where the naive p +/- z*sqrt(p(1-p)/n) collapses to a
    zero-width band: after three successes out of three it says [0.44, 1.00], not
    [1.00, 1.00].
    """

    if trials <= 0:
        return 0.0, 1.0
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


# ------------------------------------------------------------------- matcher


def descriptor(image, mask=None) -> np.ndarray | None:
    """Hue histogram of an image's object-like pixels, or None when too few remain."""

    rgb = np.asarray(image, dtype=np.float64)[..., :3] / 255.0
    hsv = rgb_to_hsv(rgb)
    keep = (hsv[..., 1] >= SATURATION_MIN) & (hsv[..., 2] >= VALUE_MIN)
    if mask is not None:
        keep &= np.asarray(mask, dtype=bool)
    hues = hsv[..., 0][keep]
    if hues.size < MIN_OBJECT_PIXELS:
        return None
    counts, _ = np.histogram(hues, bins=HUE_BINS, range=(0.0, 1.0))
    return counts / counts.sum()


def distance(a, b) -> float:
    """L1 between two descriptors, in [0, 2]; an empty cell sits at the maximum."""

    if a is None or b is None:
        return EMPTY_DISTANCE
    return float(np.abs(a - b).sum())


def closest(candidates, reference) -> tuple[tuple[float, float], float]:
    """The cell whose descriptor is nearest the reference; the first one on ties."""

    best_cell, best_distance = None, math.inf
    for cell, desc in candidates:
        d = distance(reference, desc)
        if d < best_distance:
            best_cell, best_distance = cell, d
    return best_cell, best_distance


# ------------------------------------------------------------------ policies


@dataclass(frozen=True)
class Outcome:
    policy: str
    cell: tuple[float, float]
    success: bool
    cost: int
    distance: float


def play_perceptual_oracle(episode: C1Episode, reference) -> Outcome:
    """Knows where every object is and what it looks like; must still recognise."""

    order = {cell: k for k, cell in enumerate(episode.cells)}
    views = episode.oracle_object_views().values()
    candidates = sorted(((cell, descriptor(frame, mask)) for cell, frame, mask in views),
                        key=lambda item: order[item[0]])
    cell, d = closest(candidates, reference)
    episode.look_at(*cell)
    return Outcome(ORACLE, cell, cell == episode.target_cell, 1, d)


def play_last_angle_seen(episode: C1Episode, memory, reference) -> Outcome:
    """Answers from the exploration images alone and never checks."""

    cell, d = closest(((cell, descriptor(image)) for cell, image in memory), reference)
    episode.look_at(*cell)
    return Outcome("dernier_angle", cell, cell == episode.target_cell, 1, d)


def play_exhaustive_scan(episode: C1Episode, reference) -> Outcome:
    """Revisits every cell after the designation and answers the best fresh match."""

    seen = [(cell, descriptor(episode.look_at(*cell))) for cell in episode.cells]
    cell, d = closest(seen, reference)
    cost = len(seen)
    if cell != episode.cells[-1]:
        episode.look_at(*cell)
        cost += 1
    return Outcome("balayage", cell, cell == episode.target_cell, cost, d)


def play_episode(config: C1Config, seed: int, observer=None) -> dict:
    """One episode, all three policies on it.

    Raises RuntimeError when a construction guard rejects the room, at build time
    or at the shuffle -- in both cases before any policy has acted.
    """

    with C1Episode(config, seed=seed, observer=observer) as episode:
        memory = [(cell, image) for cell, image, _ in episode.exploration()]
        episode.delay()
        reference = descriptor(episode.designate())
        target = episode.target_cell
        outcomes = [
            play_perceptual_oracle(episode, reference),
            play_last_angle_seen(episode, memory, reference),
            play_exhaustive_scan(episode, reference),
        ]
        # Scoring control: the task's own answer() on the target's cell.
        control = episode.answer(*target).success
        return {
            "seed": int(seed),
            "moved": bool(episode.moved_between_visits),
            "target": list(target),
            "reference_empty": reference is None,
            "cell_oracle_success": bool(control),
            "outcomes": {
                o.policy: {"cell": list(o.cell), "success": bool(o.success), "cost": int(o.cost),
                           "distance": float(o.distance)}
                for o in outcomes
            },
        }


# ------------------------------------------------------------------- verdict


def _bca(values) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if np.all(values == values[0]):
        # No spread, nothing to estimate: the bootstrap would divide by zero.
        return float(values[0]), float(values[0])
    low, high = paired_stats.bca_bootstrap_ci(
        values, statistic=np.mean, n_boot=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED
    )
    return float(low), float(high)


def verdict(rows: list[dict], rejected: int) -> dict:
    """Apply entry 1 of the journal to the played episodes, and nothing else."""

    total = len(rows) + int(rejected)
    rejected_fraction = rejected / total if total else 1.0
    n = len(rows)
    if n == 0:
        return {"verdict": "REJETÉE — FAISABILITÉ", "reason": "aucune pièce jouée",
                "feasibility": {"passes": False, "episodes": 0, "rejected_rooms": int(rejected)},
                "witnesses": {}}

    oracle = np.array([r["outcomes"][ORACLE]["success"] for r in rows], dtype=float)
    successes = int(oracle.sum())
    low, high = wilson(successes, n)
    feasible = (successes / n >= FEASIBILITY_MIN and low >= FEASIBILITY_WILSON_LOW_MIN
                and rejected_fraction <= REJECTED_ROOMS_MAX)
    oracle_cost = float(np.mean([r["outcomes"][ORACLE]["cost"] for r in rows]))

    witnesses = {}
    for name in WITNESSES:
        success = np.array([r["outcomes"][name]["success"] for r in rows], dtype=float)
        gap = oracle - success
        gap_low, gap_high = _bca(gap)
        cost_mean = float(np.mean([r["outcomes"][name]["cost"] for r in rows]))
        success_margin = gap_low >= SUCCESS_MARGIN_MIN
        cost_margin = cost_mean - oracle_cost >= COST_MARGIN_MIN
        witnesses[name] = {
            "success_rate": float(success.mean()),
            "success_gap": float(gap.mean()),
            "success_gap_bca_95": [gap_low, gap_high],
            "gap_signs": paired_stats.paired_sign_counts(gap),
            "cost_mean": cost_mean,
            "cost_gap": cost_mean - oracle_cost,
            "success_margin": bool(success_margin),
            "cost_margin": bool(cost_margin),
            "close_to_oracle": not (success_margin or cost_margin),
        }

    if not feasible:
        label, reason = ("REJETÉE — FAISABILITÉ",
                         "l'oracle perceptif ne lit pas la tâche telle que construite : c'est elle qu'on corrige")
    elif any(w["close_to_oracle"] for w in witnesses.values()):
        label, reason = ("REJETÉE — MARGE",
                         "un témoin est déjà proche de l'oracle : substrat épuisé pour C1 (D-060)")
    else:
        label, reason = ("MARGE EXPLOITABLE",
                         "chaque témoin laisse une marge sur un axe : un mécanisme a de la place")

    return {
        "verdict": label,
        "reason": reason,
        "feasibility": {
            "success_rate": successes / n,
            "successes": successes,
            "episodes": n,
            "wilson_95": [low, high],
            "rejected_rooms": int(rejected),
            "rejected_fraction": rejected_fraction,
            "passes": bool(feasible),
        },
        "oracle_cost": oracle_cost,
        "witnesses": witnesses,
        "cell_oracle_control": float(np.mean([r["cell_oracle_success"] for r in rows])),
        "moved_fraction": float(np.mean([r["moved"] for r in rows])),
        "reference_empty": int(sum(r["reference_empty"] for r in rows)),
    }
