"""Run DC-005: aggregate-then-clip variant under anchor noise.

Pre-registration frozen in docs/research/dc005_preregistration.md. Reuses the
DC-004 hardened bench unchanged; adds the pooled condition and keeps the old
fractional scheduler as a positive collapse control.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from learning.hardened_curiosity_benchmark import run_condition_hardened
from learning.paired_stats import (
    cohen_dz,
    monte_carlo_noninferiority_pvalue,
    monte_carlo_sign_flip_pvalue,
    paired_sign_counts,
)

CONDITIONS = ("pooled", "fractional", "babbling", "regional_lp_gain")
ALPHA = 0.05
SIGMAS = (0.0, 0.02, 0.05)
GATE_SIGMA = 0.05
NOISE_FRACTION_LIMIT = 0.15
NONINFERIORITY_RELATIVE_MARGIN = 0.05
MC_RESAMPLES = 200_000
MC_SEED = 20260722


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-budget", type=int, default=1200)
    p.add_argument("--seed-start", type=int, default=8301)
    p.add_argument("--seed-count", type=int, default=40)
    p.add_argument("--protocol", default="DC-005")
    p.add_argument("--output-dir", type=Path, default=Path("data/processed/experiments/developmental_curiosity_005"))
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

    # D5-H1: pooled versus babbling under noisy anchors.
    h1_diffs = errors["babbling"] - errors["pooled"]
    h1 = {
        "mean_relative_reduction": float((h1_diffs / errors["babbling"]).mean()),
        "permutation_pvalue": monte_carlo_sign_flip_pvalue(h1_diffs, "greater", MC_RESAMPLES, MC_SEED),
        "mean_noise_fraction": float(noise["pooled"].mean()),
        "sign_counts": paired_sign_counts(h1_diffs),
        "cohen_dz": cohen_dz(h1_diffs),
    }
    d5_h1 = bool(h1["permutation_pvalue"] < ALPHA and h1["mean_noise_fraction"] < NOISE_FRACTION_LIMIT)
    h1["pass"] = d5_h1

    # D5-H2: value added over the informational control.
    gain_diffs = errors["pooled"] - errors["regional_lp_gain"]
    margin = NONINFERIORITY_RELATIVE_MARGIN * float(errors["regional_lp_gain"].mean())
    noise_diffs = noise["regional_lp_gain"] - noise["pooled"]
    h2 = {
        "mean_paired_error_difference": float(gain_diffs.mean()),
        "margin_absolute": margin,
        "noninferiority_pvalue": monte_carlo_noninferiority_pvalue(gain_diffs, margin, MC_RESAMPLES, MC_SEED),
        "noise_fraction_gain_control": float(noise["regional_lp_gain"].mean()),
        "noise_permutation_pvalue": monte_carlo_sign_flip_pvalue(noise_diffs, "greater", MC_RESAMPLES, MC_SEED),
        "sign_counts_noise": paired_sign_counts(noise_diffs),
    }
    d5_h2 = bool(h2["noninferiority_pvalue"] < ALPHA and h2["noise_permutation_pvalue"] < ALPHA)
    h2["pass"] = d5_h2

    # D5-H3: no regression in the clean regime against the DC-003 scheduler.
    clean_pooled = series(0.0, "pooled", "structured_error_final")
    clean_fractional = series(0.0, "fractional", "structured_error_final")
    clean_diffs = clean_pooled - clean_fractional
    clean_margin = NONINFERIORITY_RELATIVE_MARGIN * float(clean_fractional.mean())
    h3 = {
        "mean_paired_difference": float(clean_diffs.mean()),
        "margin_absolute": clean_margin,
        "noninferiority_pvalue": monte_carlo_noninferiority_pvalue(clean_diffs, clean_margin, MC_RESAMPLES, MC_SEED),
        "sign_counts": paired_sign_counts(clean_fractional - clean_pooled),
    }
    d5_h3 = bool(h3["noninferiority_pvalue"] < ALPHA)
    h3["pass"] = d5_h3

    # Positive control: the old scheduler must reproduce its collapse.
    collapse_diffs = errors["fractional"] - errors["babbling"]
    positive_control = {
        "fractional_error": float(errors["fractional"].mean()),
        "babbling_error": float(errors["babbling"].mean()),
        "fractional_worse_signs": paired_sign_counts(collapse_diffs),
        "reproduced": bool(errors["fractional"].mean() > errors["babbling"].mean()),
    }

    bias_report = {}
    for sigma in SIGMAS:
        for condition in ("pooled", "fractional"):
            rows = [r for r in results if r["sigma"] == sigma and r["condition"] == condition]
            gains = [r["noise_zone_clipped_gain_mean"] for r in rows if r["noise_zone_clipped_gain_mean"] is not None]
            bias_report[f"{condition}@{sigma}"] = {
                "mean_clipped_gain": float(np.mean(gains)) if gains else 0.0,
                "noise_zone_interventions": int(sum(r["noise_zone_interventions"] or 0 for r in rows)),
            }

    decomposition = {}
    for subset, label in ((False, "standard"), (True, "permuted")):
        decomposition[label] = {
            sigma_label: float(series(sigma, "pooled", "structured_error_final", subset=subset).mean())
            for sigma, sigma_label in ((0.0, "sigma0"), (0.02, "sigma002"), (0.05, "sigma005"))
        }

    promote = bool(d5_h1 and d5_h2 and d5_h3)
    if promote:
        decision = (
            "l'ordonnanceur survit au bruit d'ancre: blocage DC-004 levé sous réserve de revue "
            "contradictoire avant conception de la simulation visuelle"
        )
    elif not d5_h1:
        decision = "arrêt de la famille développementale à gain fractionnel; regional_lp_gain devient la référence"
    elif not d5_h2:
        decision = "machinerie développementale sans valeur ajoutée mesurable: piste honnête = regional_lp_gain + garde anti-bruit"
    else:
        decision = "régression en régime propre: rejet de pooled, la revue de conception reprend"

    lines = [
        f"# {args.protocol} — gain fractionnel agrégé sous bruit d'ancre",
        "",
        f"Budget: {args.sample_budget}, graines {seeds[0]}..{seeds[-1]} "
        f"({sum(permuted_flags.values())} mondes permutés). Portes gelées dans "
        f"docs/research/dc005_preregistration.md, évaluées à σ = {GATE_SIGMA} (D5-H3 à σ = 0).",
        "",
        "| condition | erreur (σ=0.05) | fraction bruit (σ=0.05) | erreur (σ=0.02) | erreur (σ=0) |",
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
        f"- D5-H1: réduction relative {100 * h1['mean_relative_reduction']:.2f}% vs babbling, "
        f"p MC {h1['permutation_pvalue']:.3e}, signes {h1['sign_counts']['positive']}/{args.seed_count}, "
        f"bruit {100 * h1['mean_noise_fraction']:.2f}% — {'PASSE' if d5_h1 else 'ÉCHOUE'}",
        f"- D5-H2: différence erreur vs regional_lp_gain {h2['mean_paired_error_difference']:+.4f} "
        f"(marge {margin:.4f}), p non-infériorité {h2['noninferiority_pvalue']:.3e}; "
        f"bruit {100 * h1['mean_noise_fraction']:.2f}% contre {100 * h2['noise_fraction_gain_control']:.2f}%, "
        f"p {h2['noise_permutation_pvalue']:.3e} — {'PASSE' if d5_h2 else 'ÉCHOUE'}",
        f"- D5-H3 (σ=0): différence appariée vs fractional {h3['mean_paired_difference']:+.4f} "
        f"(marge {clean_margin:.4f}), p non-infériorité {h3['noninferiority_pvalue']:.3e} — "
        f"{'PASSE' if d5_h3 else 'ÉCHOUE'}",
        f"- Contrôle positif: fractional {positive_control['fractional_error']:.4f} contre babbling "
        f"{positive_control['babbling_error']:.4f} à σ = 0.05 — effondrement "
        f"{'reproduit' if positive_control['reproduced'] else 'NON REPRODUIT (campagne non interprétable)'}",
        "",
        "Rapport de biais en zone bruit (gain clippé moyen):",
    ]
    for key, block in bias_report.items():
        lines.append(f"- {key}: {block['mean_clipped_gain']:.5f} ({block['noise_zone_interventions']} interventions)")
    lines += [
        "",
        f"Décomposition pooled (erreur moyenne): standard {decomposition['standard']}, "
        f"permuté {decomposition['permuted']}",
        "",
        f"**Décision pré-enregistrée: {decision}**",
        "",
    ]
    summary = "\n".join(lines)
    payload = {
        "protocol": args.protocol,
        "status": "complete",
        "preregistration": "docs/research/dc005_preregistration.md",
        "gate_sigma": GATE_SIGMA,
        "results": results,
        "gates": {"d5_h1": h1, "d5_h2": h2, "d5_h3": h3},
        "positive_control": positive_control,
        "bias_report": bias_report,
        "decomposition": decomposition,
        "decision": decision,
        "promote": promote,
        "wall_seconds": time.perf_counter() - started,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
