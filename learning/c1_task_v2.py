"""C1 version 2: the reference is rendered under the room's own lighting.

Version 1 of the margin probe was rejected on feasibility. Entry 3 of
docs/research/c1_journal.md traced its six failures to one mechanism -- the
designated object's hue landed in a different histogram bin in the reference than
it did in the scene -- and entry 4 pre-registered this correction before any code
here existed.

`learning/c1_task.py` is frozen by the v1 manifest, so this module extends it
instead of editing it: `C1EpisodeV2` changes the reference image and nothing
else, keeping every draw from the episode's generator in the same order so a
given seed builds the same room, the same placement and the same target.

The reference stays what it has to be -- one object on a neutral backdrop, at a
fixed distance, identical in every room -- because a reference carrying any of
the scene would let whole-image matching answer the task without appearance,
which is how REF-001 ended with baselines winning for a reason that meant
nothing. Only its illumination changes.
"""

from __future__ import annotations

import math

import numpy as np

from learning.c1_task import C1Config, C1Episode, _REFERENCE_DISTANCE
from sim3d import bench_model
from sim3d.bench2_env import release_renderer


def reference_image_v2(appearance, config: C1Config) -> np.ndarray:
    """The designated object alone, lit the way the room lights it.

    No free parameter: the headlight values and both lights are read from
    `BenchRoomConfig` and placed at their real world coordinates, and the object
    stands at the bench's own camera position. The room's lighting is fixed
    configuration rather than something the room seed draws, so this image is
    identical in every room -- the property that keeps the reference from
    encoding where anything is.
    """

    import mujoco

    size = config.image_size
    room = config.bench.room
    fovy = config.bench.sensors.camera_fovy_deg
    scale = 2.0 * _REFERENCE_DISTANCE * math.tan(math.radians(10.0) / 2.0)
    half = scale / 2.0
    rgba = " ".join(f"{c:.3f}" for c in appearance.rgba)

    bx, by = room.bench_position
    z = room.table_size[2] + bench_model.Z_PLATE_TOP + bench_model.Z_CAMERA
    position = f"{bx:.4f} {by:.4f} {z:.4f}"

    if appearance.kind == "box":
        body = f'<geom type="box" pos="{position}" size="{half:.4f} {half:.4f} {half:.4f}" rgba="{rgba}"/>'
    elif appearance.kind == "cylinder":
        body = f'<geom type="cylinder" pos="{position}" size="{half:.4f} {half:.4f}" rgba="{rgba}"/>'
    else:
        body = f'<geom type="sphere" pos="{position}" size="{half:.4f}" rgba="{rgba}"/>'

    ambient = " ".join(f"{v:.3f}" for v in room.headlight_ambient_rgb)
    diffuse = " ".join(f"{v:.3f}" for v in room.headlight_diffuse_rgb)
    primary = " ".join(f"{v:.3f}" for v in room.primary_light_rgb)
    secondary = " ".join(f"{v:.3f}" for v in room.secondary_light_rgb)

    xml = f"""
<mujoco model="c1_reference_v2">
  <visual><global offwidth="{size}" offheight="{size}"/>
    <headlight ambient="{ambient}" diffuse="{diffuse}"/></visual>
  <worldbody>
    <light name="room_key_light" pos="{room.width / 2:.3f} {room.depth / 2:.3f} 2.3" dir="0 0 -1" diffuse="{primary}"/>
    <light name="room_fill_light" pos="{bx:.3f} {by - 1.5:.3f} 2.2" dir="0 0.3 -1" diffuse="{secondary}"/>
    <geom name="backdrop" type="box" pos="{bx:.4f} {by + 0.45:.4f} {z:.4f}" size="1.2 0.01 1.2" rgba="0.55 0.55 0.57 1"/>
    {body}
    <camera name="ref_cam" pos="{bx:.4f} {by - _REFERENCE_DISTANCE:.4f} {z:.4f}" xyaxes="1 0 0 0 0 1" fovy="{fovy:.3f}"/>
  </worldbody>
</mujoco>
"""
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=size, width=size)
    try:
        renderer.update_scene(data, camera="ref_cam")
        return renderer.render()
    finally:
        release_renderer(renderer)


class C1EpisodeV2(C1Episode):
    """The frozen episode, designating with a room-lit reference."""

    def designate(self) -> np.ndarray:
        # Mirrors the parent exactly, including the draw from self.rng, so the
        # target of a given seed is the same object as in version 1.
        self._target = self.appearances[int(self.rng.integers(0, len(self.appearances)))]
        image = reference_image_v2(self._target, self.config)
        self._notify("designate", target=self._target.index, reference=image)
        return image
