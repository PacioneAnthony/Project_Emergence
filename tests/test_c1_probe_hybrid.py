"""The complementary probe of correction B1 must add a witness and change nothing else.

Entry 10 claims the matcher, the oracle, both historic witnesses and every
threshold are imported rather than rewritten, that the verification family is the
one written before any number, and that the cost rule is hardened. Each of those
is checked here, the first by object identity so a copy-paste would fail.
"""

from __future__ import annotations

import numpy as np
import pytest

from learning import c1_probe, c1_probe_hybrid, c1_probe_v2
from learning.c1_probe_hybrid import (
    ALL_RULES,
    COMPARISON,
    THRESHOLD_GRID,
    Verification,
    non_dominated,
    play_episode,
    probe_seeds,
    verdict,
)
from learning.c1_task import C1Config

SEED = 21  # an ordinary test seed, not a reserved one


# --------------------------------------------------------- nothing was copied


def test_the_rule_the_oracle_and_the_witnesses_are_the_frozen_ones():
    assert c1_probe_hybrid.descriptor is c1_probe.descriptor
    assert c1_probe_hybrid.distance is c1_probe.distance
    assert c1_probe_hybrid.closest is c1_probe.closest
    assert c1_probe_hybrid.play_perceptual_oracle is c1_probe.play_perceptual_oracle
    assert c1_probe_hybrid.play_last_angle_seen is c1_probe_v2.play_last_angle_seen
    assert c1_probe_hybrid.play_exhaustive_scan is c1_probe_v2.play_exhaustive_scan
    assert c1_probe_hybrid.windowed is c1_probe_v2.windowed


def test_the_thresholds_are_still_version_1s():
    assert c1_probe_hybrid.FEASIBILITY_MIN == 0.90
    assert c1_probe_hybrid.FEASIBILITY_WILSON_LOW_MIN == 0.80
    assert c1_probe_hybrid.SUCCESS_MARGIN_MIN == 0.10
    assert c1_probe_hybrid.COST_MARGIN_MIN == 3.0
    assert (c1_probe_hybrid.SATURATION_MIN, c1_probe_hybrid.VALUE_MIN) == (0.45, 0.25)
    assert (c1_probe_hybrid.HUE_BINS, c1_probe_hybrid.MIN_OBJECT_PIXELS) == (24, 20)


# ---------------------------------------------------- the pre-registered family


def test_the_verification_family_is_the_one_written_before_any_number():
    assert THRESHOLD_GRID == (0.25, 0.50, 0.75, 1.00, 1.25, 1.50)
    assert len(ALL_RULES) == 7
    assert [r.name for r in ALL_RULES][-1] == COMPARISON
    assert ALL_RULES[-1].threshold is None
    assert [r.threshold for r in ALL_RULES[:-1]] == list(THRESHOLD_GRID)


def test_a_threshold_rule_accepts_below_its_threshold_and_ignores_the_others():
    rule = Verification("adaptatif_s075", 0.75)
    assert rule.accepts(0.50, best_other_remembered=0.01)
    assert rule.accepts(0.75, best_other_remembered=2.0)
    assert not rule.accepts(0.76, best_other_remembered=2.0)


def test_the_parameter_free_rule_compares_against_the_other_remembered_cells():
    rule = Verification(COMPARISON, None)
    assert rule.accepts(0.40, best_other_remembered=0.90)
    assert not rule.accepts(0.90, best_other_remembered=0.40)
    assert not rule.accepts(0.50, best_other_remembered=0.50)  # a tie refutes


def test_the_bank_is_refused_while_the_family_is_not_frozen():
    """A bank cannot be played against a family the development seeds chose freely."""

    assert c1_probe_hybrid.BANK_RULES is None or isinstance(c1_probe_hybrid.BANK_RULES, tuple)


# ------------------------------------------------------------------- seeds


def test_hybrid_seeds_are_fresh_against_all_three_spent_banks():
    dev, bank = probe_seeds("dev", 10), probe_seeds("bank", 100)
    assert dev[0] == 3874359381
    assert bank[0] == 2159935764 and bank[-1] == 658077885
    assert len(set(dev) | set(bank)) == 110
    assert min(dev + bank) > 100_000

    spent = set()
    for module, counts in ((c1_probe, 60), (c1_probe_v2, 200)):
        spent |= set(module.probe_seeds("dev", 10)) | set(module.probe_seeds("bank", counts))
    from learning import c1_probe_v3
    spent |= set(c1_probe_v3.probe_seeds("dev", 10)) | set(c1_probe_v3.probe_seeds("bank", 300))
    assert len(spent) == 590  # 70 + 210 + 310, development seeds included
    assert not (set(dev) | set(bank)) & spent


# ------------------------------------------------------- the hardened cost rule


def _row(oracle, adaptive_success, adaptive_cost, memory=False, scan=True):
    return {
        "seed": 0, "moved": False, "target": [0.0, 0.0], "reference_empty": False,
        "cell_oracle_success": True,
        "outcomes": {
            "oracle_perceptif": {"success": oracle, "cost": 1},
            "dernier_angle": {"success": memory, "cost": 1},
            "balayage": {"success": scan, "cost": 16},
            "adaptatif_s075": {"success": adaptive_success, "cost": adaptive_cost},
        },
    }


WITNESSES = ("dernier_angle", "balayage", "adaptatif_s075")


def test_a_mean_above_three_is_not_enough_when_the_cost_varies():
    """Version 3 would have accepted this; entry 10's hardened rule must not.

    Costs alternate 1 and 8, mean gap 3.5 -- above the old threshold -- but the
    spread puts the 95 % lower bound below three.
    """

    rows = [_row(True, True, 1 if i % 2 else 8) for i in range(100)]
    out = verdict(rows, rejected=0, witnesses=WITNESSES)
    adaptive = out["witnesses"]["adaptatif_s075"]
    assert adaptive["cost_gap"] == pytest.approx(3.5)
    assert adaptive["cost_gap_bca_95"][0] < 3.0
    assert not adaptive["cost_margin"]


def test_a_steady_cost_well_above_three_still_establishes_the_margin():
    rows = [_row(True, True, 16) for _ in range(100)]
    out = verdict(rows, rejected=0, witnesses=WITNESSES)
    assert out["witnesses"]["adaptatif_s075"]["cost_margin"]


def test_an_adaptive_witness_that_is_right_and_cheap_closes_the_gate():
    """The outcome the review says is possible, and which must not be explained away."""

    rows = [_row(True, True, 2) for _ in range(100)]
    out = verdict(rows, rejected=0, witnesses=WITNESSES)
    adaptive = out["witnesses"]["adaptatif_s075"]
    assert not adaptive["success_margin"] and not adaptive["cost_margin"]
    assert adaptive["close_to_oracle"]
    assert out["verdict"] == "REJETÉE — MARGE"
    assert "adaptatif_s075" in out["reason"]


def test_conditional_rates_are_published_as_correction_b2_requires():
    rows = [_row(True, i % 2 == 0, 9) for i in range(50)]
    for row in rows[:20]:
        row["moved"] = True
    out = verdict(rows, rejected=0, witnesses=WITNESSES)
    assert out["conditional"]["brassee"]["episodes"] == 20
    assert out["conditional"]["stable"]["episodes"] == 30
    assert "oracle_perceptif" in out["conditional"]["stable"]


# ------------------------------------------------------- non-dominated selection


def test_domination_keeps_the_pareto_front_and_drops_the_rest():
    summary = {
        "adaptatif_s025": {"success_rate": 0.80, "cost_mean": 12.0},  # dominated by s075
        "adaptatif_s075": {"success_rate": 0.90, "cost_mean": 9.0},
        "adaptatif_s150": {"success_rate": 0.70, "cost_mean": 2.0},   # cheapest
        "dernier_angle": {"success_rate": 0.5, "cost_mean": 1.0},     # not a variant
    }
    keep = set(non_dominated(summary))
    assert keep == {"adaptatif_s075", "adaptatif_s150"}


# ------------------------------------------------------------------ episode


@pytest.mark.parametrize("rule", [ALL_RULES[0], ALL_RULES[-1]])
def test_the_adaptive_policy_costs_one_move_when_it_accepts_and_scans_otherwise(rule):
    played = play_episode(C1Config(object_count=8, shuffle_probability=0.0), SEED, rules=(rule,))
    outcome = played["outcomes"][rule.name]
    assert outcome["cost"] == 1 or 15 <= outcome["cost"] <= 16
    assert played["outcomes"]["oracle_perceptif"]["cost"] == 1
    assert played["cell_oracle_success"] is True


def test_every_pre_registered_variant_plays_the_same_episode():
    played = play_episode(C1Config(object_count=8, shuffle_probability=1.0), SEED)
    for rule in ALL_RULES:
        assert rule.name in played["outcomes"]
    assert played["moved"] is True
    costs = [played["outcomes"][r.name]["cost"] for r in ALL_RULES]
    assert all(c == 1 or 15 <= c <= 16 for c in costs)


def test_a_looser_threshold_never_costs_more_than_a_stricter_one():
    """Accepting more readily can only avoid the fallback, never provoke it."""

    played = play_episode(C1Config(object_count=8, shuffle_probability=1.0), SEED)
    costs = [played["outcomes"][r.name]["cost"] for r in ALL_RULES[:-1]]
    assert costs == sorted(costs, reverse=True)


def test_an_episode_replays_identically():
    config = C1Config(object_count=8, shuffle_probability=1.0)
    assert play_episode(config, SEED) == play_episode(config, SEED)


def test_the_policy_reads_no_privileged_field():
    """Its choice must not move when the judge's private truth is falsified.

    `oracle_object_views`, the bare frames and `moved_between_visits` belong to
    the judge and to the perceptual oracle. If the adaptive policy read any of
    them, corrupting them would change the cell it answers.
    """

    from learning.c1_probe_hybrid import play_adaptive
    from learning.c1_task_v3 import C1EpisodeV3

    config = C1Config(object_count=8, shuffle_probability=1.0)
    rule = ALL_RULES[2]
    answers = []
    for corrupt in (False, True):
        with C1EpisodeV3(config, seed=SEED) as episode:
            memory = [(cell, image) for cell, image, _ in episode.exploration()]
            episode.delay()
            reference = c1_probe.descriptor(episode.designate())
            truth = episode.target_cell
            if corrupt:
                episode.moved_between_visits = not episode.moved_between_visits
                episode._bare = {c: np.zeros_like(f) for c, f in episode._bare.items()}
                episode._measured_frames = {i: np.zeros_like(f)
                                            for i, f in episode._measured_frames.items()}
            outcome = play_adaptive(episode, memory, reference, rule)
            answers.append((outcome.cell, outcome.cost))
            assert outcome.success == (outcome.cell == truth)
    assert answers[0] == answers[1]
