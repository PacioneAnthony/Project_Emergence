"""Run C1 episodes and watch them live in a browser (D-060).

    python -m scripts.research.c1_live            # then open http://127.0.0.1:8765/

The head view is exactly what the agent receives; the room view shows where it is
looking and, once designated, the object it has to find. The page lays out the
fifteen cells, the phase in progress, commanded against real angles, and alerts
for anything that looks wrong -- a head that stops short of its cell, a state that
stops being finite.

By default the display runs at 0.3 times real time: the real servo turns at
600 degrees per second, which is too fast for the eye. `--speed 0` runs as fast
as the machine allows.

The answer in these episodes is given by the oracle, which knows the target's
cell. That is a demonstration of the task's lifecycle, not a policy -- the page
says so -- and the margin probe of step 3 is what will put the trivial baseline
and the oracle side by side.
"""

from __future__ import annotations

import argparse
import math
import time

import numpy as np

from learning.c1_task import PALETTE, C1Config, C1Episode
from sim3d.bench2_content import place_in_cell
from sim3d.bench2_live import LiveView, SceneRenderer, columns_as_seen, live_camera_mjcf
from sim3d.bench2_model import Bench2Config

NAMES = (
    "cube rouge", "cylindre bleu", "sphère jaune", "cube vert", "cylindre rose",
    "sphère cyan", "cube orange", "cylindre violet", "sphère vert clair", "cube brun",
)
POINTING_TOLERANCE_DEG = 0.5
FPS = 25.0


def _nearest(cells, pan: float, tilt: float):
    return min(cells, key=lambda c: (c[0] - pan) ** 2 + (c[1] - tilt) ** 2)


def _hex(rgba) -> str:
    return "#" + "".join(f"{int(round(c * 255)):02x}" for c in rgba[:3])


class C1LiveObserver:
    """Turns an episode's events into frames, state and log lines."""

    def __init__(self, view: LiveView, renderer: SceneRenderer, speed: float, pause: float):
        self.view = view
        self.renderer = renderer
        self.speed = float(speed)
        self.pause = float(pause)
        self.tally = {"episodes": 0, "successes": 0}
        self._sim_clock = 0.0
        self._wall_start: float | None = None
        self._last_frame = 0.0
        self._last_observation = None
        self._moved: set = set()
        self._alerts: list[str] = []
        self._gaze = None

    # ------------------------------------------------------------------ steps

    def on_step(self, episode: C1Episode, observation) -> None:
        self._last_observation = observation
        self._sim_clock += episode.config.bench.control_dt
        self._pace()
        if time.monotonic() - self._last_frame >= 1.0 / FPS:
            self._frame(episode)

    def _pace(self) -> None:
        if self.speed <= 0:
            return
        now = time.monotonic()
        if self._wall_start is None:
            self._wall_start = now - self._sim_clock / self.speed
        delay = self._wall_start + self._sim_clock / self.speed - now
        if delay > 0:
            time.sleep(delay)
        elif delay < -0.5:
            # Fell behind -- rendering is slower than the requested speed. Resync
            # instead of rushing through the backlog.
            self._wall_start = now - self._sim_clock / self.speed

    def _hold(self, seconds: float) -> None:
        if seconds <= 0:
            return
        time.sleep(seconds)
        if self._wall_start is not None:
            self._wall_start += seconds

    def _frame(self, episode: C1Episode) -> None:
        head, room = self.renderer.render(episode.env, self._target_position(episode))
        self.view.publish(head, room)
        env = episode.env
        fields = {
            "pan_deg": env.servo_angle_deg(),
            "tilt_deg": env.tilt_angle_deg(),
            "moves": episode.moves,
            "sim_time": self._sim_clock,
            "speed": self.speed,
        }
        if self._last_observation is not None:
            fields["pan_cmd"] = self._last_observation.requested_pan_deg
            fields["tilt_cmd"] = self._last_observation.requested_tilt_deg
        # The white frame follows the head's real angle, frame by frame. Moving it
        # only when a cell was reached left it one cell behind for the whole of
        # every settle, which reads as the head looking somewhere it is not.
        gaze = _nearest(episode.cells, fields["pan_deg"], fields["tilt_deg"])
        if gaze != self._gaze:
            self._gaze = gaze
            fields["grid"] = self._grid(episode)
        self.view.update(**fields)
        self._last_frame = time.monotonic()

    @staticmethod
    def _target_position(episode: C1Episode):
        try:
            pan, tilt = episode.target_cell
        except RuntimeError:
            return None
        return place_in_cell(episode.config.bench, pan, tilt, (1.0, 1.0, 1.0, 1.0)).position

    # ----------------------------------------------------------------- phases

    def on_phase(self, episode: C1Episode, phase: str, info: dict) -> None:
        handler = getattr(self, f"_on_{phase}", None)
        if handler is not None:
            handler(episode, info)

    def _on_setup(self, episode, info) -> None:
        self._moved = set()
        self._alerts = []
        self._gaze = None
        worst = min(episode.object_visibility.values())
        self.view.update(
            experiment="C1",
            episode=self.tally["episodes"] + 1,
            seed=episode.seed,
            phase="setup",
            phase_label="Pièce prête — chaque objet a été vérifié visible avant de commencer",
            grid=self._grid(episode),
            visibility_min=worst,
            target=None,
            result=None,
            alerts=[],
            pointing_error_deg=None,
        )
        self.view.set_reference(None)
        self.view.log(
            f"Pièce {episode.seed} prête : {len(episode.usable)}/{len(episode.cells)} cellules "
            f"utilisables, {len(episode.placement)} objets placés, objet le moins visible à "
            f"{worst * 100:.1f} % de la vue centrale."
        )
        self._frame(episode)
        self._hold(self.pause * 0.6)

    def _on_exploration(self, episode, info) -> None:
        self.view.update(
            phase="exploration",
            phase_label="Exploration — la tête balaie les quinze cellules et voit ce qui s'y trouve",
        )
        self.view.log("Exploration : balayage des quinze cellules.")

    def _on_look(self, episode, info) -> None:
        pan, tilt = info["cell"]
        env = episode.env
        error = max(abs(env.servo_angle_deg() - pan), abs(env.tilt_angle_deg() - tilt))
        self._gaze = (pan, tilt)
        fields = {"pointing_error_deg": error, "grid": self._grid(episode)}
        if error > POINTING_TOLERANCE_DEG:
            self._alert(f"écart de pointage de {error:.2f}° sur la cellule ({pan:g}, {tilt:+g})")
        if not (np.isfinite(env.data.qpos).all() and np.isfinite(env.data.qvel).all()):
            self._alert("état de la simulation non fini (NaN ou infini)")
        fields["alerts"] = list(self._alerts)
        self.view.update(**fields)
        self._frame(episode)

    def _on_delay(self, episode, info) -> None:
        self.view.update(
            phase="delay",
            phase_label="Délai — mouvements parasites ; les objets peuvent être déplacés pendant ce temps",
        )
        self.view.log(f"Délai : {episode.config.delay_moves} mouvements parasites.")

    def _on_shuffle(self, episode, info) -> None:
        before, after = info["before"], info["after"]
        moved = [i for i in before if before[i] != after[i]]
        self._moved = {after[i] for i in moved}
        self.view.update(
            phase="shuffle",
            phase_label="Brassage — des objets ont changé de cellule pendant le délai",
            grid=self._grid(episode),
        )
        self.view.log(
            f"Brassage : {len(moved)} objet(s) déplacé(s) — "
            + ", ".join(f"{NAMES[i]} {self._cell(before[i])} → {self._cell(after[i])}" for i in moved)
        )
        self._frame(episode)
        self._hold(self.pause)

    def _on_designate(self, episode, info) -> None:
        index = info["target"]
        cell = episode.placement[index]
        self.view.set_reference(info["reference"])
        self.view.update(
            phase="designate",
            phase_label="Désignation — l'image de référence désigne l'objet à retrouver",
            target={"index": index, "label": NAMES[index], "cell": list(cell)},
            grid=self._grid(episode),
        )
        self.view.log(
            f"Cible : {NAMES[index]}, en cellule {self._cell(cell)} "
            "(vérité terrain, que l'agent ne voit pas)."
        )
        self._frame(episode)
        self._hold(self.pause * 1.5)

    def _on_answer(self, episode, info) -> None:
        result = info["result"]
        self.tally["episodes"] += 1
        self.tally["successes"] += int(result.success)
        self.view.update(
            phase="answer",
            result={
                "success": result.success,
                "answered": list(result.answered_cell),
                "target": list(result.target_cell),
                "moves": result.moves,
                "moved": result.moved_between_visits,
            },
            tally=dict(self.tally),
        )
        self.view.log(
            f"Réponse : cellule {self._cell(result.answered_cell)} — "
            f"{'succès' if result.success else 'échec'}, {result.moves} mouvements"
            f"{', objets déplacés entre les visites' if result.moved_between_visits else ''}."
        )
        self._frame(episode)
        self._hold(self.pause * 1.5)

    # ---------------------------------------------------------------- helpers

    def _alert(self, message: str) -> None:
        if message not in self._alerts:
            self._alerts.append(message)
            self.view.log(f"ALERTE : {message}")

    @staticmethod
    def _cell(cell) -> str:
        return f"({cell[0]:g}, {cell[1]:+g})"

    def _grid(self, episode: C1Episode) -> dict:
        pans = sorted({pan for pan, _ in episode.cells})
        tilts = sorted({tilt for _, tilt in episode.cells}, reverse=True)
        occupied = episode.occupied_cells()
        cells = []
        for pan, tilt in episode.cells:
            index = occupied.get((pan, tilt))
            cells.append({
                "pan": pan,
                "tilt": tilt,
                "usable": (pan, tilt) in episode.usable,
                "color": _hex(PALETTE[index][1]) if index is not None else None,
                "kind": PALETTE[index][0] if index is not None else None,
                "moved": (pan, tilt) in self._moved,
            })
        try:
            target = list(episode.target_cell)
        except RuntimeError:
            target = None
        return {
            "cols": columns_as_seen(pans),
            "rows": tilts,
            "cells": cells,
            "gaze": list(self._gaze) if self._gaze is not None else None,
            "target": target,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seed", type=int, default=100, help="first room; each episode uses the next")
    parser.add_argument("--episodes", type=int, default=0, help="0 runs until interrupted")
    parser.add_argument("--objects", type=int, default=8)
    parser.add_argument("--shuffle", type=float, default=0.5, help="probability that objects move during the delay")
    parser.add_argument("--speed", type=float, default=0.3, help="display speed as a multiple of real time; 0 = flat out")
    parser.add_argument("--pause", type=float, default=1.2, help="seconds held on each phase change")
    args = parser.parse_args()

    view = LiveView(port=args.port)
    print(f"Vue en direct : {view.url}", flush=True)
    bench = Bench2Config()
    bench = Bench2Config(extra_mjcf=live_camera_mjcf(bench))
    renderer = SceneRenderer(head_size=C1Config().image_size)
    observer = C1LiveObserver(view, renderer, speed=args.speed, pause=args.pause)

    count = 0
    try:
        while args.episodes <= 0 or count < args.episodes:
            seed = args.seed + count
            count += 1
            view.update(
                experiment="C1",
                episode=observer.tally["episodes"] + 1,
                seed=seed,
                phase="preparation",
                phase_label=f"Préparation de la pièce {seed} — vérification que chaque objet sera visible",
            )
            config = C1Config(object_count=args.objects, shuffle_probability=args.shuffle, bench=bench)
            try:
                episode = C1Episode(config, seed=seed, observer=observer)
            except RuntimeError as exc:
                view.log(f"Pièce {seed} écartée avant de commencer : {exc}")
                continue
            with episode:
                for _ in episode.exploration():
                    pass
                episode.delay()
                episode.designate()
                view.update(
                    phase_label="Réponse — donnée ici par l'oracle, qui connaît la cellule : "
                    "démonstration du déroulé, pas une politique"
                )
                target = episode.target_cell
                episode.look_at(*target)
                episode.answer(*target)
        if args.episodes > 0:
            view.update(phase="done", phase_label=f"Terminé — {count} épisode(s). Ctrl+C pour arrêter le serveur.")
            while True:
                time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        renderer.close()
        view.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
