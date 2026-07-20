"""Resumable/keep-awake runner for the frozen TV-001 campaign."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from learning.paired_stats import (
    bca_bootstrap_ci,
    cohen_dz,
    exact_sign_flip_pvalue,
    holm_correction,
    paired_sign_counts,
    rank_biserial,
)

CALIBRATION_SEEDS = (9201, 9202, 9203)
CAMPAIGN_SEEDS = tuple(range(9301, 9313))
CONDITIONS = ("babbling", "regional_lp_gain")
PROTOCOL = "docs/research/tv_real_jepa_001_preregistration.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TV-001 real-JEPA campaign")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/experiments/tv_real_jepa_001"))
    parser.add_argument("--anchor-dir", type=Path, default=Path("data/raw/tv_real_jepa_001"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--calibration-only", action="store_true")
    parser.add_argument("--campaign-only", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument(
        "--review-accepted",
        action="store_true",
        help="Required for campaign seeds after the pre-campaign contradictory review.",
    )
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


def is_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "complete"
    except (OSError, json.JSONDecodeError):
        return False


def run_paths(output_dir: Path, condition: str, seed: int) -> tuple[Path, Path]:
    run_dir = output_dir / "runs" / f"{condition}_seed{seed}"
    return run_dir / "metrics.json", Path("models") / f"tv001_{condition}_seed{seed}.pth"


def run_calibration(args: argparse.Namespace, seeds: tuple[int, ...]) -> dict:
    import torch

    from learning.train_visual_jepa import resolve_device
    from learning.tv_exploration import calibrate_noise

    output = args.output_dir / "calibration.json"
    report = calibrate_noise(seeds, args.anchor_dir, resolve_device(args.device), output=output)
    print(json.dumps(report, indent=2), flush=True)
    return report


def launch_run(
    args: argparse.Namespace,
    condition: str,
    seed: int,
    probe_batches: int,
    *,
    smoke: bool = False,
) -> None:
    metrics, checkpoint = run_paths(args.output_dir, condition, seed)
    command = [
        sys.executable,
        "-m",
        "learning.tv_exploration",
        "--condition",
        condition,
        "--seed",
        str(seed),
        "--probe-batches",
        str(probe_batches),
        "--device",
        args.device,
        "--anchor-dir",
        str(args.anchor_dir),
        "--output",
        str(checkpoint),
        "--metrics-output",
        str(metrics),
    ]
    if smoke:
        command.extend(
            [
                "--rounds",
                "2",
                "--frames-per-round",
                "80",
                "--episodes-per-round",
                "2",
                "--epochs-per-round",
                "1",
            ]
        )
    print(f"[tv001] {condition} seed={seed}", flush=True)
    subprocess.run(command, check=True)


def _stat_block(values: np.ndarray, p_raw: float, p_holm: float) -> dict:
    ci = bca_bootstrap_ci(values, n_boot=10_000, seed=20260720)
    return {
        "mean": float(np.mean(values)),
        "ci_bca_95": [float(ci[0]), float(ci[1])],
        "p_exact": float(p_raw),
        "p_holm": float(p_holm),
        "signs": paired_sign_counts(values),
        "cohen_dz": cohen_dz(values),
        "rank_biserial": rank_biserial(values),
        "values": values.tolist(),
    }


def summarize(output_dir: Path, seeds: tuple[int, ...]) -> dict:
    records: dict[str, dict[int, dict]] = {condition: {} for condition in CONDITIONS}
    missing = []
    for condition in CONDITIONS:
        for seed in seeds:
            path, _ = run_paths(output_dir, condition, seed)
            if not is_complete(path):
                missing.append(str(path))
                continue
            records[condition][seed] = json.loads(path.read_text(encoding="utf-8"))
    if missing:
        return {"status": "incomplete", "missing": missing, "protocol": PROTOCOL}

    babbling_error = np.asarray(
        [records["babbling"][seed]["final_external"]["structured_error"] for seed in seeds]
    )
    regional_error = np.asarray(
        [records["regional_lp_gain"][seed]["final_external"]["structured_error"] for seed in seeds]
    )
    relative_reduction = (babbling_error - regional_error) / babbling_error
    babbling_tv = np.asarray([records["babbling"][seed]["television_fraction"] for seed in seeds])
    regional_tv = np.asarray([records["regional_lp_gain"][seed]["television_fraction"] for seed in seeds])
    tv_difference = babbling_tv - regional_tv
    p_raw = np.asarray(
        [
            exact_sign_flip_pvalue(relative_reduction, "greater"),
            exact_sign_flip_pvalue(tv_difference, "greater"),
        ]
    )
    p_holm = holm_correction(p_raw)

    improvements = {
        condition: np.asarray([records[condition][seed]["structured_improvement"] for seed in seeds])
        for condition in CONDITIONS
    }
    regional_entropies = np.asarray(
        [records["regional_lp_gain"][seed]["structured_coverage_entropy"] for seed in seeds]
    )
    regional_min_shares = np.asarray(
        [records["regional_lp_gain"][seed]["structured_bin_min_decision_share"] for seed in seeds]
    )
    budgets_exact = all(
        records[condition][seed]["frames_budget"] == 8000
        and records[condition][seed]["decision_budget"] == 1600
        for condition in CONDITIONS
        for seed in seeds
    )
    calibration_path = output_dir / "calibration.json"
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    learner_guard = all(float(np.mean(improvements[condition])) >= 0.10 for condition in CONDITIONS)
    coverage_guard = bool(np.min(regional_entropies) >= 0.75 and np.min(regional_min_shares) >= 0.02)
    construction_guard = bool(calibration.get("status") == "passed")
    h1 = bool(np.mean(relative_reduction) >= 0.05 and p_holm[0] <= 0.05)
    h2 = bool(np.mean(regional_tv) < 0.15 and p_holm[1] <= 0.05)
    interpretable = bool(learner_guard and coverage_guard and construction_guard and budgets_exact)
    promoted = bool(h1 and h2 and interpretable)

    summary = {
        "status": "complete",
        "protocol": PROTOCOL,
        "seeds": list(seeds),
        "tv_h1": {**_stat_block(relative_reduction, p_raw[0], p_holm[0]), "passed": h1},
        "tv_h2": {
            **_stat_block(tv_difference, p_raw[1], p_holm[1]),
            "regional_tv_mean": float(np.mean(regional_tv)),
            "babbling_tv_mean": float(np.mean(babbling_tv)),
            "passed": h2,
        },
        "guards": {
            "learner": learner_guard,
            "coverage": coverage_guard,
            "construction": construction_guard,
            "budgets": budgets_exact,
            "improvement_mean": {key: float(np.mean(value)) for key, value in improvements.items()},
            "regional_entropy_min": float(np.min(regional_entropies)),
            "regional_bin_share_min": float(np.min(regional_min_shares)),
        },
        "interpretable": interpretable,
        "promoted": promoted,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    verdict = "PROMU" if promoted else ("NON INTERPRÉTABLE" if not interpretable else "REJETÉ")
    rows = []
    for seed in seeds:
        rows.append(
            f"| {seed} | {babbling_error[seeds.index(seed)]:.4f} | "
            f"{regional_error[seeds.index(seed)]:.4f} | {relative_reduction[seeds.index(seed)]:+.2%} | "
            f"{babbling_tv[seeds.index(seed)]:.2%} | {regional_tv[seeds.index(seed)]:.2%} |"
        )
    markdown = "\n".join(
        [
            "# Résultats TV-001 — exploration active avec JEPA réel",
            "",
            f"Protocole: `{PROTOCOL}`.",
            "",
            "| graine | erreur structurée babbling | erreur structurée regional | réduction | TV babbling | TV regional |",
            "|---|---:|---:|---:|---:|---:|",
            *rows,
            "",
            f"- TV-H1: moyenne {np.mean(relative_reduction):+.2%}, p exacte {p_raw[0]:.6g}, p Holm {p_holm[0]:.6g} — {'PASSÉE' if h1 else 'REJETÉE'}.",
            f"- TV-H2: allocation regional {np.mean(regional_tv):.2%} contre {np.mean(babbling_tv):.2%}, p Holm {p_holm[1]:.6g} — {'PASSÉE' if h2 else 'REJETÉE'}.",
            f"- Garde apprenant: {'passé' if learner_guard else 'échoué'}; couverture: {'passée' if coverage_guard else 'échouée'}; construction: {'passée' if construction_guard else 'échouée'}; budgets: {'exacts' if budgets_exact else 'incorrects'}.",
            "",
            f"**Décision pré-enregistrée: {verdict}.**",
            "",
        ]
    )
    (output_dir / "summary.md").write_text(markdown, encoding="utf-8")
    return summary


def main() -> None:
    args = build_parser().parse_args()
    prevent_system_sleep()
    started = time.perf_counter()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.smoke:
        smoke_dir = Path("data/processed/experiments/tv_real_jepa_smoke")
        smoke_anchor = Path("data/raw/tv_real_jepa_smoke")
        args.output_dir = smoke_dir
        args.anchor_dir = smoke_anchor
        launch_run(args, "regional_lp_gain", 9991, 4, smoke=True)
        print(f"[tv001] smoke terminé en {time.perf_counter() - started:.1f}s", flush=True)
        return

    calibration_path = args.output_dir / "calibration.json"
    if not args.summary_only and not args.campaign_only:
        calibration = run_calibration(args, CALIBRATION_SEEDS)
        if calibration["status"] != "passed":
            raise SystemExit("TV-001 calibration failed its frozen gate; campaign not started")

    if args.calibration_only:
        return

    if args.summary_only:
        result = summarize(args.output_dir, CAMPAIGN_SEEDS)
        print(json.dumps(result, indent=2), flush=True)
        return

    if not args.review_accepted:
        raise SystemExit("TV-001 campaign requires --review-accepted after CLAUDE_REVIEW_REQUEST.md is resolved")
    if not calibration_path.exists():
        raise SystemExit("missing calibration.json")
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    if calibration.get("status") != "passed" or calibration.get("selected_probe_batches") is None:
        raise SystemExit("calibration did not pass the frozen gate")
    probe_batches = int(calibration["selected_probe_batches"])

    for seed in CAMPAIGN_SEEDS:
        order = CONDITIONS if seed % 2 else tuple(reversed(CONDITIONS))
        for condition in order:
            metrics, _ = run_paths(args.output_dir, condition, seed)
            if is_complete(metrics):
                print(f"[tv001] {condition} seed={seed} déjà complet, sauté", flush=True)
                continue
            launch_run(args, condition, seed, probe_batches)
    result = summarize(args.output_dir, CAMPAIGN_SEEDS)
    print(json.dumps(result, indent=2), flush=True)
    print(f"[tv001] campagne terminée en {(time.perf_counter() - started) / 60.0:.1f} min", flush=True)


if __name__ == "__main__":
    main()
