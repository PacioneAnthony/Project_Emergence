"""Run DC-003R: unchanged replication with the frozen paired statistical gate.

Analysis frozen in docs/research/dc003r_preregistration.md. Reuses run_condition
from fractional_curiosity_benchmark without modification; only the analysis
differs from DC-003.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from learning.fractional_curiosity_benchmark import CONDITIONS, run_condition
from learning.paired_stats import (
    bca_bootstrap_ci,
    cohen_dz,
    exact_sign_flip_pvalue,
    holm_correction,
    noninferiority_sign_flip_pvalue,
    paired_sign_counts,
    rank_biserial,
)

ALPHA = 0.05
MIN_RELATIVE_EFFECT = 0.10
NONINFERIORITY_RELATIVE_MARGIN = 0.05
BOOTSTRAP_SEED = 20260720
BOOTSTRAP_RESAMPLES = 10_000


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-budget", type=int, default=1200)
    p.add_argument("--seed-start", type=int, default=6301)
    p.add_argument("--seed-count", type=int, default=20)
    p.add_argument("--protocol", default="DC-003R")
    p.add_argument("--output-dir", type=Path, default=Path("data/processed/experiments/developmental_curiosity_003R"))
    return p


def stat_line(x) -> str:
    x = np.asarray(x, dtype=float)
    return f"{x.mean():.4f} +/- {x.std(ddof=1):.4f} [{x.min():.4f}, {x.max():.4f}]"


def main() -> None:
    args = parser().parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seed_count))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = [run_condition(c, s, args.sample_budget) for c in CONDITIONS for s in seeds]
    rows = {c: [r for r in results if r["condition"] == c] for c in CONDITIONS}
    errors = {c: np.array([r["structured_error_final"] for r in rows[c]]) for c in CONDITIONS}
    noise = {c: np.array([r["noise_fraction"] for r in rows[c]]) for c in CONDITIONS}
    entropy = {c: np.array([r["coverage_entropy"] for r in rows[c]]) for c in CONDITIONS}
    signatures = int(sum(r["signature_pass"] for r in rows["fractional"]))

    # R-H1: paired efficacy versus the two naive baselines, Holm-corrected.
    h1 = {}
    raw_pvalues = []
    for control in ("babbling", "round_robin_habituation"):
        error_diffs = errors[control] - errors["fractional"]
        relative_reductions = error_diffs / errors[control]
        pvalue = exact_sign_flip_pvalue(error_diffs, alternative="greater")
        raw_pvalues.append(pvalue)
        ci_low, ci_high = bca_bootstrap_ci(
            relative_reductions, np.mean, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, ALPHA
        )
        h1[control] = {
            "mean_relative_reduction": float(relative_reductions.mean()),
            "permutation_pvalue": pvalue,
            "bca_ci_relative_reduction": [ci_low, ci_high],
            "sign_counts": paired_sign_counts(error_diffs),
            "cohen_dz": cohen_dz(error_diffs),
            "rank_biserial": rank_biserial(error_diffs),
        }
    adjusted = holm_correction(raw_pvalues)
    for control, adjusted_pvalue in zip(("babbling", "round_robin_habituation"), adjusted):
        h1[control]["holm_pvalue"] = float(adjusted_pvalue)
        h1[control]["pass"] = bool(
            h1[control]["mean_relative_reduction"] >= MIN_RELATIVE_EFFECT
            and adjusted_pvalue < ALPHA
            and h1[control]["bca_ci_relative_reduction"][0] > 0.0
        )
    r_h1 = h1["babbling"]["pass"] and h1["round_robin_habituation"]["pass"]

    # R-H1b: non-inferiority against regional_lp with the frozen 5% margin.
    lp_diffs = errors["fractional"] - errors["regional_lp"]
    margin = NONINFERIORITY_RELATIVE_MARGIN * float(errors["regional_lp"].mean())
    h1b = {
        "mean_paired_difference": float(lp_diffs.mean()),
        "margin_absolute": margin,
        "noninferiority_pvalue": noninferiority_sign_flip_pvalue(lp_diffs, margin),
        "sign_counts": paired_sign_counts(errors["regional_lp"] - errors["fractional"]),
        "cohen_dz": cohen_dz(lp_diffs),
        "rank_biserial": rank_biserial(lp_diffs),
    }
    r_h1b = bool(h1b["noninferiority_pvalue"] < ALPHA)
    h1b["pass"] = r_h1b

    # R-H2: noise avoidance, unchanged thresholds plus a paired permutation test.
    noise_diffs = noise["babbling"] - noise["fractional"]
    h2 = {
        "mean_noise_fraction": float(noise["fractional"].mean()),
        "threshold_versus_babbling": bool(noise["fractional"].mean() <= 0.5 * noise["babbling"].mean()),
        "below_round_robin": bool(noise["fractional"].mean() < noise["round_robin_habituation"].mean()),
        "below_regional_lp": bool(noise["fractional"].mean() < noise["regional_lp"].mean()),
        "permutation_pvalue": exact_sign_flip_pvalue(noise_diffs, alternative="greater"),
        "sign_counts": paired_sign_counts(noise_diffs),
    }
    r_h2 = bool(
        h2["threshold_versus_babbling"]
        and h2["below_round_robin"]
        and h2["below_regional_lp"]
        and h2["permutation_pvalue"] < ALPHA
    )
    h2["pass"] = r_h2

    # R-H3, coverage and stability: unchanged from the DC-003 freeze.
    r_h3 = signatures >= 16
    coverage = bool(entropy["fractional"].mean() >= 0.65)
    stability = bool(errors["fractional"].std(ddof=1) <= errors["babbling"].std(ddof=1))

    promote = bool(r_h1 and r_h1b and r_h2 and r_h3 and coverage and stability)
    if promote:
        decision = "promotion vers DC-004 (pré-enregistrement DC-004 requis avant exécution)"
    elif not r_h1:
        decision = "arrêt de la famille d'ordonnanceurs à gain fractionnel, revue conceptuelle"
    elif not r_h1b:
        decision = "pas de promotion: piste honnête = LP régional + garde anti-bruit"
    else:
        decision = "pas de promotion: échec partiel, consignation et revue dédiée"

    lines = [
        f"# {args.protocol} — réplication appariée du gain fractionnel",
        "",
        f"Budget: {args.sample_budget}, graines {seeds[0]}..{seeds[-1]}. "
        f"Portes gelées dans docs/research/dc003r_preregistration.md.",
        "",
        "| condition | erreur structurée | fraction bruit | entropie |",
        "|---|---:|---:|---:|",
    ]
    for c in CONDITIONS:
        lines.append(f"| {c} | {stat_line(errors[c])} | {stat_line(noise[c])} | {stat_line(entropy[c])} |")
    lines += [""]
    for control in ("babbling", "round_robin_habituation"):
        block = h1[control]
        lines.append(
            f"- R-H1 vs {control}: réduction relative {100 * block['mean_relative_reduction']:.2f}%, "
            f"p permutation {block['permutation_pvalue']:.3e} (Holm {block['holm_pvalue']:.3e}), "
            f"IC BCa 95% [{100 * block['bca_ci_relative_reduction'][0]:.2f}%, "
            f"{100 * block['bca_ci_relative_reduction'][1]:.2f}%], "
            f"signes {block['sign_counts']['positive']}/{args.seed_count}, "
            f"dz {block['cohen_dz']:.2f}, rrb {block['rank_biserial']:.2f} — "
            f"{'PASSE' if block['pass'] else 'ÉCHOUE'}"
        )
    lines += [
        f"- R-H1b vs regional_lp: différence appariée {h1b['mean_paired_difference']:+.4f} "
        f"(marge {h1b['margin_absolute']:.4f}), p non-infériorité {h1b['noninferiority_pvalue']:.3e}, "
        f"signes favorables {h1b['sign_counts']['positive']}/{args.seed_count}, "
        f"dz {h1b['cohen_dz']:.2f}, rrb {h1b['rank_biserial']:.2f} — {'PASSE' if r_h1b else 'ÉCHOUE'}",
        f"- R-H2: bruit {100 * h2['mean_noise_fraction']:.2f}%, p permutation vs babbling "
        f"{h2['permutation_pvalue']:.3e}, signes {h2['sign_counts']['positive']}/{args.seed_count} — "
        f"{'PASSE' if r_h2 else 'ÉCHOUE'}",
        f"- R-H3: signatures {signatures}/{args.seed_count} — {'PASSE' if r_h3 else 'ÉCHOUE'}",
        f"- Couverture: entropie moyenne {entropy['fractional'].mean():.3f} — "
        f"{'PASSE' if coverage else 'ÉCHOUE'}",
        f"- Stabilité: écart-type {errors['fractional'].std(ddof=1):.4f} contre "
        f"{errors['babbling'].std(ddof=1):.4f} (babbling) — {'PASSE' if stability else 'ÉCHOUE'}",
        "",
        f"**Décision pré-enregistrée: {decision}**",
        "",
    ]
    summary = "\n".join(lines)
    payload = {
        "protocol": args.protocol,
        "status": "complete",
        "preregistration": "docs/research/dc003r_preregistration.md",
        "results": results,
        "gates": {
            "r_h1": {"pass": bool(r_h1), "by_control": h1},
            "r_h1b": h1b,
            "r_h2": h2,
            "r_h3": {"pass": bool(r_h3), "signatures": signatures},
            "coverage": {"pass": coverage, "mean_entropy": float(entropy["fractional"].mean())},
            "stability": {
                "pass": stability,
                "fractional_std": float(errors["fractional"].std(ddof=1)),
                "babbling_std": float(errors["babbling"].std(ddof=1)),
            },
        },
        "decision": decision,
        "promote_dc004": promote,
        "wall_seconds": time.perf_counter() - started,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
