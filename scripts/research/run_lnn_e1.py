"""Run and summarize the E1 multi-seed LNN replication campaign."""

from __future__ import annotations

import argparse
import atexit
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any


TRAIN_LOG = Path("data/raw/sim2d_zoh_scan05_medium_dagger_001.csv")
JEPA_CHECKPOINT = Path("models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth")
EXPERIMENT_ROOT = Path("data/processed/experiments")
SUMMARY_DIR = EXPERIMENT_ROOT / "lnn_e1_multiseed"


@dataclass(frozen=True)
class RunSpec:
    family: str
    seed: int
    tag: str
    aux_weight: float = 0.0

    @property
    def checkpoint(self) -> Path:
        return Path("models") / f"{self.tag}.pth"

    @property
    def train_dir(self) -> Path:
        return EXPERIMENT_ROOT / self.tag

    @property
    def train_metrics(self) -> Path:
        return self.train_dir / "metrics.json"

    def rollout_tag(self, randomized: bool) -> str:
        suffix = "rollout_randomized_001" if randomized else "rollout_001"
        return f"{self.tag}_{suffix}"

    def rollout_log(self, randomized: bool) -> Path:
        return Path("data/raw") / f"{self.rollout_tag(randomized)}.csv"

    def rollout_metrics(self, randomized: bool) -> Path:
        return EXPERIMENT_ROOT / self.rollout_tag(randomized) / "metrics.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run E1 multi-seed LNN replications and aggregate closed-loop metrics.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[4202, 5202, 6202])
    parser.add_argument("--reference-seeds", type=int, nargs="+", default=[7301, 7302])
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--epochs", type=int, default=2500)
    parser.add_argument("--rollout-episodes", type=int, default=5)
    parser.add_argument("--rollout-steps", type=int, default=6000)
    parser.add_argument("--nominal-seed", type=int, default=1001)
    parser.add_argument("--randomized-seed", type=int, default=2201)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-new-trainings", type=int, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)
    prevent_system_sleep()
    specs = build_specs(args.seeds, args.reference_seeds)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    write_manifest(specs, args)

    new_trainings = 0
    if not args.summary_only:
        for spec in specs:
            needs_training = args.force or not (spec.checkpoint.exists() and spec.train_metrics.exists())
            if needs_training and args.max_new_trainings is not None and new_trainings >= args.max_new_trainings:
                print(f"Training limit reached; leaving {spec.tag} pending.", flush=True)
                continue
            if needs_training:
                run_stage(spec, "train", train_command(spec, args), spec.train_dir / "train.log", args.dry_run)
                new_trainings += 1
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
                            rollout_command(spec, args, randomized),
                            metrics_path.parent / f"{stage}.log",
                            args.dry_run,
                        )
                    else:
                        print(f"Reusing {metrics_path}", flush=True)

            if not args.dry_run:
                write_summary(specs)

    if not args.dry_run:
        summary = write_summary(specs)
        print(f"E1 status: {summary['completed_runs']}/{summary['expected_runs']} runs complete", flush=True)
        print(f"Summary: {SUMMARY_DIR / 'summary.md'}", flush=True)


def validate_args(args: argparse.Namespace) -> None:
    if args.epochs <= 0 or args.rollout_episodes <= 0 or args.rollout_steps <= 0:
        raise ValueError("Epochs, rollout episodes and rollout steps must be positive.")
    if args.max_new_trainings is not None and args.max_new_trainings < 0:
        raise ValueError("--max-new-trainings must be >= 0.")
    if not TRAIN_LOG.exists():
        raise FileNotFoundError(TRAIN_LOG)
    if not JEPA_CHECKPOINT.exists():
        raise FileNotFoundError(JEPA_CHECKPOINT)


def build_specs(seeds: list[int], reference_seeds: list[int]) -> list[RunSpec]:
    existing_tags = {
        ("control", 4202): "lnn_dagger_seed4202_control_001",
        ("aux_0.3", 4202): "lnn_jepa_aux_w03_001",
        ("aux_1.0", 4202): "lnn_jepa_aux_w10_001",
    }
    specs: list[RunSpec] = []
    for seed in seeds:
        for family, weight, slug in (
            ("control", 0.0, "control"),
            ("aux_0.3", 0.3, "aux_w03"),
            ("aux_1.0", 1.0, "aux_w10"),
        ):
            tag = existing_tags.get((family, seed), f"lnn_e1_{slug}_seed{seed}")
            specs.append(RunSpec(family=family, seed=int(seed), tag=tag, aux_weight=weight))
    for seed in reference_seeds:
        specs.append(RunSpec(family="reference_extra", seed=int(seed), tag=f"lnn_e1_reference_seed{seed}"))
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
        "20",
        "--seed",
        str(spec.seed),
        "--device",
        args.device,
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


def rollout_command(spec: RunSpec, args: argparse.Namespace, randomized: bool) -> list[str]:
    command = [
        sys.executable,
        "-u",
        "-m",
        "learning.rollout_lnn",
        "--checkpoint",
        str(spec.checkpoint),
        "--episodes",
        str(args.rollout_episodes),
        "--steps",
        str(args.rollout_steps),
        "--seed",
        str(args.randomized_seed if randomized else args.nominal_seed),
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


def run_stage(spec: RunSpec, stage: str, command: list[str], log_path: Path, dry_run: bool) -> None:
    print(f"\n=== {spec.tag} / {stage} ===", flush=True)
    print(subprocess.list2cmdline(command), flush=True)
    if dry_run:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            handle.write(line)
            handle.flush()
        code = process.wait()
    if code != 0:
        raise subprocess.CalledProcessError(code, command)


def write_manifest(specs: list[RunSpec], args: argparse.Namespace) -> None:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_log": str(TRAIN_LOG),
        "jepa_checkpoint": str(JEPA_CHECKPOINT),
        "training_seeds": [int(value) for value in args.seeds],
        "reference_seeds": [int(value) for value in args.reference_seeds],
        "nominal_rollout_seed": int(args.nominal_seed),
        "randomized_rollout_seed": int(args.randomized_seed),
        "runs": [spec_to_dict(spec) for spec in specs],
    }
    (SUMMARY_DIR / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def spec_to_dict(spec: RunSpec) -> dict[str, Any]:
    return {
        "family": spec.family,
        "seed": spec.seed,
        "tag": spec.tag,
        "aux_weight": spec.aux_weight,
        "checkpoint": str(spec.checkpoint),
        "train_metrics": str(spec.train_metrics),
        "nominal_metrics": str(spec.rollout_metrics(False)),
        "randomized_metrics": str(spec.rollout_metrics(True)),
    }


def write_summary(specs: list[RunSpec]) -> dict[str, Any]:
    rows = [row for spec in specs if (row := load_run_row(spec)) is not None]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["family"]), []).append(row)
    observation_only = grouped.get("control", []) + grouped.get("reference_extra", [])

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expected_runs": len(specs),
        "completed_runs": len(rows),
        "runs": rows,
        "families": {name: aggregate_rows(values) for name, values in grouped.items()},
        "observation_only_combined": aggregate_rows(observation_only),
        "historical_anchor": load_historical_anchor(),
    }
    (SUMMARY_DIR / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (SUMMARY_DIR / "summary.md").write_text(render_summary_markdown(payload), encoding="utf-8")
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
        "validation_rmse": float(train["validation"]["rmse_mean"]),
        "nominal_collision_rate": float(nominal["collision_rate"]),
        "nominal_collision_events": int(nominal["collision_events"]),
        "nominal_events_per_1000_steps": float(nominal["collision_events_per_1000_steps"]),
        "randomized_collision_rate": float(randomized["collision_rate"]),
        "randomized_collision_events": int(randomized["collision_events"]),
        "randomized_events_per_1000_steps": float(randomized["collision_events_per_1000_steps"]),
    }


def load_rollout_metrics(path: Path) -> dict[str, Any]:
    metrics = load_json(path)
    if "collision_events" not in metrics:
        log_path = Path(metrics["log"])
        events = collision_events_from_csv(log_path)
        total_steps = max(1, int(metrics["total_steps"]))
        metrics["collision_events"] = events
        metrics["collision_events_per_1000_steps"] = 1000.0 * events / total_steps
    return metrics


def collision_events_from_csv(path: Path) -> int:
    events = 0
    previous_episode: str | None = None
    in_collision = False
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            episode = row.get("episode")
            if episode != previous_episode:
                previous_episode = episode
                in_collision = False
            collision = str(row.get("collision", "0")).strip().lower() in {"1", "true", "yes"}
            if collision and not in_collision:
                events += 1
            in_collision = collision
    return events


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "validation_rmse",
        "nominal_collision_rate",
        "nominal_events_per_1000_steps",
        "randomized_collision_rate",
        "randomized_events_per_1000_steps",
    )
    result: dict[str, Any] = {"n": len(rows), "seeds": [int(row["seed"]) for row in rows]}
    for metric in metrics:
        values = [float(row[metric]) for row in rows]
        result[metric] = summarize_values(values)
    return result


def summarize_values(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "std": None, "min": None, "max": None}
    return {
        "mean": statistics.fmean(values),
        "std": statistics.stdev(values) if len(values) >= 2 else None,
        "min": min(values),
        "max": max(values),
    }


def load_historical_anchor() -> dict[str, Any] | None:
    nominal_path = EXPERIMENT_ROOT / "lnn_zoh_scan05_medium_dagger_002_rollout_001" / "metrics.json"
    randomized_path = EXPERIMENT_ROOT / "lnn_zoh_scan05_medium_dagger_002_rollout_randomized_001" / "metrics.json"
    if not nominal_path.exists() or not randomized_path.exists():
        return None
    nominal = load_rollout_metrics(nominal_path)
    randomized = load_rollout_metrics(randomized_path)
    return {
        "tag": "lnn_zoh_scan05_medium_dagger_002",
        "training_seed": None,
        "nominal_collision_rate": float(nominal["collision_rate"]),
        "nominal_collision_events": int(nominal["collision_events"]),
        "randomized_collision_rate": float(randomized["collision_rate"]),
        "randomized_collision_events": int(randomized["collision_events"]),
    }


def render_summary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# E1 - Replication multi-graines LNN",
        "",
        f"Runs complets: {payload['completed_runs']} / {payload['expected_runs']}.",
        "",
        "| famille | n | RMSE validation | collisions nominales | evenements nominaux / 1000 | collisions randomisees | evenements randomises / 1000 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    order = ("control", "aux_0.3", "aux_1.0", "reference_extra")
    for family in order:
        summary = payload["families"].get(family)
        if summary is None:
            continue
        lines.append(
            f"| `{family}` | {summary['n']} | {format_stat(summary['validation_rmse'])} | "
            f"{format_percent_stat(summary['nominal_collision_rate'])} | "
            f"{format_stat(summary['nominal_events_per_1000_steps'])} | "
            f"{format_percent_stat(summary['randomized_collision_rate'])} | "
            f"{format_stat(summary['randomized_events_per_1000_steps'])} |"
        )
    lines.extend(
        [
            "",
            "Les intervalles affiches sont min-max entre graines d'entrainement; `+/-` est l'ecart-type echantillon.",
            "Le checkpoint historique `dagger_002` reste une ancre, mais sa graine d'entrainement est inconnue et il n'entre pas dans les moyennes E1.",
            (
                "E1 est complet; la decision suivante est documentee dans `docs/research/jepa_lnn_e1_results.md`."
                if all(payload["families"].get(name, {}).get("n", 0) >= 3 for name in ("control", "aux_0.3", "aux_1.0"))
                else "Aucune decision sur E2 ne doit etre prise avant que les trois familles principales aient chacune au moins trois runs complets."
            ),
            "",
            "## Runs",
            "",
            "| famille | seed | RMSE | nominal | ev. nom. | randomise | ev. rand. |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["runs"]:
        lines.append(
            f"| `{row['family']}` | {row['seed']} | {row['validation_rmse']:.6f} | "
            f"{100.0 * row['nominal_collision_rate']:.2f}% | {row['nominal_collision_events']} | "
            f"{100.0 * row['randomized_collision_rate']:.2f}% | {row['randomized_collision_events']} |"
        )
    return "\n".join(lines) + "\n"


def format_stat(stat: dict[str, Any]) -> str:
    if stat["mean"] is None:
        return "n/a"
    spread = "n/a" if stat["std"] is None or not math.isfinite(stat["std"]) else f"{stat['std']:.3f}"
    return f"{stat['mean']:.3f} +/- {spread} [{stat['min']:.3f}, {stat['max']:.3f}]"


def format_percent_stat(stat: dict[str, Any]) -> str:
    if stat["mean"] is None:
        return "n/a"
    spread = "n/a" if stat["std"] is None else f"{100.0 * stat['std']:.2f}%"
    return f"{100.0 * stat['mean']:.2f}% +/- {spread} [{100.0 * stat['min']:.2f}%, {100.0 * stat['max']:.2f}%]"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def prevent_system_sleep() -> None:
    if os.name != "nt":
        return
    import ctypes

    es_continuous = 0x80000000
    es_system_required = 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(es_continuous | es_system_required)
    atexit.register(ctypes.windll.kernel32.SetThreadExecutionState, es_continuous)


if __name__ == "__main__":
    main()
