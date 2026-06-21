import numpy as np
import pytest

from learning.efference_copy import EfferenceCopy
from learning.controllability import ControllabilityEstimator, SkillScheduler, SkillSchedulerConfig


def _fitted_ec(gain: float = 0.03) -> EfferenceCopy:
    ec = EfferenceCopy()
    ec.fit(np.array([-5.0, 5.0]), np.array([-gain * 5, gain * 5]))
    return ec


def test_controllability_higher_for_correlated_than_random():
    rng = np.random.default_rng(7)
    cmds = rng.uniform(-5, 5, 500)

    # Correlated: gyro tightly tracks command
    gyro_correlated = 0.03 * cmds + rng.normal(0, 0.0005, 500)
    c_corr = ControllabilityEstimator(n_permutations=200, rng=np.random.default_rng(0)).estimate(
        cmds, gyro_correlated, _fitted_ec()
    )

    # Random: gyro independent of command
    gyro_random = rng.normal(0, 0.05, 500)
    c_rand = ControllabilityEstimator(n_permutations=200, rng=np.random.default_rng(0)).estimate(
        cmds, gyro_random, _fitted_ec()
    )

    # Correlated gyro must score strictly higher than random gyro
    assert c_corr > c_rand + 0.1


def test_high_controllability_when_model_fits_well():
    rng = np.random.default_rng(7)
    cmds = rng.uniform(-5, 5, 500)
    gyro = 0.03 * cmds + rng.normal(0, 0.0005, 500)

    c = ControllabilityEstimator(n_permutations=200, rng=np.random.default_rng(0)).estimate(
        cmds, gyro, _fitted_ec()
    )
    assert c > 0.7


def test_controllability_output_bounded():
    c = ControllabilityEstimator(n_permutations=20, rng=np.random.default_rng(99)).estimate(
        np.array([1.0, -1.0]), np.array([0.03, -0.03]), _fitted_ec()
    )
    assert 0.0 <= c <= 1.0


def test_controllability_returns_zero_for_single_sample():
    c = ControllabilityEstimator().estimate(
        np.array([1.0]), np.array([0.03]), _fitted_ec()
    )
    assert c == 0.0


def test_interest_decreases_after_habituation():
    scheduler = SkillScheduler()
    key = ("d0", "a0")
    base = scheduler.interest(controllability=0.8, prediction_progress=0.5, state_key=key, distance_m=1.0)
    scheduler.update_habituation(key)
    after = scheduler.interest(controllability=0.8, prediction_progress=0.5, state_key=key, distance_m=1.0)
    assert after < base


def test_interest_penalised_near_obstacle():
    cfg = SkillSchedulerConfig(risk_threshold=0.10, risk_penalty=2.0)
    scheduler = SkillScheduler(cfg)
    key = ("near",)
    far = scheduler.interest(controllability=0.5, prediction_progress=0.5, state_key=key, distance_m=0.50)
    near = scheduler.interest(controllability=0.5, prediction_progress=0.5, state_key=key, distance_m=0.03)
    assert near < far


def test_decay_all_reduces_habituation():
    scheduler = SkillScheduler()
    key = ("x",)
    scheduler.update_habituation(key)
    h_before = scheduler._habituation[key]
    scheduler.decay_all()
    assert scheduler._habituation[key] < h_before


def test_new_state_key_starts_at_zero_habituation():
    scheduler = SkillScheduler()
    assert scheduler._habituation[("unseen",)] == 0.0
