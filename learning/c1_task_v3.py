"""C1 version 3: a palette the reader can actually tell apart.

Version 2 was rejected on feasibility, 178 rooms out of 200 against a threshold
of 180. Entry 6 traced its twenty-two failures to two objects and entry 7
pre-registered this version before any of this code existed.

The correction entry 4 had pre-registered -- giving the comparison rule a
tolerance -- was refuted by measurement before being adopted: smoothing the
histogram changes nothing and a circular transport distance makes it worse,
because the orange cube sits 1.23 hue bins from the yellow sphere while the
rendering's own shift is a full bin. Tolerance moves a target and its distractor
closer at the same rate.

So the rule is left exactly as frozen, and the palette changes instead. Eight
hues evenly spread around the circle are three bins apart, and all eight carry
the same high saturation, which repairs the second failure for an arithmetic
reason: the reader needs saturation 0.45 *after* rendering, rendering adds white
light and can only lower saturation, and the old magenta cylinder started at
0.588 where every other colour started above 0.75.

`learning/c1_task.py` and `learning/c1_task_v2.py` are both frozen by manifests,
so this module extends them and edits neither.
"""

from __future__ import annotations

import contextlib

import numpy as np

from learning import c1_task
from learning.c1_probe import descriptor  # the frozen matcher, imported not copied
from learning.c1_task import C1Config
from learning.c1_task_v2 import C1EpisodeV2

# Eight hues at k/8 of the circle -- three of the matcher's twenty-four bins
# apart -- at a single saturation of 0.90 and value 0.95. Frozen in entry 7 of
# docs/research/c1_journal.md before this file existed.
PALETTE_V3: tuple[tuple[str, tuple[float, float, float, float]], ...] = (
    ("box", (0.950, 0.095, 0.095, 1.0)),
    ("cylinder", (0.950, 0.736, 0.095, 1.0)),
    ("sphere", (0.522, 0.950, 0.095, 1.0)),
    ("box", (0.095, 0.950, 0.309, 1.0)),
    ("cylinder", (0.095, 0.950, 0.950, 1.0)),
    ("sphere", (0.095, 0.309, 0.950, 1.0)),
    ("box", (0.522, 0.095, 0.950, 1.0)),
    ("cylinder", (0.950, 0.095, 0.736, 1.0)),
)


@contextlib.contextmanager
def using_palette(palette):
    """Swap the frozen module's palette for the length of one call.

    `C1Episode.__init__` reads its appearances from a module-level constant, and
    the file's bytes are frozen by two manifests, so the constant cannot be
    turned into a configuration field and the constructor cannot be subclassed
    around without copying thirty lines of frozen logic. Swapping the name for
    the duration of the parent constructor is the smallest change that leaves
    the frozen file untouched and every draw from the episode's generator in its
    original order. Nothing else in the episode reads the constant: placement,
    shuffling and designation all work from `self.appearances`.
    """

    original = c1_task.PALETTE
    c1_task.PALETTE = palette
    try:
        yield
    finally:
        c1_task.PALETTE = original


class C1EpisodeV3(C1EpisodeV2):
    """Version 2's episode, with the new palette and a guard that reads."""

    def __init__(self, config: C1Config | None = None, seed: int = 0, observer=None):
        with using_palette(PALETTE_V3):
            super().__init__(config, seed=seed, observer=observer)

    def _measure(self, placement):
        """Measure visibility, then require that the object can also be *read*.

        The two tests were never the same. The visibility guard counts pixels
        that changed by more than 25 between the room with the object and the
        room without it; the frozen matcher counts pixels that are saturated,
        0.45 and 0.25. In version 2 an object could pass the first while the
        oracle read an empty cell -- five of that bank's twenty-two failures.

        An unreadable object is reported at zero visibility, which is below any
        admissible threshold, so the parent's own retry moves it to a free cell.
        Nothing else changes, and a room where no placement can be read at all
        still ends as a construction rejection, counted against the threshold
        that allows at most a tenth of them.
        """

        seen, env = super()._measure(placement)
        for index, cell in placement.items():
            frame = self._measured_frames[index]
            mask = np.abs(frame - self._bare[cell]).sum(axis=2) > 25
            if descriptor(frame.astype(np.uint8), mask) is None:
                seen[index] = 0.0
        return seen, env
