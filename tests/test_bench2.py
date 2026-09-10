"""Two-axis neck (D-060, step 1): the grid, the sign of tilt, and the frozen bench."""

from __future__ import annotations

import numpy as np
import pytest

from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig
from sim3d import bench2_model
from sim3d.bench2_env import Bench2HeadEnv, Bench2Observation
from sim3d.bench2_model import Bench2Config, build_bench2_mjcf, grid_shape, view_cells

SEED = 4242


@pytest.fixture(scope="module")
def env():
    environment = Bench2HeadEnv(Bench2Config(seed=SEED))
    environment.reset(seed=SEED)
    yield environment
    environment.close()


# ------------------------------------------------------------------- the grid


def test_grid_is_five_by_three():
    config = Bench2Config(seed=SEED)
    assert grid_shape(config) == (5, 3)
    cells = view_cells(config)
    assert len(cells) == 15
    assert sorted({pan for pan, _ in cells}) == [30.0, 60.0, 90.0, 120.0, 150.0]
    assert sorted({tilt for _, tilt in cells}) == [-30.0, 0.0, 30.0]


def test_every_cell_is_reachable():
    config = Bench2Config(seed=SEED)
    for pan, tilt in view_cells(config):
        assert config.servo.min_deg <= pan <= config.servo.max_deg
        assert config.tilt.min_deg <= tilt <= config.tilt.max_deg


def test_cell_centers_are_one_field_of_view_apart():
    config = Bench2Config(seed=SEED)
    fov = config.sensors.camera_fovy_deg
    pans = sorted({pan for pan, _ in view_cells(config)})
    assert all(b - a == pytest.approx(fov) for a, b in zip(pans, pans[1:]))


# ------------------------------------------------------------------ the joint


def test_model_has_one_tilt_joint_and_one_tilt_actuator(env):
    names = [env.model.joint(i).name for i in range(env.model.njnt)]
    assert names.count(bench2_model.JOINT_TILT) == 1
    actuators = [env.model.actuator(i).name for i in range(env.model.nu)]
    assert actuators.count(bench2_model.ACT_TILT) == 1
    assert bench2_model.BODY_TILT in [env.model.body(i).name for i in range(env.model.nbody)]


def test_build_refuses_to_run_if_the_frozen_bench_changed(monkeypatch):
    """The transformation is anchored on the frozen template; it must fail loudly."""

    config = Bench2Config(seed=SEED)
    monkeypatch.setattr(
        bench2_model.bench_model, "build_bench_mjcf", lambda *a, **k: "<mujoco/>"
    )
    with pytest.raises(RuntimeError, match="anchor"):
        build_bench2_mjcf(config, [])


# ------------------------------------------------------------- sign and droop


def test_positive_tilt_raises_the_view(env):
    """A positive command must look up. The naive hinge axis does the opposite."""

    import mujoco

    camera = env.model.camera(bench2_model.CAMERA_HEAD).id
    heights = {}
    for tilt in (30.0, 0.0, -30.0):
        env.settle_at(90.0, tilt)
        mujoco.mj_forward(env.model, env.data)
        heights[tilt] = -env.data.cam_xmat[camera].reshape(3, 3)[2, 2]

    assert heights[30.0] == pytest.approx(0.5, abs=1e-3)
    assert heights[0.0] == pytest.approx(0.0, abs=1e-3)
    assert heights[-30.0] == pytest.approx(-0.5, abs=1e-3)


def test_tilt_does_not_droop_under_gravity(env):
    """The hinge runs through the barrel, so the moving body is balanced."""

    env.reset(seed=SEED)
    for _ in range(200):
        env.step(90.0, 0.0)
    assert env.tilt_angle_deg() == pytest.approx(0.0, abs=1e-4)


# ------------------------------------------------------- the frozen one-axis bench


def test_zero_tilt_renders_exactly_like_the_frozen_bench():
    """The two-axis world differs from the frozen one by the tilt joint alone."""

    one = BenchHeadEnv(BenchConfig(seed=SEED))
    two = Bench2HeadEnv(Bench2Config(seed=SEED))
    try:
        one.reset(seed=SEED)
        two.reset(seed=SEED)
        for pan in (60.0, 90.0, 120.0):
            for _ in range(150):
                one.step(pan)
                two.step(pan, 0.0)
            a = one.render_camera(64, 64)
            b = two.render_camera(64, 64)
            assert np.array_equal(a, b), f"pan {pan} renders differently"
    finally:
        one.close()
        two.close()


# ------------------------------------------------------------ the step contract


def test_step_takes_two_commands(env):
    env.reset(seed=SEED)
    observation = env.settle_at(120.0, 30.0)
    assert isinstance(observation, Bench2Observation)
    assert observation.pan_deg == pytest.approx(120.0, abs=0.1)
    assert observation.tilt_deg == pytest.approx(30.0, abs=0.2)


def test_panning_alone_does_not_recenter_the_tilt(env):
    env.reset(seed=SEED)
    env.settle_at(90.0, 30.0)
    for _ in range(50):
        env.step(120.0)  # no tilt argument
    assert env.tilt_angle_deg() == pytest.approx(30.0, abs=0.2)


def test_commands_are_clamped_to_the_joint_ranges(env):
    env.reset(seed=SEED)
    observation = env.step(999.0, 999.0)
    assert observation.requested_pan_deg == env.config.servo.max_deg
    assert observation.requested_tilt_deg == env.config.tilt.max_deg


def test_observation_carries_both_angles(env):
    env.reset(seed=SEED)
    observation = env.settle_at(60.0, -30.0)
    proprioception = observation.proprioception()
    assert proprioception.shape == (2,)
    assert proprioception[0] == pytest.approx(60.0, abs=0.1)
    assert proprioception[1] == pytest.approx(-30.0, abs=0.2)


# ----------------------------------------------------------------- distinctness


def test_cells_are_distinct(env):
    """Every cell must be recognisable, by more than it differs from itself."""

    env.reset(seed=SEED)
    cells = view_cells(env.config)

    def sweep(order):
        return np.stack([
            (env.settle_at(pan, tilt), env.render_camera(64, 64).astype(np.float32))[1]
            for pan, tilt in order
        ])

    forward = sweep(cells)
    backward = sweep(list(reversed(cells)))[::-1]

    def distance(a, b):
        return float(np.abs(a - b).mean())

    n = len(cells)
    intra_max = max(distance(forward[i], backward[i]) for i in range(n))
    inter_min = min(distance(forward[i], backward[j]) for i in range(n) for j in range(n) if i != j)
    assert inter_min > intra_max

    for i in range(n):
        nearest = min(range(n), key=lambda j: distance(forward[i], backward[j]))
        assert nearest == i, f"cell {cells[i]} is closer to {cells[nearest]} than to itself"
