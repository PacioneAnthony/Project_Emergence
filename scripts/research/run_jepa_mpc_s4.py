"""Run paired S4 JEPA MPC-lite diagnostics on held-out simulator seeds."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np

from scripts.research.run_lnn_e1 import prevent_system_sleep


CHECKPOINT = Path("models/lnn_zoh_scan05_medium_dagger_002.pth")
JEPA_CHECKPOINT = Path("models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth")
ROOT = Path("data/processed/experiments/jepa_mpc_s4")


@dataclass(frozen=True)
class RunSpec:
    family: str
    protocol: str
    seed: int

    @property
    def tag(self) -> str:
        return f"{self.family}_{self.protocol}_seed{self.seed}"

    @property
    def directory(self) -> Path:
        return ROOT / self.tag

    @property
    def metrics(self) -> Path:
        return self.directory / "metrics.json"

    @property
    def rollout_log(self) -> Path:
        return Path("data/raw/jepa_mpc_s4") / f"{self.tag}.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run paired S4 JEPA MPC-lite diagnostics.")
    parser.add_argument("--nominal-seeds", type=int, nargs="+", default=[3101, 3102, 3103])
    parser.add_argument("--randomized-seeds", type=int, nargs="+", default=[3201, 3202, 3203])
    parser.add_argument("--steps", type=int, default=3000)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.steps <= 0:
        raise ValueError("--steps must be > 0.")
    if not CHECKPOINT.exists() or not JEPA_CHECKPOINT.exists():
        raise FileNotFoundError("S4 checkpoint or JEPA checkpoint is missing.")
    prevent_system_sleep()
    specs = build_specs(args.nominal_seeds, args.randomized_seeds)
    ROOT.mkdir(parents=True, exist_ok=True)
    write_manifest(specs, args)

    if not args.summary_only:
        for spec in specs:
            if spec.metrics.exists() and not args.force:
                print(f"Reusing {spec.metrics}", flush=True)
                continue
            run_spec(spec, args)
            write_summary(specs)

    summary = write_summary(specs)
    print(f"S4 status: {summary['completed_runs']}/{summary['expected_runs']} runs complete", flush=True)
    print(f"Summary: {ROOT / 'summary.md'}", flush=True)


def build_specs(nominal_seeds: list[int], randomized_seeds: list[int]) -> list[RunSpec]:
    specs = []
    for protocol, seeds in (("nominal", nominal_seeds), ("randomized", randomized_seeds)):
        for seed in seeds:
            for family in ("baseline", "slow_only", "conservative"):
                specs.append(RunSpec(family, protocol, int(seed)))
    return specs


def run_spec(spec: RunSpec, args: argparse.Namespace) -> None:
    spec.directory.mkdir(parents=True, exist_ok=True)
    spec.rollout_log.parent.mkdir(parents=True, exist_ok=True)
    module = "learning.rollout_lnn" if spec.family == "baseline" else "learning.rollout_jepa_mpc"
    command = [
        sys.executable,
        "-u",
        "-m",
        module,
        "--checkpoint",
        str(CHECKPOINT),
        "--episodes",
        "1",
        "--steps",
        str(args.steps),
        "--seed",
        str(spec.seed),
        "--device",
        args.device,
        "--output",
        str(spec.rollout_log),
        "--metrics-output",
        str(spec.metrics),
    ]
    if spec.protocol == "nominal":
        command.append("--no-domain-randomization")
    if spec.family != "baseline":
        command.extend(
            [
                "--jepa-checkpoint",
                str(JEPA_CHECKPOINT),
                "--candidate-profile",
                spec.family,
            ]
        )
    print(f"[S4] {spec.tag}", flush=True)
    with (spec.directory / "run.log").open("w", encoding="utf-8") as handle:
        completed = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"S4 run failed for {spec.tag}; see {spec.directory / 'run.log'}")


def write_manifest(specs: list[RunSpec], args: argparse.Namespace) -> None:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": str(CHECKPOINT),
        "jepa_checkpoint": str(JEPA_CHECKPOINT),
        "steps": int(args.steps),
        "selection_seeds_only": True,
        "runs": [spec.__dict__ for spec in specs],
    }
    (ROOT / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_summary(specs: list[RunSpec]) -> dict[str, Any]:
    rows = []
    for spec in specs:
        if not spec.metrics.exists():
            continue
        metrics = json.loads(spec.metrics.read_text(encoding="utf-8"))
        rows.append(
            {
                "family": spec.family,
                "protocol": spec.protocol,
                "seed": spec.seed,
                "collision_rate": float(metrics["collision_rate"]),
                "events_per_1000_steps": float(metrics["collision_events_per_1000_steps"]),
                "reward_mean_per_step": float(metrics["reward_mean_per_step"]),
                "intervention_rate": float(metrics.get("mpc", {}).get("intervention_rate", 0.0)),
            }
        )
    groups: dict[str, Any] = {}
    for protocol in ("nominal", "randomized"):
        for family in ("baseline", "slow_only", "conservative"):
            selected = [row for row in rows if row["protocol"] == protocol and row["family"] == family]
            groups[f"{family}_{protocol}"] = aggregate(selected)
    paired = paired_deltas(rows)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "expected_runs": len(specs),
        "completed_runs": len(rows),
        "runs": rows,
        "groups": groups,
        "paired_deltas_vs_baseline": paired,
    }
    (ROOT / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (ROOT / "summary.md").write_text(render_summary(payload), encoding="utf-8")
    return payload


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"n": len(rows)}
    for key in ("collision_rate", "events_per_1000_steps", "reward_mean_per_step", "intervention_rate"):
        values = np.asarray([row[key] for row in rows], dtype=np.float64)
        result[key] = {
            "mean": float(values.mean()) if len(values) else None,
            "std": float(values.std(ddof=1)) if len(values) > 1 else None,
        }
    return result


def paired_deltas(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {(row["family"], row["protocol"], row["seed"]): row for row in rows}
    result = {}
    for family in ("slow_only", "conservative"):
        for protocol in ("nominal", "randomized"):
            deltas = []
            seeds = sorted({row["seed"] for row in rows if row["protocol"] == protocol})
            for seed in seeds:
                baseline = lookup.get(("baseline", protocol, seed))
                candidate = lookup.get((family, protocol, seed))
                if baseline is not None and candidate is not None:
                    deltas.append(candidate["collision_rate"] - baseline["collision_rate"])
            values = np.asarray(deltas, dtype=np.float64)
            result[f"{family}_{protocol}"] = {
                "n": len(deltas),
                "mean_collision_rate_delta": float(values.mean()) if len(values) else None,
                "improved_seeds": int(np.sum(values < 0.0)) if len(values) else 0,
                "tied_seeds": int(np.sum(values == 0.0)) if len(values) else 0,
                "regressed_seeds": int(np.sum(values > 0.0)) if len(values) else 0,
            }
    return result


def render_summary(payload: dict[str, Any]) -> str:
    lines = [
        "# S4 - JEPA MPC-lite",
        "",
        f"Runs complets: {payload['completed_runs']} / {payload['expected_runs']}.",
        "",
        "| famille | protocole | n | collisions | evenements / 1000 | interventions |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for protocol in ("nominal", "randomized"):
        for family in ("baseline", "slow_only", "conservative"):
            group = payload["groups"][f"{family}_{protocol}"]
            lines.append(
                f"| `{family}` | {protocol} | {group['n']} | {format_percent(group['collision_rate'])} | "
                f"{format_number(group['events_per_1000_steps'])} | {format_percent(group['intervention_rate'])} |"
            )
    lines.extend(["", "## Differences appariees vs baseline", ""])
    for key, value in payload["paired_deltas_vs_baseline"].items():
        delta = value["mean_collision_rate_delta"]
        delta_text = "n/a" if delta is None else f"{100.0 * delta:+.2f} points"
        lines.append(
            f"- `{key}`: {delta_text}; ameliore {value['improved_seeds']}, "
            f"egal {value['tied_seeds']}, regresse {value['regressed_seeds']}."
        )
    return "\n".join(lines) + "\n"


def format_percent(stat: dict[str, float | None]) -> str:
    if stat["mean"] is None:
        return "n/a"
    std = "n/a" if stat["std"] is None else f"{100.0 * stat['std']:.2f}%"
    return f"{100.0 * stat['mean']:.2f}% +/- {std}"


def format_number(stat: dict[str, float | None]) -> str:
    if stat["mean"] is None:
        return "n/a"
    std = "n/a" if stat["std"] is None else f"{stat['std']:.2f}"
    return f"{stat['mean']:.2f} +/- {std}"


if __name__ == "__main__":
    main()
