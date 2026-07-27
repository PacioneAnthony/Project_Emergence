from __future__ import annotations

from collections import Counter

import numpy as np

from cognitive.models import ExperimentSignals
from learning.life_009 import (
    EXPERIMENT_COMMAND_COST,
    LIFE009_AMPLITUDES,
    LIFE009_PLANS,
    OneStepRidgeCompetence,
    PolicyHistory,
    ProgressRidgePolicy,
    build_private_evaluation_bank,
    normalized_auc,
    policy_feature_vector,
    sample_organism_parameters,
)
from learning.life_009_campaign import build_teacher_trajectory


def test_life009_plans_have_frozen_amplitudes_and_command_costs():
    by_primitive = {plan.primitive: plan for plan in LIFE009_PLANS}
    expected = {
        "probe_fine_bounded_servo": (15.0, 180.0),
        "probe_medium_bounded_servo": (40.0, 480.0),
        "probe_wide_bounded_servo": (70.0, 840.0),
    }
    for primitive, (amplitude, cost) in expected.items():
        plan = by_primitive[primitive]
        previous = 90.0
        deltas = []
        for target in plan.targets_deg:
            deltas.append(abs(target - previous))
            previous = target
        assert set(deltas) == {amplitude}
        assert sum(deltas) == cost
    assert EXPERIMENT_COMMAND_COST == {
        "probe_fine": 180.0,
        "probe_medium": 480.0,
        "probe_wide": 840.0,
    }


def test_private_bank_is_exactly_split_between_reachable_and_out_of_domain():
    parameters = sample_organism_parameters(99001)
    first = build_private_evaluation_bank(parameters)
    second = build_private_evaluation_bank(parameters)
    assert first == second
    assert Counter(item.command_amplitude_deg for item in first) == {
        amplitude: 8 for amplitude in LIFE009_AMPLITUDES
    }
    model = OneStepRidgeCompetence()
    assert model.mae(first) > 0.0
    assert normalized_auc([model.mae(first)] * 25) == 1.0


def test_unseen_amplitude_features_are_finite_and_deterministic():
    parameters = sample_organism_parameters(99002)
    evaluation = build_private_evaluation_bank(parameters)
    model = OneStepRidgeCompetence(
        item for item in evaluation if item.command_amplitude_deg == 15.0
    )
    assert model.amplitude_count(110.0) == 0
    assert model.amplitude_residual_mean(110.0) == 0.0
    assert np.isfinite(model.amplitude_uncertainty(110.0))
    vector = policy_feature_vector(
        model,
        experiment_id="probe_wide",
        cycle_index=1,
        history=PolicyHistory(),
        signals=ExperimentSignals(0.5, 0.5, 0.5, 0.5, 0.1, 0.5),
    )
    assert np.all(np.isfinite(vector))


def test_teacher_branches_are_isolated_and_policy_fit_is_bit_reproducible(tmp_path):
    parameters = sample_organism_parameters(99003)
    evaluation = build_private_evaluation_bank(parameters)
    result = build_teacher_trajectory(
        tmp_path / "teacher",
        parameters=parameters,
        evaluation=evaluation,
        cycles=2,
    )
    assert len(result.examples) == 6
    assert result.replay_bit_identical
    assert result.main_counts == {
        "proposals": 2,
        "executions": 2,
        "cycles": 2,
        "complete_cycles": 2,
        "running_executions": 0,
    }
    first = ProgressRidgePolicy()
    first.fit(result.examples)
    second = ProgressRidgePolicy()
    second.fit(result.examples)
    assert first.digest() == second.digest()
