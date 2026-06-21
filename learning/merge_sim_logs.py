"""Merge simulator CSV logs while keeping episode boundaries distinct."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge sim2d CSV logs and renumber episodes per input file.")
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args.inputs)
    written = merge_logs(args.inputs, args.output)
    print(f"Merged {len(args.inputs)} logs into {args.output} ({written} rows)", flush=True)


def validate_args(inputs: list[Path]) -> None:
    if not inputs:
        raise ValueError("--inputs must include at least one CSV log.")
    missing = [str(path) for path in inputs if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Input logs do not exist: {', '.join(missing)}")


def merge_logs(inputs: list[Path], output: Path) -> int:
    """Merge logs and offset each file's episode ids after the previous max."""

    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = union_fieldnames(inputs)
    episode_offset = 0
    written = 0
    with output.open("w", newline="", encoding="utf-8") as out_handle:
        writer = csv.DictWriter(out_handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for path in inputs:
            max_episode = -1
            with path.open("r", newline="", encoding="utf-8") as in_handle:
                reader = csv.DictReader(in_handle)
                for row in reader:
                    original_episode = int(float(row.get("episode", 0)))
                    max_episode = max(max_episode, original_episode)
                    row["episode"] = str(original_episode + episode_offset)
                    writer.writerow({name: row.get(name, "") for name in fieldnames})
                    written += 1
            episode_offset += max_episode + 1
    return written


def union_fieldnames(inputs: list[Path]) -> list[str]:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for path in inputs:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"CSV log has no header: {path}")
            for name in reader.fieldnames:
                if name not in seen:
                    fieldnames.append(name)
                    seen.add(name)
    if "episode" not in seen:
        raise ValueError("Merged logs must contain an episode column.")
    return fieldnames


if __name__ == "__main__":
    main()
