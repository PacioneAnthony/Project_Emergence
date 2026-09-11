"""The C1 margin probe implements entry 1 of the journal, and nothing else."""

from __future__ import annotations

import numpy as np
import pytest

from learning import c1_probe
from learning.c1_probe import (
    ORACLE,
    WITNESSES,
    closest,
    descriptor,
    distance,
    play_episode,
    probe_seeds,
    verdict,
)
from learning.c1_task import C1Config

SEED = 21  # an ordinary test seed, not a reserved one


# ------------------------------------------------------------ journal, entry 1


def test_seeds_follow_the_journal_recipe():
    """The seeds printed when the threshold was written are reproduced exactly."""

    assert probe_seeds("dev", 10)[0] == 3647248449
    assert probe_seeds("bank", 60)[:5] == [3689464201, 1033883426, 4064828593, 1777496830, 347949206]
    assert len(set(probe_seeds("dev", 10)) | set(probe_seeds("bank", 60))) == 70


def test_constants_are_the_journals():
    assert c1_probe.FEASIBILITY_MIN == 0.90
    assert c1_probe.FEASIBILITY_WILSON_LOW_MIN == 0.80
    assert c1_probe.REJECTED_ROOMS_MAX == 0.10
    assert c1_probe.SUCCESS_MARGIN_MIN == 0.10
    assert c1_probe.COST_MARGIN_MIN == 3.0
    assert (c1_probe.BOOTSTRAP_RESAMPLES, c1_probe.BOOTSTRAP_SEED) == (10_000, 0)
    assert (c1_probe.SATURATION_MIN, c1_probe.VALUE_MIN) == (0.45, 0.25)
    assert (c1_probe.HUE_BINS, c1_probe.MIN_OBJECT_PIXELS, c1_probe.EMPTY_DISTANCE) == (24, 20, 2.0)


# ------------------------------------------------------------------ matcher


def _image(rgb, size=16):
    return np.tile(np.array(rgb, dtype=np.uint8), (size, size, 1))


def test_descriptor_sees_a_saturated_colour_and_ignores_grey():
    red = descriptor(_image((230, 25, 25)))
    assert red is not None and red.argmax() == 0 and red.sum() == pytest.approx(1.0)
    assert descriptor(_image((140, 140, 145))) is None


def test_descriptor_keeps_only_the_masked_pixels():
    image = _image((230, 25, 25))
    mask = np.zeros(image.shape[:2], dtype=bool)
    assert descriptor(image, mask) is None
    mask[:5, :5] = True  # 25 pixels, above the minimum of 20
    assert descriptor(image, mask) is not None


def test_distance_bounds_and_first_on_ties():
    red, blue = descriptor(_image((230, 25, 25))), descriptor(_image((25, 25, 230)))
    assert distance(red, red) == 0.0
    assert distance(red, blue) == pytest.approx(2.0)
    assert distance(None, red) == 2.0
    assert closest([((30.0, 0.0), red), ((60.0, 0.0), red)], red) == ((30.0, 0.0), 0.0)


# ------------------------------------------------------------------ verdict


def _row(oracle, last, scan, costs=(1, 1, 16)):
    return {
        "seed": 0, "moved": False, "target": [0.0, 0.0], "reference_empty": False,
        "cell_oracle_success": True,
        "outcomes": {
            ORACLE: {"success": oracle, "cost": costs[0]},
            "dernier_angle": {"success": last, "cost": costs[1]},
            "balayage": {"success": scan, "cost": costs[2]},
        },
    }


def test_exploitable_when_memory_is_cheap_but_wrong_and_scanning_is_right_but_dear():
    out = verdict([_row(True, i % 2 == 0, True) for i in range(60)], rejected=0)
    assert out["feasibility"]["passes"]
    last, scan = out["witnesses"]["dernier_angle"], out["witnesses"]["balayage"]
    assert last["success_margin"] and not last["cost_margin"]
    assert scan["cost_margin"] and not scan["success_margin"]
    assert out["verdict"] == "MARGE EXPLOITABLE"


def test_rejected_when_the_oracle_cannot_read_the_task():
    out = verdict([_row(i % 5 != 0, False, False) for i in range(60)], rejected=0)  # 80 %
    assert not out["feasibility"]["passes"]
    assert out["verdict"] == "REJETÉE — FAISABILITÉ"


def test_rejected_when_a_witness_is_already_close():
    out = verdict([_row(True, True, True, costs=(1, 1, 2)) for _ in range(60)], rejected=0)
    assert out["witnesses"]["balayage"]["close_to_oracle"]
    assert out["verdict"] == "REJETÉE — MARGE"


def test_rejected_when_too_many_rooms_were_refused():
    rows = [_row(True, False, True) for _ in range(50)]
    assert not verdict(rows, rejected=10)["feasibility"]["passes"]  # 10 / 60 = 16.7 %


def test_an_unestablished_margin_counts_as_absent():
    """One miss in five is a 20-point gap that five episodes cannot establish."""

    out = verdict([_row(True, i != 0, True, costs=(1, 1, 1)) for i in range(5)], rejected=0)
    last = out["witnesses"]["dernier_angle"]
    assert last["success_gap"] == pytest.approx(0.2)
    assert not last["success_margin"]
    assert last["close_to_oracle"]


# ------------------------------------------------------------------ episode


@pytest.fixture(scope="module")
def played():
    return play_episode(C1Config(object_count=8, shuffle_probability=1.0), SEED)


def test_all_three_policies_play_the_same_episode(played):
    assert set(played["outcomes"]) == {ORACLE, *WITNESSES}
    assert played["outcomes"][ORACLE]["cost"] == 1
    assert played["outcomes"]["dernier_angle"]["cost"] == 1
    assert played["outcomes"]["balayage"]["cost"] in (15, 16)
    assert played["cell_oracle_success"] is True
    assert played["moved"] is True
    assert played["reference_empty"] is False


def test_an_episode_replays_identically(played):
    assert play_episode(C1Config(object_count=8, shuffle_probability=1.0), SEED) == played
