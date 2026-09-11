"""Watch a two-axis bench episode live, in a browser (D-060).

Two things are hard to see from numbers alone: what the head is actually looking
at, and whether the simulated world is doing something absurd. Three faults found
while building C1 -- objects hidden behind the tabletop, wall panels seen edge-on,
spheres buried under the table -- were invisible in the code and obvious the
moment an image was rendered. This module makes that looking continuous.

It serves one local page with two live streams and the experiment's state:

* the head view, at exactly the resolution the agent receives, upscaled without
  smoothing so that every pixel on screen is one of the agent's pixels;
* the room seen from behind the robot, with the gaze drawn into the scene: a red
  axis stopped on the first surface it meets, orange rays along the edges of the
  30 degree field, and a gold marker over the object to find once one is
  designated.

The viewer watches and never changes. It renders from the episode's own MjData
without stepping it or calling mj_forward, and draws nothing from the episode's
random generator, so a run with the viewer attached yields the same images and
the same results as a run without it -- a test pins this. The overview camera it
adds to the room changes no pixel of the head view, which is measured too.

Orientation. The robot faces -y. Its right is world -x, and a *small* pan value
turns it to its right: that is measured by placing a marker on either side of
the head. The overview camera's right is also world -x, so the room view, the
head view and the grid on the page all read the same way round -- the robot's
left on the left.
"""

from __future__ import annotations

import collections
import io
import json
import math
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mujoco
import numpy as np
from PIL import Image

from sim3d import bench_model
from sim3d.bench2_model import Bench2Config

OVERVIEW_CAMERA = "live_overview"
OVERVIEW_RIGHT = np.array([-1.0, 0.0, 0.0])
HEAD_UPSCALE = 4


def live_camera_mjcf(config: Bench2Config) -> str:
    """A camera behind and above the bench, looking over the head into the room."""

    room = config.room
    bx, by = room.bench_position
    y = min(by + 0.7, room.depth - 0.1)
    z = room.table_size[2] + 1.08
    return (
        f'    <camera name="{OVERVIEW_CAMERA}" pos="{bx:.4f} {y:.4f} {z:.4f}" '
        'xyaxes="-1 0 0 0 -0.4600 0.8880" fovy="70"/>\n'
    )


def columns_as_seen(pans) -> list[float]:
    """Pan values ordered left to right as the robot sees them.

    A cell's bearing is projected onto the overview camera's right vector, so
    the order follows from the same geometry that draws the room view.
    """

    def screen_x(pan: float) -> float:
        heading = math.radians(pan - 180.0)
        return float(np.dot([math.cos(heading), math.sin(heading), 0.0], OVERVIEW_RIGHT))

    return sorted(pans, key=screen_x)


# ------------------------------------------------------------------ rendering


class SceneRenderer:
    """Renders the head view and the annotated room view from a live env."""

    def __init__(self, head_size: int = 96, room_size: tuple[int, int] = (640, 400)):
        self.head_size = int(head_size)
        self.room_size = room_size
        self._model = None
        self._head = None
        self._room = None

    def _ensure(self, env) -> None:
        if env.model is self._model:
            return
        self.close()
        model = env.model
        self._model = model
        self._head = mujoco.Renderer(model, height=self.head_size, width=self.head_size)
        width, height = self.room_size
        self._room = mujoco.Renderer(model, height=height, width=width)
        self._head_cam = model.camera(bench_model.CAMERA_HEAD).id
        self._head_body = model.body(bench_model.HEAD_BODY).id
        names = {model.camera(i).name for i in range(model.ncam)}
        self._has_overview = OVERVIEW_CAMERA in names

    def render(self, env, target_position=None) -> tuple[np.ndarray, np.ndarray | None]:
        self._ensure(env)
        option = env._clean_scene_option()
        self._head.update_scene(env.data, camera=bench_model.CAMERA_HEAD, scene_option=option)
        head = self._head.render().copy()
        if not self._has_overview:
            return head, None
        self._room.update_scene(env.data, camera=OVERVIEW_CAMERA, scene_option=option)
        self._draw_gaze(env)
        if target_position is not None:
            self._draw_target(np.asarray(target_position, dtype=np.float64))
        return head, self._room.render().copy()

    # Annotations are extra geoms appended to the overview scene only; the head
    # renderer's scene is separate and never sees them.

    def _draw_gaze(self, env) -> None:
        model, data = env.model, env.data
        cam = self._head_cam
        origin = np.array(data.cam_xpos[cam], dtype=np.float64)
        frame = np.array(data.cam_xmat[cam], dtype=np.float64).reshape(3, 3)
        right, up, forward = frame[:, 0], frame[:, 1], -frame[:, 2]
        half = math.tan(math.radians(float(model.cam_fovy[cam]) / 2.0))
        rays = [forward] + [
            forward + sx * half * right + sy * half * up for sx in (-1.0, 1.0) for sy in (-1.0, 1.0)
        ]
        for k, direction in enumerate(rays):
            direction = direction / np.linalg.norm(direction)
            end = origin + direction * self._first_hit(model, data, origin, direction)
            if k == 0:
                self._line(origin, end, 0.007, (1.0, 0.18, 0.18, 0.95))
                self._sphere(end, 0.03, (1.0, 0.18, 0.18, 0.95))
            else:
                self._line(origin, end, 0.0025, (1.0, 0.65, 0.2, 0.55))

    def _draw_target(self, position: np.ndarray) -> None:
        top = position + np.array([0.0, 0.0, 0.42])
        self._line(position + np.array([0.0, 0.0, 0.10]), top, 0.012, (1.0, 0.85, 0.1, 0.9))
        self._sphere(top, 0.04, (1.0, 0.85, 0.1, 0.95))

    def _first_hit(self, model, data, origin, direction) -> float:
        geomid = np.zeros(1, dtype=np.int32)
        distance = mujoco.mj_ray(
            model, data, np.ascontiguousarray(origin), np.ascontiguousarray(direction),
            None, 1, self._head_body, geomid,
        )
        return float(distance) if distance > 0 else 6.0

    def _slot(self):
        scene = self._room.scene
        if scene.ngeom >= scene.maxgeom:
            return None
        geom = scene.geoms[scene.ngeom]
        scene.ngeom += 1
        return geom

    def _line(self, a, b, width, rgba) -> None:
        geom = self._slot()
        if geom is None:
            return
        mujoco.mjv_initGeom(
            geom, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), np.zeros(9),
            np.array(rgba, dtype=np.float32),
        )
        mujoco.mjv_connector(
            geom, mujoco.mjtGeom.mjGEOM_CAPSULE, width,
            np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64),
        )

    def _sphere(self, position, radius, rgba) -> None:
        geom = self._slot()
        if geom is None:
            return
        mujoco.mjv_initGeom(
            geom, mujoco.mjtGeom.mjGEOM_SPHERE, np.array([radius, 0.0, 0.0]),
            np.asarray(position, dtype=np.float64), np.eye(3).ravel(),
            np.array(rgba, dtype=np.float32),
        )

    def close(self) -> None:
        for renderer in (self._head, self._room):
            if renderer is not None:
                renderer.close()
        self._head = self._room = None
        self._model = None


# ------------------------------------------------------------------- serving


def _jpeg(rgb: np.ndarray, quality: int) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def _png(rgb: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(buffer, format="PNG")
    return buffer.getvalue()


class LiveView:
    """Frames and state published by the experiment, read by the browser.

    Everything MuJoCo happens in the experiment's thread; the HTTP threads only
    ever read bytes and a dict under a lock.
    """

    def __init__(self, port: int = 8765, host: str = "127.0.0.1"):
        self._cond = threading.Condition()
        self._frames: dict[str, bytes] = {}
        self._frame_seq = 0
        self._state: dict = {"phase": "attente", "phase_label": "En attente de l'expérience…"}
        self._log: collections.deque = collections.deque(maxlen=120)
        self._reference: bytes | None = None
        self._reference_version = 0
        self._closed = False

        view = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:  # keep the terminal for the experiment
                pass

            def do_GET(self) -> None:
                view._handle(self)

        self._server = ThreadingHTTPServer((host, port), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self.url = f"http://{host}:{self.port}/"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    # -------------------------------------------------------------- publishing

    def publish(self, head: np.ndarray, room: np.ndarray | None) -> None:
        big = np.repeat(np.repeat(head, HEAD_UPSCALE, axis=0), HEAD_UPSCALE, axis=1)
        frames = {"head": _jpeg(big, 92)}
        if room is not None:
            frames["room"] = _jpeg(room, 85)
        with self._cond:
            self._frames.update(frames)
            self._frame_seq += 1
            self._cond.notify_all()

    def update(self, **fields) -> None:
        with self._cond:
            self._state.update(fields)

    def log(self, message: str) -> None:
        with self._cond:
            self._log.append(f"{time.strftime('%H:%M:%S')}  {message}")

    def set_reference(self, rgb: np.ndarray | None) -> None:
        with self._cond:
            self._reference = None if rgb is None else _png(rgb)
            self._reference_version += 1

    def snapshot(self) -> dict:
        with self._cond:
            state = dict(self._state)
            state["log"] = list(self._log)
            state["reference_version"] = self._reference_version if self._reference else 0
        return state

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()
        self._server.shutdown()
        self._server.server_close()

    # ---------------------------------------------------------------- handling

    def _handle(self, request: BaseHTTPRequestHandler) -> None:
        path = request.path.split("?", 1)[0]
        try:
            if path in ("/", "/index.html"):
                self._send(request, 200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
            elif path == "/state":
                body = json.dumps(self.snapshot(), ensure_ascii=False, default=_jsonable)
                self._send(request, 200, "application/json; charset=utf-8", body.encode("utf-8"))
            elif path == "/reference.png":
                with self._cond:
                    data = self._reference
                if data is None:
                    self._send(request, 404, "text/plain", b"no reference yet")
                else:
                    self._send(request, 200, "image/png", data)
            elif path in ("/stream/head", "/stream/room"):
                self._stream(request, path.rsplit("/", 1)[1])
            else:
                self._send(request, 404, "text/plain", b"not found")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    @staticmethod
    def _send(request, status: int, content_type: str, body: bytes) -> None:
        request.send_response(status)
        request.send_header("Content-Type", content_type)
        request.send_header("Content-Length", str(len(body)))
        request.send_header("Cache-Control", "no-store")
        request.end_headers()
        request.wfile.write(body)

    def _stream(self, request, name: str) -> None:
        request.send_response(200)
        request.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        request.send_header("Cache-Control", "no-store")
        request.send_header("Connection", "close")
        request.end_headers()
        last = -1
        try:
            while True:
                with self._cond:
                    self._cond.wait_for(lambda: self._frame_seq != last or self._closed, timeout=1.0)
                    if self._closed:
                        return
                    seq, data = self._frame_seq, self._frames.get(name)
                if data is None or seq == last:
                    continue
                last = seq
                request.wfile.write(
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n"
                )
                request.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return


def _jsonable(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, tuple):
        return list(value)
    return str(value)


PAGE = r"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Émergence — vue en direct</title>
<style>
:root { --bg:#0f1115; --panel:#171a21; --line:#262b35; --text:#e6e8ec; --muted:#8b93a3;
        --red:#ff5a5a; --ok:#3ecf8e; --warn:#ffb020; --gold:#ffd23f; }
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--text);
       font:14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { display:flex; align-items:center; gap:12px; padding:12px 18px;
         border-bottom:1px solid var(--line); flex-wrap:wrap }
h1 { font-size:16px; margin:0; font-weight:600 }
.badge { padding:2px 10px; border-radius:999px; background:#232834; color:var(--muted); font-size:12px }
.badge.live { background:#1d3a2c; color:var(--ok) }
.badge.down { background:#3a1d1d; color:var(--red) }
#phase { flex:1 1 420px; font-size:15px }
main { display:grid; grid-template-columns:minmax(260px,1fr) minmax(380px,1.6fr); gap:14px; padding:14px 18px }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:12px; min-width:0 }
.panel h2 { font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted);
            margin:0 0 8px; font-weight:600 }
.wide { grid-column:1 / -1 }
.split { display:grid; grid-template-columns:minmax(300px,1.2fr) minmax(260px,1fr); gap:14px }
.view { position:relative; background:#000; border-radius:6px; overflow:hidden }
.view img { display:block; width:100%; height:auto; image-rendering:pixelated }
.cross::before, .cross::after { content:""; position:absolute; background:rgba(255,255,255,.35); pointer-events:none }
.cross::before { left:50%; top:0; bottom:0; width:1px }
.cross::after { top:50%; left:0; right:0; height:1px }
.note { color:var(--muted); font-size:12px; margin-top:6px }
canvas { width:100%; height:auto; display:block }
table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums }
td { padding:4px 0; border-bottom:1px solid var(--line); vertical-align:top }
td:first-child { color:var(--muted); width:46% }
.bad { color:var(--red); font-weight:600 } .good { color:var(--ok); font-weight:600 }
#alerts div { color:var(--warn); margin:6px 0 0 }
.refbox { display:flex; gap:12px; align-items:center; margin-top:12px }
/* The slot keeps its dark square when there is no target; only the image
   inside is hidden. Clearing an <img>'s src left Chromium's broken-image icon. */
.refslot { width:96px; height:96px; flex:none; border-radius:6px; border:1px solid var(--line);
           background:#222; overflow:hidden }
#ref { display:block; width:100%; height:100%; image-rendering:pixelated; visibility:hidden }
#log { font:12px/1.5 ui-monospace, Consolas, monospace; max-height:240px; overflow:auto;
       white-space:pre-wrap; color:#c9cdd6 }
@media (max-width:900px) { main, .split { grid-template-columns:1fr } }
</style></head>
<body>
<header>
  <h1>Émergence — vue en direct</h1>
  <span id="conn" class="badge">connexion…</span>
  <span id="who" class="badge"></span>
  <div id="phase">En attente de l'expérience…</div>
</header>
<main>
  <section class="panel">
    <h2>Ce que voit la tête</h2>
    <div class="view cross"><img id="head" src="/stream/head" alt="Vue de la tête"></div>
    <div class="note">L'image exacte que reçoit l'agent, 96 × 96 pixels, agrandie sans lissage.
      La croix marque l'axe du regard.</div>
  </section>
  <section class="panel">
    <h2>La pièce, vue de derrière le robot</h2>
    <div class="view"><img id="room" src="/stream/room" alt="Vue de la pièce"></div>
    <div class="note">Rayon rouge : l'axe du regard, arrêté sur la première surface touchée.
      Rayons orange : les bords du champ de 30°. Repère doré : l'objet à retrouver — vérité
      terrain, que l'agent ne voit pas.</div>
  </section>
  <div class="wide split">
    <section class="panel">
      <h2>Les quinze cellules</h2>
      <canvas id="grid" width="600" height="340"></canvas>
      <div class="note">Vues depuis le robot : sa gauche à gauche. Cadre blanc : cellule regardée.
        Cadre doré en pointillés : cellule de la cible. Pointillés orange : objet déplacé au dernier
        brassage. Hachures : cellule que la pièce masque, jamais utilisée.</div>
    </section>
    <section class="panel">
      <h2>État</h2>
      <table id="kv"></table>
      <div class="refbox"><div class="refslot"><img id="ref" alt=""></div><div id="refnote" class="note">Aucune cible désignée pour l'instant.</div></div>
      <div id="alerts"></div>
    </section>
  </div>
  <section class="panel wide"><h2>Journal</h2><div id="log"></div></section>
</main>
<script>
const $ = id => document.getElementById(id);
let refVersion = -1, lastLog = "";
const fmt = (x, d) => (x === null || x === undefined) ? "—" : Number(x).toFixed(d);
const row = (k, v, cls) => `<tr><td>${k}</td><td class="${cls || ""}">${v}</td></tr>`;

function hatch(ctx, x, y, w, h) {
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
  ctx.strokeStyle = "#3a3f4b"; ctx.lineWidth = 1;
  for (let k = -h; k < w; k += 8) { ctx.beginPath(); ctx.moveTo(x + k, y + h); ctx.lineTo(x + k + h, y); ctx.stroke(); }
  ctx.restore();
}
function shape(ctx, kind, color, cx, cy, r) {
  ctx.fillStyle = color;
  if (kind === "sphere") { ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill(); }
  else if (kind === "cylinder") {
    ctx.fillRect(cx - r * 0.7, cy - r, r * 1.4, r * 2);
    ctx.beginPath(); ctx.ellipse(cx, cy - r, r * 0.7, r * 0.25, 0, 0, Math.PI * 2); ctx.fill();
  } else { ctx.fillRect(cx - r, cy - r, r * 2, r * 2); }
}
function drawGrid(g) {
  const c = $("grid"), ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);
  if (!g) return;
  const left = 70, top = 44, cw = (c.width - left - 10) / g.cols.length, ch = (c.height - top - 10) / g.rows.length;
  ctx.font = "12px system-ui"; ctx.fillStyle = "#8b93a3";
  ctx.textAlign = "left"; ctx.fillText("← gauche du robot", left, 14);
  ctx.textAlign = "right"; ctx.fillText("droite du robot →", c.width - 10, 14);
  ctx.textAlign = "center";
  g.cols.forEach((p, i) => ctx.fillText(`pan ${p}°`, left + cw * (i + 0.5), top - 8));
  ctx.textAlign = "right";
  g.rows.forEach((t, j) => ctx.fillText(`tilt ${t > 0 ? "+" : ""}${t}°`, left - 8, top + ch * (j + 0.5) + 4));
  const at = pos => [g.cols.indexOf(pos[0]), g.rows.indexOf(pos[1])];
  for (const cell of g.cells) {
    const [i, j] = at([cell.pan, cell.tilt]);
    const x = left + cw * i + 3, y = top + ch * j + 3, w = cw - 6, h = ch - 6;
    ctx.fillStyle = "#1e222b"; ctx.fillRect(x, y, w, h);
    if (!cell.usable) hatch(ctx, x, y, w, h);
    if (cell.color) shape(ctx, cell.kind, cell.color, x + w / 2, y + h / 2, Math.min(w, h) * 0.3);
    if (cell.moved) { ctx.strokeStyle = "#ffb020"; ctx.lineWidth = 2; ctx.setLineDash([2, 3]); ctx.strokeRect(x + 3, y + 3, w - 6, h - 6); ctx.setLineDash([]); }
  }
  const mark = (pos, color, dash, width) => {
    if (!pos) return; const [i, j] = at(pos); if (i < 0 || j < 0) return;
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash);
    ctx.strokeRect(left + cw * i + 1.5, top + ch * j + 1.5, cw - 3, ch - 3); ctx.setLineDash([]);
  };
  mark(g.target, "#ffd23f", [6, 4], 3);
  mark(g.gaze, "#ffffff", [], 3);
}

async function tick() {
  try {
    const s = await (await fetch("/state", {cache: "no-store"})).json();
    $("conn").textContent = "en direct"; $("conn").className = "badge live";
    $("who").textContent = s.experiment ? `${s.experiment} · épisode ${s.episode ?? "—"} · pièce ${s.seed ?? "—"}` : "";
    $("phase").textContent = s.phase_label || s.phase || "";
    const err = s.pointing_error_deg;
    let kv = "";
    kv += row("Consigne pan / tilt", `${fmt(s.pan_cmd, 1)}° / ${fmt(s.tilt_cmd, 1)}°`);
    kv += row("Angle réel pan / tilt", `${fmt(s.pan_deg, 2)}° / ${fmt(s.tilt_deg, 2)}°`);
    kv += row("Écart au dernier arrêt", err === null || err === undefined ? "—" : `${fmt(err, 3)}°`, err > 0.5 ? "bad" : "");
    kv += row("Mouvements", s.moves ?? "—");
    kv += row("Temps simulé", s.sim_time === undefined ? "—" : `${fmt(s.sim_time, 1)} s`);
    kv += row("Vitesse d'affichage", s.speed ? `${s.speed} × le temps réel` : "maximale");
    if (s.visibility_min !== undefined) kv += row("Objet le moins visible", `${fmt(s.visibility_min * 100, 1)} % de la vue centrale`);
    if (s.result) kv += row("Dernière réponse", s.result.success ? "succès" : "échec", s.result.success ? "good" : "bad");
    if (s.tally && s.tally.episodes) kv += row("Bilan", `${s.tally.successes} / ${s.tally.episodes}`);
    $("kv").innerHTML = kv;
    if (s.reference_version !== refVersion) {
      refVersion = s.reference_version;
      const ref = $("ref");
      if (refVersion > 0) { ref.src = "/reference.png?v=" + refVersion; ref.style.visibility = "visible"; }
      else { ref.style.visibility = "hidden"; ref.removeAttribute("src"); }
    }
    $("refnote").textContent = s.target ? `Objet à retrouver : ${s.target.label}.` : "Aucune cible désignée pour l'instant.";
    $("alerts").innerHTML = (s.alerts || []).map(a => `<div>⚠ ${a}</div>`).join("");
    drawGrid(s.grid);
    const text = (s.log || []).join("\n");
    if (text !== lastLog) {
      const el = $("log"), atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 4;
      el.textContent = text; lastLog = text; if (atBottom) el.scrollTop = el.scrollHeight;
    }
  } catch (e) {
    $("conn").textContent = "déconnecté"; $("conn").className = "badge down";
  }
}
for (const id of ["head", "room"]) {
  const img = $(id);
  img.onerror = () => setTimeout(() => { img.src = `/stream/${id}?t=${Date.now()}`; }, 1000);
}
setInterval(tick, 250); tick();
</script>
</body></html>
"""
