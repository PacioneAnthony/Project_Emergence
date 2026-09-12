"""Version 3 changes a palette and a guard, and must change nothing else.

Entry 7 of the C1 journal claims two things that are easy to assert and easy to
get wrong: that the comparison rule is untouched, and that the new palette is
separated by construction rather than by hope. Both are checked here, the first
by object identity with the frozen module and the second by arithmetic on the
colours themselves.
"""

from __future__ import annotations

import colorsys

import numpy as np
import pytest

from learning import c1_probe, c1_probe_v2, c1_probe_v3
from learning.c1_probe import HUE_BINS, SATURATION_MIN, descriptor
from learning.c1_probe_v3 import probe_seeds
from learning.c1_task import PALETTE, Appearance, C1Config
from learning.c1_task_v2 import reference_image_v2
from learning.c1_task_v3 import PALETTE_V3

SEED = 21  # an ordinary test seed, not a reserved one


# --------------------------------------------------------- nothing was copied


def test_the_rule_the_oracle_and_the_verdict_are_the_frozen_ones():
    assert c1_probe_v3.descriptor is c1_probe.descriptor
    assert c1_probe_v3.distance is c1_probe.distance
    assert c1_probe_v3.closest is c1_probe.closest
    assert c1_probe_v3.play_perceptual_oracle is c1_probe.play_perceptual_oracle
    assert c1_probe_v3.verdict is c1_probe.verdict


def test_the_witnesses_are_version_2s():
    assert c1_probe_v3.play_last_angle_seen is c1_probe_v2.play_last_angle_seen
    assert c1_probe_v3.play_exhaustive_scan is c1_probe_v2.play_exhaustive_scan
    assert c1_probe_v3.windowed is c1_probe_v2.windowed


def test_every_threshold_is_still_the_one_written_for_version_1():
    assert c1_probe_v3.FEASIBILITY_MIN == 0.90
    assert c1_probe_v3.FEASIBILITY_WILSON_LOW_MIN == 0.80
    assert c1_probe_v3.REJECTED_ROOMS_MAX == 0.10
    assert c1_probe_v3.SUCCESS_MARGIN_MIN == 0.10
    assert c1_probe_v3.COST_MARGIN_MIN == 3.0
    assert (c1_probe_v3.SATURATION_MIN, c1_probe_v3.VALUE_MIN) == (0.45, 0.25)
    assert (c1_probe_v3.HUE_BINS, c1_probe_v3.MIN_OBJECT_PIXELS) == (24, 20)


# ------------------------------------------------------------------- palette


def _hsv(rgba):
    return colorsys.rgb_to_hsv(*rgba[:3])


def test_the_new_palette_separates_hues_far_beyond_the_rendering_shift():
    """The measured shift is one bin; entry 7 asks for three."""

    bins = sorted(_hsv(rgba)[0] * HUE_BINS for _, rgba in PALETTE_V3)
    gaps = [min((b - a) % HUE_BINS, (a - b) % HUE_BINS)
            for a, b in zip(bins, bins[1:] + bins[:1])]
    assert min(gaps) == pytest.approx(3.0, abs=0.05)


def test_the_old_palette_was_the_problem():
    """The pair that failed 15 times out of 15 is barely more than one bin apart."""

    bins = sorted(_hsv(rgba)[0] * HUE_BINS for _, rgba in PALETTE[:8])
    gaps = [min((b - a) % HUE_BINS, (a - b) % HUE_BINS)
            for a, b in zip(bins, bins[1:] + bins[:1])]
    assert min(gaps) < 1.5


def test_every_new_colour_has_room_above_the_readers_saturation_floor():
    """Rendering adds white light and can only lower saturation.

    The old magenta cylinder started at 0.588, a margin of 0.138, and was the
    one object the reader lost in dim cells.
    """

    saturations = [_hsv(rgba)[1] for _, rgba in PALETTE_V3]
    assert min(saturations) == pytest.approx(0.90, abs=0.01)
    assert min(saturations) - SATURATION_MIN > 0.40
    assert min(_hsv(rgba)[1] for _, rgba in PALETTE[:8]) < 0.60  # the old outlier

    assert len(PALETTE_V3) == 8
    assert {kind for kind, _ in PALETTE_V3} == {"box", "cylinder", "sphere"}


def test_the_new_references_are_readable_and_distinct():
    config = C1Config(object_count=8)
    described = []
    for index, (kind, rgba) in enumerate(PALETTE_V3):
        image = reference_image_v2(Appearance(index, kind, rgba), config)
        desc = descriptor(image)
        assert desc is not None, f"reference {index} is unreadable"
        described.append(desc)
    peaks = [int(np.argmax(d)) for d in described]
    assert len(set(peaks)) == 8


# ------------------------------------------------------------------- seeds


def test_v3_seeds_are_fresh_against_both_spent_banks():
    dev, bank = probe_seeds("dev", 10), probe_seeds("bank", 300)
    assert dev[0] == 3541371033
    assert bank[0] == 2205167222
    assert len(set(dev) | set(bank)) == 310
    assert min(dev + bank) > 100_000

    spent = set(c1_probe.probe_seeds("dev", 10)) | set(c1_probe.probe_seeds("bank", 60))
    spent |= set(c1_probe_v2.probe_seeds("dev", 10)) | set(c1_probe_v2.probe_seeds("bank", 200))
    assert not (set(dev) | set(bank)) & spent


# ------------------------------------------------------------- the new guard


def test_every_placed_object_is_readable_and_not_merely_visible():
    """The contract version 2 lacked: the guard now measures what the reader needs."""

    from learning.c1_task_v3 import C1EpisodeV3

    with C1EpisodeV3(C1Config(object_count=8, shuffle_probability=1.0), seed=SEED) as episode:
        for index, (cell, frame, mask) in episode.oracle_object_views().items():
            assert descriptor(frame, mask) is not None, f"object {index} placed unreadable"
        list(episode.exploration())
        episode.delay()
        for index, (cell, frame, mask) in episode.oracle_object_views().items():
            assert descriptor(frame, mask) is not None, f"object {index} unreadable after a shuffle"


def test_the_episode_uses_the_new_palette_and_restores_the_frozen_one():
    """The palette swap must not leak out of the constructor."""

    from learning import c1_task
    from learning.c1_task_v3 import C1EpisodeV3

    before = c1_task.PALETTE
    with C1EpisodeV3(C1Config(object_count=8), seed=SEED) as episode:
        assert c1_task.PALETTE is before
        assert [a.rgba for a in episode.appearances] == [rgba for _, rgba in PALETTE_V3]
    assert c1_task.PALETTE is before
