from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from learning import reafference_002 as ref2
from learning import reafference_003 as ref3
from scripts.research import run_reafference_003 as runner
from sim3d import bench_model
from sim3d.bench_env import BenchHeadEnv


REPO = Path(__file__).resolve().parents[1]


def test_ref3_reserved_spaces_and_spec_are_new() -> None:
    assert ref3.RESERVED_SEEDS == tuple(range(14301, 14317))
    assert not set(ref3.RESERVED_SEEDS) & set(ref2.RESERVED_SEEDS)
    assert ref3.SMOKE_SEED == 14991
    assert ref3.SMOKE_SEED not in ref3.RESERVED_SEEDS
    assert ref3.ANALYSIS_SEED == 2026072701
    assert ref3.Ref3Spec().version == "ref-003-c1-c8-v1"
    assert ref3.Ref3Spec().digest() != ref2.Ref2Spec().digest()


def test_inherited_digests_match_the_preregistered_files() -> None:
    assert ref3.verify_inherited_digests(REPO) == ref3.INHERITED_DIGESTS


def test_structural_field_envelope_has_frozen_margin() -> None:
    envelope = ref3.field_envelope()
    assert envelope["passed"]
    assert envelope["left_deg"] == pytest_approx(26.7275785514)
    assert envelope["right_deg"] == pytest_approx(28.9492242338)
    assert envelope["residual_margin_deg"] == pytest_approx(2.2216456824)


def test_ref3_world_parameters_are_distinct_and_exact() -> None:
    config = ref3.ref3_bench_config(14990, bearing_deg=83.0, context=1)
    assert config.room.width == 3.6
    assert config.room.depth == 4.1
    assert config.room.object_count == 8
    assert config.room.reafference_distance_m == ref3.REF3_DISTANCE_M
    assert config.room.reafference_travel_m == ref3.REF3_TRAVEL_M
    assert config.room.reafference_bearing_deg == 83.0


def test_dynamic_bearing_and_object_dimensions_are_applied_without_rebuild() -> None:
    env = BenchHeadEnv(ref3.ref3_bench_config(14990, bearing_deg=80.0, context=0))
    try:
        body_id = env.model.body("ref_external_body").id
        before = env.model.body_pos[body_id].copy()
        ref3.configure_external_object(env, bearing_deg=83.0)
        after = env.model.body_pos[body_id].copy()
        assert not np.array_equal(before, after)
        assert np.allclose(
            env.model.geom(bench_model.GEOM_EXTERNAL).size,
            (
                ref3.REF3_OBJECT_HALF_WIDTH_M,
                0.018,
                ref3.REF3_OBJECT_HALF_HEIGHT_M,
            ),
        )
        assert np.allclose(
            env.model.joint(bench_model.JOINT_EXTERNAL).range,
            (-ref3.REF3_TRAVEL_M / 2.0, ref3.REF3_TRAVEL_M / 2.0),
        )
        env.set_external_object_displacement(-0.10)
        for _ in range(20):
            env.step(76.0)
        start = env.render_camera(64, 64)
        env.set_external_object_displacement(0.10)
        end = env.render_camera(64, 64)
        effect = np.mean(np.abs(end.astype(float) - start.astype(float))) / 255.0
        assert effect >= ref3.REF3_VISIBILITY_MINIMUM
    finally:
        env.close()


def test_pretransition_head_pose_is_exact_and_history_independent() -> None:
    env = BenchHeadEnv(ref3.ref3_bench_config(14990, bearing_deg=80.0, context=0))
    try:
        for _ in range(5):
            env.step(150.0)
        first = ref3.set_pretransition_head_pose(env, 36.25)
        qpos_first = float(env.data.qpos[env._qpos_servo])
        for _ in range(5):
            env.step(15.0)
        second = ref3.set_pretransition_head_pose(env, 36.25)
        assert first.as5600_deg == second.as5600_deg
        assert float(env.data.qpos[env._qpos_servo]) == qpos_first
        assert float(env.data.qvel[env._qvel_servo]) == 0.0
    finally:
        env.close()


def test_object_plan_never_clips_and_mixed_motion_is_independent() -> None:
    spec = ref3.Ref3Spec()
    motion = ref3.build_matched_motion_plans(14990, spec)["mixed"]
    starts, ends = ref3._feasible_object_plan(14990, "mixed", motion)
    deltas = ends - starts
    half = ref3.REF3_TRAVEL_M / 2.0
    assert np.all(starts >= -half)
    assert np.all(starts <= half)
    assert np.all(ends >= -half - 1e-7)
    assert np.all(ends <= half + 1e-7)
    assert np.min(np.abs(deltas)) >= 0.07 - 1e-6
    assert np.max(np.abs(deltas)) <= 0.18 + 1e-6
    assert abs(ref2._correlation(motion["signed_amplitude_deg"], deltas)) <= 0.05


def test_bearing_plan_is_bounded_reproducible_and_bank_specific() -> None:
    left = ref3._bearing_plan(14990, "mixed", 768)
    same = ref3._bearing_plan(14990, "mixed", 768)
    other = ref3._bearing_plan(14990, "external_only", 768)
    assert np.array_equal(left, same)
    assert not np.array_equal(left, other)
    assert np.all(np.abs(left) <= ref3.REF3_BEARING_OFFSET_MAX_DEG)
    assert np.std(left) > 1.0


def test_counterfactual_fields_are_not_part_of_the_learner_bank_contract() -> None:
    audit_fields = {
        "object_start_m",
        "object_end_m",
        "bearing_offset_deg",
        "counterfactual_effect",
        "head_photometric_change",
        "effect_ratio",
        "object_image_x",
        "counterfactual_digest",
    }
    assert not audit_fields & set(ref2.Ref2Bank.__annotations__)


def test_review_gate_is_open_but_campaign_stays_closed_before_smoke(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(runner, "SMOKE_RESULT", tmp_path / "absent_smoke_14991.json")
    assert runner.review_authorized()
    authorized, reason = runner.campaign_authorized(
        ref3.Ref3Spec(),
        review_accepted=True,
    )
    assert not authorized
    assert "smoke 14991" in reason


def test_ref3_analysis_adds_absolute_sanity_gate_and_new_seed() -> None:
    evaluations = [_successful_evaluation(seed) for seed in ref3.RESERVED_SEEDS]
    analysis = ref3.analyze_evaluations(evaluations)
    assert analysis["analysis_seed"] == ref3.ANALYSIS_SEED
    assert analysis["seeds"] == list(ref3.RESERVED_SEEDS)
    assert analysis["sanity_external"]["transport_jepa"]["minimum"] == 0.70
    assert analysis["sanity_external"]["transport_jepa"]["passed"]
    assert analysis["guards"]["sanity_external_absolute"]


def _successful_evaluation(seed: int) -> dict:
    methods = ref3.CONDITIONS + ("pixel_change", "yaw_warp")
    rates = {}
    for method in methods:
        mixed = 0.80 if method == "transport_jepa" else 0.50
        external = 0.80 if method == "transport_jepa" else 0.55
        rates[method] = {
            "moving_self_test": [0.01] * 6,
            "micro_self_test": [0.01] * 6,
            "mixed": [mixed] * 6,
            "external_only": [external] * 6,
        }
    return {
        "seed": seed,
        "rates_by_bin": rates,
        "self_error_by_bin": {
            "transport_jepa": [0.10] * 6,
            "concat_relative_jepa": [0.20] * 6,
            "no_command_jepa": [0.20] * 6,
        },
        "h5": {
            condition: {
                "permuted_minus_normal_by_bin": [0.05] * 6,
                "inverted_minus_normal_by_bin": [0.05] * 6,
            }
            for condition in ref3.CONDITIONS
        },
        "learner_guard": {
            condition: {"passed": True}
            for condition in ref3.CONDITIONS
        },
    }


def pytest_approx(value: float):
    import pytest

    return pytest.approx(value, rel=0, abs=1e-9)
