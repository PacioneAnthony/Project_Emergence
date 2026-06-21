"""Run E2: cosine JEPA auxiliary weight with E3 rollout checkpoint selection."""

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
SUMMARY_DIR = EXPERIMENT_ROOT / "lnn_e2_aux_schedule"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run E2 scheduled JEPA auxiliary experiments.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[4202, 5202, 6202])
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--epochs", type=int, default=2500)
    parser.add_argument("--initial-weight", type=float, default=1.0)
    parser.add_argument("--final-weight", type=float, default=0.1)
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
        print(f"E2 status: {summary['completed_runs']}/{summary['expected_runs']} runs complete", flush=True)
        print(f"Summary: {SUMMARY_DIR / 'summary.md'}", flush=True)


def validate_args(args: argparse.Namespace) -> None:
    if args.epochs <= 0 or args.rollout_eval_every <= 0:
        raise ValueError("Epoch counts must be positive.")
    if args.initial_weight < 0.0 or args.final_weight < 0.0:
        raise ValueError("Auxiliary weights must be non-negative.")
    if args.selection_min_mean_forward_speed < 0.0:
        raise ValueError("Selection speed threshold must be non-negative.")
    if not TRAIN_LOG.exists() or not JEPA_CHECKPOINT.exists():
        raise FileNotFoundError("E2 training data or JEPA checkpoint is missing.")


def build_specs(seeds: list[int]) -> list[RunSpec]:
    return [RunSpec("aux_1.0_to_0.1", int(seed), f"lnn_e2_aux_schedule_seed{seed}", 1.0) for seed in seeds]


def train_command(spec: RunSpec, args: argparse.Namespace) -> list[str]:
    return [
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
        "--jepa-aux-checkpoint",
        str(JEPA_CHECKPOINT),
        "--jepa-aux-weight",
        str(args.initial_weight),
        "--jepa-aux-final-weight",
        str(args.final_weight),
        "--jepa-aux-head-hidden-dim",
        "128",
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
        "schedule": {"type": "cosine", "initial_weight": args.initial_weight, "final_weight": args.final_weight},
        "selection": {
            "nominal_seed": args.selection_nominal_seed,
            "randomized_seed": args.selection_randomized_seed,
            "episodes": args.rollout_eval_episodes,
            "steps": args.rollout_eval_steps,
            "minimum_mean_forward_speed": args.selection_min_mean_forward_speed,
        },
        "runs": [{"seed": spec.seed, "tag": spec.tag} for spec in specs],
    }
    (SUMMARY_DIR / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_summary(specs: list[RunSpec]) -> dict[str, Any]:
    rows = [row for spec in specs if (row := load_run_row(spec)) is not None]
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expected_runs": len(specs),
        "completed_runs": len(rows),
        "runs": rows,
        "aggregate": aggregate_rows(rows),
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
    aggregate = payload["aggregate"]
    lines = [
        "# E2 - Schedule cosine du poids JEPA",
        "",
        f"Runs complets: {payload['completed_runs']} / {payload['expected_runs']}.",
        "",
    ]
    if aggregate["n"]:
        lines.extend(
            [
                f"- nominal: {format_percent(aggregate['nominal_collision_rate'])}",
                f"- evenements nominaux / 1000: {format_stat(aggregate['nominal_events_per_1000_steps'])}",
                f"- randomise: {format_percent(aggregate['randomized_collision_rate'])}",
                f"- evenements randomises / 1000: {format_stat(aggregate['randomized_events_per_1000_steps'])}",
                "",
                "| seed | epoch selectionne | nominal | ev. nom. | randomise | ev. rand. |",
                "|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in payload["runs"]:
            lines.append(
                f"| {row['seed']} | {row['best_epoch']} | {100.0 * row['nominal_collision_rate']:.2f}% | "
                f"{row['nominal_collision_events']} | {100.0 * row['randomized_collision_rate']:.2f}% | "
                f"{row['randomized_collision_events']} |"
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
