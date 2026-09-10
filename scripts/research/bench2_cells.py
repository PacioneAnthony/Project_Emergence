"""Verify the two-axis view grid: are the cells actually distinct? (D-060, step 1)

Renders every cell twice, arriving from opposite sweep directions, and asks the
only question that matters for a spatial memory: can a cell be told apart from
every other one, by more than a cell differs from itself?

  intra  the largest distance between the two renders of the same cell -- servo
         repeatability plus sensor noise, the floor below which nothing is
         distinguishable;
  inter  the smallest distance between two different cells;
  ident. how many cells are correctly recognised by nearest neighbour.

Distance is the mean absolute pixel difference. This is a substrate check, not
the margin probe of step 3: it says the cells exist, not that a task on them has
any headroom.

    python -m scripts.research.bench2_cells --seeds 11 4242 90210 --sheet out.png
"""

from __future__ import annotations

import argparse

import numpy as np

from sim3d.bench2_env import Bench2HeadEnv
from sim3d.bench2_model import Bench2Config, grid_shape, view_cells


def render_cells(env: Bench2HeadEnv, cells, size: int) -> np.ndarray:
    frames = []
    for pan, tilt in cells:
        env.settle_at(pan, tilt)
        frames.append(env.render_camera(size, size).astype(np.float32))
    return np.stack(frames)


def distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.abs(a - b).mean())


def separability(seed: int, size: int = 128) -> dict:
    """Render one room's grid twice and score how separable its cells are."""

    config = Bench2Config(seed=seed)
    cells = view_cells(config)
    env = Bench2HeadEnv(config)
    try:
        env.reset(seed=seed)
        forward = render_cells(env, cells, size)
        backward = render_cells(env, list(reversed(cells)), size)[::-1]
    finally:
        env.close()

    n = len(cells)
    intra = [distance(forward[i], backward[i]) for i in range(n)]
    inter = {
        (i, j): distance(forward[i], backward[j])
        for i in range(n)
        for j in range(n)
        if i != j
    }
    identified = [i for i in range(n) if min(range(n), key=lambda j: distance(forward[i], backward[j])) == i]
    closest = min(inter, key=inter.get)

    rows = sorted({tilt for _, tilt in cells}, reverse=True)
    per_row = {}
    for tilt in rows:
        idx = [k for k, (_, t) in enumerate(cells) if t == tilt]
        others = [inter[(i, j)] for i in idx for j in idx if i != j]
        per_row[tilt] = {
            "contrast": float(np.mean([forward[k].std() for k in idx])),
            "luminance": float(np.mean([forward[k].mean() for k in idx])),
            "inter_min_within_row": float(min(others)) if others else None,
        }

    return {
        "seed": seed,
        "cells": n,
        "grid": grid_shape(config),
        "intra_max": float(max(intra)),
        "inter_min": float(min(inter.values())),
        "margin": float(min(inter.values()) / max(max(intra), 1e-9)),
        "identified": len(identified),
        "closest_pair": [list(cells[closest[0]]), list(cells[closest[1]])],
        "per_row": {str(k): v for k, v in per_row.items()},
    }


def contact_sheet(seed: int, path: str, size: int = 128) -> None:
    """One image of the whole grid, laid out as the grid looks."""

    import matplotlib.image

    config = Bench2Config(seed=seed)
    cells = view_cells(config)
    cols, rows = grid_shape(config)
    env = Bench2HeadEnv(config)
    try:
        env.reset(seed=seed)
        frames = render_cells(env, cells, size)
    finally:
        env.close()
    sheet = np.zeros((rows * size, cols * size, 3), dtype=np.uint8)
    for k, frame in enumerate(frames):
        r, c = divmod(k, cols)
        sheet[r * size : (r + 1) * size, c * size : (c + 1) * size] = frame.astype(np.uint8)
    matplotlib.image.imsave(path, sheet)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 4242, 90210, 777, 20260911])
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--sheet", type=str, default=None, help="write a contact sheet for the first seed")
    args = parser.parse_args()

    results = [separability(seed, args.size) for seed in args.seeds]
    header = f"{'seed':>10} {'cells':>6} {'intra max':>10} {'inter min':>10} {'margin':>7} {'ident.':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['seed']:>10} {r['cells']:>6} {r['intra_max']:>10.4f} {r['inter_min']:>10.4f}"
            f" {r['margin']:>6.1f}x {r['identified']:>4}/{r['cells']}"
        )

    print("\nper row, averaged over seeds:")
    for tilt in results[0]["per_row"]:
        contrast = np.mean([r["per_row"][tilt]["contrast"] for r in results])
        luminance = np.mean([r["per_row"][tilt]["luminance"] for r in results])
        within = np.mean([r["per_row"][tilt]["inter_min_within_row"] for r in results])
        print(
            f"   tilt {float(tilt):+6.1f} : contrast {contrast:6.2f}   luminance {luminance:6.1f}"
            f"   closest pair within row {within:7.3f}"
        )

    weakest = min(results[0]["per_row"], key=lambda t: results[0]["per_row"][t]["contrast"])
    print(f"\nweakest row: tilt {float(weakest):+.1f}")

    if args.sheet:
        contact_sheet(args.seeds[0], args.sheet, args.size)
        print(f"contact sheet: {args.sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
