"""Run pre-registered DC-002 or its unchanged independent replication."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from learning.interventional_curiosity_benchmark import CONDITIONS, run_condition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DC-002 fixed-anchor curiosity benchmark")
    parser.add_argument("--sample-budget", type=int, default=1200)
    parser.add_argument("--seed-start", type=int, default=5201)
    parser.add_argument("--seed-count", type=int, default=20)
    parser.add_argument("--protocol", default="DC-002")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/experiments/developmental_curiosity_002"),
    )
    return parser


def stat(values: list[float]) -> str:
    return (
        f"{statistics.mean(values):.4f} +/- {statistics.stdev(values):.4f} "
        f"[{min(values):.4f}, {max(values):.4f}]"
    )


def main() -> None:
    args = build_parser().parse_args()
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = []
    for condition in CONDITIONS:
        for seed in seeds:
            result = run_condition(condition, seed, args.sample_budget)
            results.append(result)
            print(
                f"{condition} seed={seed}: structured={result['structured_error_final']:.4f} "
                f"noise={result['noise_fraction']:.3f} entropy={result['coverage_entropy']:.3f}",
                flush=True,
            )

    grouped = {condition: [r for r in results if r["condition"] == condition] for condition in CONDITIONS}
    errors = {c: [r["structured_error_final"] for r in rows] for c, rows in grouped.items()}
    noise = {c: [r["noise_fraction"] for r in rows] for c, rows in grouped.items()}
    entropy = {c: [r["coverage_entropy"] for r in rows] for c, rows in grouped.items()}
    active = grouped["interventional"]
    babble = grouped["babbling"]
    rr = grouped["round_robin_habituation"]

    reduction_babble = 1.0 - statistics.mean(errors["interventional"]) / statistics.mean(errors["babbling"])
    reduction_rr = 1.0 - statistics.mean(errors["interventional"]) / statistics.mean(errors["round_robin_habituation"])
    h1 = (
        reduction_babble >= 0.10
        and reduction_rr >= 0.10
        and max(errors["interventional"]) < min(errors["babbling"])
        and max(errors["interventional"]) < min(errors["round_robin_habituation"])
        and statistics.mean(a["structured_error_final"] - b["structured_error_final"] for a, b in zip(active, babble)) < 0
        and statistics.mean(a["structured_error_final"] - b["structured_error_final"] for a, b in zip(active, rr)) < 0
    )
    h2 = (
        statistics.mean(noise["interventional"]) <= 0.5 * statistics.mean(noise["babbling"])
        and statistics.mean(noise["interventional"]) < statistics.mean(noise["round_robin_habituation"])
        and statistics.mean(noise["interventional"]) < statistics.mean(noise["regional_lp"])
    )
    signature_count = sum(row["signature_pass"] for row in active)
    h3 = signature_count >= 16
    coverage_guard = statistics.mean(entropy["interventional"]) >= 0.65
    stability = statistics.stdev(errors["interventional"]) <= statistics.stdev(errors["babbling"])
    promote = h1 and h2 and h3 and coverage_guard and stability

    lines = [
        f"# {args.protocol} — progrès interventional sur ancres fixes",
        "",
        f"Budget: {args.sample_budget} exemples, graines {seeds[0]}..{seeds[-1]}.",
        "",
        "| condition | erreur structurée finale | fraction bruit | entropie couverture |",
        "|---|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        lines.append(f"| {condition} | {stat(errors[condition])} | {stat(noise[condition])} | {stat(entropy[condition])} |")
    lines.extend(
        [
            "",
            f"- réduction vs babbling: {reduction_babble * 100:.2f}%",
            f"- réduction vs round-robin+habituation: {reduction_rr * 100:.2f}%",
            f"- signatures temporelles: {signature_count}/{len(seeds)}",
            "",
            f"**DC2-H1 efficacité: {'VALIDÉE' if h1 else 'REJETÉE'}**",
            f"**DC2-H2 évitement du bruit: {'VALIDÉE' if h2 else 'REJETÉE'}**",
            f"**DC2-H3 progression graduelle: {'VALIDÉE' if h3 else 'REJETÉE'}**",
            f"**Garde-fou couverture: {'VALIDÉ' if coverage_guard else 'ÉCHOUÉ'}**",
            f"**Stabilité: {'VALIDÉE' if stability else 'REJETÉE'}**",
            f"**Promotion vers réplication: {'OUI' if promote else 'NON'}**",
            "",
        ]
    )
    summary = "\n".join(lines)
    payload = {
        "protocol": args.protocol,
        "status": "complete",
        "sample_budget": args.sample_budget,
        "seeds": list(seeds),
        "results": results,
        "verdicts": {
            "dc2_h1": h1,
            "dc2_h2": h2,
            "dc2_h3": h3,
            "coverage_guard": coverage_guard,
            "stability": stability,
            "promote_replication": promote,
        },
        "wall_seconds": time.perf_counter() - started,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
