"""Version 2 changes three things and must be shown to change nothing else.

Entry 4 of the C1 journal claims the matcher, the oracle and the thresholds are
reused rather than rewritten. These tests make that claim checkable: they assert
object identity with the frozen v1 module, so a copy-paste would fail here.
"""

from __future__ import annotations

import numpy as np
import pytest

from learning import c1_probe, c1_probe_v2
from learning.c1_probe_v2 import central_window, probe_seeds, windowed
from learning.c1_task import PALETTE, Appearance, C1Config, C1Episode, reference_image
from learning.c1_task_v2 import C1EpisodeV2, reference_image_v2

SEED = 21  # an ordinary test seed, not a reserved one


# --------------------------------------------------------- nothing was copied


def test_the_matcher_and_the_oracle_are_the_frozen_ones():
    """Identity, not equality: v2 must not hold its own copy of the rule."""

    assert c1_probe_v2.descriptor is c1_probe.descriptor
    assert c1_probe_v2.distance is c1_probe.distance
    assert c1_probe_v2.closest is c1_probe.closest
    assert c1_probe_v2.play_perceptual_oracle is c1_probe.play_perceptual_oracle
    assert c1_probe_v2.verdict is c1_probe.verdict
    assert c1_probe_v2.wilson is c1_probe.wilson


def test_every_threshold_is_the_one_written_for_version_1():
    assert c1_probe_v2.FEASIBILITY_MIN == 0.90
    assert c1_probe_v2.FEASIBILITY_WILSON_LOW_MIN == 0.80
    assert c1_probe_v2.REJECTED_ROOMS_MAX == 0.10
    assert c1_probe_v2.SUCCESS_MARGIN_MIN == 0.10
    assert c1_probe_v2.COST_MARGIN_MIN == 3.0
    assert (c1_probe_v2.SATURATION_MIN, c1_probe_v2.VALUE_MIN) == (0.45, 0.25)
    assert (c1_probe_v2.HUE_BINS, c1_probe_v2.MIN_OBJECT_PIXELS) == (24, 20)
    assert c1_probe_v2.EMPTY_DISTANCE == 2.0


# ------------------------------------------------------------------- seeds


def test_v2_seeds_are_fresh_and_never_reuse_version_1():
    """A consumed bank is closed; entry 4 of the journal reserves 210 new seeds."""

    dev, bank = probe_seeds("dev", 10), probe_seeds("bank", 200)
    assert dev[0] == 3848342225
    assert bank[0] == 2956972568 and bank[-1] == 1504345451
    assert len(set(dev) | set(bank)) == 210
    assert min(dev + bank) > 100_000

    v1 = set(c1_probe.probe_seeds("dev", 10)) | set(c1_probe.probe_seeds("bank", 60))
    assert not (set(dev) | set(bank)) & v1


# ----------------------------------------------------------- central window


def test_the_window_is_the_one_the_visibility_guard_measures_in():
    mask = central_window(np.zeros((96, 96, 3), dtype=np.uint8))
    assert mask.shape == (96, 96)
    assert mask.sum() == 48 * 48
    assert mask[24:72, 24:72].all()
    assert not mask[:24].any() and not mask[72:].any()


def test_the_window_keeps_the_centre_and_drops_the_clutter():
    """A cell's own object is central; the room's colours are not."""

    frame = np.zeros((96, 96, 3), dtype=np.uint8)
    frame[:, :] = (20, 20, 22)  # unsaturated room, ignored by the matcher anyway
    frame[:16, :16] = (230, 25, 25)  # clutter in a corner
    assert windowed(frame) is None  # nothing saturated in the centre

    frame[40:56, 40:56] = (25, 25, 230)  # the cell's own object
    described = windowed(frame)
    assert described is not None
    assert described.argmax() == c1_probe.descriptor(frame[24:72, 24:72]).argmax()


# ------------------------------------------------------- the room-lit reference


def test_the_reference_still_says_nothing_about_where_anything_is():
    """The v1 property that must survive: same appearance, same image, any room."""

    config = C1Config(object_count=8)
    appearance = Appearance(3, *PALETTE[3])
    assert np.array_equal(
        reference_image_v2(appearance, config), reference_image_v2(appearance, config)
    )

    with C1EpisodeV2(config, seed=SEED) as a, C1EpisodeV2(config, seed=SEED + 7) as b:
        assert a.placement[3] != b.placement[3] or a.usable != b.usable
        assert np.array_equal(
            reference_image_v2(appearance, a.config), reference_image_v2(appearance, b.config)
        )


def test_the_reference_is_lit_differently_from_version_1():
    config = C1Config(object_count=8)
    appearance = Appearance(6, *PALETTE[6])  # the orange cube, v1's five failures
    old = reference_image(appearance, config).astype(np.float32)
    new = reference_image_v2(appearance, config).astype(np.float32)
    assert new.shape == old.shape
    assert np.abs(new - old).mean() > 1.0


def test_the_references_still_tell_the_appearances_apart():
    config = C1Config(object_count=8)
    images = [
        reference_image_v2(Appearance(i, *PALETTE[i]), config).astype(np.float32) for i in range(8)
    ]
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            assert np.abs(images[i] - images[j]).mean() > 1.0


# -------------------------------------------------------------- same episode


def test_version_2_builds_the_same_world_and_designates_the_same_object():
    """Only the reference image changes: every draw from the generator is in order.

    If designating consumed the generator differently, a seed would build one room
    in v1 and another in v2, and the two versions would not be comparable at all.
    """

    config = C1Config(object_count=8, shuffle_probability=1.0)
    with C1Episode(config, seed=SEED) as old, C1EpisodeV2(config, seed=SEED) as new:
        assert old.placement == new.placement
        for episode in (old, new):
            list(episode.exploration())
            episode.delay()
            episode.designate()
        assert old.placement == new.placement
        assert old.moved_between_visits == new.moved_between_visits
        assert old.target_cell == new.target_cell


@pytest.mark.parametrize("policy", ["dernier_angle", "balayage"])
def test_each_witness_reports_its_own_name_and_cost(policy):
    played = c1_probe_v2.play_episode(C1Config(object_count=8, shuffle_probability=0.0), SEED)
    assert set(played["outcomes"]) == {c1_probe_v2.ORACLE, *c1_probe_v2.WITNESSES}
    assert played["outcomes"][c1_probe_v2.ORACLE]["cost"] == 1
    assert played["outcomes"]["dernier_angle"]["cost"] == 1
    assert played["outcomes"]["balayage"]["cost"] in (15, 16)
    assert played["cell_oracle_success"] is True
    assert policy in played["outcomes"]
