"""C1 and the cell content it stands on (D-060, step 2).

The tests that matter here are the ones that would have caught the faults this
task was built against: an object that cannot be seen, and a cue that answers the
question without appearance.
"""

from __future__ import annotations

import numpy as np
import pytest

from learning.c1_task import PALETTE, Appearance, C1Config, C1Episode, reference_image
from sim3d.bench2_content import (
    ANGULAR_SIZE_DEG,
    camera_pose,
    cell_elevation,
    cell_surface_hit,
    items_mjcf,
    place_in_cell,
    usable_cells,
)
from sim3d.bench2_env import Bench2HeadEnv
from sim3d.bench2_model import Bench2Config, view_cells

SEED = 21


@pytest.fixture(scope="module")
def episode():
    ep = C1Episode(C1Config(object_count=8, shuffle_probability=0.0), seed=SEED)
    yield ep
    ep.close()


# ------------------------------------------------------------------ placement


def test_downward_rays_land_on_the_table_not_the_floor():
    """The bench stands on a table; a downward ray meets it 19 cm out."""

    config = Bench2Config()
    surface, point = cell_surface_hit(config, 90.0, -30.0)
    assert surface == "table"
    assert point[2] == pytest.approx(config.room.table_size[2], abs=1e-6)


def test_level_and_upward_rays_land_on_a_wall():
    config = Bench2Config()
    for tilt in (0.0, 30.0):
        surface, _ = cell_surface_hit(config, 90.0, tilt)
        assert surface == "wall"


def test_upward_item_stays_inside_its_cell_even_when_the_ray_clears_the_wall():
    """Central bearings look over the wall; the item slides down, not out."""

    config = Bench2Config()
    fov = config.sensors.camera_fovy_deg
    for pan in (60.0, 90.0, 120.0):
        _, point = cell_surface_hit(config, pan, 30.0)
        assert point[2] <= config.room.wall_height
        elevation = cell_elevation(config, pan, 30.0, point)
        assert abs(elevation - 30.0) <= fov / 2.0, f"pan {pan} elevation {elevation}"


def test_items_are_sized_by_angle_not_by_metres():
    """A cell's surface is 0.19 m away downward and 3.5 m away upward."""

    config = Bench2Config()
    near = place_in_cell(config, 90.0, -30.0, (1.0, 0, 0, 1))
    far = place_in_cell(config, 90.0, 30.0, (1.0, 0, 0, 1))
    assert near.scale < far.scale / 5.0
    for item in (near, far):
        origin, _ = camera_pose(config, item.pan_deg, item.tilt_deg)
        distance = float(np.linalg.norm(np.asarray(item.position) - origin))
        subtended = 2.0 * np.degrees(np.arctan(item.scale / 2.0 / distance))
        assert subtended == pytest.approx(ANGULAR_SIZE_DEG, abs=1.0)


def test_placed_items_produce_loadable_mjcf():
    config = Bench2Config()
    items = {
        f"item_{i}": place_in_cell(config, pan, tilt, (0.9, 0.2, 0.2, 1.0))
        for i, (pan, tilt) in enumerate(view_cells(config))
    }
    env = Bench2HeadEnv(Bench2Config(seed=SEED, extra_mjcf=items_mjcf(items, config)))
    try:
        env.reset(seed=SEED)
        assert env.model is not None
    finally:
        env.close()


def test_most_cells_can_show_an_object():
    config = Bench2Config()
    fractions = usable_cells(config, SEED, view_cells(config))
    assert len(fractions) == 15
    assert sum(1 for v in fractions.values() if v >= 0.02) >= 13


# ------------------------------------------------------------------- episode


def test_every_placed_object_is_actually_visible(episode):
    """The guard that REF-003 lacked: measured where the object really stands."""

    assert len(episode.placement) == episode.config.object_count
    assert len(set(episode.placement.values())) == episode.config.object_count
    worst = min(episode.object_visibility.values())
    assert worst >= episode.config.min_visible_fraction


def test_objects_only_go_in_cells_that_can_show_them(episode):
    for cell in episode.placement.values():
        assert cell in episode.usable


def test_some_cells_are_left_empty(episode):
    """Seeing nothing has to be informative too, or presence answers the task."""

    assert len(episode.placement) < len(episode.cells)


def test_exploration_visits_every_cell():
    with C1Episode(C1Config(object_count=8, shuffle_probability=0.0), seed=SEED) as ep:
        visited = [cell for cell, _, _ in ep.exploration()]
        assert sorted(visited) == sorted(ep.cells)


def test_answering_the_target_cell_succeeds_and_another_fails():
    with C1Episode(C1Config(object_count=8, shuffle_probability=0.0), seed=SEED) as ep:
        list(ep.exploration())
        ep.delay()
        ep.designate()
        target = ep.target_cell
        assert ep.answer(*target).success
        other = next(c for c in ep.cells if c != target)
        assert not ep.answer(*other).success


def test_target_cell_is_unavailable_before_designation():
    with C1Episode(C1Config(object_count=8), seed=SEED) as ep:
        with pytest.raises(RuntimeError):
            _ = ep.target_cell


def test_objects_move_between_visits_when_asked():
    with C1Episode(C1Config(object_count=8, shuffle_probability=1.0), seed=SEED) as ep:
        before = dict(ep.placement)
        list(ep.exploration())
        ep.delay()
        assert ep.moved_between_visits
        assert any(before[k] != ep.placement[k] for k in before)


def test_objects_stay_put_when_not_asked():
    with C1Episode(C1Config(object_count=8, shuffle_probability=0.0), seed=SEED) as ep:
        before = dict(ep.placement)
        list(ep.exploration())
        ep.delay()
        assert not ep.moved_between_visits
        assert before == ep.placement


# ----------------------------------------------------------------- the cue


def test_reference_images_tell_appearances_apart():
    config = C1Config(object_count=8)
    images = [reference_image(Appearance(i, *PALETTE[i]), config).astype(np.float32) for i in range(8)]
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            assert np.abs(images[i] - images[j]).mean() > 1.0


def test_the_reference_says_nothing_about_where_the_object_is():
    """Same appearance, different rooms and cells: the reference must not move.

    If it carried any of the scene, whole-image matching would answer the task
    without appearance -- the way REF-001's pixel baselines won for nothing.
    """

    config = C1Config(object_count=8)
    appearance = Appearance(3, *PALETTE[3])
    first = reference_image(appearance, config)
    second = reference_image(appearance, config)
    assert np.array_equal(first, second)

    with C1Episode(config, seed=SEED) as a, C1Episode(config, seed=SEED + 7) as b:
        assert a.placement[3] != b.placement[3] or a.usable != b.usable
        assert np.array_equal(
            reference_image(appearance, a.config), reference_image(appearance, b.config)
        )


def test_a_room_with_too_few_usable_cells_is_refused():
    config = C1Config(object_count=8, min_visible_fraction=0.99)
    with pytest.raises(RuntimeError, match="usable cells"):
        C1Episode(config, seed=SEED)
