"""The live viewer watches experiments and never changes them."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import numpy as np
import pytest

from learning.c1_task import C1Config, C1Episode
from sim3d.bench2_env import Bench2HeadEnv
from sim3d.bench2_live import LiveView, SceneRenderer, columns_as_seen, live_camera_mjcf
from sim3d.bench2_model import Bench2Config

SEED = 21


class RenderEveryStep:
    """The most intrusive observer there is: it renders at every single step."""

    def __init__(self):
        self.renderer = SceneRenderer()
        self.frames = 0

    def on_step(self, episode, observation):
        head, room = self.renderer.render(episode.env)
        assert room is not None
        self.frames += 1

    def on_phase(self, episode, phase, info):
        pass


def _run(config, observer=None):
    with C1Episode(config, seed=SEED, observer=observer) as episode:
        images = [image.copy() for _, image, _ in episode.exploration()]
        episode.delay()
        episode.designate()
        result = episode.answer(*episode.target_cell)
        return episode.placement, images, result


def test_watching_an_episode_does_not_change_it():
    """Same seed, with and without the viewer: identical images and results.

    The watched run also has the overview camera in its room, so this pins both
    claims at once -- the camera adds no pixel to the head view, and rendering,
    ray casting and drawing at every step perturb nothing.
    """

    plain = C1Config(object_count=8, shuffle_probability=1.0)
    watched = C1Config(
        object_count=8,
        shuffle_probability=1.0,
        bench=Bench2Config(extra_mjcf=live_camera_mjcf(Bench2Config())),
    )
    observer = RenderEveryStep()
    try:
        placement_a, images_a, result_a = _run(plain)
        placement_b, images_b, result_b = _run(watched, observer)
    finally:
        observer.renderer.close()

    assert observer.frames > 50
    assert placement_a == placement_b
    assert len(images_a) == len(images_b)
    for a, b in zip(images_a, images_b):
        assert np.array_equal(a, b)
    assert result_a == result_b


def test_overview_camera_adds_no_pixel_to_the_head_view():
    plain = Bench2HeadEnv(Bench2Config(seed=SEED))
    watched = Bench2HeadEnv(Bench2Config(seed=SEED, extra_mjcf=live_camera_mjcf(Bench2Config())))
    try:
        plain.reset(seed=SEED)
        watched.reset(seed=SEED)
        for pan, tilt in ((30.0, 30.0), (90.0, 0.0), (150.0, -30.0)):
            plain.settle_at(pan, tilt)
            watched.settle_at(pan, tilt)
            assert np.array_equal(plain.render_camera(96, 96), watched.render_camera(96, 96))
    finally:
        plain.close()
        watched.close()


def test_the_grid_reads_the_way_the_robot_sees():
    """A small pan turns the head to its right, so it goes on the right."""

    assert columns_as_seen([30.0, 60.0, 90.0, 120.0, 150.0]) == [150.0, 120.0, 90.0, 60.0, 30.0]


def test_renderer_follows_a_rebuilt_world():
    """Shuffling rebuilds the MuJoCo model; the viewer must follow, not crash."""

    renderer = SceneRenderer()
    try:
        for seed in (SEED, SEED + 1):
            env = Bench2HeadEnv(Bench2Config(seed=seed, extra_mjcf=live_camera_mjcf(Bench2Config())))
            env.reset(seed=seed)
            env.settle_at(90.0, 0.0)
            head, room = renderer.render(env, target_position=(1.5, 1.0, 1.0))
            assert head.shape == (96, 96, 3)
            assert room.shape == (400, 640, 3)
            env.close()
    finally:
        renderer.close()


@pytest.fixture
def view():
    live = LiveView(port=0)
    yield live
    live.close()


def _get(url: str, timeout: float = 5.0) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""


def test_page_state_and_reference_are_served(view):
    status, body = _get(view.url)
    assert status == 200 and "vue en direct" in body.decode("utf-8")

    view.update(experiment="C1", phase="exploration", pan_deg=np.float64(90.0))
    view.log("premier message")
    status, body = _get(view.url + "state")
    state = json.loads(body)
    assert status == 200
    assert state["phase"] == "exploration" and state["pan_deg"] == 90.0
    assert state["log"][-1].endswith("premier message")
    assert state["reference_version"] == 0

    assert _get(view.url + "reference.png")[0] == 404
    view.set_reference(np.zeros((96, 96, 3), dtype=np.uint8))
    status, body = _get(view.url + "reference.png")
    assert status == 200 and body.startswith(b"\x89PNG")


def test_streams_deliver_jpeg_frames(view):
    view.publish(np.zeros((96, 96, 3), dtype=np.uint8), np.zeros((400, 640, 3), dtype=np.uint8))
    for name in ("head", "room"):
        with urllib.request.urlopen(view.url + f"stream/{name}", timeout=5.0) as response:
            assert response.headers["Content-Type"].startswith("multipart/x-mixed-replace")
            chunk = response.read(256)
            assert b"--frame" in chunk and b"image/jpeg" in chunk and b"\xff\xd8" in chunk
