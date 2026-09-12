"""The complementary probe demanded by correction B1 (D-060, step 3).

The contradictory review of 2026-09-12 (`docs/research/c1_margin_review.md`)
returned AUTORISER AVEC CORRECTIONS BLOQUANTES on one substantive ground: the
strongest simple witness available was never played. Version 3's witnesses jump
straight from a policy that never verifies to one that verifies everywhere,
leaving the obvious middle vacant -- and that middle is exactly the trade-off the
margin claims. Entry 10 of docs/research/c1_journal.md pre-registers this probe
and was committed in 3fbac61 before this module existed.

The adaptive policy: remember the fifteen exploration views, pick the cell whose
remembered image is nearest the reference, revisit that one cell, and apply a
deterministic verification rule. Accept and answer there, for one move; refute
and visit the fourteen others once each, then point at the best.

Two verification families are pre-registered, both reading through the frozen
matcher on the same central window version 2's witnesses use: an absolute
threshold on a fixed grid, and one parameter-free comparison. Every
non-dominated variant on the development seeds travels in the same bank, because
otherwise a strict rule -- expensive, therefore keeping a cost margin -- could be
kept while the lax rule that would close the gate was quietly dropped.

The cost rule is hardened as the review asks: this policy's cost varies by
episode, so a cost margin now needs a 95 % lower bound of at least three moves,
not a mean. It is applied to the historic witnesses too, which is stricter than
version 3 and simpler to defend than a two-speed rule.

Nothing that decides is rewritten here: the matcher, the perceptual oracle, both
historic witnesses, the interval machinery and every threshold are imported.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

from learning.c1_probe import (  # noqa: F401  (re-exported on purpose)
    COST_MARGIN_MIN,
    EMPTY_DISTANCE,
    FEASIBILITY_MIN,
    FEASIBILITY_WILSON_LOW_MIN,
    HUE_BINS,
    MIN_OBJECT_PIXELS,
    ORACLE,
    REJECTED_ROOMS_MAX,
    SATURATION_MIN,
    SUCCESS_MARGIN_MIN,
    VALUE_MIN,
    Outcome,
    closest,
    descriptor,
    distance,
    play_perceptual_oracle,
    wilson,
)
from learning.c1_probe import _bca as bca_interval  # the same interval, not a copy
from learning.c1_probe_v2 import play_exhaustive_scan, play_last_angle_seen, windowed
from learning.c1_task import C1Config
from learning.c1_task_v3 import C1EpisodeV3

NAMESPACE = "c1-margin-hybrid/v1"

HISTORIC = ("dernier_angle", "balayage")

# The verification family, frozen in entry 10 before any number existed.
THRESHOLD_GRID = (0.25, 0.50, 0.75, 1.00, 1.25, 1.50)
COMPARISON = "adaptatif_comparaison"


@dataclass(frozen=True)
class Verification:
    """One admissible verification rule. `threshold` None means the comparison rule."""

    name: str
    threshold: float | None

    def accepts(self, fresh: float, best_other_remembered: float) -> bool:
        """Does the fresh view of the remembered cell survive verification?"""

        if self.threshold is None:
            # Parameter-free: the fresh view must beat every other remembered one.
            return fresh < best_other_remembered
        return fresh <= self.threshold


ALL_RULES: tuple[Verification, ...] = tuple(
    Verification(f"adaptatif_s{int(round(t * 100)):03d}", t) for t in THRESHOLD_GRID
) + (Verification(COMPARISON, None),)

# Fixed by the second commit, after the ten development rooms selected the
# non-dominated variants and before the freeze. The runner refuses the bank while
# this is None, so a bank cannot be played against an unfrozen family.
#
# On development: s025 and s050 reach 90 % for 13.0 moves, s150 and the
# parameter-free rule 80 % for 7.0, and s075, s100 and s125 are dominated -- each
# is matched on success and beaten on cost by s150. The two cheapest already read
# as close to the oracle on ten rooms, and they travel in the bank all the same.
# Dropping them is exactly the manoeuvre the review's clause exists to forbid:
# keeping only the expensive variants would preserve a cost margin by selection.
BANK_RULES: tuple[str, ...] | None = (
    "adaptatif_s025",
    "adaptatif_s050",
    "adaptatif_s150",
    COMPARISON,
)


def probe_seeds(subspace: str, count: int) -> list[int]:
    """The project's recipe under the hybrid namespace; nothing is reused from C1."""

    seeds = []
    for i in range(count):
        blob = json.dumps([NAMESPACE, subspace, i], separators=(",", ":"), ensure_ascii=False)
        seeds.append(int.from_bytes(hashlib.sha256(blob.encode()).digest()[:4], "big"))
    return seeds


def rules_named(names) -> tuple[Verification, ...]:
    by_name = {rule.name: rule for rule in ALL_RULES}
    return tuple(by_name[name] for name in names)


# ------------------------------------------------------------------- policy


def play_adaptive(episode, memory, reference, rule: Verification) -> Outcome:
    """Remember, verify the single remembered cell, scan only after refutation.

    Admissible: it reads its own exploration images, the reference, and the views
    its own actions produce. It never touches `moved_between_visits`,
    `target_cell`, `oracle_object_views`, an object mask, a bare render or the
    seed. The cell is chosen before any comparison with the truth.
    """

    remembered = [(cell, windowed(image)) for cell, image in memory]
    guess, _ = closest(remembered, reference)

    fresh_image = episode.look_at(*guess)
    cost = 1
    fresh = windowed(fresh_image)
    fresh_distance = distance(reference, fresh)
    others = [distance(reference, desc) for cell, desc in remembered if cell != guess]
    best_other = min(others) if others else EMPTY_DISTANCE

    if rule.accepts(fresh_distance, best_other):
        return Outcome(rule.name, guess, guess == episode.target_cell, cost, fresh_distance)

    # Refuted: visit the fourteen others once each, in scan order.
    seen = {guess: fresh}
    last = guess
    for cell in episode.cells:
        if cell == guess:
            continue
        seen[cell] = windowed(episode.look_at(*cell))
        cost += 1
        last = cell

    # Candidates in scan order, so ties break exactly as the exhaustive scan's do.
    candidates = [(cell, seen[cell]) for cell in episode.cells]
    answer, d = closest(candidates, reference)
    if answer != last:
        episode.look_at(*answer)
        cost += 1
    return Outcome(rule.name, answer, answer == episode.target_cell, cost, d)


def play_episode(config: C1Config, seed: int, rules=ALL_RULES, observer=None) -> dict:
    """One episode: the oracle, both historic witnesses, and every adaptive variant.

    Every policy plays the same room, so all comparisons stay paired. Looking
    does not change the world -- the shuffle, if any, happened during the delay --
    so the order in which the policies run does not affect what they see.
    """

    with C1EpisodeV3(config, seed=seed, observer=observer) as episode:
        memory = [(cell, image) for cell, image, _ in episode.exploration()]
        episode.delay()
        reference = descriptor(episode.designate())
        target = episode.target_cell
        outcomes = [
            play_perceptual_oracle(episode, reference),
            play_last_angle_seen(episode, memory, reference),
            play_exhaustive_scan(episode, reference),
        ]
        outcomes += [play_adaptive(episode, memory, reference, rule) for rule in rules]
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


# ------------------------------------------------------ non-dominated selection


def non_dominated(summary: dict) -> list[str]:
    """Adaptive variants no other variant beats on both success and cost.

    A variant is dominated when another is at least as good on both axes and
    strictly better on one. Entry 10 sends every survivor into the same bank.
    """

    names = [name for name in summary if name.startswith("adaptatif_")]
    keep = []
    for name in names:
        a = summary[name]
        beaten = any(
            summary[other]["success_rate"] >= a["success_rate"]
            and summary[other]["cost_mean"] <= a["cost_mean"]
            and (summary[other]["success_rate"] > a["success_rate"]
                 or summary[other]["cost_mean"] < a["cost_mean"])
            for other in names if other != name
        )
        if not beaten:
            keep.append(name)
    return keep


# ------------------------------------------------------------------- verdict


def verdict(rows: list[dict], rejected: int, witnesses) -> dict:
    """Entry 1's gate, with entry 10's hardened cost rule, and nothing else.

    The success margin is unchanged. The cost margin now needs the 95 % lower
    bound of the paired cost gap to reach three moves, because the adaptive
    policy's cost varies by episode where the exhaustive scan's barely does.
    """

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
    oracle_cost = np.array([r["outcomes"][ORACLE]["cost"] for r in rows], dtype=float)

    reported = {}
    for name in witnesses:
        success = np.array([r["outcomes"][name]["success"] for r in rows], dtype=float)
        cost = np.array([r["outcomes"][name]["cost"] for r in rows], dtype=float)
        gap = oracle - success
        gap_low, gap_high = bca_interval(gap)
        cost_gap = cost - oracle_cost
        cost_low, cost_high = bca_interval(cost_gap)
        success_margin = gap_low >= SUCCESS_MARGIN_MIN
        cost_margin = cost_low >= COST_MARGIN_MIN
        reported[name] = {
            "success_rate": float(success.mean()),
            "success_gap": float(gap.mean()),
            "success_gap_bca_95": [gap_low, gap_high],
            "cost_mean": float(cost.mean()),
            "cost_gap": float(cost_gap.mean()),
            "cost_gap_bca_95": [cost_low, cost_high],
            "success_margin": bool(success_margin),
            "cost_margin": bool(cost_margin),
            "close_to_oracle": not (success_margin or cost_margin),
        }

    if not feasible:
        label, reason = ("REJETÉE — FAISABILITÉ",
                         "la faisabilité de la v3 ne se reproduit pas sur ces pièces neuves")
    elif any(w["close_to_oracle"] for w in reported.values()):
        close = [name for name, w in reported.items() if w["close_to_oracle"]]
        label, reason = ("REJETÉE — MARGE",
                         f"témoin proche de l'oracle : {', '.join(close)} — substrat épuisé pour C1 (D-060)")
    else:
        label, reason = ("MARGE EXPLOITABLE",
                         "aucun témoin simple, adaptatif compris, n'est à la fois aussi juste et aussi économe")

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
        "oracle_cost": float(oracle_cost.mean()),
        "witnesses": reported,
        "cell_oracle_control": float(np.mean([r["cell_oracle_success"] for r in rows])),
        "moved_fraction": float(np.mean([r["moved"] for r in rows])),
        "conditional": _conditional(rows, witnesses),
    }


def _conditional(rows: list[dict], witnesses) -> dict:
    """Rates split by shuffle, which correction B2 requires published alongside."""

    out = {}
    for key, wanted in (("stable", False), ("brassee", True)):
        subset = [r for r in rows if bool(r["moved"]) is wanted]
        if not subset:
            continue
        out[key] = {"episodes": len(subset)}
        for name in (ORACLE, *witnesses):
            out[key][name] = float(np.mean([r["outcomes"][name]["success"] for r in subset]))
    return out
