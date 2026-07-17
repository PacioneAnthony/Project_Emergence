"""Active exploration vs babbling campaign (resumable).

Protocol: docs/research/active_exploration_probe.md. 2 conditions x 3 seeds,
each run alternates collection and training rounds at identical budgets;
verdicts H-A1 (k=3 moving prediction ratio) and H-A2 (angle probe MAE) are
judged on the final full evaluation with disjoint min-max intervals.
"""

from __future__ import annotations

import argparse
import atexit
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

SEEDS = (4301, 4302, 4303)
CONDITIONS = ("active", "babbling")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Active exploration campaign on the bench twin.")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--frames-per-round", type=int, default=2500)
    parser.add_argument("--epochs-per-round", type=int, default=60)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--prefix", type=str, default="")
    parser.add_argument("--summary-dir", type=Path, default=Path("data/processed/experiments/active_exploration_001"))
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    return parser


def prevent_system_sleep() -> None:
    if os.name != "nt":
        return
    import ctypes

    es_continuous = 0x80000000
    es_system_required = 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(es_continuous | es_system_required)
    atexit.register(ctypes.windll.kernel32.SetThreadExecutionState, es_continuous)


def run_tag(prefix: str, condition: str, seed: int) -> str:
    return f"{prefix}active_explo_{condition}_seed{seed}"


def metrics_path(tag: str) -> Path:
    return Path("data/processed/experiments") / tag / "metrics.json"


def is_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "complete"
    except (json.JSONDecodeError, OSError):
        return False


def launch_run(args: argparse.Namespace, condition: str, seed: int) -> None:
    tag = run_tag(args.prefix, condition, seed)
    command = [
        sys.executable,
        "-m",
        "learning.active_exploration",
        "--condition",
        condition,
        "--seed",
        str(seed),
        "--rounds",
        str(args.rounds),
        "--frames-per-round",
        str(args.frames_per_round),
        "--epochs-per-round",
        str(args.epochs_per_round),
        "--device",
        args.device,
        "--output",
        f"models/{tag}.pth",
        "--metrics-output",
        str(metrics_path(tag)),
    ]
    if args.smoke:
        command.extend(["--frames-per-episode", "100", "--val-subsample", "500"])
    print(f"[active] run {tag} ...", flush=True)
    subprocess.run(command, check=True)


def stat(values: list[float]) -> str:
    if not values:
        return "n/a"
    if len(values) == 1:
        return f"{values[0]:.4f}"
    return f"{statistics.mean(values):.4f} +/- {statistics.stdev(values):.4f} [{min(values):.4f}, {max(values):.4f}]"


def verdict(active_values: list[float], control_values: list[float]) -> str:
    if not active_values or not control_values:
        return "indéterminé"
    disjoint = max(active_values) < min(control_values)
    better_mean = statistics.mean(active_values) < statistics.mean(control_values)
    if better_mean and disjoint:
        return "VALIDÉE"
    return "moyenne favorable, intervalles non disjoints" if better_mean else "REJETÉE"


def summarize(args: argparse.Namespace, seeds: tuple[int, ...]) -> str:
    rows = []
    collected: dict[str, dict[str, list[float]]] = {
        c: {"ratio_k3": [], "angle": [], "entropy": []} for c in CONDITIONS
    }
    curves: dict[str, list[list[float]]] = {c: [] for c in CONDITIONS}
    for condition in CONDITIONS:
        for seed in seeds:
            path = metrics_path(run_tag(args.prefix, condition, seed))
            if not is_complete(path):
                rows.append(f"| {condition} | {seed} | incomplet | | | |")
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            final = data["final_eval"]
            ratio_k3 = float(final["per_horizon"]["3"]["pred_to_copy_ratio_moving"])
            angle = float(final["angle_probe_mae_deg"])
            entropy = float(statistics.mean(r["coverage_entropy"] for r in data["rounds"]))
            collected[condition]["ratio_k3"].append(ratio_k3)
            collected[condition]["angle"].append(angle)
            collected[condition]["entropy"].append(entropy)
            curves[condition].append(
                [float(r["eval"]["per_horizon"]["3"]["pred_to_copy_ratio_moving"]) for r in data["rounds"]]
            )
            rows.append(
                f"| {condition} | {seed} | {ratio_k3:.4f} | {angle:.2f} | {entropy:.3f} | {data.get('frames_budget', '?')} |"
            )

    active = collected["active"]
    control = collected["babbling"]
    h_a1 = verdict(active["ratio_k3"], control["ratio_k3"])
    h_a2 = verdict(active["angle"], control["angle"])

    curve_lines = []
    for condition in CONDITIONS:
        if curves[condition]:
            rounds_count = min(len(c) for c in curves[condition])
            means = [
                statistics.mean(c[i] for c in curves[condition]) for i in range(rounds_count)
            ]
            curve_lines.append(f"- courbe ratio k=3 mouvement `{condition}` (moyenne par round): " + ", ".join(f"{m:.4f}" for m in means))

    return "\n".join(
        [
            "# Exploration active par learning progress vs babbling (jumeau du banc)",
            "",
            f"Protocole: `docs/research/active_exploration_probe.md`.",
            "",
            "| condition | graine | ratio k=3 mouvement (final) | MAE angle (deg) | entropie couverture | images |",
            "|---|---|---|---|---|---|",
            *rows,
            "",
            f"- ratio k=3 `active`: {stat(active['ratio_k3'])}",
            f"- ratio k=3 `babbling`: {stat(control['ratio_k3'])}",
            f"- MAE angle `active`: {stat(active['angle'])}",
            f"- MAE angle `babbling`: {stat(control['angle'])}",
            f"- entropie `active`: {stat(active['entropy'])} | `babbling`: {stat(control['entropy'])}",
            *curve_lines,
            "",
            f"**H-A1 (prédiction k=3 mouvement, active < babbling, intervalles disjoints): {h_a1}**",
            f"**H-A2 (MAE angle, active < babbling, intervalles disjoints): {h_a2}**",
            "",
        ]
    )


def main() -> None:
    args = build_parser().parse_args()
    seeds = SEEDS
    if args.smoke:
        args.rounds = 2
        args.frames_per_round = 300
        args.epochs_per_round = 2
        args.prefix = "smoke_"
        args.summary_dir = Path("data/processed/experiments/active_exploration_smoke")
        seeds = (4301,)

    prevent_system_sleep()
    started = time.perf_counter()

    if not args.summary_only:
        for condition in CONDITIONS:
            for seed in seeds:
                if is_complete(metrics_path(run_tag(args.prefix, condition, seed))):
                    print(f"[active] {run_tag(args.prefix, condition, seed)} deja complet, saute.", flush=True)
                    continue
                launch_run(args, condition, seed)

    summary = summarize(args, seeds)
    args.summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary_dir / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"[active] termine en {(time.perf_counter() - started) / 60.0:.1f} min, resume: {summary_path}", flush=True)
    print(summary, flush=True)


if __name__ == "__main__":
    main()
