"""The diagnostic correction C1 demands, before any mechanism code exists.

The second contradictory review (`docs/research/c1_preregistration_review.md`,
commit `184612a`) blocks every line of mechanism code until a gap is measured.
Its objection: if the target is exchangeable among the unvisited cells after a
refutation, every search order has the same expected rank -- 7.5 visits out of
fourteen -- and mutual exclusion buys nothing, because learning that a cell is
occupied requires visiting it, which would have eliminated it anyway. A policy
that stops correctly on discovery already sits at the optimum.

That theorem holds in its model. Whether it holds for C1 v3 is unknown, because
`_draw_placement` draws from `usable`, `_place_and_verify` relocates failing
objects, `C1EpisodeV3._measure` adds an appearance-dependent readability guard,
and refutation is an event selected by visual distances.

So this module measures, on fresh development rooms, whether any gap survives
the simple rules -- and separates two candidates for it:

* at an identical stop rule, two search **orders**: raster against increasing
  remembered distance. A gap there contradicts the exchangeable-search model for
  this distribution;
* at an identical order, two **stop rules**: a global threshold against a fixed
  per-appearance table. A gap there isolates calibration instead.

Protocol, frozen before the first number: `docs/research/c1_prereg_audit_protocol.md`.
Nothing here is a mechanism, nothing learns online, and no bank is opened.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np

# Everything that decides is imported from the frozen probes, never rewritten.
from learning.c1_probe import EMPTY_DISTANCE, closest, descriptor, distance
from learning.c1_probe_hybrid import Verification, windowed
from learning.c1_task import C1Config
from learning.c1_task_v3 import C1EpisodeV3

NAMESPACE = "c1-prereg-audit/v1"
COUNTS = {"tune": 40, "diag": 60}

# The stop grid, frozen in the protocol. None means "never stop".
STOP_RULES: dict[str, float | None] = {
    "sans_arret": None,
    "a025": 0.25,
    "a050": 0.50,
    "a075": 0.75,
    "a100": 1.00,
    "a125": 1.25,
    "a150": 1.50,
}
TABLE = "table"
ORDERS = ("raster", "memoire")

VERIFICATIONS = {
    "comparaison": Verification("comparaison", None),
    "s150": Verification("s150", 1.50),
}

# Correction C4's tolerance, reused by the table's calibration rule.
CALIBRATION_TOLERANCE = 0.02


@dataclass(frozen=True)
class Variant:
    """One declared policy of the factorial plan."""

    verification: str
    order: str
    stop: str

    @property
    def name(self) -> str:
        return f"{self.verification}|{self.order}|{self.stop}"


def declared_variants() -> tuple[Variant, ...]:
    """The twenty variants of the protocol, and only those."""

    plan = [
        Variant("comparaison", order, stop)
        for order in ORDERS
        for stop in (*STOP_RULES, TABLE)
    ]
    plan += [
        Variant("s150", order, stop) for order in ORDERS for stop in ("sans_arret", "a075")
    ]
    return tuple(plan)


def tuning_variants() -> tuple[Variant, ...]:
    """The eighteen measurable on the tuning rooms: everything but the table.

    The table is defined by those rooms, so scoring it there would be optimistic
    by construction. The protocol was corrected on this point before the first
    measurement was taken.
    """

    return tuple(v for v in declared_variants() if v.stop != TABLE)


def table_variants() -> tuple[Variant, ...]:
    """The two the tuning rooms define, measured out of sample at the diagnostic."""

    return tuple(v for v in declared_variants() if v.stop == TABLE)


def probe_seeds(subspace: str, count: int) -> list[int]:
    """The project's recipe; nothing is reused from the spent or reserved spaces."""

    seeds = []
    for i in range(count):
        blob = json.dumps([NAMESPACE, subspace, i], separators=(",", ":"), ensure_ascii=False)
        seeds.append(int.from_bytes(hashlib.sha256(blob.encode()).digest()[:4], "big"))
    return seeds


def apparent_class(reference) -> int:
    """The reference's dominant hue bin -- admissible, it is read from the reference."""

    return -1 if reference is None else int(np.argmax(reference))


# ------------------------------------------------------------------- policy


def play_variant(episode, memory, reference, variant: Variant, table=None) -> dict:
    """One declared variant on one episode, with the diagnostics the judge publishes.

    Admissible throughout: exploration images, the reference, and what its own
    actions return. `target_cell` is read once, after the answer is fixed, and
    only to score -- exactly as the frozen probes do.
    """

    if variant.stop == TABLE and table is None:
        # Checked before anything is played, not inside the fallback branch: a
        # table variant without a table is a programming error whichever way the
        # verification goes, and it must fail the same way every time.
        raise RuntimeError(
            "the per-appearance table is required for a table variant; the tuning "
            "rooms define it, so table variants are only played at the diagnostic"
        )

    verification = VERIFICATIONS[variant.verification]
    remembered = [(cell, windowed(image)) for cell, image in memory]
    remembered_distance = {cell: distance(reference, desc) for cell, desc in remembered}

    guess, _ = closest(remembered, reference)
    fresh = windowed(episode.look_at(*guess))
    cost = 1
    fresh_distance = distance(reference, fresh)
    others = [d for cell, d in remembered_distance.items() if cell != guess]
    accepted = verification.accepts(fresh_distance, min(others) if others else EMPTY_DISTANCE)

    target = episode.target_cell  # judge only, after the choice is determined

    if accepted:
        return {
            "cell": list(guess), "success": guess == target, "cost": cost,
            "accepted": True, "false_acceptance": guess != target,
            "target_rejected": False, "rank": 0, "ideal_cost": 1, "stopped": True,
        }

    # Refuted: walk the fourteen others in the variant's order.
    threshold = (table.get(apparent_class(reference)) if variant.stop == TABLE
                 else STOP_RULES[variant.stop])

    order = [cell for cell in episode.cells if cell != guess]
    if variant.order == "memoire":
        index = {cell: k for k, cell in enumerate(episode.cells)}
        order.sort(key=lambda cell: (remembered_distance[cell], index[cell]))

    seen = {guess: fresh}
    rank = None
    stopped_at = None
    last = guess
    for step, cell in enumerate(order, start=1):
        seen[cell] = windowed(episode.look_at(*cell))
        cost += 1
        last = cell
        if cell == target and rank is None:
            rank = step
        if threshold is not None and distance(reference, seen[cell]) <= threshold:
            stopped_at = cell
            break

    if stopped_at is not None:
        answer = stopped_at  # already there: no extra pointing
    else:
        candidates = [(cell, seen[cell]) for cell in episode.cells if cell in seen]
        answer, _ = closest(candidates, reference)
        if answer != last:
            episode.look_at(*answer)
            cost += 1

    return {
        "cell": list(answer), "success": answer == target, "cost": cost,
        "accepted": False, "false_acceptance": False,
        "target_rejected": guess == target,
        "rank": rank,
        # Privileged: what this order would have cost with perfect recognition.
        # A bound on what ordering can ever return, never an attainable margin.
        "ideal_cost": 1 + rank if rank is not None else cost,
        "stopped": stopped_at is not None,
    }


def play_episode(config: C1Config, seed: int, variants, table=None) -> dict:
    """Every declared variant on the same room, so all comparisons stay paired."""

    with C1EpisodeV3(config, seed=seed) as episode:
        memory = [(cell, image) for cell, image, _ in episode.exploration()]
        episode.delay()
        reference = descriptor(episode.designate())
        return {
            "seed": int(seed),
            "moved": bool(episode.moved_between_visits),
            "apparent_class": apparent_class(reference),
            "target_index": int(episode._target.index),
            "variants": {v.name: play_variant(episode, memory, reference, v, table)
                         for v in variants},
        }


# --------------------------------------------------------------- calibration


def calibrate_table(rows) -> dict[int, float | None]:
    """The protocol's rule, applied to the tuning rooms and to nothing else.

    Per apparent class, at raster order and `comparaison` verification: the
    cheapest stop rule among those whose success is within 0.02 of the class's
    best. Ties go to the strictest threshold, then to `sans_arret` last.
    """

    order = list(STOP_RULES)  # strictest first, `sans_arret` leading
    ranked = sorted(order, key=lambda name: (STOP_RULES[name] is None, STOP_RULES[name] or 0.0))
    table: dict[int, float | None] = {}
    for klass in sorted({row["apparent_class"] for row in rows}):
        subset = [r for r in rows if r["apparent_class"] == klass]
        scores = {}
        for stop in STOP_RULES:
            name = Variant("comparaison", "raster", stop).name
            success = float(np.mean([r["variants"][name]["success"] for r in subset]))
            cost = float(np.mean([r["variants"][name]["cost"] for r in subset]))
            scores[stop] = (success, cost)
        best_success = max(s for s, _ in scores.values())
        eligible = [s for s, (succ, _) in scores.items() if succ >= best_success - CALIBRATION_TOLERANCE]
        chosen = min(eligible, key=lambda s: (scores[s][1], ranked.index(s)))
        table[klass] = STOP_RULES[chosen]
    return table


def summarise(rows, variants) -> dict:
    """Success, cost and the diagnostics, globally and split by shuffle."""

    out = {}
    for variant in variants:
        name = variant.name
        played = [r["variants"][name] for r in rows]
        ranks = [p["rank"] for p in played if p["rank"] is not None]
        block = {
            "success_rate": float(np.mean([p["success"] for p in played])),
            "cost_mean": float(np.mean([p["cost"] for p in played])),
            "fallback_rate": float(np.mean([not p["accepted"] for p in played])),
            "false_acceptance": int(sum(p["false_acceptance"] for p in played)),
            "target_rejected": int(sum(p["target_rejected"] for p in played)),
            "stopped_rate": float(np.mean([p["stopped"] for p in played])),
            "ideal_cost_mean": float(np.mean([p["ideal_cost"] for p in played])),
            "rank_mean": float(np.mean(ranks)) if ranks else None,
        }
        for key, wanted in (("stable", False), ("brassee", True)):
            subset = [r["variants"][name] for r in rows if bool(r["moved"]) is wanted]
            if subset:
                block[key] = {
                    "episodes": len(subset),
                    "success_rate": float(np.mean([p["success"] for p in subset])),
                    "cost_mean": float(np.mean([p["cost"] for p in subset])),
                }
        out[name] = block
    return out


def non_dominated(summary: dict) -> list[str]:
    """Variants no other variant beats on both success and cost."""

    names = list(summary)
    keep = []
    for name in names:
        a = summary[name]
        beaten = any(
            summary[o]["success_rate"] >= a["success_rate"]
            and summary[o]["cost_mean"] <= a["cost_mean"]
            and (summary[o]["success_rate"] > a["success_rate"]
                 or summary[o]["cost_mean"] < a["cost_mean"])
            for o in names if o != name
        )
        if not beaten:
            keep.append(name)
    return keep
