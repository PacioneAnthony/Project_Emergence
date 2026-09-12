"""The diagnostic must measure the two candidate gaps and add nothing else.

Its whole value rests on three claims: the comparison rule is the frozen one, the
variant plan is the one written before any number, and the privileged "ideal
stop" never leaks into a policy's decision. Each is checked here.
"""

from __future__ import annotations

import numpy as np
import pytest

from learning import c1_audit, c1_probe, c1_probe_hybrid
from learning.c1_audit import (
    ORDERS,
    STOP_RULES,
    TABLE,
    Variant,
    apparent_class,
    calibrate_table,
    declared_variants,
    non_dominated,
    play_episode,
    probe_seeds,
    table_variants,
    tuning_variants,
)
from learning.c1_task import C1Config

SEED = 21  # an ordinary test seed, not a reserved one


# --------------------------------------------------------- nothing was copied


def test_the_matcher_and_the_window_are_the_frozen_ones():
    assert c1_audit.descriptor is c1_probe.descriptor
    assert c1_audit.distance is c1_probe.distance
    assert c1_audit.closest is c1_probe.closest
    assert c1_audit.windowed is c1_probe_hybrid.windowed
    assert c1_audit.Verification is c1_probe_hybrid.Verification


# ------------------------------------------------- the plan written in advance


def test_the_stop_grid_is_the_protocols():
    assert list(STOP_RULES) == ["sans_arret", "a025", "a050", "a075", "a100", "a125", "a150"]
    assert STOP_RULES["sans_arret"] is None
    assert [STOP_RULES[k] for k in list(STOP_RULES)[1:]] == [0.25, 0.50, 0.75, 1.00, 1.25, 1.50]
    assert ORDERS == ("raster", "memoire")


def test_twenty_variants_exactly_as_declared():
    variants = declared_variants()
    assert len(variants) == 20
    assert len({v.name for v in variants}) == 20
    comparaison = [v for v in variants if v.verification == "comparaison"]
    s150 = [v for v in variants if v.verification == "s150"]
    assert len(comparaison) == 16  # 2 orders x (7 thresholds + the table)
    assert len(s150) == 4          # 2 orders x {sans_arret, a075}
    assert {v.stop for v in s150} == {"sans_arret", "a075"}
    assert sum(1 for v in variants if v.stop == TABLE) == 2


def test_the_tuning_plan_excludes_the_table_those_rooms_define():
    """Scoring the table on the rooms that calibrated it would be optimistic.

    The protocol was corrected on this point before the first measurement. The
    tuning phase measures the eighteen fixed-threshold variants; the two table
    variants join the diagnostic out of sample.
    """

    tuning, tables = tuning_variants(), table_variants()
    assert len(tuning) == 18 and len(tables) == 2
    assert all(v.stop != TABLE for v in tuning)
    assert all(v.stop == TABLE for v in tables)
    assert set(tuning) | set(tables) == set(declared_variants())
    assert not set(tuning) & set(tables)


def test_a_table_variant_without_a_table_fails_loudly():
    """The crash that exposed the circularity must stay a loud, named error."""

    with pytest.raises(RuntimeError, match="table"):
        play_episode(C1Config(object_count=8, shuffle_probability=0.0), SEED,
                     table_variants(), table=None)


def test_seeds_are_fresh_against_every_spent_and_reserved_space():
    from learning import c1_probe_v2, c1_probe_v3

    tune, diag = probe_seeds("tune", 40), probe_seeds("diag", 60)
    assert tune[0] == 3870390072 and diag[0] == 3787161888
    assert not set(tune) & set(diag)
    assert len(set(tune) | set(diag)) == 100
    assert min(tune + diag) > 100_000

    spent = set(c1_probe.probe_seeds("dev", 10)) | set(c1_probe.probe_seeds("bank", 60))
    spent |= set(c1_probe_v2.probe_seeds("dev", 10)) | set(c1_probe_v2.probe_seeds("bank", 200))
    spent |= set(c1_probe_v3.probe_seeds("dev", 10)) | set(c1_probe_v3.probe_seeds("bank", 300))
    spent |= set(c1_probe_hybrid.probe_seeds("dev", 10)) | set(c1_probe_hybrid.probe_seeds("bank", 100))
    # c1-mechanism/v1 is reserved and the review forbids opening it.
    import hashlib, json
    for sub, n in (("dev", 10), ("bank", 300)):
        for i in range(n):
            blob = json.dumps(["c1-mechanism/v1", sub, i], separators=(",", ":"), ensure_ascii=False)
            spent.add(int.from_bytes(hashlib.sha256(blob.encode()).digest()[:4], "big"))
    assert len(spent) == 1010
    assert not (set(tune) | set(diag)) & spent


# ------------------------------------------------------- the calibration rule


def test_apparent_class_reads_the_reference_and_nothing_else():
    reference = np.zeros(24)
    reference[7] = 1.0
    assert apparent_class(reference) == 7
    assert apparent_class(None) == -1


def _tuning_row(klass, per_stop):
    """per_stop maps a stop name to (success, cost) for the raster/comparaison variant."""

    variants = {}
    for stop, (success, cost) in per_stop.items():
        variants[Variant("comparaison", "raster", stop).name] = {
            "success": success, "cost": cost, "accepted": False, "false_acceptance": False,
            "target_rejected": False, "rank": 3, "ideal_cost": 4, "stopped": True,
            "cell": [90.0, 0.0],
        }
    return {"seed": 0, "moved": False, "apparent_class": klass, "target_index": 0,
            "variants": variants}


def test_calibration_takes_the_cheapest_rule_within_tolerance():
    """The cheapest rule wins, unless its success falls outside the tolerance."""

    per_stop = {name: (True, 16.0) for name in STOP_RULES}
    per_stop["a125"] = (True, 8.0)
    per_stop["a150"] = (True, 5.0)
    rows = [_tuning_row(3, per_stop) for _ in range(25)]
    assert calibrate_table(rows)[3] == 1.50  # cheapest, and it matches the best success

    # Drop a150 four points below the best: outside the 0.02 tolerance, so the
    # next cheapest eligible rule takes over rather than the cheapest overall.
    for row in rows[:1]:
        row["variants"][Variant("comparaison", "raster", "a150").name]["success"] = False
    assert calibrate_table(rows)[3] == 1.25


def test_calibration_breaks_a_cost_tie_on_the_strictest_threshold():
    """Ties go to the strictest threshold, and `sans_arret` comes last."""

    rows = [_tuning_row(5, {name: (True, 16.0) for name in STOP_RULES}) for _ in range(10)]
    assert calibrate_table(rows)[5] == 0.25


def test_a_class_absent_from_tuning_gets_no_threshold():
    rows = [_tuning_row(3, {name: (True, 16.0) for name in STOP_RULES})]
    table = calibrate_table(rows)
    assert set(table) == {3}
    assert table.get(9, None) is None


# ------------------------------------------------------------------- episode


@pytest.fixture(scope="module")
def played():
    return play_episode(C1Config(object_count=8, shuffle_probability=1.0), SEED,
                        declared_variants(), table={k: 0.75 for k in range(24)})


def test_every_declared_variant_plays_the_same_room(played):
    assert set(played["variants"]) == {v.name for v in declared_variants()}
    assert played["moved"] is True
    for record in played["variants"].values():
        assert record["cost"] == 1 or 2 <= record["cost"] <= 16


def test_accepting_costs_one_move_and_never_reports_a_rank(played):
    for record in played["variants"].values():
        if record["accepted"]:
            assert record["cost"] == 1 and record["rank"] == 0
            assert record["target_rejected"] is False


def test_a_looser_threshold_never_costs_more_at_equal_order(played):
    for order in ORDERS:
        costs = [played["variants"][Variant("comparaison", order, stop).name]["cost"]
                 for stop in ("a025", "a050", "a075", "a100", "a125", "a150")]
        assert costs == sorted(costs, reverse=True)


def test_never_stopping_is_the_frozen_gate_behaviour(played):
    for order in ORDERS:
        record = played["variants"][Variant("comparaison", order, "sans_arret").name]
        assert record["cost"] == 1 or 15 <= record["cost"] <= 16
        assert record["stopped"] is False or record["accepted"]


def test_the_ideal_cost_is_privileged_and_never_beaten_by_the_policy(played):
    """It bounds what this order could return with perfect recognition."""

    for record in played["variants"].values():
        if record["rank"]:
            assert record["ideal_cost"] == 1 + record["rank"]
            assert record["ideal_cost"] <= record["cost"]


def test_the_two_orders_visit_the_same_cells_in_a_different_sequence(played):
    """If the orders never differed, the ordering comparison would be empty."""

    ranks = {order: played["variants"][Variant("comparaison", order, "sans_arret").name]["rank"]
             for order in ORDERS}
    assert set(ranks) == {"raster", "memoire"}


def test_an_episode_replays_identically():
    config = C1Config(object_count=8, shuffle_probability=1.0)
    table = {k: 0.75 for k in range(24)}
    first = play_episode(config, SEED, declared_variants(), table)
    second = play_episode(config, SEED, declared_variants(), table)
    assert first == second


# ------------------------------------------------------------- domination


def test_the_mean_rank_ignores_episodes_that_never_searched():
    """Accepted episodes carry rank 0; counting them halves the mean.

    The first tuning report showed ranks near 3.3 for both orders, which would
    have looked like a large ordering effect against the exchangeable prediction
    of 7.5. It was this bug: more than half the episodes accepted and never
    searched at all.
    """

    from learning.c1_audit import summarise

    variant = Variant("comparaison", "raster", "sans_arret")

    def row(rank, accepted):
        return {"seed": 0, "moved": False, "apparent_class": 0, "target_index": 0,
                "variants": {variant.name: {
                    "cell": [90.0, 0.0], "success": True, "cost": 1 if accepted else 8,
                    "accepted": accepted, "false_acceptance": False,
                    "target_rejected": False, "rank": rank,
                    "ideal_cost": 1 if accepted else 1 + rank, "stopped": accepted}}}

    rows = [row(0, True), row(0, True), row(7, False), row(9, False)]
    block = summarise(rows, [variant])[variant.name]
    assert block["rank_mean"] == pytest.approx(8.0)   # not 4.0
    assert block["fallback_rate"] == pytest.approx(0.5)


def test_domination_keeps_the_front():
    summary = {
        "a": {"success_rate": 0.90, "cost_mean": 9.0},
        "b": {"success_rate": 0.80, "cost_mean": 12.0},   # dominated by a
        "c": {"success_rate": 0.70, "cost_mean": 3.0},
    }
    assert set(non_dominated(summary)) == {"a", "c"}
