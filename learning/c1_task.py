"""C1 -- find an object designated by its appearance (D-060, step 2).

An episode has three phases. During **exploration** the head sweeps the grid and
sees whatever stands in each cell. A **delay** is then filled with other
movements. Finally a **reference image** designates one object and the head must
end up pointing at the cell holding it.

Three decisions keep the task from being solvable for the wrong reason.

*The reference is rendered on a neutral backdrop*, not cropped from the scene. A
reference taken from the scene would carry the background with it, and matching
whole images would solve the task without appearance ever being used -- which is
how REF-001 ended with baselines winning for a reason that meant nothing.

*Every object is a distractor for every other one.* There is no separate
distractor class marked differently: the object designated at probe time is one
of the same set, so "something is here" narrows the search without answering it.
Cells are deliberately left empty so that seeing nothing is informative too.

*Objects may move between visits*, with probability `shuffle_probability`. A
policy that only memorises where things were is therefore right sometimes and
wrong sometimes, which is what separates it from one that looks and checks. This
is the point of the task, not a nuisance.

This module builds the task and scores it. It contains no mechanism, no learning
and no preregistration: the margin probe of step 3 is what decides whether
anything gets built on top of it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from sim3d import bench_model
from sim3d.bench2_content import items_mjcf, place_in_cell, usable_cells
from sim3d.bench2_env import Bench2HeadEnv
from sim3d.bench2_model import Bench2Config, view_cells

# Saturated, well separated hues. Appearance is (shape, colour): the palette is
# large enough that no two objects in an episode look alike.
PALETTE: tuple[tuple[str, tuple[float, float, float, float]], ...] = (
    ("box", (0.90, 0.10, 0.10, 1.0)),
    ("cylinder", (0.10, 0.45, 0.90, 1.0)),
    ("sphere", (0.95, 0.75, 0.05, 1.0)),
    ("box", (0.10, 0.70, 0.25, 1.0)),
    ("cylinder", (0.85, 0.35, 0.85, 1.0)),
    ("sphere", (0.05, 0.75, 0.75, 1.0)),
    ("box", (0.95, 0.50, 0.10, 1.0)),
    ("cylinder", (0.35, 0.15, 0.65, 1.0)),
    ("sphere", (0.55, 0.90, 0.20, 1.0)),
    ("box", (0.60, 0.30, 0.10, 1.0)),
)


@dataclass(frozen=True)
class Appearance:
    index: int
    kind: str
    rgba: tuple[float, float, float, float]


@dataclass
class C1Config:
    object_count: int = 8
    shuffle_probability: float = 0.5
    image_size: int = 96
    exploration_order: str = "raster"  # "raster" | "random"
    delay_moves: int = 6
    min_visible_fraction: float = 0.02
    max_placement_attempts: int = 12
    bench: Bench2Config = field(default_factory=Bench2Config)

    def __post_init__(self) -> None:
        if self.object_count > len(PALETTE):
            raise ValueError(f"at most {len(PALETTE)} distinct appearances are available")
        if self.object_count > len(view_cells(self.bench)):
            raise ValueError("more objects than cells")


@dataclass
class C1Result:
    success: bool
    answered_cell: tuple[float, float]
    target_cell: tuple[float, float]
    moves: int
    moved_between_visits: bool


class C1Episode:
    """One episode. Build it, explore, delay, then answer."""

    def __init__(self, config: C1Config | None = None, seed: int = 0, observer=None):
        self.config = config or C1Config()
        self.seed = int(seed)
        # Anything with on_phase(episode, phase, info) and on_step(episode,
        # observation) -- the live viewer is one. It watches the episode's own
        # world only, never the hidden renders used to verify visibility.
        self.observer = observer
        self.rng = np.random.default_rng(self.seed)
        self.cells = view_cells(self.config.bench)

        self.appearances = [
            Appearance(index=i, kind=PALETTE[i][0], rgba=PALETTE[i][1])
            for i in range(self.config.object_count)
        ]

        # What this room looks like with none of C1's objects in it. Every
        # visibility claim below is measured against these frames.
        self._bare = self._bare_frames()

        # A generic probe in every cell finds the ones the room's own solids
        # occlude -- about one per room, since the frozen room scatters objects
        # up to 1.7 m tall in front of the bench.
        self.visibility = usable_cells(
            self.config.bench, self.seed, self.cells, image_size=self.config.image_size
        )
        self.usable = [c for c, v in self.visibility.items() if v >= self.config.min_visible_fraction]
        if len(self.usable) < self.config.object_count:
            raise RuntimeError(
                f"room {self.seed} shows only {len(self.usable)} usable cells for "
                f"{self.config.object_count} objects"
            )

        self.moved_between_visits = False
        self._target: Appearance | None = None
        self.moves = 0
        self.env = None
        self.placement, self.object_visibility = self._place_and_verify()
        self._attach(self.env)
        self._notify("setup")

    # ------------------------------------------------------------------ world

    def _draw_placement(self) -> dict[int, tuple[float, float]]:
        """One usable cell per object, all distinct; the rest stay empty."""

        chosen = self.rng.choice(len(self.usable), size=self.config.object_count, replace=False)
        return {a.index: self.usable[int(c)] for a, c in zip(self.appearances, chosen)}

    def _bench_config(self, placement: dict[int, tuple[float, float]]) -> Bench2Config:
        base = self.config.bench
        items = {}
        for appearance in self.appearances:
            pan, tilt = placement[appearance.index]
            items[f"c1_object_{appearance.index}"] = place_in_cell(
                base, pan, tilt, appearance.rgba, kind=appearance.kind
            )
        return Bench2Config(
            physics_timestep=base.physics_timestep,
            control_dt=base.control_dt,
            servo=base.servo,
            sensors=base.sensors,
            room=base.room,
            seed=base.seed if base.seed is not None else self.seed,
            randomize_room=base.randomize_room,
            tilt=base.tilt,
            # Keep whatever the caller already put in the bench -- a camera for
            # the live view, say. Dropping it made that content vanish from the
            # episode's world while still being present in the bare frames.
            extra_mjcf=(base.extra_mjcf or "") + items_mjcf(items, base),
        )

    def _rebuild(self, placement: dict[int, tuple[float, float]]) -> None:
        """Swap the world, keeping the head exactly where it is."""

        pan, tilt = self.env.servo_angle_deg(), self.env.tilt_angle_deg()
        self.env.close()
        self.env = Bench2HeadEnv(self._bench_config(placement))
        self.env.reset(seed=self.seed)
        self._attach(self.env)
        self.env.settle_at(pan, tilt)

    # ------------------------------------------------------- visibility guard

    def _bare_frames(self) -> dict[tuple[float, float], np.ndarray]:
        size = self.config.image_size
        env = Bench2HeadEnv(self.config.bench)
        try:
            env.reset(seed=self.seed)
            frames = {}
            for pan, tilt in self.cells:
                env.settle_at(pan, tilt)
                frames[(pan, tilt)] = env.render_camera(size, size).astype(np.float32)
            return frames
        finally:
            env.close()

    def _measure(self, placement) -> tuple[dict[int, float], Bench2HeadEnv]:
        """How much of its own cell each placed object actually changes."""

        size = self.config.image_size
        lo, hi = size // 4, size - size // 4
        env = Bench2HeadEnv(self._bench_config(placement))
        env.reset(seed=self.seed)
        seen = {}
        for appearance in self.appearances:
            cell = placement[appearance.index]
            env.settle_at(*cell)
            frame = env.render_camera(size, size).astype(np.float32)[lo:hi, lo:hi]
            reference = self._bare[cell][lo:hi, lo:hi]
            seen[appearance.index] = float(
                (np.abs(frame - reference).sum(axis=2) > 25).mean()
            )
        return seen, env

    def _place_and_verify(self):
        """Draw a placement in which every object is genuinely visible.

        A cell that passes the generic probe can still hide a particular object:
        the probe tests occlusion, and a dark cylinder against a dark wall fails
        on local contrast instead. REF-003 died of exactly this distinction --
        objects provably inside the field, with no usable contrast -- so each
        object is measured where it actually stands, and any that disappears is
        moved to a free cell before the episode starts. This builds a valid
        world; it never re-rolls after seeing a result.
        """

        placement = self._draw_placement()
        for _ in range(self.config.max_placement_attempts):
            seen, env = self._measure(placement)
            failed = [i for i, v in seen.items() if v < self.config.min_visible_fraction]
            if not failed:
                self.env = env
                return placement, seen
            env.close()
            free = [c for c in self.usable if c not in placement.values()]
            if len(free) < len(failed):
                break
            picks = self.rng.choice(len(free), size=len(failed), replace=False)
            for index, pick in zip(failed, picks):
                placement[index] = free[int(pick)]
        raise RuntimeError(
            f"room {self.seed}: no placement makes all {self.config.object_count} objects "
            f"visible after {self.config.max_placement_attempts} attempts"
        )

    # ----------------------------------------------------------------- phases

    def exploration(self):
        """Visit every cell once. Yields (cell, image, proprioception)."""

        order = list(self.cells)
        if self.config.exploration_order == "random":
            order = [order[i] for i in self.rng.permutation(len(order))]
        self._notify("exploration")
        for pan, tilt in order:
            observation = self.env.settle_at(pan, tilt)
            self.moves += 1
            self._notify("look", cell=(pan, tilt))
            yield (pan, tilt), self._render(), observation.proprioception()

    def delay(self):
        """Fill time with other movements, and possibly move the objects."""

        self._notify("delay")
        for _ in range(self.config.delay_moves):
            pan, tilt = self.cells[int(self.rng.integers(0, len(self.cells)))]
            self.env.settle_at(pan, tilt)
            self.moves += 1
            self._notify("look", cell=(pan, tilt))
        if self.rng.random() < self.config.shuffle_probability:
            before = dict(self.placement)
            self.placement = self._draw_placement()
            self.moved_between_visits = True
            self._rebuild(self.placement)
            self._notify("shuffle", before=before, after=dict(self.placement))

    def designate(self) -> np.ndarray:
        """Pick the object to find and return its reference image."""

        self._target = self.appearances[int(self.rng.integers(0, len(self.appearances)))]
        image = reference_image(self._target, self.config)
        self._notify("designate", target=self._target.index, reference=image)
        return image

    # --------------------------------------------------------------- policy API

    def look_at(self, pan_deg: float, tilt_deg: float) -> np.ndarray:
        self.env.settle_at(float(pan_deg), float(tilt_deg))
        self.moves += 1
        self._notify("look", cell=_nearest_cell(self.cells, pan_deg, tilt_deg))
        return self._render()

    def answer(self, pan_deg: float, tilt_deg: float) -> C1Result:
        if self._target is None:
            raise RuntimeError("designate() must be called before answer()")
        answered = _nearest_cell(self.cells, pan_deg, tilt_deg)
        target = self.placement[self._target.index]
        result = C1Result(
            success=answered == target,
            answered_cell=answered,
            target_cell=target,
            moves=self.moves,
            moved_between_visits=self.moved_between_visits,
        )
        self._notify("answer", result=result)
        return result

    @property
    def target_cell(self) -> tuple[float, float]:
        """Ground truth. For the oracle and for scoring only -- never for a policy."""

        if self._target is None:
            raise RuntimeError("designate() must be called first")
        return self.placement[self._target.index]

    def occupied_cells(self) -> dict[tuple[float, float], int]:
        return {cell: index for index, cell in self.placement.items()}

    # ---------------------------------------------------------------- plumbing

    def _attach(self, env) -> None:
        if self.observer is not None:
            env.step_callbacks.append(lambda observation: self.observer.on_step(self, observation))

    def _notify(self, phase: str, **info) -> None:
        if self.observer is not None:
            self.observer.on_phase(self, phase, info)

    def _render(self) -> np.ndarray:
        size = self.config.image_size
        return self.env.render_camera(size, size)

    def close(self) -> None:
        self.env.close()

    def __enter__(self) -> "C1Episode":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _nearest_cell(cells, pan_deg: float, tilt_deg: float) -> tuple[float, float]:
    return min(cells, key=lambda c: (c[0] - pan_deg) ** 2 + (c[1] - tilt_deg) ** 2)


# --------------------------------------------------------------- the reference

_REFERENCE_DISTANCE = 1.0


def reference_image(appearance: Appearance, config: C1Config) -> np.ndarray:
    """The designated object alone, on a neutral backdrop.

    Deliberately not a crop of the scene: a reference carrying its background
    would let whole-image matching answer the question without appearance.
    """

    import mujoco

    size = config.image_size
    fovy = config.bench.sensors.camera_fovy_deg
    scale = 2.0 * _REFERENCE_DISTANCE * math.tan(math.radians(10.0) / 2.0)
    rgba = " ".join(f"{c:.3f}" for c in appearance.rgba)
    half = scale / 2.0
    if appearance.kind == "box":
        body = f'<geom type="box" pos="0 0 0" size="{half:.4f} {half:.4f} {half:.4f}" rgba="{rgba}"/>'
    elif appearance.kind == "cylinder":
        body = f'<geom type="cylinder" pos="0 0 0" size="{half:.4f} {half:.4f}" rgba="{rgba}"/>'
    else:
        body = f'<geom type="sphere" pos="0 0 0" size="{half:.4f}" rgba="{rgba}"/>'

    xml = f"""
<mujoco model="c1_reference">
  <visual><global offwidth="{size}" offheight="{size}"/>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.65 0.65 0.65"/></visual>
  <worldbody>
    <light name="key" pos="0 -0.6 1.2" dir="0 0.4 -1" diffuse="0.7 0.7 0.7"/>
    <geom name="backdrop" type="box" pos="0 0.45 0" size="1.2 0.01 1.2" rgba="0.55 0.55 0.57 1"/>
    {body}
    <camera name="ref_cam" pos="0 {-_REFERENCE_DISTANCE:.4f} 0" xyaxes="1 0 0 0 0 1" fovy="{fovy:.3f}"/>
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
        renderer.close()


def bench_defaults() -> Bench2Config:
    """The bench C1 runs on, exposed so a probe can report what it measured."""

    return Bench2Config(room=bench_model.BenchRoomConfig())
