"""Charts for the live view: the outcome per policy, and the simulation's health.

Kept apart from `bench2_live.py` so the page's layout and the plotting code read
separately. Everything is drawn on <canvas> by the functions below, with no chart
library, so the page keeps working offline -- a CDN would not guarantee that.

Four small charts, two per question Anthony asked. *Is anything progressing?* --
the cumulative success rate per policy with its 95 % Wilson interval and the
chance level, and the number of moves per episode: the two quantities the margin
probe of step 3 compares between a witness and the oracle. *Is the simulation
doing something absurd?* -- the pointing error at every stop against the alert
threshold, and the visibility of each room's least visible object against the
guard's threshold.

Colour follows the project's charting method. The policy colours are the first
three dark-mode categorical slots, validated against this page's own surface
#171a21: every check passes, adjacent and all-pairs, worst CVD separation 9.4. A
policy keeps its colour for good, so the oracle is not repainted when the
witnesses arrive. Health series are drawn in neutral ink rather than a policy
colour, so blue never reads as "the oracle" on a chart about the simulation. A
point on the wrong side of its threshold turns status red and carries a warning
sign in the tooltip and the table -- never colour alone. Every chart has a hover
crosshair, the same readout on keyboard focus, and a table view.
"""

CHARTS_CSS = r"""
.charts-head { display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 16px; margin-bottom:10px }
.charts-head h2 { margin:0 }
.charts-head .note { margin:0; flex:1 1 440px }
.charts-grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:14px }
.chart { margin:0; border:1px solid var(--line); border-radius:8px; padding:10px 12px 8px; min-width:0 }
.chart figcaption { display:flex; flex-direction:column; gap:2px; margin-bottom:6px }
.chart .ct { font-weight:600; font-size:13px; color:var(--text) }
.chart .cs { font-size:12px; color:var(--muted) }
.legend { display:flex; flex-wrap:wrap; gap:4px 14px; font-size:12px; color:#c9cdd6; margin:2px 0 6px }
.legend .key { display:inline-block; width:14px; height:2px; border-radius:1px; vertical-align:middle; margin-right:6px }
.legend .dotkey { width:8px; height:8px; border-radius:50% }
.plot { position:relative }
.plot canvas { display:block; width:100%; height:200px; outline:none; border-radius:4px; cursor:crosshair }
.plot canvas:focus-visible { box-shadow:0 0 0 2px #3987e5 }
.tip { position:absolute; top:6px; left:0; pointer-events:none; z-index:2; background:#0f1115;
       border:1px solid var(--line); border-radius:6px; padding:6px 8px; font-size:12px; line-height:1.4;
       min-width:120px; box-shadow:0 4px 14px rgba(0,0,0,.4) }
.tip .tx { color:var(--muted) }
.tip .row { display:flex; align-items:center; gap:6px; white-space:nowrap }
.tip .row b { color:var(--text); font-weight:600 }
.tip .row .l { color:#c9cdd6 }
.tip .key { width:12px; height:2px; border-radius:1px; flex:none }
.legend[hidden], .tip[hidden] { display:none }
.chart details { margin-top:6px; font-size:12px; color:var(--muted) }
.chart details summary { cursor:pointer }
.chart table { margin-top:6px; width:auto; min-width:60%; font-variant-numeric:tabular-nums }
.chart th { text-align:left; color:var(--muted); font-weight:600; padding:3px 12px 3px 0;
            border-bottom:1px solid var(--line) }
.chart td, .chart td:first-child { width:auto; padding:3px 12px 3px 0; color:#c9cdd6 }
@media (max-width:900px) { .charts-grid { grid-template-columns:1fr } }
"""

CHARTS_HTML = r"""  <section class="panel wide">
    <div class="charts-head">
      <h2>Au fil des épisodes</h2>
      <p class="note" id="charts-note"></p>
    </div>
    <div class="charts-grid">
      <figure class="chart" data-chart="success">
        <figcaption><span class="ct">Taux de succès cumulé</span>
          <span class="cs">Par politique, avec son intervalle de confiance à 95 %. Pointillés : le hasard, une cellule sur quinze.</span></figcaption>
        <div class="legend" hidden></div>
        <div class="plot"><canvas tabindex="0" role="img" aria-label="Taux de succès cumulé par politique, épisode par épisode"></canvas><div class="tip" hidden></div></div>
        <details><summary>Voir les données — 15 dernières valeurs</summary><table></table></details>
      </figure>
      <figure class="chart" data-chart="moves">
        <figcaption><span class="ct">Mouvements par épisode</span>
          <span class="cs">Exploration, délai et réponse compris : ce que coûte chaque politique.</span></figcaption>
        <div class="legend" hidden></div>
        <div class="plot"><canvas tabindex="0" role="img" aria-label="Nombre de mouvements par épisode et par politique"></canvas><div class="tip" hidden></div></div>
        <details><summary>Voir les données — 15 dernières valeurs</summary><table></table></details>
      </figure>
      <figure class="chart" data-chart="pointing">
        <figcaption><span class="ct">Écart de pointage à chaque arrêt</span>
          <span class="cs">Consigne contre angle réel quand la tête s'arrête, échelle logarithmique. Pointillés : le seuil d'alerte.</span></figcaption>
        <div class="legend" hidden></div>
        <div class="plot"><canvas tabindex="0" role="img" aria-label="Écart de pointage à chaque arrêt de la tête"></canvas><div class="tip" hidden></div></div>
        <details><summary>Voir les données — 15 dernières valeurs</summary><table></table></details>
      </figure>
      <figure class="chart" data-chart="visibility">
        <figcaption><span class="ct">Visibilité de l'objet le moins visible</span>
          <span class="cs">Part de la vue centrale qu'il occupe, pièce par pièce. Pointillés : le seuil sous lequel le garde déplace un objet.</span></figcaption>
        <div class="legend" hidden></div>
        <div class="plot"><canvas tabindex="0" role="img" aria-label="Visibilité de l'objet le moins visible, pièce par pièce"></canvas><div class="tip" hidden></div></div>
        <details><summary>Voir les données — 15 dernières valeurs</summary><table></table></details>
      </figure>
    </div>
  </section>
"""

CHARTS_JS = r"""
(function () {
  "use strict";
  // First three slots of the dark categorical palette, validated on #171a21.
  const SLOTS = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];
  const INK = {
    primary: "#e6e8ec", secondary: "#c9cdd6", muted: "#8b93a3", grid: "#262b35",
    axis: "#3a3f4b", surface: "#171a21", neutral: "#c9cdd6", critical: "#d03b3b",
  };
  const FONT = "11px system-ui, -apple-system, 'Segoe UI', sans-serif";
  const charts = new Map();

  const fr = (v, d) => Number(v).toLocaleString("fr-FR", {minimumFractionDigits: d, maximumFractionDigits: d});
  const pct = (v, d) => fr(v * 100, d === undefined ? 0 : d) + " %";
  const deg = v => (v >= 0.1 ? fr(v, 2) : v >= 0.01 ? fr(v, 3) : fr(v, 4)) + "°";
  const degTick = v => fr(v, Math.max(0, -Math.floor(Math.log10(v) + 1e-9))) + "°";
  const shortLabel = label => (label.indexOf("— ") >= 0 ? label.split("— ").pop() : label);

  function rgba(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return "rgba(" + ((n >> 16) & 255) + ", " + ((n >> 8) & 255) + ", " + (n & 255) + ", " + a + ")";
  }

  function niceStep(span, target) {
    const raw = span / Math.max(1, target);
    const p = Math.pow(10, Math.floor(Math.log10(raw)));
    for (const k of [1, 2, 2.5, 5, 10]) if (k * p >= raw) return k * p;
    return 10 * p;
  }

  function allX(c) {
    if (!c.spec) return [];
    const seen = new Set();
    for (const s of c.spec.series) for (const p of s.points) seen.add(p[0]);
    return Array.from(seen).sort((a, b) => a - b);
  }

  function nearestX(c, x) {
    const xs = allX(c);
    if (!xs.length) return null;
    let best = xs[0];
    for (const v of xs) if (Math.abs(v - x) < Math.abs(best - x)) best = v;
    return best;
  }

  function entry(fig) {
    let c = charts.get(fig);
    if (c) return c;
    const canvas = fig.querySelector("canvas");
    c = {fig: fig, canvas: canvas, tip: fig.querySelector(".tip"), legend: fig.querySelector(".legend"),
         table: fig.querySelector("table"), details: fig.querySelector("details"),
         spec: null, geo: null, hoverX: null};
    charts.set(fig, c);
    canvas.addEventListener("pointermove", ev => {
      if (!c.geo) return;
      const rect = canvas.getBoundingClientRect();
      c.hoverX = nearestX(c, c.geo.ix(ev.clientX - rect.left));
      paint(c);
    });
    canvas.addEventListener("pointerleave", () => { if (document.activeElement !== canvas) { c.hoverX = null; paint(c); } });
    canvas.addEventListener("focus", () => {
      if (c.hoverX === null) { const xs = allX(c); c.hoverX = xs.length ? xs[xs.length - 1] : null; }
      paint(c);
    });
    canvas.addEventListener("blur", () => { c.hoverX = null; paint(c); });
    canvas.addEventListener("keydown", ev => {
      const xs = allX(c);
      if (!xs.length) return;
      let i = xs.indexOf(c.hoverX);
      if (i < 0) i = xs.length - 1;
      if (ev.key === "ArrowLeft") i = Math.max(0, i - 1);
      else if (ev.key === "ArrowRight") i = Math.min(xs.length - 1, i + 1);
      else if (ev.key === "Home") i = 0;
      else if (ev.key === "End") i = xs.length - 1;
      else if (ev.key === "Escape") { c.hoverX = null; paint(c); return; }
      else return;
      ev.preventDefault();
      c.hoverX = xs[i];
      paint(c);
    });
    if (c.details) c.details.addEventListener("toggle", () => table(c));
    return c;
  }

  function geometry(c) {
    const spec = c.spec, canvas = c.canvas;
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    if (W < 60 || H < 60) return null;
    if (canvas.width !== Math.round(W * dpr)) canvas.width = Math.round(W * dpr);
    if (canvas.height !== Math.round(H * dpr)) canvas.height = Math.round(H * dpr);
    const labelled = spec.kind === "line" && spec.series.length >= 1 && spec.series.length <= 4;
    const m = {l: 58, r: labelled ? 164 : 14, t: 14, b: 24};
    const xs = allX(c);
    const x0 = xs.length ? xs[0] : 0;
    let x1 = xs.length ? xs[xs.length - 1] : 1;
    if (x1 <= x0) x1 = x0 + 1;
    const ys = [];
    for (const s of spec.series) for (const p of s.points) ys.push(p[1]);
    for (const r of spec.refs) ys.push(r.y);
    let y0, y1, ticks;
    if (spec.y.log) {
      const positive = ys.filter(v => v > 0);
      y0 = Math.pow(10, Math.floor(Math.log10(Math.min(spec.y.min, ...positive))));
      y1 = Math.pow(10, Math.ceil(Math.log10(Math.max(spec.y.max, ...positive))));
      ticks = [];
      for (let t = y0; t <= y1 * 1.0001; t *= 10) ticks.push(t);
    } else if (spec.y.ticks) {
      y0 = spec.y.min; y1 = spec.y.max; ticks = spec.y.ticks;
    } else {
      y0 = spec.y.min;
      const top = Math.max(y0 + 1e-9, ...ys);
      const step = niceStep((top - y0) * 1.08, 4);
      y1 = y0 + Math.ceil((top - y0) * 1.08 / step) * step;
      ticks = [];
      for (let t = y0; t <= y1 + step * 1e-6; t += step) ticks.push(t);
    }
    const pw = W - m.l - m.r, ph = H - m.t - m.b;
    const px = x => m.l + (x - x0) / (x1 - x0) * pw;
    const ix = sx => x0 + (sx - m.l) / pw * (x1 - x0);
    const lo = Math.log10(y0), span = Math.log10(y1) - lo;
    const py = spec.y.log
      ? v => m.t + (1 - (Math.log10(Math.max(v, y0)) - lo) / span) * ph
      : v => m.t + (1 - (v - y0) / (y1 - y0)) * ph;
    let xstep = niceStep(x1 - x0, 5);
    xstep = xstep < 1 ? 1 : Math.ceil(xstep);
    const xticks = [];
    for (let t = Math.ceil(x0 / xstep) * xstep; t <= x1 + 1e-9; t += xstep) xticks.push(t);
    return {W, H, dpr, m, x0, x1, y0, y1, px, py, ix, ticks, xticks, labelled};
  }

  function dot(ctx, x, y, color) {
    ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fillStyle = INK.surface; ctx.fill();
    ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
  }

  function refLines(ctx, g, spec) {
    for (const r of spec.refs) {
      if (r.y < g.y0 || r.y > g.y1) continue;
      const y = Math.round(g.py(r.y)) + 0.5;
      ctx.save();
      ctx.setLineDash([4, 4]); ctx.strokeStyle = r.color; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(g.m.l, y); ctx.lineTo(g.W - g.m.r, y); ctx.stroke();
      ctx.restore();
    }
  }

  // Labels go on last, at whichever of four spots -- above or below their line,
  // at its left or right end -- has the fewest data points under it. A point
  // sitting on a threshold label is exactly the aberration the chart exists to
  // show: with only left and right to choose from, a tie hid one under the text.
  // Below the line is the usual escape, since what crosses an alert threshold
  // lies above it. A spot is only allowed if the text stays inside the plot; the
  // halo keeps it legible if every spot is crowded.
  function refLabels(ctx, g, spec) {
    ctx.font = FONT; ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    const top = g.m.t, bottom = g.H - g.m.b;
    for (const r of spec.refs) {
      if (r.y < g.y0 || r.y > g.y1) continue;
      const y = Math.round(g.py(r.y)) + 0.5;
      const w = ctx.measureText(r.label).width;
      const spots = [];
      for (const x of [g.m.l + 6, g.W - g.m.r - 6 - w]) {
        if (y - 15 >= top) spots.push({x: x, base: y - 4, lo: y - 14, hi: y - 1});
        if (y + 17 <= bottom) spots.push({x: x, base: y + 13, lo: y + 3, hi: y + 16});
      }
      if (!spots.length) spots.push({x: g.m.l + 6, base: y - 4, lo: y - 14, hi: y - 1});
      let best = spots[0], fewest = Infinity;
      for (const spot of spots) {
        let hits = 0;
        for (const s of spec.series) for (const p of s.points) {
          const px = g.px(p[0]), py = g.py(p[1]);
          if (px > spot.x - 7 && px < spot.x + w + 7 && py > spot.lo - 7 && py < spot.hi + 7) hits++;
        }
        if (hits < fewest) { fewest = hits; best = spot; }
      }
      ctx.lineWidth = 3; ctx.strokeStyle = INK.surface; ctx.lineJoin = "round";
      ctx.strokeText(r.label, best.x, best.base);
      ctx.fillStyle = INK.muted;
      ctx.fillText(r.label, best.x, best.base);
      ctx.lineWidth = 1;
    }
  }

  function endLabels(ctx, g, spec) {
    const ends = spec.series.filter(s => s.points.length).map(s => {
      const p = s.points[s.points.length - 1];
      return {s: s, y: g.py(p[1]), v: p[1]};
    }).sort((a, b) => a.y - b.y);
    // Lines that converge at the right edge are not labelled at all: nudged
    // labels detach from their lines, and the legend and tooltip carry them.
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 16) return;
    const x = g.W - g.m.r + 12;
    ctx.textBaseline = "middle"; ctx.textAlign = "left";
    for (const e of ends) {
      const value = e.s.fmt(e.v);
      ctx.font = "600 " + FONT; ctx.fillStyle = INK.primary;
      ctx.fillText(value, x, e.y);
      const w = ctx.measureText(value).width;
      ctx.font = FONT; ctx.fillStyle = INK.secondary;
      const name = shortLabel(e.s.label);
      if (x + w + 6 + ctx.measureText(name).width <= g.W - 4) ctx.fillText(name, x + w + 6, e.y);
    }
    ctx.font = FONT;
  }

  function paint(c) {
    const spec = c.spec;
    if (!spec) return;
    const g = geometry(c);
    if (!g) return;
    c.geo = g;
    const ctx = c.canvas.getContext("2d");
    ctx.setTransform(g.dpr, 0, 0, g.dpr, 0, 0);
    ctx.clearRect(0, 0, g.W, g.H);
    ctx.font = FONT; ctx.lineWidth = 1;

    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (const t of g.ticks) {
      const y = Math.round(g.py(t)) + 0.5;
      ctx.strokeStyle = INK.grid;
      ctx.beginPath(); ctx.moveTo(g.m.l, y); ctx.lineTo(g.W - g.m.r, y); ctx.stroke();
      ctx.fillStyle = INK.muted; ctx.fillText((spec.y.tick || spec.y.fmt)(t), g.m.l - 8, y);
    }
    const base = Math.round(g.H - g.m.b) + 0.5;
    ctx.strokeStyle = INK.axis;
    ctx.beginPath(); ctx.moveTo(g.m.l, base); ctx.lineTo(g.W - g.m.r, base); ctx.stroke();

    const has = spec.series.some(s => s.points.length);
    if (!has) {
      refLines(ctx, g, spec);
      refLabels(ctx, g, spec);
      ctx.fillStyle = INK.muted; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(spec.empty, g.m.l + (g.W - g.m.l - g.m.r) / 2, g.m.t + (g.H - g.m.t - g.m.b) / 2);
      c.tip.hidden = true; legend(c);
      return;
    }

    ctx.fillStyle = INK.muted; ctx.textAlign = "center"; ctx.textBaseline = "top";
    for (const t of g.xticks) ctx.fillText(fr(t, 0), g.px(t), base + 5);
    refLines(ctx, g, spec);

    for (const s of spec.series) {
      if (!s.band || s.band.length < 2) continue;
      ctx.fillStyle = rgba(s.color, 0.10);
      ctx.beginPath();
      s.band.forEach((b, i) => { const x = g.px(b[0]), y = g.py(b[2]); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
      for (let i = s.band.length - 1; i >= 0; i--) ctx.lineTo(g.px(s.band[i][0]), g.py(s.band[i][1]));
      ctx.closePath(); ctx.fill();
    }

    for (const s of spec.series) {
      if (spec.kind === "line") {
        ctx.strokeStyle = s.color; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.lineCap = "round";
        ctx.beginPath();
        s.points.forEach((p, i) => { const x = g.px(p[0]), y = g.py(p[1]); if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y); });
        ctx.stroke();
        const last = s.points[s.points.length - 1];
        if (last) dot(ctx, g.px(last[0]), g.py(last[1]), s.color);
      } else {
        for (const p of s.points) dot(ctx, g.px(p[0]), g.py(p[1]), s.flag && s.flag(p[1]) ? INK.critical : s.color);
      }
    }
    ctx.lineWidth = 1;
    if (g.labelled) endLabels(ctx, g, spec);
    refLabels(ctx, g, spec);

    if (c.hoverX !== null && c.hoverX !== undefined) {
      const x = Math.round(g.px(c.hoverX)) + 0.5;
      ctx.strokeStyle = rgba(INK.secondary, 0.55);
      ctx.beginPath(); ctx.moveTo(x, g.m.t); ctx.lineTo(x, base); ctx.stroke();
      tooltip(c, g);
    } else {
      c.tip.hidden = true;
    }
    legend(c);
    table(c);
  }

  function valueAt(spec, s, x) {
    if (spec.kind === "line") {
      // A cumulative rate is defined at every episode: the value as of x.
      let found = null;
      for (const q of s.points) { if (q[0] <= x) found = q; else break; }
      return found;
    }
    return s.points.find(q => q[0] === x) || null;
  }

  function tooltip(c, g) {
    const tip = c.tip, spec = c.spec, x = c.hoverX;
    tip.replaceChildren();
    const head = document.createElement("div");
    head.className = "tx";
    head.textContent = spec.x.label + " " + fr(x, 0);
    tip.appendChild(head);
    for (const s of spec.series) {
      const p = valueAt(spec, s, x);
      if (!p) continue;
      const flagged = s.flag && s.flag(p[1]);
      const row = document.createElement("div");
      row.className = "row";
      const key = document.createElement("span");
      key.className = "key";
      key.style.background = flagged ? INK.critical : s.color;
      const value = document.createElement("b");
      value.textContent = (flagged ? "⚠ " : "") + s.fmt(p[1]);
      const label = document.createElement("span");
      label.className = "l";
      label.textContent = s.label;
      row.append(key, value, label);
      tip.appendChild(row);
      const band = s.band ? s.band.find(q => q[0] === p[0]) : null;
      if (band) {
        const interval = document.createElement("div");
        interval.className = "tx";
        interval.textContent = "intervalle à 95 % : " + s.fmt(band[1]) + " – " + s.fmt(band[2]);
        tip.appendChild(interval);
      }
    }
    tip.hidden = false;
    tip.style.left = "0px";
    const w = tip.offsetWidth, anchor = g.px(x);
    tip.style.left = (anchor + 12 + w > g.W ? Math.max(4, anchor - 12 - w) : anchor + 12) + "px";
  }

  function legend(c) {
    const el = c.legend, series = c.spec.series.filter(s => s.points.length);
    if (series.length < 2) { el.hidden = true; return; }
    const signature = series.map(s => s.key + s.color).join("|");
    if (el.dataset.sig !== signature) {
      el.replaceChildren();
      for (const s of series) {
        const item = document.createElement("span");
        const key = document.createElement("span");
        key.className = c.spec.kind === "line" ? "key" : "key dotkey";
        key.style.background = s.color;
        item.append(key, document.createTextNode(s.label));
        el.appendChild(item);
      }
      el.dataset.sig = signature;
    }
    el.hidden = false;
  }

  function table(c) {
    if (!c.details || !c.details.open || !c.spec) return;
    const t = c.table, spec = c.spec;
    t.replaceChildren();
    const head = t.insertRow();
    for (const text of [spec.x.label].concat(spec.series.map(s => s.label))) {
      const th = document.createElement("th");
      th.textContent = text;
      head.appendChild(th);
    }
    for (const x of allX(c).slice(-15).reverse()) {
      const row = t.insertRow();
      row.insertCell().textContent = fr(x, 0);
      for (const s of spec.series) {
        const p = s.points.find(q => q[0] === x);
        const flagged = p && s.flag && s.flag(p[1]);
        row.insertCell().textContent = p ? (flagged ? "⚠ " : "") + s.fmt(p[1]) : "—";
      }
    }
  }

  function render(name, spec) {
    const fig = document.querySelector('figure.chart[data-chart="' + name + '"]');
    if (!fig) return;
    const c = entry(fig);
    c.spec = spec;
    if (c.hoverX !== null && allX(c).indexOf(c.hoverX) < 0) c.hoverX = nearestX(c, c.hoverX);
    paint(c);
  }

  window.addEventListener("resize", () => { for (const c of charts.values()) paint(c); });

  window.drawCharts = function (data) {
    if (!data) return;
    const policies = data.policies || [];
    const colour = p => SLOTS[p.slot % SLOTS.length];

    const note = document.getElementById("charts-note");
    if (note) {
      const onlyOracle = policies.every(p => p.key === "oracle");
      note.textContent = onlyOracle
        ? "Rien n'apprend pour l'instant : l'oracle connaît la cellule de la cible, ses deux courbes du haut sont donc plates par construction. Elles montreront l'écart entre les témoins et l'oracle quand la sonde de l'étape 3 tournera. Les deux du bas surveillent la simulation elle-même."
        : "L'écart entre un témoin et l'oracle, en succès comme en mouvements, est la marge que mesure la sonde. Les deux graphes du bas surveillent la simulation elle-même.";
    }

    render("success", {
      kind: "line",
      x: {label: "épisode"},
      y: {min: 0, max: 1, ticks: [0, 0.25, 0.5, 0.75, 1], fmt: v => pct(v)},
      series: policies.map(p => {
        const rows = (data.success || {})[p.key] || [];
        return {key: p.key, label: p.label, color: colour(p), fmt: v => pct(v, 1),
                points: rows.map(r => [r[0], r[1]]), band: rows.map(r => [r[0], r[2], r[3]])};
      }),
      refs: data.chance ? [{y: data.chance, label: "hasard : " + pct(data.chance, 1), color: INK.muted}] : [],
      empty: "En attente de la première réponse…",
    });

    render("moves", {
      kind: "dots",
      x: {label: "épisode"},
      y: {min: 0, fmt: v => fr(v, 0)},
      series: policies.map(p => ({key: p.key, label: p.label, color: colour(p),
                                  fmt: v => fr(v, 0) + " mouvements",
                                  points: (data.moves || {})[p.key] || []})),
      refs: [],
      empty: "En attente de la première réponse…",
    });

    const threshold = data.pointing_threshold;
    render("pointing", {
      kind: "dots",
      x: {label: "arrêt"},
      y: {log: true, min: 1e-4, max: 1, fmt: deg, tick: degTick},
      series: [{key: "pointing", label: "écart de pointage", color: INK.neutral, fmt: deg,
                points: data.pointing || [], flag: v => v > threshold}],
      refs: threshold ? [{y: threshold, label: "⚠ seuil d'alerte : " + deg(threshold), color: INK.critical}] : [],
      empty: "En attente du premier arrêt…",
    });

    const guard = data.visibility_threshold;
    render("visibility", {
      kind: "dots",
      x: {label: "épisode"},
      y: {min: 0, fmt: v => pct(v)},
      series: [{key: "visibility", label: "objet le moins visible", color: INK.neutral,
                fmt: v => pct(v, 1), points: data.visibility || [], flag: v => v < guard}],
      refs: guard ? [{y: guard, label: "⚠ seuil du garde : " + pct(guard), color: INK.critical}] : [],
      empty: "En attente de la première pièce…",
    });
  };
})();
"""
