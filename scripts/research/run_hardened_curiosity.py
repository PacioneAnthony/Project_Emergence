"""Run DC-004: hardened benchmark with the frozen gates.

Pre-registration frozen in docs/research/dc004_preregistration.md. Gates are
evaluated at sigma = 0.05; sigma = 0.02 and sigma = 0 passes are reported
descriptively, including the clip-bias report in the noise zone.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from learning.hardened_curiosity_benchmark import CONDITIONS, run_condition_hardened
from learning.paired_stats import (
    cohen_dz,
    exact_sign_flip_pvalue,
    monte_carlo_noninferiority_pvalue,
    monte_carlo_sign_flip_pvalue,
    paired_sign_counts,
)

ALPHA = 0.05
SIGMAS = (0.0, 0.02, 0.05)
GATE_SIGMA = 0.05
NOISE_FRACTION_LIMIT = 0.15
NONINFERIORITY_RELATIVE_MARGIN = 0.05
MC_RESAMPLES = 200_000
MC_SEED = 20260721


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-budget", type=int, default=1200)
    p.add_argument("--seed-start", type=int, default=7301)
    p.add_argument("--seed-count", type=int, default=40)
    p.add_argument("--protocol", default="DC-004")
    p.add_argument("--output-dir", type=Path, default=Path("data/processed/experiments/developmental_curiosity_004"))
    return p


def stat_line(x) -> str:
    x = np.asarray(x, dtype=float)
    return f"{x.mean():.4f} +/- {x.std(ddof=1):.4f} [{x.min():.4f}, {x.max():.4f}]"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))
    permuted_flags = {seed: seed % 2 == 0 for seed in seeds}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    results = [
        run_condition_hardened(c, s, sigma, permuted_flags[s], args.sample_budget)
        for sigma in SIGMAS
        for c in CONDITIONS
        for s in seeds
    ]

    def series(sigma: float, condition: str, key: str, subset=None) -> np.ndarray:
        rows = [
            r
            for r in results
            if r["sigma"] == sigma and r["condition"] == condition and (subset is None or r["permuted"] == subset)
        ]
        rows.sort(key=lambda r: r["seed"])
        return np.array([r[key] for r in rows])

    errors = {c: series(GATE_SIGMA, c, "structured_error_final") for c in CONDITIONS}
    noise = {c: series(GATE_SIGMA, c, "noise_fraction") for c in CONDITIONS}

    # D4-H1: efficacy and noise avoidance under noisy anchors.
    h1_diffs = errors["babbling"] - errors["fractional"]
    h1 = {
        "mean_relative_reduction": float((h1_diffs / errors["babbling"]).mean()),
        "permutation_pvalue": monte_carlo_sign_flip_pvalue(h1_diffs, "greater", MC_RESAMPLES, MC_SEED),
        "mean_noise_fraction": float(noise["fractional"].mean()),
        "sign_counts": paired_sign_counts(h1_diffs),
        "cohen_dz": cohen_dz(h1_diffs),
    }
    d4_h1 = bool(h1["permutation_pvalue"] < ALPHA and h1["mean_noise_fraction"] < NOISE_FRACTION_LIMIT)
    h1["pass"] = d4_h1

    # D4-H2: informational control.
    gain_diffs = errors["fractional"] - errors["regional_lp_gain"]
    margin = NONINFERIORITY_RELATIVE_MARGIN * float(errors["regional_lp_gain"].mean())
    noise_diffs = noise["regional_lp_gain"] - noise["fractional"]
    h2 = {
        "mean_paired_error_difference": float(gain_diffs.mean()),
        "margin_absolute": margin,
        "noninferiority_pvalue": monte_carlo_noninferiority_pvalue(gain_diffs, margin, MC_RESAMPLES, MC_SEED),
        "noise_fraction_gain_control": float(noise["regional_lp_gain"].mean()),
        "noise_permutation_pvalue": monte_carlo_sign_flip_pvalue(noise_diffs, "greater", MC_RESAMPLES, MC_SEED),
        "sign_counts_error": paired_sign_counts(errors["regional_lp_gain"] - errors["fractional"]),
        "sign_counts_noise": paired_sign_counts(noise_diffs),
    }
    d4_h2 = bool(h2["noninferiority_pvalue"] < ALPHA and h2["noise_permutation_pvalue"] < ALPHA)
    h2["pass"] = d4_h2

    # D4-H3: permuted-geometry subset, exact test on 20 worlds.
    permuted_h3_diffs = series(GATE_SIGMA, "babbling", "structured_error_final", subset=True) - series(
        GATE_SIGMA, "fractional", "structured_error_final", subset=True
    )
    h3 = {
        "mean_paired_difference": float(permuted_h3_diffs.mean()),
        "worlds": int(permuted_h3_diffs.size),
        "permutation_pvalue": exact_sign_flip_pvalue(permuted_h3_diffs, "greater"),
        "sign_counts": paired_sign_counts(permuted_h3_diffs),
        "mean_noise_fraction_permuted": float(series(GATE_SIGMA, "fractional", "noise_fraction", subset=True).mean()),
    }
    d4_h3 = bool(h3["permutation_pvalue"] < ALPHA)
    h3["pass"] = d4_h3

    # Clip-bias report: mean clipped gain observed in the noise zone per sigma.
    bias_report = {}
    for sigma in SIGMAS:
        rows = [r for r in results if r["sigma"] == sigma and r["condition"] == "fractional"]
        gains = [r["noise_zone_clipped_gain_mean"] for r in rows if r["noise_zone_clipped_gain_mean"] is not None]
        visits = int(sum(r["noise_zone_interventions"] or 0 for r in rows))
        bias_report[str(sigma)] = {
            "mean_clipped_gain": float(np.mean(gains)) if gains else 0.0,
            "worlds_with_noise_visits": len(gains),
            "noise_zone_interventions": visits,
        }

    promote = bool(d4_h1 and d4_h2 and d4_h3)
    if promote:
        decision = "promotion: conditions de la revue remplies pour concevoir la simulation visuelle"
    elif not d4_h1:
        decision = "échec robustesse au bruit d'ancre: retour en conception (clip et normalisation du gain), pas de simulation visuelle"
    elif not d4_h2:
        decision = "échec contrôle informationnel: piste honnête = LP régional + information interventionnelle, revue conceptuelle"
    else:
        decision = "échec géométrie seul: revue de conception du descripteur de frontière avant toute suite"

    lines = [
        f"# {args.protocol} — durcissement du gain fractionnel",
        "",
        f"Budget: {args.sample_budget}, graines {seeds[0]}..{seeds[-1]} "
        f"({sum(permuted_flags.values())} mondes permutés, graines paires). "
        f"Portes gelées dans docs/research/dc004_preregistration.md, évaluées à σ = {GATE_SIGMA}.",
        "",
        "| condition | erreur structurée (σ=0.05) | fraction bruit | erreur (σ=0.02) | erreur (σ=0) |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in CONDITIONS:
        lines.append(
            f"| {c} | {stat_line(errors[c])} | {stat_line(noise[c])} "
            f"| {stat_line(series(0.02, c, 'structured_error_final'))} "
            f"| {stat_line(series(0.0, c, 'structured_error_final'))} |"
        )
    lines += [
        "",
        f"- D4-H1: réduction relative {100 * h1['mean_relative_reduction']:.2f}% vs babbling, "
        f"p MC {h1['permutation_pvalue']:.3e}, signes {h1['sign_counts']['positive']}/{args.seed_count}, "
        f"bruit {100 * h1['mean_noise_fraction']:.2f}% (< {100 * NOISE_FRACTION_LIMIT:.0f}%) — "
        f"{'PASSE' if d4_h1 else 'ÉCHOUE'}",
        f"- D4-H2: différence erreur vs regional_lp_gain {h2['mean_paired_error_difference']:+.4f} "
        f"(marge {margin:.4f}), p non-infériorité {h2['noninferiority_pvalue']:.3e}; "
        f"bruit {100 * h2['noise_fraction_gain_control']:.2f}% (contrôle) contre "
        f"{100 * h1['mean_noise_fraction']:.2f}%, p {h2['noise_permutation_pvalue']:.3e} — "
        f"{'PASSE' if d4_h2 else 'ÉCHOUE'}",
        f"- D4-H3 (20 mondes permutés): différence appariée {h3['mean_paired_difference']:+.4f}, "
        f"p exact {h3['permutation_pvalue']:.3e}, signes {h3['sign_counts']['positive']}/{h3['worlds']}, "
        f"bruit en géométrie permutée {100 * h3['mean_noise_fraction_permuted']:.2f}% — "
        f"{'PASSE' if d4_h3 else 'ÉCHOUE'}",
        "",
        "Rapport de biais du clip (gain fractionnel moyen en zone bruit):",
    ]
    for sigma in SIGMAS:
        block = bias_report[str(sigma)]
        lines.append(
            f"- σ = {sigma}: gain clippé moyen {block['mean_clipped_gain']:.5f} "
            f"({block['noise_zone_interventions']} interventions en zone bruit, "
            f"{block['worlds_with_noise_visits']} mondes)"
        )
    lines += ["", f"**Décision pré-enregistrée: {decision}**", ""]
    summary = "\n".join(lines)
    payload = {
        "protocol": args.protocol,
        "status": "complete",
        "preregistration": "docs/research/dc004_preregistration.md",
        "gate_sigma": GATE_SIGMA,
        "results": results,
        "gates": {"d4_h1": h1, "d4_h2": h2, "d4_h3": h3},
        "bias_report": bias_report,
        "decision": decision,
        "promote_visual_simulation": promote,
        "wall_seconds": time.perf_counter() - started,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
