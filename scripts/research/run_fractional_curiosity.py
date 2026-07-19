"""Run DC-003 or its unchanged independent replication."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from learning.fractional_curiosity_benchmark import CONDITIONS, run_condition


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--sample-budget", type=int, default=1200)
    p.add_argument("--seed-start", type=int, default=5301)
    p.add_argument("--seed-count", type=int, default=20)
    p.add_argument("--protocol", default="DC-003")
    p.add_argument("--output-dir", type=Path, default=Path("data/processed/experiments/developmental_curiosity_003"))
    return p


def stat(x):
    return f"{statistics.mean(x):.4f} +/- {statistics.stdev(x):.4f} [{min(x):.4f}, {max(x):.4f}]"


def main() -> None:
    args = parser().parse_args()
    seeds = range(args.seed_start, args.seed_start + args.seed_count)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = [run_condition(c, s, args.sample_budget) for c in CONDITIONS for s in seeds]
    g = {c: [r for r in results if r["condition"] == c] for c in CONDITIONS}
    e = {c: [r["structured_error_final"] for r in rows] for c, rows in g.items()}
    n = {c: [r["noise_fraction"] for r in rows] for c, rows in g.items()}
    h = {c: [r["coverage_entropy"] for r in rows] for c, rows in g.items()}
    active, babble, rr = g["fractional"], g["babbling"], g["round_robin_habituation"]
    red_b = 1 - statistics.mean(e["fractional"]) / statistics.mean(e["babbling"])
    red_r = 1 - statistics.mean(e["fractional"]) / statistics.mean(e["round_robin_habituation"])
    h1 = red_b >= .10 and red_r >= .10 and max(e["fractional"]) < min(e["babbling"]) and max(e["fractional"]) < min(e["round_robin_habituation"])
    h1 &= statistics.mean(a["structured_error_final"]-b["structured_error_final"] for a,b in zip(active,babble)) < 0
    h1 &= statistics.mean(a["structured_error_final"]-b["structured_error_final"] for a,b in zip(active,rr)) < 0
    h2 = statistics.mean(n["fractional"]) <= .5*statistics.mean(n["babbling"])
    h2 &= statistics.mean(n["fractional"]) < statistics.mean(n["round_robin_habituation"])
    h2 &= statistics.mean(n["fractional"]) < statistics.mean(n["regional_lp"])
    sig = sum(r["signature_pass"] for r in active)
    h3 = sig >= 16
    coverage = statistics.mean(h["fractional"]) >= .65
    stability = statistics.stdev(e["fractional"]) <= statistics.stdev(e["babbling"])
    promote = h1 and h2 and h3 and coverage and stability
    lines=[f"# {args.protocol} — gain fractionnel sur mondes randomisés","",f"Budget: {args.sample_budget}, graines {args.seed_start}..{args.seed_start+args.seed_count-1}.","","| condition | erreur structurée | fraction bruit | entropie |","|---|---:|---:|---:|"]
    for c in CONDITIONS: lines.append(f"| {c} | {stat(e[c])} | {stat(n[c])} | {stat(h[c])} |")
    lines += ["",f"- réduction vs babbling: {100*red_b:.2f}%",f"- réduction vs round-robin: {100*red_r:.2f}%",f"- signatures: {sig}/{args.seed_count}","",f"**DC3-H1: {'VALIDÉE' if h1 else 'REJETÉE'}**",f"**DC3-H2: {'VALIDÉE' if h2 else 'REJETÉE'}**",f"**DC3-H3: {'VALIDÉE' if h3 else 'REJETÉE'}**",f"**Couverture: {'VALIDÉE' if coverage else 'REJETÉE'}**",f"**Stabilité: {'VALIDÉE' if stability else 'REJETÉE'}**",f"**Promotion réplication: {'OUI' if promote else 'NON'}**",""]
    summary="\n".join(lines)
    payload={"protocol":args.protocol,"status":"complete","results":results,"verdicts":{"h1":h1,"h2":h2,"h3":h3,"coverage":coverage,"stability":stability,"promote_replication":promote},"wall_seconds":time.perf_counter()-started}
    (args.output_dir/"metrics.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    (args.output_dir/"summary.md").write_text(summary,encoding="utf-8")
    print(summary)


if __name__ == "__main__": main()
