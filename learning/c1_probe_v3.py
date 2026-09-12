"""The C1 margin probe, version 3 (D-060, step 3).

Thresholds and design: docs/research/c1_journal.md, entry 7, committed in
5be9c8b before this module existed.

Two corrections against version 2, both justified by measurement rather than by
preference, and both aimed at the task rather than at the gate:

* a palette whose hues are three bins apart and whose saturation is uniform,
  which repairs both of version 2's failing objects (`learning.c1_task_v3`);
* a visibility guard that accepts an object only where the reader can read it.

Everything that decides is imported from the frozen version 1 module -- the
matcher, the perceptual oracle, the verdict and every threshold -- and the
windowed witnesses come from version 2 unchanged. Nothing here re-implements a
rule.

What this version actually tests is stated in entry 7 and repeated here because
it is easy to misread: feasibility is now expected to pass *by construction*,
so a high feasibility is not a discovery. The informative quantity is the
margin, and version 2's signal on it was unfavourable.
"""

from __future__ import annotations

import hashlib
import json

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

# The windowed witnesses of version 2, likewise imported rather than rewritten.
from learning.c1_probe_v2 import (  # noqa: F401
    central_window,
    play_exhaustive_scan,
    play_last_angle_seen,
    windowed,
)
from learning.c1_task import C1Config
from learning.c1_task_v3 import C1EpisodeV3

NAMESPACE = "c1-margin-probe/v3"


def probe_seeds(subspace: str, count: int) -> list[int]:
    """The project's recipe under the v3 namespace: nothing is reused from v1 or v2."""

    seeds = []
    for i in range(count):
        blob = json.dumps([NAMESPACE, subspace, i], separators=(",", ":"), ensure_ascii=False)
        seeds.append(int.from_bytes(hashlib.sha256(blob.encode()).digest()[:4], "big"))
    return seeds


def play_episode(config: C1Config, seed: int, observer=None) -> dict:
    """One episode, all three policies on it.

    Raises RuntimeError when a construction guard rejects the room, at build
    time or at the shuffle -- in both cases before any policy has acted.
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
