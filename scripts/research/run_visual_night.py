"""Overnight visual sensorimotor campaign on the bench twin (resumable).

Protocol pre-registered in docs/research/visual_bench_probe.md:
corpus generation (CPU workers) -> 2 variants x 3 seeds of visual JEPA
training (GPU) -> summary with H1/H2/H3 verdicts. Completed runs are
skipped, so the runner can be relaunched after an interruption.
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
VARIANTS = ("action", "no_action")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Overnight visual JEPA campaign on the bench twin.")
    parser.add_argument("--corpus", type=Path, default=Path("data/raw/bench_visual_corpus"))
    parser.add_argument("--corpus-episodes", type=int, default=120)
    parser.add_argument("--corpus-seconds", type=float, default=90.0)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--eval-every", type=int, default=4)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--summary-dir", type=Path, default=Path("data/processed/experiments/visual_night_001"))
    parser.add_argument("--prefix", type=str, default="", help="Tag prefix for this campaign's runs (e.g. v2_).")
    parser.add_argument("--select", choices=("ratio", "final"), default="ratio", help="Checkpoint selection passed to the trainer.")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Tiny end-to-end check of the whole night pipeline.")
    return parser


def prevent_system_sleep() -> None:
    if os.name != "nt":
        return
    import ctypes

    es_continuous = 0x80000000
    es_system_required = 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(es_continuous | es_system_required)
    atexit.register(ctypes.windll.kernel32.SetThreadExecutionState, es_continuous)


def run_tag(variant: str, seed: int, prefix: str = "") -> str:
    return f"{prefix}visual_jepa_{variant}_seed{seed}"


def metrics_path(tag: str) -> Path:
    return Path("data/processed/experiments") / tag / "metrics.json"


def is_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "complete"
    except (json.JSONDecodeError, OSError):
        return False


def launch_training(args: argparse.Namespace, variant: str, seed: int) -> None:
    tag = run_tag(variant, seed, args.tag_prefix)
    command = [
        sys.executable,
        "-m",
        "learning.train_visual_jepa",
        "--corpus",
        str(args.corpus),
        "--epochs",
        str(args.epochs),
        "--eval-every",
        str(args.eval_every),
        "--early-stopping-patience",
        str(args.patience),
        "--batch-size",
        str(args.batch_size),
        "--seed",
        str(seed),
        "--device",
        args.device,
        "--output",
        f"models/{tag}.pth",
        "--metrics-output",
        str(metrics_path(tag)),
    ]
    command.extend(["--select", args.select])
    if variant == "no_action":
        command.append("--no-action")
    print(f"[night] training {tag} ...", flush=True)
    subprocess.run(command, check=True)


def summarize(args: argparse.Namespace, seeds: tuple[int, ...]) -> str:
    rows = []
    per_variant: dict[str, dict[str, list[float]]] = {
        v: {"ratio": [], "moving": [], "angle": [], "r2": []} for v in VARIANTS
    }
    for variant in VARIANTS:
        for seed in seeds:
            path = metrics_path(run_tag(variant, seed, args.tag_prefix))
            if not is_complete(path):
                rows.append(f"| {variant} | {seed} | incomplet | | | | |")
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            best = data.get("selected_metrics") or data.get("best", {})
            ratio = float(best.get("pred_to_copy_ratio", math.nan))
            moving = float(best.get("pred_to_copy_ratio_moving", math.nan))
            angle = float(best.get("angle_probe_mae_deg", math.nan))
            r2 = float(best.get("distance_probe_r2", math.nan))
            per_variant[variant]["ratio"].append(ratio)
            if not math.isnan(moving):
                per_variant[variant]["moving"].append(moving)
            per_variant[variant]["angle"].append(angle)
            per_variant[variant]["r2"].append(r2)
            moving_text = "n/a" if math.isnan(moving) else f"{moving:.4f}"
            rows.append(
                f"| {variant} | {seed} | {ratio:.4f} | {moving_text} | {angle:.2f} | {r2:.3f} | {data.get('epochs_run', '?')} |"
            )

    def stat(values: list[float]) -> str:
        if not values:
            return "n/a"
        if len(values) == 1:
            return f"{values[0]:.4f}"
        return f"{statistics.mean(values):.4f} +/- {statistics.stdev(values):.4f} [{min(values):.4f}, {max(values):.4f}]"

    action = per_variant["action"]
    control = per_variant["no_action"]

    def verdict(action_values: list[float], control_values: list[float]) -> str:
        if not action_values or not control_values:
            return "indéterminé"
        disjoint = max(action_values) < min(control_values)
        better_mean = statistics.mean(action_values) < statistics.mean(control_values)
        if better_mean and disjoint:
            return "VALIDÉE"
        return "moyenne favorable, intervalles non disjoints" if better_mean else "REJETÉE"

    h1 = verdict(action["ratio"], control["ratio"])
    h1_moving = verdict(action["moving"], control["moving"])
    h2 = "indéterminé"
    if action["angle"]:
        h2 = "VALIDÉE" if statistics.mean(action["angle"]) < 5.0 else "REJETÉE"
    h3 = "indéterminé"
    if action["r2"]:
        h3 = "VALIDÉE" if statistics.mean(action["r2"]) > 0.5 else "REJETÉE"

    lines = [
        "# Campagne nocturne - contingence sensorimotrice visuelle (jumeau du banc)",
        "",
        f"Protocole: `docs/research/visual_bench_probe.md`. Corpus: `{args.corpus}`.",
        "",
        "| variante | graine | ratio pred/copie (val) | ratio mouvement | MAE angle (deg) | R2 distance | epochs |",
        "|---|---|---|---|---|---|---|",
        *rows,
        "",
        f"- ratio `action`: {stat(action['ratio'])}",
        f"- ratio `no_action`: {stat(control['ratio'])}",
        f"- ratio mouvement `action`: {stat(action['moving'])}",
        f"- ratio mouvement `no_action`: {stat(control['moving'])}",
        f"- MAE angle `action`: {stat(action['angle'])}",
        f"- R2 distance `action`: {stat(action['r2'])}",
        "",
        f"**H1 (la commande motrice améliore la prédiction): {h1}**",
        f"**H1-mouvement (idem, paires |delta angle| > 5 deg): {h1_moving}**",
        f"**H2 (pose lisible dans le latent, MAE < 5 deg): {h2}**",
        f"**H3 (distance lisible, R2 > 0.5): {h3}**",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = build_parser().parse_args()
    seeds = SEEDS
    args.tag_prefix = args.prefix
    if args.smoke:
        args.corpus = Path("data/raw/bench_visual_corpus_smoke")
        args.corpus_episodes = 6
        args.corpus_seconds = 8.0
        args.epochs = 6
        args.eval_every = 2
        args.patience = 0
        args.batch_size = 64
        args.summary_dir = Path("data/processed/experiments/visual_night_smoke")
        seeds = (4301,)
        args.tag_prefix = "smoke_"

    prevent_system_sleep()
    started = time.perf_counter()

    if not args.summary_only:
        from sim3d.bench_corpus import BenchCorpusSpec, generate_corpus

        spec = BenchCorpusSpec(
            episodes=args.corpus_episodes,
            seconds=args.corpus_seconds,
            output_dir=str(args.corpus),
        )
        manifest = generate_corpus(spec, workers=args.workers)
        print(
            f"[night] corpus: {manifest['episodes']} pieces, {manifest['total_frames']} frames "
            f"({manifest['generated_now']} nouvelles) en {manifest['wall_seconds']:.0f}s",
            flush=True,
        )

        for variant in VARIANTS:
            for seed in seeds:
                if args.smoke and variant == "no_action" and seed != seeds[0]:
                    continue
                if is_complete(metrics_path(run_tag(variant, seed, args.tag_prefix))):
                    print(f"[night] {run_tag(variant, seed, args.tag_prefix)} deja complet, saute.", flush=True)
                    continue
                launch_training(args, variant, seed)

    summary = summarize(args, seeds)
    args.summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary_dir / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"[night] termine en {(time.perf_counter() - started) / 60.0:.1f} min, resume: {summary_path}", flush=True)
    print(summary, flush=True)


if __name__ == "__main__":
    main()
