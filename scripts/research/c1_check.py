"""What C1 actually is, measured (D-060, step 2).

Reports the properties a task has to have before anyone designs a mechanism for
it. This is not the margin probe of step 3: nothing here compares a policy to a
baseline or to an oracle. It answers a narrower question -- is the task built
correctly, or does it have a hole in it?

  usable cells      how many of the 15 can show an object at all, per room
  object visibility how much of the central view each placed object changes
  per-row size      the same, split by row: a difficulty gradient, not a leak,
                    because the reference image is rendered on a neutral
                    backdrop and carries nothing about placement
  reference apart   how far apart two different appearances are, in the
                    reference rendering that designates them
  shuffle           how often objects actually move between visits

    python -m scripts.research.c1_check --seeds 20 21 22 23
"""

from __future__ import annotations

import argparse
import collections

import numpy as np

from learning.c1_task import PALETTE, Appearance, C1Config, C1Episode, reference_image
from sim3d.bench2_live import columns_as_seen


def episode_facts(seed: int, config: C1Config) -> dict | None:
    try:
        episode = C1Episode(config, seed=seed)
    except RuntimeError as exc:
        return {"seed": seed, "rejected": str(exc)}
    try:
        by_row = collections.defaultdict(list)
        for index, cell in episode.placement.items():
            by_row[cell[1]].append(episode.object_visibility[index])
        return {
            "seed": seed,
            "usable": len(episode.usable),
            "visibility": dict(episode.object_visibility),
            "by_row": {tilt: list(values) for tilt, values in by_row.items()},
        }
    finally:
        episode.close()


def reference_separation(config: C1Config) -> tuple[float, float]:
    """Smallest and largest distance between two reference renderings."""

    images = [
        reference_image(Appearance(i, *PALETTE[i]), config).astype(np.float32)
        for i in range(config.object_count)
    ]
    pairs = [
        float(np.abs(images[i] - images[j]).mean())
        for i in range(len(images))
        for j in range(i + 1, len(images))
    ]
    return min(pairs), max(pairs)


def shuffle_rate(seeds, config: C1Config) -> tuple[int, int]:
    moved = total = 0
    for seed in seeds:
        try:
            episode = C1Episode(config, seed=seed)
        except RuntimeError:
            continue
        try:
            before = dict(episode.placement)
            list(episode.exploration())
            episode.delay()
            total += 1
            moved += any(before[k] != episode.placement[k] for k in before)
        finally:
            episode.close()
    return moved, total


def contact_sheet(seed: int, path: str, config: C1Config | None = None) -> None:
    """The grid as C1 leaves it, with the reference strip underneath."""

    import matplotlib.image

    from sim3d.bench2_model import grid_shape

    config = config or C1Config(object_count=8, shuffle_probability=0.0)
    episode = C1Episode(config, seed=seed)
    try:
        frames = {cell: image for cell, image, _ in episode.exploration()}
        cols, rows = grid_shape(config.bench)
        cells = episode.cells
        size = config.image_size
        references = [
            reference_image(Appearance(i, *PALETTE[i]), config)
            for i in range(config.object_count)
        ]
    finally:
        episode.close()

    ref_size = max(1, (cols * size) // len(references))
    sheet = np.zeros(((rows + 1) * size, cols * size, 3), dtype=np.uint8)
    # As the robot sees it, its left on the left: pan decreases left to right.
    order = columns_as_seen(sorted({pan for pan, _ in cells}))
    tilts = sorted({tilt for _, tilt in cells}, reverse=True)
    for cell in cells:
        r, c = tilts.index(cell[1]), order.index(cell[0])
        sheet[r * size : (r + 1) * size, c * size : (c + 1) * size] = frames[cell]
    for i, reference in enumerate(references):
        strip = reference[:: max(1, size // ref_size), :: max(1, size // ref_size)]
        h, w = strip.shape[:2]
        x0 = i * ref_size
        sheet[rows * size : rows * size + h, x0 : x0 + w] = strip[:, : min(w, cols * size - x0)]
    matplotlib.image.imsave(path, sheet)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(20, 32)))
    parser.add_argument("--objects", type=int, default=8)
    args = parser.parse_args()

    config = C1Config(object_count=args.objects, shuffle_probability=0.0)
    facts = [episode_facts(seed, config) for seed in args.seeds]
    good = [f for f in facts if "rejected" not in f]
    rejected = [f for f in facts if "rejected" in f]

    print(f"{'seed':>6} {'usable cells':>13} {'least visible object':>21} {'most':>8}")
    for f in good:
        values = list(f["visibility"].values())
        print(f"{f['seed']:>6} {f['usable']:>13} {min(values) * 100:>20.1f}% {max(values) * 100:>7.1f}%")
    if rejected:
        print(f"\nrooms rejected before running: {[f['seed'] for f in rejected]}")

    all_values = [v for f in good for v in f["visibility"].values()]
    print(f"\nevery placed object is visible: {min(all_values) * 100:.1f}% at worst, over "
          f"{len(all_values)} placements in {len(good)} rooms")

    by_row = collections.defaultdict(list)
    for f in good:
        for tilt, values in f["by_row"].items():
            by_row[tilt].extend(values)
    print("\napparent size by row (difficulty gradient, not a leak):")
    for tilt in sorted(by_row, reverse=True):
        v = np.array(by_row[tilt])
        print(f"   tilt {tilt:+6.1f} : n={len(v):3d}  median {np.median(v) * 100:5.1f}%"
              f"   range {v.min() * 100:4.1f}% - {v.max() * 100:5.1f}%")

    low, high = reference_separation(config)
    print(f"\nreference images: closest pair {low:.2f}, furthest {high:.2f} mean abs difference")

    moved, total = shuffle_rate(args.seeds[:8], C1Config(object_count=args.objects, shuffle_probability=1.0))
    print(f"shuffle at p=1.0: objects moved in {moved}/{total} episodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
