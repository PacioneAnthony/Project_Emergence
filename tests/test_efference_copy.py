import numpy as np
import pytest

from learning.efference_copy import EfferenceCopy, EfferenceCopyReport, evaluate_efference_copy


def test_fit_recovers_known_gain_and_bias():
    rng = np.random.default_rng(42)
    cmds = rng.uniform(-5, 5, 200)
    gyro_deltas = 0.03 * cmds + 0.001 + rng.normal(0, 0.001, 200)

    ec = EfferenceCopy()
    ec.fit(cmds, gyro_deltas)

    assert abs(ec.gain - 0.03) < 0.005
    assert abs(ec.bias - 0.001) < 0.002


def test_residuals_shape_and_dtype():
    ec = EfferenceCopy()
    ec.fit(np.array([-1.0, 1.0]), np.array([-0.03, 0.03]))
    res = ec.residuals(np.array([0.0, 2.0, -2.0]), np.array([0.0, 0.06, -0.06]))
    assert res.shape == (3,)
    assert res.dtype == np.float32


def test_predict_and_scalar_residual():
    ec = EfferenceCopy(gain=0.03, bias=0.0)
    pred = ec.predict(10.0)
    assert abs(pred - 0.30) < 1e-6
    assert ec.residual(pred, 0.31) == pytest.approx(0.01, abs=1e-6)


def test_evaluate_auroc_above_random_for_separable_signal():
    rng = np.random.default_rng(0)
    n = 400
    cmds = rng.uniform(-5, 5, n)
    gyro_deltas = 0.03 * cmds + rng.normal(0, 0.001, n)
    external = rng.random(n) < 0.15
    gyro_deltas[external] += rng.uniform(0.05, 0.15, np.sum(external))

    report = evaluate_efference_copy(cmds, gyro_deltas, external)
    assert report.auroc > 0.65
    assert isinstance(report.passed, bool)


def test_evaluate_requires_minimum_samples():
    with pytest.raises(ValueError, match="at least 4"):
        evaluate_efference_copy(
            np.array([1.0, 2.0]),
            np.array([1.0, 2.0]),
            np.array([False, False]),
        )


def test_fit_requires_matching_lengths():
    ec = EfferenceCopy()
    with pytest.raises(ValueError, match="same length"):
        ec.fit(np.array([1.0, 2.0]), np.array([1.0]))


def test_fit_requires_at_least_two_samples():
    ec = EfferenceCopy()
    with pytest.raises(ValueError, match="at least 2"):
        ec.fit(np.array([1.0]), np.array([0.03]))
