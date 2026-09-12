"""The C1 margin probe, version 2 (D-060, step 3).

Version 1 was rejected on feasibility by one room: the perceptual oracle read
54 of 60 rooms where the threshold, written before any witness existed, demanded
a Wilson lower bound of 0.80 and got 0.7985. Entry 4 of docs/research/c1_journal.md
pre-registers this version and was committed before this module existed.

Three corrections, and nothing else:

* the reference is rendered under the room's own lighting (`learning.c1_task_v2`);
* both witnesses read the central window of each frame, the same one the
  visibility guard uses and the one every object is placed in. This strengthens
  them, so it can only shrink the margin claimed against them;
* the bank goes from 60 to 200 rooms, because at exactly 90 % a bank of 60 could
  not clear its own Wilson threshold. Only n changes.

Everything else is imported from `learning.c1_probe`, whose bytes are frozen in
the v1 manifest: the matcher, the thresholds, the perceptual oracle and the
verdict all run exactly as they did. "The rule did not change" is therefore a
property of this file's imports rather than a claim in its docstring.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np

# The frozen v1 probe. Imported, never copied and never shadowed.
from learning.c1_probe import (  # noqa: F401  (re-exported on purpose)
    COST_MARGIN_MIN,
    EMPTY_DISTANCE,
    FEASIBILITY_MIN,
    FEASIBILITY_WILSON_LOW_MIN,
    HUE_BINS,
    MIN_OBJECT_PIXELS,
    ORACLE,
    POLICIES,
    REJECTED_ROOMS_MAX,
    SATURATION_MIN,
    SUCCESS_MARGIN_MIN,
    VALUE_MIN,
    WITNESSES,
    Outcome,
    closest,
    descriptor,
    distance,
    play_perceptual_oracle,
    verdict,
    wilson,
)
from learning.c1_task import C1Config
from learning.c1_task_v2 import C1EpisodeV2

NAMESPACE = "c1-margin-probe/v2"


def probe_seeds(subspace: str, count: int) -> list[int]:
    """The journal's recipe, under the v2 namespace: no seed is reused from v1."""

    seeds = []
    for i in range(count):
        blob = json.dumps([NAMESPACE, subspace, i], separators=(",", ":"), ensure_ascii=False)
        seeds.append(int.from_bytes(hashlib.sha256(blob.encode()).digest()[:4], "big"))
    return seeds


# ------------------------------------------------------- the witnesses' window


def central_window(image) -> np.ndarray:
    """The central half of a frame, as a boolean mask.

    `size // 4` to `size - size // 4` on both axes: the window `usable_cells` and
    the visibility guard already measure in, and the one `place_in_cell` centres
    every object in. Entry 3 of the journal suspected the room's coloured clutter
    of polluting the whole-frame histogram, which would have made the witnesses
    artificially weak -- the REF-001 trap, where a baseline lost for a reason that
    meant nothing.
    """

    height, width = np.asarray(image).shape[:2]
    mask = np.zeros((height, width), dtype=bool)
    mask[height // 4 : height - height // 4, width // 4 : width - width // 4] = True
    return mask


def windowed(image):
    """The frozen descriptor, offered the central window instead of the frame."""

    return descriptor(image, central_window(image))


# ------------------------------------------------------------------ policies


def play_last_angle_seen(episode, memory, reference) -> Outcome:
    """Answers from the exploration images alone and never checks."""

    cell, d = closest(((cell, windowed(image)) for cell, image in memory), reference)
    episode.look_at(*cell)
    return Outcome("dernier_angle", cell, cell == episode.target_cell, 1, d)


def play_exhaustive_scan(episode, reference) -> Outcome:
    """Revisits every cell after the designation and answers the best fresh match."""

    seen = [(cell, windowed(episode.look_at(*cell))) for cell in episode.cells]
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

    The reference is read whole, not windowed: it is rendered on a neutral
    backdrop and the object already fills it, so a window would change nothing
    there. The witnesses' window exists to keep the room out of their histograms.
    """

    with C1EpisodeV2(config, seed=seed, observer=observer) as episode:
        memory = [(cell, image) for cell, image, _ in episode.exploration()]
        episode.delay()
        reference = descriptor(episode.designate())
        target = episode.target_cell
        outcomes = [
            play_perceptual_oracle(episode, reference),
            play_last_angle_seen(episode, memory, reference),
            play_exhaustive_scan(episode, reference),
        ]
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
