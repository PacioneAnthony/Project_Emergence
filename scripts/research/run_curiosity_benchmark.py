"""Run the pre-registered DC-001 controlled curiosity benchmark."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from learning.curiosity_benchmark import CONDITIONS, run_condition


SEEDS = tuple(range(5101, 5121))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DC-001 continuous curiosity benchmark")
    parser.add_argument("--budget", type=int, default=1200)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/experiments/developmental_curiosity_001"),
    )
    return parser


def stat(values: list[float]) -> str:
    return (
        f"{statistics.mean(values):.4f} +/- {statistics.stdev(values):.4f} "
        f"[{min(values):.4f}, {max(values):.4f}]"
    )


def main() -> None:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = []
    for condition in CONDITIONS:
        for seed in SEEDS:
            result = run_condition(condition, seed, args.budget)
            results.append(result)
            print(
                f"{condition} seed={seed}: structured={result['structured_error_final']:.4f} "
                f"noise={result['noise_fraction']:.3f} entropy={result['coverage_entropy']:.3f}",
                flush=True,
            )

    by_condition = {
        condition: [result for result in results if result["condition"] == condition]
        for condition in CONDITIONS
    }
    dev = by_condition["developmental"]
    babble = by_condition["babbling"]
    rr = by_condition["round_robin_habituation"]
    regional = by_condition["regional_lp"]

    errors = {c: [r["structured_error_final"] for r in rows] for c, rows in by_condition.items()}
    noise = {c: [r["noise_fraction"] for r in rows] for c, rows in by_condition.items()}
    entropy = {c: [r["coverage_entropy"] for r in rows] for c, rows in by_condition.items()}
    reduction_babble = 1.0 - statistics.mean(errors["developmental"]) / statistics.mean(errors["babbling"])
    reduction_rr = 1.0 - statistics.mean(errors["developmental"]) / statistics.mean(errors["round_robin_habituation"])
    disjoint_babble = max(errors["developmental"]) < min(errors["babbling"])
    disjoint_rr = max(errors["developmental"]) < min(errors["round_robin_habituation"])
    paired_babble = statistics.mean(d["structured_error_final"] - b["structured_error_final"] for d, b in zip(dev, babble)) < 0
    paired_rr = statistics.mean(d["structured_error_final"] - b["structured_error_final"] for d, b in zip(dev, rr)) < 0
    h1 = reduction_babble >= 0.10 and reduction_rr >= 0.10 and disjoint_babble and disjoint_rr and paired_babble and paired_rr
    h2 = (
        statistics.mean(noise["developmental"]) <= 0.5 * statistics.mean(noise["babbling"])
        and statistics.mean(noise["developmental"]) < statistics.mean(noise["round_robin_habituation"])
        and statistics.mean(noise["developmental"]) < statistics.mean(noise["regional_lp"])
    )
    signature_count = sum(result["signature_pass"] for result in dev)
    h3 = signature_count >= 16
    coverage_guard = statistics.mean(entropy["developmental"]) >= 0.65

    lines = [
        "# DC-001 — curiosité développementale continue",
        "",
        f"Budget: {args.budget} décisions, graines 5101..5120. Protocole: `docs/research/developmental_curiosity_probe.md`.",
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
            f"- signatures temporelles developmental: {signature_count}/20",
            "",
            f"**DC-H1 efficacité: {'VALIDÉE' if h1 else 'REJETÉE'}**",
            f"**DC-H2 évitement du bruit: {'VALIDÉE' if h2 else 'REJETÉE'}**",
            f"**DC-H3 progression graduelle: {'VALIDÉE' if h3 else 'REJETÉE'}**",
            f"**Garde-fou couverture: {'VALIDÉ' if coverage_guard else 'ÉCHOUÉ'}**",
            "",
        ]
    )
    summary = "\n".join(lines)
    payload = {
        "protocol": "DC-001",
        "status": "complete",
        "budget": args.budget,
        "seeds": list(SEEDS),
        "results": results,
        "verdicts": {"dc_h1": h1, "dc_h2": h2, "dc_h3": h3, "coverage_guard": coverage_guard},
        "wall_seconds": time.perf_counter() - started,
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (args.output_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
