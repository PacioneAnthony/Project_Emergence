"""Run E3: multi-seed LNN training with checkpoint selection by mini-rollouts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from scripts.research.run_lnn_e1 import (
    JEPA_CHECKPOINT,
    TRAIN_LOG,
    RunSpec,
    aggregate_rows,
    load_json,
    load_rollout_metrics,
    prevent_system_sleep,
    run_stage,
)


EXPERIMENT_ROOT = Path("data/processed/experiments")
SUMMARY_DIR = EXPERIMENT_ROOT / "lnn_e3_rollout_selection"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run E3 rollout-selected LNN experiments.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[4202, 5202, 6202])
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--epochs", type=int, default=2500)
    parser.add_argument("--rollout-eval-every", type=int, default=250)
    parser.add_argument("--rollout-eval-episodes", type=int, default=5)
    parser.add_argument("--rollout-eval-steps", type=int, default=2000)
    parser.add_argument("--selection-nominal-seed", type=int, default=3101)
    parser.add_argument("--selection-randomized-seed", type=int, default=3201)
    parser.add_argument("--selection-min-mean-forward-speed", type=float, default=0.05)
    parser.add_argument("--final-nominal-seed", type=int, default=1001)
    parser.add_argument("--final-randomized-seed", type=int, default=2201)
    parser.add_argument("--final-episodes", type=int, default=5)
    parser.add_argument("--final-steps", type=int, default=6000)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only-tag", action="append", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)
    prevent_system_sleep()
    specs = build_specs(args.seeds)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    write_manifest(specs, args)

    if not args.summary_only:
        for spec in specs:
            if args.only_tag and spec.tag not in set(args.only_tag):
                continue
            if args.force or not (spec.checkpoint.exists() and spec.train_metrics.exists()):
                run_stage(spec, "train", train_command(spec, args), spec.train_dir / "train.log", args.dry_run)
            else:
                print(f"Reusing training artifacts for {spec.tag}", flush=True)

            if args.dry_run or spec.checkpoint.exists():
                for randomized in (False, True):
                    metrics_path = spec.rollout_metrics(randomized)
                    if args.force or not metrics_path.exists():
                        stage = "rollout_randomized" if randomized else "rollout_nominal"
                        run_stage(
                            spec,
                            stage,
                            final_rollout_command(spec, args, randomized),
                            metrics_path.parent / f"{stage}.log",
                            args.dry_run,
                        )
                    else:
                        print(f"Reusing {metrics_path}", flush=True)
            if not args.dry_run:
                write_summary(specs)

    if not args.dry_run:
        summary = write_summary(specs)
        print(f"E3 status: {summary['completed_runs']}/{summary['expected_runs']} runs complete", flush=True)
        print(f"Summary: {SUMMARY_DIR / 'summary.md'}", flush=True)


def validate_args(args: argparse.Namespace) -> None:
    positive = (
        args.epochs,
        args.rollout_eval_every,
        args.rollout_eval_episodes,
        args.rollout_eval_steps,
        args.final_episodes,
        args.final_steps,
    )
    if any(value <= 0 for value in positive):
        raise ValueError("Epoch and rollout sizes must be positive.")
    if not TRAIN_LOG.exists():
        raise FileNotFoundError(TRAIN_LOG)
    if not JEPA_CHECKPOINT.exists():
        raise FileNotFoundError(JEPA_CHECKPOINT)


def build_specs(seeds: list[int]) -> list[RunSpec]:
    specs: list[RunSpec] = []
    for seed in seeds:
        specs.append(RunSpec("control", int(seed), f"lnn_e3_control_seed{seed}"))
        specs.append(RunSpec("aux_0.3", int(seed), f"lnn_e3_aux_w03_seed{seed}", aux_weight=0.3))
    return specs


def train_command(spec: RunSpec, args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "-u",
        "-m",
        "learning.train_lnn",
        "--log",
        str(TRAIN_LOG),
        "--epochs",
        str(args.epochs),
        "--batch-size",
        "256",
        "--sequence-length",
        "64",
        "--state-dim",
        "64",
        "--hidden-dim",
        "128",
        "--lr",
        "3e-4",
        "--eval-every",
        "50",
        "--early-stopping-patience",
        "0",
        "--seed",
        str(spec.seed),
        "--device",
        args.device,
        "--rollout-select",
        "--rollout-eval-every",
        str(args.rollout_eval_every),
        "--rollout-eval-episodes",
        str(args.rollout_eval_episodes),
        "--rollout-eval-steps",
        str(args.rollout_eval_steps),
        "--rollout-nominal-seed",
        str(args.selection_nominal_seed),
        "--rollout-randomized-seed",
        str(args.selection_randomized_seed),
        "--rollout-min-mean-forward-speed",
        str(args.selection_min_mean_forward_speed),
        "--output",
        str(spec.checkpoint),
        "--metrics-output",
        str(spec.train_metrics),
    ]
    if spec.aux_weight > 0.0:
        command.extend(
            [
                "--jepa-aux-checkpoint",
                str(JEPA_CHECKPOINT),
                "--jepa-aux-weight",
                str(spec.aux_weight),
                "--jepa-aux-head-hidden-dim",
                "128",
            ]
        )
    return command


def final_rollout_command(spec: RunSpec, args: argparse.Namespace, randomized: bool) -> list[str]:
    command = [
        sys.executable,
        "-u",
        "-m",
        "learning.rollout_lnn",
        "--checkpoint",
        str(spec.checkpoint),
        "--episodes",
        str(args.final_episodes),
        "--steps",
        str(args.final_steps),
        "--seed",
        str(args.final_randomized_seed if randomized else args.final_nominal_seed),
        "--dt",
        "0.02",
        "--pwm-period",
        "0.02",
        "--device",
        args.device,
        "--output",
        str(spec.rollout_log(randomized)),
        "--metrics-output",
        str(spec.rollout_metrics(randomized)),
    ]
    if not randomized:
        command.append("--no-domain-randomization")
    return command


def write_manifest(specs: list[RunSpec], args: argparse.Namespace) -> None:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_protocol": {
            "nominal_seed": args.selection_nominal_seed,
            "randomized_seed": args.selection_randomized_seed,
            "episodes": args.rollout_eval_episodes,
            "steps": args.rollout_eval_steps,
            "every_epochs": args.rollout_eval_every,
            "minimum_mean_forward_speed": args.selection_min_mean_forward_speed,
        },
        "final_protocol": {
            "nominal_seed": args.final_nominal_seed,
            "randomized_seed": args.final_randomized_seed,
            "episodes": args.final_episodes,
            "steps": args.final_steps,
        },
        "runs": [{"family": spec.family, "seed": spec.seed, "tag": spec.tag} for spec in specs],
    }
    (SUMMARY_DIR / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_summary(specs: list[RunSpec]) -> dict[str, Any]:
    rows = [row for spec in specs if (row := load_run_row(spec)) is not None]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["family"]), []).append(row)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expected_runs": len(specs),
        "completed_runs": len(rows),
        "runs": rows,
        "families": {name: aggregate_rows(values) for name, values in grouped.items()},
    }
    (SUMMARY_DIR / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (SUMMARY_DIR / "summary.md").write_text(render_summary(payload), encoding="utf-8")
    return payload


def load_run_row(spec: RunSpec) -> dict[str, Any] | None:
    paths = (spec.train_metrics, spec.rollout_metrics(False), spec.rollout_metrics(True))
    if not all(path.exists() for path in paths):
        return None
    train = load_json(spec.train_metrics)
    nominal = load_rollout_metrics(spec.rollout_metrics(False))
    randomized = load_rollout_metrics(spec.rollout_metrics(True))
    return {
        "family": spec.family,
        "seed": spec.seed,
        "tag": spec.tag,
        "best_epoch": int(train["best_epoch"]),
        "best_offline_epoch": int(train["best_offline_epoch"]),
        "validation_rmse": float(train["validation"]["rmse_mean"]),
        "nominal_collision_rate": float(nominal["collision_rate"]),
        "nominal_collision_events": int(nominal["collision_events"]),
        "nominal_events_per_1000_steps": float(nominal["collision_events_per_1000_steps"]),
        "randomized_collision_rate": float(randomized["collision_rate"]),
        "randomized_collision_events": int(randomized["collision_events"]),
        "randomized_events_per_1000_steps": float(randomized["collision_events_per_1000_steps"]),
    }


def render_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# E3 - Selection de checkpoint par mini-rollouts",
        "",
        f"Runs complets: {payload['completed_runs']} / {payload['expected_runs']}.",
        "",
        "| famille | n | collisions nominales | evenements nominaux / 1000 | collisions randomisees | evenements randomises / 1000 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for family in ("control", "aux_0.3"):
        summary = payload["families"].get(family)
        if summary is None:
            continue
        lines.append(
            f"| `{family}` | {summary['n']} | {format_percent(summary['nominal_collision_rate'])} | "
            f"{format_stat(summary['nominal_events_per_1000_steps'])} | "
            f"{format_percent(summary['randomized_collision_rate'])} | "
            f"{format_stat(summary['randomized_events_per_1000_steps'])} |"
        )
    lines.extend(
        [
            "",
            "Les rollouts finaux utilisent des graines distinctes de celles de selection.",
            "Le succes E3 exige une dispersion inferieure a E1 sans regression moyenne sur le pire protocole.",
            "",
            "## Runs",
            "",
            "| famille | seed | epoch selectionne | meilleur epoch RMSE | nominal | ev. nom. | randomise | ev. rand. |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["runs"]:
        lines.append(
            f"| `{row['family']}` | {row['seed']} | {row['best_epoch']} | {row['best_offline_epoch']} | "
            f"{100.0 * row['nominal_collision_rate']:.2f}% | {row['nominal_collision_events']} | "
            f"{100.0 * row['randomized_collision_rate']:.2f}% | {row['randomized_collision_events']} |"
        )
    return "\n".join(lines) + "\n"


def format_stat(stat: dict[str, Any]) -> str:
    if stat["mean"] is None:
        return "n/a"
    std = "n/a" if stat["std"] is None else f"{stat['std']:.3f}"
    return f"{stat['mean']:.3f} +/- {std} [{stat['min']:.3f}, {stat['max']:.3f}]"


def format_percent(stat: dict[str, Any]) -> str:
    if stat["mean"] is None:
        return "n/a"
    std = "n/a" if stat["std"] is None else f"{100.0 * stat['std']:.2f}%"
    return f"{100.0 * stat['mean']:.2f}% +/- {std} [{100.0 * stat['min']:.2f}%, {100.0 * stat['max']:.2f}%]"


if __name__ == "__main__":
    main()
