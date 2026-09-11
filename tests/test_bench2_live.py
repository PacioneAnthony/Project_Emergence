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


# ------------------------------------------------------------------- charts

from scripts.research.c1_live import POLICIES, C1Charts, wilson  # noqa: E402


def test_wilson_is_honest_at_the_extremes():
    """Three out of three is not a certainty: the band must not collapse to 100 %."""

    low, high = wilson(3, 3)
    assert high == 1.0 and 0.40 < low < 0.45
    low, high = wilson(0, 10)
    assert low == 0.0 and 0.25 < high < 0.30
    assert wilson(0, 0) == (0.0, 1.0)


def test_interval_narrows_as_episodes_accumulate():
    widths = [wilson(n, n)[1] - wilson(n, n)[0] for n in (1, 5, 20, 100)]
    assert widths == sorted(widths, reverse=True)


def test_charts_collect_outcomes_per_policy():
    charts = C1Charts()
    charts.configure(chance=1 / 15, visibility_threshold=0.02)
    charts.add_result("oracle", 1, True, 22)
    charts.add_result("balayage", 2, False, 30)
    charts.add_result("oracle", 3, True, 22)
    data = charts.to_dict()
    assert [p["key"] for p in data["policies"]] == ["oracle", "balayage"]
    assert data["success"]["oracle"][-1][:2] == [3, 1.0]
    assert data["success"]["balayage"][-1][:2] == [2, 0.0]
    assert data["moves"]["balayage"] == [[2, 30]]
    assert data["chance"] == pytest.approx(1 / 15)


def test_a_policy_keeps_its_colour_whoever_else_is_on_the_chart():
    """Colour follows the entity: the oracle is not repainted when witnesses arrive."""

    alone = C1Charts()
    alone.add_result("oracle", 1, True, 22)
    crowded = C1Charts()
    crowded.add_result("dernier_angle", 1, False, 9)
    crowded.add_result("balayage", 1, True, 30)
    crowded.add_result("oracle", 1, True, 22)

    def slot(data, key):
        return next(p["slot"] for p in data["policies"] if p["key"] == key)

    oracle = list(POLICIES).index("oracle")
    assert slot(alone.to_dict(), "oracle") == slot(crowded.to_dict(), "oracle") == oracle
    assert len({p["slot"] for p in crowded.to_dict()["policies"]}) == 3


def test_health_series_are_capped_so_the_runner_can_go_all_night():
    charts = C1Charts()
    for _ in range(C1Charts.MAX_STOPS + 50):
        charts.add_stop(0.001)
    stops = charts.to_dict()["pointing"]
    assert len(stops) == C1Charts.MAX_STOPS
    assert stops[-1][0] == C1Charts.MAX_STOPS + 50


def test_page_carries_the_charts(view):
    body = _get(view.url)[1].decode("utf-8")
    assert "Au fil des épisodes" in body and "<!--charts-->" not in body
    for resource in ("charts.js", "charts.css"):
        status, data = _get(view.url + resource)
        assert status == 200 and len(data) > 500
    assert b"drawCharts" in _get(view.url + "charts.js")[1]


def test_the_viewer_following_a_new_world_does_not_blank_the_episode():
    """SceneRenderer drops its old renderers when the model changes; doing so must
    not blank the renderer of the env the episode goes on using."""

    renderer = SceneRenderer()
    first = Bench2HeadEnv(Bench2Config(seed=SEED, extra_mjcf=live_camera_mjcf(Bench2Config())))
    second = Bench2HeadEnv(Bench2Config(seed=SEED + 1, extra_mjcf=live_camera_mjcf(Bench2Config())))
    try:
        first.reset(seed=SEED)
        first.settle_at(90.0, 0.0)
        renderer.render(first)
        second.reset(seed=SEED + 1)
        second.settle_at(90.0, 0.0)
        before = second.render_camera(96, 96).copy()
        renderer.render(second)  # the viewer switches worlds and releases its old renderers
        assert np.array_equal(second.render_camera(96, 96), before)
    finally:
        renderer.close()
        first.close()
        second.close()
