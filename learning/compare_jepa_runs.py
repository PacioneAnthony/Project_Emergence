"""Compare JEPA evaluation metrics across experiment runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare JEPA metrics.json files.")
    parser.add_argument("metrics", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = [load_metric_row(path) for path in args.metrics]
    text = render_markdown(rows)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text)


def load_metric_row(path: Path) -> dict[str, Any]:
    metrics = json.loads(path.read_text(encoding="utf-8"))
    latent = metrics["latent_prediction"]
    decoder = metrics["observation_decoder"]
    probe = metrics["observation_probe"]
    health = metrics["latent_health"]
    dims = metrics.get("checkpoint_dims", {})
    return {
        "run": infer_run_name(path),
        "samples": int(metrics["n_samples"]),
        "latent_dim": int(dims.get("latent_dim", 0)),
        "latent_mse": float(latent["mse"]),
        "latent_persistence_mse": float(latent["persistence_mse"]),
        "latent_improvement": float(latent["improvement_vs_persistence"]),
        "obs_decoder_rmse": float(decoder["rmse_mean"]),
        "obs_probe_rmse": float(probe["rmse_mean"]),
        "obs_persistence_rmse": float(decoder["persistence_rmse_mean"]),
        "latent_std_mean": float(health["std_mean"]),
    }


def infer_run_name(path: Path) -> str:
    parts = path.parts
    if len(parts) >= 3 and parts[-2] == "eval":
        return parts[-3]
    return path.parent.name


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# JEPA Run Comparison",
        "",
        "| run | samples | latent dim | latent mse | latent impr. | decoder rmse | probe rmse | persistence rmse | latent std mean |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {run} | {samples} | {latent_dim} | {latent_mse:.6f} | {latent_improvement:.2%} | "
            "{obs_decoder_rmse:.6f} | {obs_probe_rmse:.6f} | {obs_persistence_rmse:.6f} | "
            "{latent_std_mean:.4f} |".format(**row)
        )

    lines.extend(
        [
            "",
            "Notes:",
            "",
            "- `latent impr.` is improvement against latent persistence baseline.",
            "- Decoder/probe RMSE should be compared against `persistence rmse`; lower is better.",
            "- `probe rmse` measures how linearly decodable the target observation is from the predicted latent.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
