from __future__ import annotations

import numpy as np
import pytest
import torch

from learning.reafference_002 import (
    CONDITIONS,
    MOBILE_MATCHED_BANKS,
    Ref2Spec,
    SpatialReafferenceJEPA,
    analyze_evaluations,
    build_motor_input,
    build_matched_motion_plans,
    counterfactual_permutation,
    matched_motion_signature,
    pooled_vicreg_latent,
    predicted_servo_displacement_deg,
    spatial_score,
    yaw_warp,
    yaw_warp_error,
)
from scripts.research import run_reafference_002


def motor_arrays():
    current = np.array([70.0, 100.0], dtype=np.float32)
    targets = np.array(
        [[80.0, 82.0, 84.0, 86.0, 88.0], [90.0, 88.0, 86.0, 84.0, 82.0]],
        dtype=np.float32,
    )
    horizons = np.array([3, 5], dtype=np.int64)
    return current, targets, horizons


def test_motor_input_uses_only_declared_pre_transition_values() -> None:
    current, targets, horizons = motor_arrays()
    first = build_motor_input(current, targets, horizons)
    unrelated_future_angles = np.array([-999.0, 999.0])
    unrelated_object_state = np.array([123.0, 456.0])
    second = build_motor_input(current, targets, horizons)
    assert np.array_equal(first, second)
    assert unrelated_future_angles.shape == unrelated_object_state.shape
    assert np.all(first[0, 1 + horizons[0] : 1 + 5] == 0)


def test_mobile_bank_schedules_are_matched_as_exact_multisets() -> None:
    plans = build_matched_motion_plans(13991)
    for angle_bin in range(6):
        signatures = [
            matched_motion_signature(plans[kind], angle_bin) for kind in MOBILE_MATCHED_BANKS
        ]
        assert signatures[1:] == signatures[:-1]


def test_micro_calibration_has_nonzero_balanced_two_degree_commands() -> None:
    plans = build_matched_motion_plans(13991)
    for kind in ("micro_self_calibration", "micro_self_test"):
        amplitudes = plans[kind]["signed_amplitude_deg"]
        assert np.all(np.abs(amplitudes) == 2)
        for angle_bin in range(6):
            selected = plans[kind]["angle_bin"] == angle_bin
            assert np.sum(amplitudes[selected] > 0) == 64
            assert np.sum(amplitudes[selected] < 0) == 64


def test_h5_mapping_is_opposite_sign_derangement_in_frozen_strata() -> None:
    plan = build_matched_motion_plans(13991)["moving_self_test"]
    mapping = counterfactual_permutation(plan, seed=2026072601)
    assert np.all(mapping != np.arange(len(mapping)))
    assert np.all(plan["angle_bin"][mapping] == plan["angle_bin"])
    assert np.all(plan["horizon"][mapping] == plan["horizon"])
    assert np.all(
        np.abs(plan["signed_amplitude_deg"][mapping])
        == np.abs(plan["signed_amplitude_deg"])
    )
    assert np.all(
        np.sign(plan["signed_amplitude_deg"][mapping])
        == -np.sign(plan["signed_amplitude_deg"])
    )


def test_ref2_spec_digest_changes_with_protocol_budget() -> None:
    assert Ref2Spec().digest() != Ref2Spec(optimizer_steps=10).digest()


def test_spatial_encoder_exposes_frozen_map_shape() -> None:
    model = SpatialReafferenceJEPA("transport_jepa")
    maps = model.encode_map(torch.rand(2, 3, 64, 64))
    assert maps.shape == (2, 128, 8, 8)
    assert pooled_vicreg_latent(maps).shape == (2, 128)


def test_three_conditions_have_identical_parameter_capacity() -> None:
    counts = []
    trainable = []
    for condition in CONDITIONS:
        torch.manual_seed(123)
        model = SpatialReafferenceJEPA(condition)
        counts.append(sum(parameter.numel() for parameter in model.parameters()))
        trainable.append(sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad))
    assert len(set(counts)) == 1
    assert len(set(trainable)) == 1


def test_all_parameters_receive_gradient_in_each_condition() -> None:
    current, targets, horizons = motor_arrays()
    motor = torch.from_numpy(build_motor_input(current, targets, horizons))
    for condition in CONDITIONS:
        torch.manual_seed(456)
        model = SpatialReafferenceJEPA(condition)
        frames = torch.rand(2, 3, 64, 64)
        target = torch.rand(2, 128, 8, 8)
        _, prediction = model(frames, motor)
        torch.mean((prediction - target) ** 2).backward()
        missing = [
            name
            for name, parameter in model.named_parameters()
            if parameter.grad is None or not torch.any(parameter.grad != 0)
        ]
        assert not missing, (condition, missing)


def test_zero_relative_command_makes_transport_identity_and_equal_inputs() -> None:
    torch.manual_seed(789)
    transport = SpatialReafferenceJEPA("transport_jepa")
    torch.manual_seed(789)
    concat = SpatialReafferenceJEPA("concat_relative_jepa")
    frames = torch.rand(2, 3, 64, 64)
    motor = torch.zeros(2, 7)
    motor[:, 0] = torch.tensor([-0.25, 0.5])
    motor[:, -1] = 1.0
    current_map = transport.encode_map(frames)
    assert torch.equal(current_map, concat.encode_map(frames))
    transport_input = transport.predictor_input(current_map, motor)
    concat_input = concat.predictor_input(current_map, motor)
    assert torch.equal(transport_input, concat_input)


def test_spatial_score_rejects_static_degenerate_calibration() -> None:
    current = torch.zeros(2, 128, 8, 8)
    target = current.clone()
    prediction = torch.ones_like(current)
    score, _, copy_error = spatial_score(prediction, current, target)
    assert torch.all(copy_error == 0)
    assert torch.all(score == 1)


def test_frozen_servo_predictor_is_rate_limited_and_horizon_masked() -> None:
    current = np.array([90.0, 90.0])
    commands = np.array([[170.0] * 5, [170.0] * 5])
    horizon = np.array([1, 5])
    delta = predicted_servo_displacement_deg(current, commands, horizon)
    assert np.array_equal(delta, np.array([12.0, 60.0]))


def test_yaw_warp_zero_displacement_is_bit_identity() -> None:
    rng = np.random.default_rng(12)
    frames = rng.integers(0, 256, size=(2, 64, 64, 3), dtype=np.uint8)
    current = np.array([80.0, 100.0])
    targets = np.repeat(current[:, None], 5, axis=1)
    result = yaw_warp(frames, current, targets, np.array([1, 5]))
    assert np.array_equal(result.warped, frames.astype(np.float32))
    assert np.all(result.valid_mask)
    assert np.all(result.predicted_delta_deg == 0)
    assert np.all(yaw_warp_error(result.warped, frames, result.valid_mask) == 0)


def test_yaw_warp_sign_reverses_landmark_displacement() -> None:
    frame = np.zeros((1, 64, 64, 3), dtype=np.uint8)
    frame[0, 32, 32] = 255
    current = np.array([90.0])
    positive = yaw_warp(frame, current, np.full((1, 5), 100.0), np.array([1])).warped
    negative = yaw_warp(frame, current, np.full((1, 5), 80.0), np.array([1])).warped
    positive_x = np.unravel_index(np.argmax(positive[0, :, :, 0]), (64, 64))[1]
    negative_x = np.unravel_index(np.argmax(negative[0, :, :, 0]), (64, 64))[1]
    assert positive_x < 32 < negative_x


def test_yaw_warp_rejects_wrong_resolution() -> None:
    with pytest.raises(ValueError, match="64x64"):
        yaw_warp(
            np.zeros((1, 32, 32, 3), dtype=np.uint8),
            np.array([90.0]),
            np.full((1, 5), 90.0),
            np.array([1]),
        )


def test_ref2_review_and_all_eight_amendments_are_machine_visible() -> None:
    assert run_reafference_002.amendments_integrated()
    assert run_reafference_002.review_authorized()


def test_ref2_time_projection_includes_three_condition_amortization() -> None:
    gate = run_reafference_002.frozen_time_manifest(30.0, [10.0, 11.0, 12.0])
    assert gate["projected_seconds"] == pytest.approx(48 * (10 + 11))
    assert gate["effective_cap_seconds"] == 75 * 60


def test_ref2_analysis_uses_exact_eight_test_holm_family() -> None:
    evaluations = []
    methods = CONDITIONS + ("pixel_change", "yaw_warp")
    for seed in range(13301, 13317):
        rates = {
            method: {
                "mixed": [0.9] * 6 if method == "transport_jepa" else [0.1] * 6,
                "external_only": [0.8] * 6,
                "moving_self_test": [0.02] * 6,
                "micro_self_test": [0.02] * 6,
            }
            for method in methods
        }
        evaluations.append(
            {
                "seed": seed,
                "rates_by_bin": rates,
                "self_error_by_bin": {
                    "transport_jepa": [0.1] * 6,
                    "concat_relative_jepa": [0.2] * 6,
                    "no_command_jepa": [0.2] * 6,
                },
                "h5": {
                    condition: {
                        "permuted_minus_normal_by_bin": [0.1] * 6,
                        "inverted_minus_normal_by_bin": [0.1] * 6,
                    }
                    for condition in CONDITIONS
                },
                "learner_guard": {
                    condition: {"passed": True} for condition in CONDITIONS
                },
            }
        )
    analysis = analyze_evaluations(evaluations)
    assert analysis["holm_family_size"] == 8
    assert len(analysis["tests"]) == 8
    assert analysis["decision"]["eligible_for_contradictory_review"]
