"""Put content in every cell of the two-axis grid (D-060, step 2).

The frozen bench scatters its objects on the floor in front of the bench and its
wall panels at camera height, so the middle row of the view grid is rich and the
other two are not: looking up gives the top of the wall and the sky, looking down
gives the plain tabletop. Measured on five rooms, contrast falls from 46 at the
centre to 30 above and 26 below. A target placed outside the middle row would be
invisible, which is the feasibility fault that ended REF-002 and REF-003.

The frozen bench cannot be edited -- its bytes are the audit unit (D-061) -- but
`build_bench_mjcf` takes a `wall_panels` string of extra geoms, which is the hook
this module uses.

One placement rule for every row: an item sits where the cell's centre ray meets
the room -- the tabletop just in front of the head, the floor beyond it, or a
wall. An upward ray that clears the wall is slid down its face to the highest
point that exists. Items are sized by the angle they subtend, not in metres,
because a cell's surface can be 0.17 m or 3.7 m away.

Every claim here is checked by rendering an item and counting the pixels it
changes, not by trusting the geometry.

Distractors and targets are placed by the same rule and drawn from the same
shapes. Only appearance separates them: if merely *seeing something* identified a
target, the task would be solved without appearance at all, which is how REF-001
ended up with baselines winning for a reason that meant nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from sim3d import bench_model
from sim3d.bench2_model import X_BARREL, Bench2Config

WALL_MARGIN = 0.10  # keep panels below the wall's top edge
ANGULAR_SIZE_DEG = 10.0  # a third of the 30 degree field, in every cell
CAMERA_LENS_OFFSET = -X_BARREL  # lens sits this far in front of the tilt hinge


@dataclass(frozen=True)
class CellItem:
    """One thing placed in one cell."""

    pan_deg: float
    tilt_deg: float
    surface: str  # "floor" | "wall"
    position: tuple[float, float, float]
    rgba: tuple[float, float, float, float]
    kind: str  # "box" | "cylinder" | "sphere"
    scale: float


# ------------------------------------------------------------------- geometry


def camera_pose(config: Bench2Config, pan_deg: float, tilt_deg: float):
    """World position of the lens and its unit viewing direction, for a cell.

    Mirrors the MJCF exactly, including the 20 mm swing of the lens about the
    tilt hinge, so content lands where the camera actually looks rather than
    where a neck-axis approximation says it does.
    """

    room = config.room
    bx, by = room.bench_position
    base_z = room.table_size[2] + bench_model.Z_PLATE_TOP

    theta = math.radians(tilt_deg - config.tilt.neutral_deg)
    lens_x = X_BARREL + CAMERA_LENS_OFFSET * math.cos(theta)
    lens_z = bench_model.Z_CAMERA + CAMERA_LENS_OFFSET * math.sin(theta)

    heading = math.radians(pan_deg - 180.0)
    forward = np.array([math.cos(heading), math.sin(heading)])

    origin = np.array([bx + lens_x * forward[0], by + lens_x * forward[1], base_z + lens_z])
    direction = np.array(
        [math.cos(theta) * forward[0], math.cos(theta) * forward[1], math.sin(theta)]
    )
    return origin, direction


def cell_surface_hit(config: Bench2Config, pan_deg: float, tilt_deg: float):
    """Where a cell's centre ray meets the room: ("floor" | "wall", point).

    An upward ray that would pass over the wall is clamped to just under its top
    edge, so the cell still gets content instead of open sky.
    """

    room = config.room
    origin, direction = camera_pose(config, pan_deg, tilt_deg)

    candidates: list[tuple[float, str]] = []

    # The table the bench stands on is a surface like any other, and a downward
    # ray meets it long before it reaches the floor: 17 cm out, for a camera
    # 10 cm above the table looking down 30 degrees. Ignoring it put every
    # downward item behind the tabletop, invisible.
    table_lx, table_ly, table_h = room.table_size
    bx, by = room.bench_position
    if direction[2] < -1e-9:
        t_table = (table_h - origin[2]) / direction[2]
        if t_table > 1e-6:
            hit = origin + t_table * direction
            if abs(hit[0] - bx) <= table_lx / 2.0 and abs(hit[1] - by) <= table_ly / 2.0:
                candidates.append((t_table, "table"))
        candidates.append((-origin[2] / direction[2], "floor"))

    for axis, bound in ((0, 0.0), (0, room.width), (1, 0.0), (1, room.depth)):
        if abs(direction[axis]) > 1e-9:
            t = (bound - origin[axis]) / direction[axis]
            if t > 1e-6:
                candidates.append((t, "wall"))

    reachable = [(t, kind) for t, kind in candidates if t > 1e-6]
    if not reachable:
        raise RuntimeError(f"cell ({pan_deg}, {tilt_deg}) has no surface in the room")
    distance, surface = min(reachable)
    point = origin + distance * direction

    ceiling = room.wall_height - WALL_MARGIN
    if surface == "wall" and point[2] > ceiling:
        # The ray clears the wall's top edge. Keep the item flush on the wall it
        # would have hit and slide it down to the highest point that exists. The
        # elevation drops below the cell centre but stays inside the cell, which
        # the rendering check confirms rather than assumes.
        point = np.array([point[0], point[1], ceiling])
    return surface, point


def cell_elevation(config: Bench2Config, pan_deg: float, tilt_deg: float, point) -> float:
    """Elevation of a world point as seen from the cell's lens, in degrees."""

    origin, _ = camera_pose(config, pan_deg, tilt_deg)
    offset = np.asarray(point) - origin
    return math.degrees(math.atan2(offset[2], math.hypot(offset[0], offset[1])))


# ------------------------------------------------------------------- placement


def place_in_cell(
    config: Bench2Config,
    pan_deg: float,
    tilt_deg: float,
    rgba: tuple[float, float, float, float],
    kind: str = "box",
    angular_size_deg: float = ANGULAR_SIZE_DEG,
) -> CellItem:
    """An item centred on the cell, sitting on whatever surface the ray meets.

    Size is angular, not metric, so every item subtends the same fraction of the
    field wherever it stands. The surfaces a cell can reach are between 0.17 m
    and 3.7 m away: a single metric size would fill the whole view downward and
    be three pixels wide upward, and apparent size alone would then betray which
    row an item is in, before appearance says anything.
    """

    origin, _ = camera_pose(config, pan_deg, tilt_deg)
    surface, hit = cell_surface_hit(config, pan_deg, tilt_deg)
    half_angle = math.tan(math.radians(angular_size_deg) / 2.0)

    # An item standing on a surface has its centre half its own height above the
    # hit point, which on the tabletop 19 cm away moves it markedly closer to the
    # lens. Sizing from the distance to the *surface* therefore made downward
    # items much larger on screen than wall items, and apparent size alone then
    # told you which row an object was in. Solve for the size that the item's own
    # centre subtends; three passes are ample.
    point = np.asarray(hit, dtype=float)
    scale = 2.0 * float(np.linalg.norm(point - origin)) * half_angle
    for _ in range(3):
        if surface == "floor":
            point = np.array([hit[0], hit[1], scale / 2.0])
        elif surface == "table":
            point = np.array([hit[0], hit[1], config.room.table_size[2] + scale / 2.0])
        scale = 2.0 * float(np.linalg.norm(point - origin)) * half_angle
    return CellItem(
        pan_deg=float(pan_deg),
        tilt_deg=float(tilt_deg),
        surface=surface,
        position=(float(point[0]), float(point[1]), float(point[2])),
        rgba=rgba,
        kind=kind,
        scale=float(scale),
    )


def item_geom(name: str, item: CellItem, config: Bench2Config) -> str:
    """MJCF for one placed item. Wall items are panels angled toward the bench."""

    rgba = " ".join(f"{c:.3f}" for c in item.rgba)
    x, y, z = item.position
    half = item.scale / 2.0

    if item.surface == "wall":
        # Panels face the bench instead of lying flush on the wall. Flush panels
        # are seen edge-on at oblique bearings and shrink on screen, while items
        # on the tabletop are seen face-on: apparent size then said which row an
        # object was in, before appearance said anything. A sign angled toward
        # the observer is also what anyone mounting one would do.
        heading = math.radians(item.pan_deg - 180.0)
        rotation = heading - math.pi / 2.0
        standoff = 0.02
        px = x - standoff * math.cos(heading)
        py = y - standoff * math.sin(heading)
        return (
            f'    <geom name="{name}" type="box" pos="{px:.4f} {py:.4f} {z:.4f}"'
            f' size="{half:.4f} 0.0100 {half:.4f}" euler="0 0 {rotation:.6f}"'
            f' rgba="{rgba}" contype="0" conaffinity="0"/>\n'
        )

    if item.kind == "cylinder":
        return (
            f'    <geom name="{name}" type="cylinder" pos="{x:.4f} {y:.4f} {z:.4f}"'
            f' size="{half:.4f} {half:.4f}" rgba="{rgba}" contype="0" conaffinity="0"/>\n'
        )
    if item.kind == "sphere":
        return (
            f'    <geom name="{name}" type="sphere" pos="{x:.4f} {y:.4f} {z:.4f}"'
            f' size="{half:.4f}" rgba="{rgba}" contype="0" conaffinity="0"/>\n'
        )
    return (
        f'    <geom name="{name}" type="box" pos="{x:.4f} {y:.4f} {z:.4f}"'
        f' size="{half:.4f} {half:.4f} {half:.4f}" rgba="{rgba}" contype="0" conaffinity="0"/>\n'
    )


def items_mjcf(items: dict[str, CellItem], config: Bench2Config) -> str:
    return "".join(item_geom(name, item, config) for name, item in items.items())


# ----------------------------------------------------------- usable cells


def usable_cells(
    config: Bench2Config,
    seed: int,
    cells,
    image_size: int = 96,
    min_visible_fraction: float = 0.02,
    probe_rgba: tuple[float, float, float, float] = (0.95, 0.15, 0.15, 1.0),
) -> dict:
    """Which cells can actually show an object, measured by rendering one.

    The frozen room scatters solids up to 1.7 m tall in front of the bench, so a
    panel on the far wall can sit entirely behind one of them. An analytical
    visibility argument is not enough -- that is precisely what REF-003 proved,
    when objects provably inside the field turned out to be occluded. So a probe
    is placed in every cell and the pixels it changes are counted.

    Only the central half of the frame counts, so a probe in a neighbouring cell
    intruding at the edge cannot be mistaken for this cell's own.

    Returns {cell: visible_fraction}. This runs before any placement is drawn:
    it constructs a valid world, it never selects results after seeing them.
    """

    from sim3d.bench2_env import Bench2HeadEnv  # local: bench2_env imports this module

    cells = list(cells)
    probes = {
        f"usable_probe_{i}": place_in_cell(config, pan, tilt, probe_rgba)
        for i, (pan, tilt) in enumerate(cells)
    }
    lo, hi = image_size // 4, image_size - image_size // 4
    extra = getattr(config, "extra_mjcf", "")

    bare = Bench2HeadEnv(_with_extra(config, extra))
    probed = Bench2HeadEnv(_with_extra(config, extra + items_mjcf(probes, config)))
    try:
        bare.reset(seed=seed)
        probed.reset(seed=seed)
        result = {}
        for pan, tilt in cells:
            bare.settle_at(pan, tilt)
            probed.settle_at(pan, tilt)
            a = bare.render_camera(image_size, image_size).astype(np.float32)[lo:hi, lo:hi]
            b = probed.render_camera(image_size, image_size).astype(np.float32)[lo:hi, lo:hi]
            changed = (np.abs(a - b).sum(axis=2) > 25).mean()
            result[(pan, tilt)] = float(changed)
    finally:
        bare.close()
        probed.close()
    return {cell: fraction for cell, fraction in result.items()}


def _with_extra(config: Bench2Config, extra: str) -> Bench2Config:
    import dataclasses

    return dataclasses.replace(config, extra_mjcf=extra)
