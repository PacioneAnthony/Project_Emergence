#!/usr/bin/env python3
"""Resumable runner for the frozen J6-AR001 protocol."""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from learning.j6_adaptive_replay import (  # noqa: E402
    CONDITIONS,
    DOMAINS,
    RESERVED_SEEDS,
    SMOKE_SEED,
    AdaptiveSpec,
    _load_npz,
    _load_shared,
    analyze_results,
    bank_path,
    corpus_path,
    evaluate_banks,
    monitor_metrics,
    prepare_seed,
    recompute_rho,
    run_condition,
    state_digest,
)
from learning.train_visual_jepa import resolve_device  # noqa: E402
from learning.tv_exploration import AnchorBank  # noqa: E402
from sim3d.j6_adaptive_domains import STRUCTURED_CENTERS_DEG, adaptive_bench_config  # noqa: E402


OUTPUT_ROOT = REPO / "data" / "processed" / "experiments" / "j6_adaptive_replay_001"
PREREG = REPO / "docs" / "research" / "j6_adaptive_replay_001_preregistration.md"
REVIEW = REPO / "docs" / "research" / "j6_adaptive_replay_001_review.md"
SMOKE_RESULT = OUTPUT_ROOT / "smoke_11991.json"
MAX_CAMPAIGN_SECONDS = 75 * 60


def amendments_integrated() -> bool:
    if not PREREG.exists():
        return False
    text = PREREG.read_text(encoding="utf-8")
    fragments = ("### C1", "### C2", "### C3", "### C4", "`2026072001`")
    return all(fragment in text for fragment in fragments)


def review_authorized() -> bool:
    if not REVIEW.exists():
        return False
    text = REVIEW.read_text(encoding="utf-8").upper()
    return "AUTORISER AVEC CORRECTIONS BLOQUANTES" in text and amendments_integrated()


def campaign_authorized(review_accepted: bool, spec: AdaptiveSpec) -> tuple[bool, str]:
    if not review_accepted:
        return False, "pass --review-accepted after accepting the recorded Claude verdict"
    if not review_authorized():
        return False, "Claude authorization or C1-C4 amendment is missing"
    if not SMOKE_RESULT.exists():
        return False, "smoke 11991 has not passed"
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    if not smoke.get("passed") or smoke.get("spec_digest") != spec.digest():
        return False, "smoke 11991 is red or belongs to another manifest"
    return True, "authorized"


@contextlib.contextmanager
def keep_awake():
    if os.name != "nt":
        yield
        return
    continuous, system_required = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(continuous | system_required)
    try:
        yield
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(continuous)


def _settle(env, angle: float, steps: int = 40) -> None:
    for _ in range(steps):
        env.step(angle)


def manipulation_checks(seed: int) -> dict:
    from sim3d.bench_env import BenchHeadEnv

    frames = {}
    belt_effect = {}
    for domain in DOMAINS:
        env = BenchHeadEnv(adaptive_bench_config(domain, seed))
        control = BenchHeadEnv(adaptive_bench_config(domain, seed, belt=False))
        domain_frames, effects = [], []
        try:
            for sector, angle in enumerate(STRUCTURED_CENTERS_DEG):
                if env.model.geom(f"j6ar_panel_{sector}").id < 0:
                    raise AssertionError(f"missing physical panel {sector} in {domain}")
                _settle(env, angle)
                _settle(control, angle)
                frame = env.render_camera(64, 64)
                baseline = control.render_camera(64, 64)
                domain_frames.append(frame)
                effects.append(float(np.mean(np.abs(frame.astype(float) - baseline.astype(float))) / 255.0))
        finally:
            env.close()
            control.close()
        if min(effects) <= 0.03:
            raise AssertionError(f"domain {domain}: belt is not visibly present in every structured sector")
        frames[domain] = np.stack(domain_frames).astype(float)
        belt_effect[domain] = effects
    pairwise = {}
    for left, right in (("D", "E"), ("E", "F"), ("D", "F")):
        distances = [float(np.mean(np.abs(a - b)) / 255.0) for a, b in zip(frames[left], frames[right])]
        if min(distances) < 0.08:
            raise AssertionError(f"visual distance {left}/{right} below 0.08: {distances}")
        pairwise[f"{left}_{right}"] = distances
    luminance = lambda x: 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
    chroma = lambda x: float(np.mean(np.max(x, axis=-1) - np.min(x, axis=-1)) / 255.0)
    luminance_ratio = float(np.median(luminance(frames["E"])) / np.median(luminance(frames["D"])))
    chroma_change = abs(chroma(frames["F"]) - chroma(frames["D"])) / max(chroma(frames["D"]), 1e-8)
    if luminance_ratio > 0.75 or chroma_change < 0.05:
        raise AssertionError("D/E/F light manipulation diverged")
    return {"belt_effect": belt_effect, "pairwise_visual_distance": pairwise, "luminance_E_over_D": luminance_ratio, "chroma_F_relative_to_D": chroma_change}


def _frame_hashes(frames: np.ndarray) -> set[bytes]:
    return {hashlib.sha256(frame.tobytes()).digest() for frame in frames}


def assert_smoke(spec: AdaptiveSpec, results: list[dict], device, elapsed_seconds: float) -> dict:
    if len(results) != 3 or {item["condition"] for item in results} != set(CONDITIONS):
        raise AssertionError("smoke requires the three frozen conditions")
    checks = {"manipulations": manipulation_checks(SMOKE_SEED), "elapsed_seconds": elapsed_seconds}
    corpora = [item["corpus_sha256"] for item in results]
    if not all(item == corpora[0] for item in corpora[1:]):
        raise AssertionError("shared corpus is not bit-identical between conditions")
    checks["shared_corpus"] = corpora[0]

    shared = prepare_seed(SMOKE_SEED, OUTPUT_ROOT, spec, device)
    monitor_banks = {domain: AnchorBank.load(bank_path(OUTPUT_ROOT, SMOKE_SEED, domain, "monitor")) for domain in DOMAINS}
    decision_banks = {domain: AnchorBank.load(bank_path(OUTPUT_ROOT, SMOKE_SEED, domain, "decision")) for domain in DOMAINS}
    digests, decisions, monitors = [], [], []
    for _ in CONDITIONS:
        model, probes, _ = _load_shared(SMOKE_SEED, OUTPUT_ROOT, spec, device)
        digests.append(state_digest(model, probes))
        decisions.append(evaluate_banks(model, probes, decision_banks, device))
        monitors.append(monitor_metrics(model, monitor_banks, device))
    if len(set(digests)) != 1 or digests[0] != shared["post_D_state_digest"]:
        raise AssertionError("B3 post-D weights diverged")
    if len({json.dumps(item, sort_keys=True) for item in decisions}) != 1 or len({json.dumps(item, sort_keys=True) for item in monitors}) != 1:
        raise AssertionError("B3 post-D evaluations diverged")
    if len({item["post_D_state_digest"] for item in results}) != 1:
        raise AssertionError("condition results do not share post-D state")
    checks["b3"] = {"state_digest": digests[0], "decision_and_monitor_evaluations_identical": True}

    disjoint = {}
    for domain in DOMAINS:
        training = _load_npz(corpus_path(OUTPUT_ROOT, SMOKE_SEED, domain))
        training_hash = _frame_hashes(training["frames"])
        monitor_hash = _frame_hashes(monitor_banks[domain].frames_start)
        decision_hash = _frame_hashes(decision_banks[domain].frames_start)
        if training_hash & monitor_hash or training_hash & decision_hash or monitor_hash & decision_hash:
            raise AssertionError(f"training/monitor/decision leakage in {domain}")
        for bank in (monitor_banks[domain], decision_banks[domain]):
            counts = [int(np.sum(bank.angle_bins == angle)) for angle in range(6)]
            if min(counts) < 64:
                raise AssertionError(f"fewer than 64 anchors per structured competence in {domain}")
        disjoint[domain] = True
    checks["three_way_disjoint_banks"] = disjoint

    expected_budget = {"images": 12_000, "decisions": 2_400, "optimizer_steps": 4_500, "session_steps": 1_500, "batch_size": 256}
    for item in results:
        if item["budgets"] != expected_budget:
            raise AssertionError("interaction or optimizer budget diverged")
    checks["budgets"] = expected_budget

    parity = {}
    for session in ("D", "E", "F"):
        reports = [item["training"][session] for item in results]
        counts = {report["monitor_evaluations"] for report in reports}
        schedules = {tuple(report["monitor_steps"]) for report in reports}
        sizes = {json.dumps(report["monitor_bank_sizes"], sort_keys=True) for report in reports}
        if len(counts) != 1 or len(schedules) != 1 or len(sizes) != 1:
            raise AssertionError(f"monitor evaluation parity failed in {session}")
        parity[session] = {"evaluations": counts.pop(), "steps": list(schedules.pop()), "bank_sizes": json.loads(sizes.pop())}
    checks["monitor_parity"] = parity

    adaptive = next(item for item in results if item["condition"] == "adaptive_replay")
    composition = {}
    for session in ("E", "F"):
        blocks = adaptive["training"][session]["blocks"][:-1]
        for block in blocks:
            rho = recompute_rho(block["d_old"], block["d_current"])
            if rho != block["applied_rho"]:
                raise AssertionError("rho is not exactly recomputable")
            if block["old_per_batch"] != 256 * rho or block["current_per_batch"] != 256 * (1 - rho):
                raise AssertionError("adaptive batch composition diverged")
            if block["effective_old_pairs"] != spec.monitor_block_steps * block["old_per_batch"]:
                raise AssertionError("effective old-pair count diverged")
        composition[session] = {"blocks": len(blocks), "rho_recomputable": True, "exact_batches": True}
    checks["adaptive_composition"] = composition

    tv = {}
    for item in results:
        tv[item["condition"]] = {}
        for session in ("E", "F"):
            replay = item["training"][session]["replay"]
            total = replay["replayed_pairs"]
            television = replay["television_pairs"]
            value = replay["effective_tv_fraction_among_replayed"]
            if total == 0:
                if value is not None or television != 0:
                    raise AssertionError("empty TV denominator must stay empty")
            elif not np.isclose(value, television / total):
                raise AssertionError("TV fraction is not conditional on replayed pairs")
            tv[item["condition"]][session] = {"replayed": total, "television": television, "fraction": value}
    checks["tv_denominator"] = tv

    for item in results:
        for domain in ("D", "E"):
            if len(item["regression_relative"].get(domain, [])) != 6 or len(item["regression_abs"].get(domain, [])) != 6:
                raise AssertionError("D/E absolute and relative regressions missing")
    checks["metrics"] = {"relative_and_absolute_D_E": True, "final_F_by_bin": True}
    return checks


def completed_campaign_seconds() -> float:
    seconds = 0.0
    for path in (OUTPUT_ROOT / "shared").glob("seed_*_post_d.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("seed") in RESERVED_SEEDS:
            seconds += float(item.get("elapsed_seconds", 0.0))
    for path in (OUTPUT_ROOT / "runs").glob("seed_*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("seed") in RESERVED_SEEDS:
            seconds += float(item.get("elapsed_seconds_after_D", 0.0))
    return seconds


def write_results_documents(analysis: dict, results: list[dict], elapsed_minutes: float) -> None:
    report = REPO / "docs" / "research" / "j6_adaptive_replay_001_results.md"
    decision = analysis["decision"]["adaptive_replay_eligible"]
    lines = [
        "# Résultats J6-AR001 — replay adaptatif et plasticité",
        "",
        "Date: 2026-07-20. Simulation uniquement sous D-008. Aucune promotion avant revue Claude.",
        "",
        "## Intégrité",
        "",
        "- 16 triplets appariés, 48 runs, graines 11301..11316.",
        "- Corpus, banques, B3, budgets et parité de suivi contrôlés; smoke 11991 vert.",
        f"- Temps GPU/mural cumulé consigné: `{elapsed_minutes:.2f}` minutes, plafond 75 minutes.",
        "",
        "## Portes gelées",
        "",
        f"- B1 D/E: `{analysis['b1_forgetting_guard']['D']['passed']}` / `{analysis['b1_forgetting_guard']['E']['passed']}`.",
        f"- H1 uniform D/E: `{analysis['h1_uniform_value']['D']['passed']}` / `{analysis['h1_uniform_value']['E']['passed']}`.",
        f"- H2 rétention adaptive D/E: `{analysis['h2_retention_noninferiority']['D']['passed']}` / `{analysis['h2_retention_noninferiority']['E']['passed']}`.",
        f"- H3a plasticité supérieure: `{analysis['h3a_plasticity_superiority']['passed']}`; H3b non-infériorité face à naïf: `{analysis['h3b_current_noninferiority']['passed']}`.",
        f"- Gardes apprenant/activation E/activation F/TV: `{analysis['learner_guard']['passed']}` / `{analysis['activation_guard']['E']['passed']}` / `{analysis['activation_guard']['F']['passed']}` / `{all(v['passed'] for v in analysis['tv_guard'].values())}`.",
        "",
        "## Décision mécanique suspendue",
        "",
        f"`adaptive_replay_eligible={decision}`. Ce booléen applique mécaniquement les portes mais ne constitue pas une promotion. Une revue contradictoire des résultats est obligatoire.",
        "",
        "## Limite de portée pré-enregistrée",
        "",
        "Même en cas de succès, la campagne établit seulement la valeur de ce calendrier. Elle ne démontre pas que l'adaptativité est nécessaire face à une fraction statique basse non testée. La dynamique attendue est une rampe rho=0 puis une saturation potentiellement rapide vers 0,5 après acquisition courante.",
        "",
        "## Analyse complète",
        "",
        "```json",
        json.dumps(analysis, indent=2, sort_keys=True),
        "```",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    prompt = """Tu es le relecteur contradictoire des résultats J6-AR001. Lis intégralement docs/research/j6_adaptive_replay_001_preregistration.md, docs/research/j6_adaptive_replay_001_review.md, docs/research/j6_adaptive_replay_001_results.md, docs/research/j6_adaptive_replay_001_analysis.json et docs/research/j6_adaptive_replay_001_runs.json. Recalcule les portes B1 D/E, H1 D/E, H2 D/E avec la règle B2 amendée, H3a/H3b et Holm depuis les 48 runs. Audite B3, les budgets, la séparation suivi/décision, la recomputabilité de rho, la composition effective des batchs, la parité des évaluations, l'activation et la fraction TV conditionnelle aux seules paires rejouées. Distingue PASS, FAIL et NON INTERPRÉTABLE. Vérifie qu'une éventuelle éligibilité ne résout pas H3 en abandonnant la rétention et respecte la limite de portée sur l'adaptativité. Réponds par AUTORISER, AUTORISER AVEC CORRECTIONS ou NE PAS AUTORISER, puis dis explicitement si adaptive_replay peut être promu. Ne propose aucun retuning sur 11301..11316."""
    request = f"""# Demande de revue contradictoire Claude — résultats J6-AR001

Date: 2026-07-20

Le pré-enregistrement a été autorisé avec C1–C4 intégrées avant code et calcul. Le smoke 11991 est vert et les 48 runs réservés sont terminés. Aucune promotion n'a été faite.

Fichiers: `docs/research/j6_adaptive_replay_001_preregistration.md`, `docs/research/j6_adaptive_replay_001_review.md`, `docs/research/j6_adaptive_replay_001_results.md`, `docs/research/j6_adaptive_replay_001_analysis.json`, `docs/research/j6_adaptive_replay_001_runs.json`.

## Prompt exact

```text
{prompt}
```
"""
    (REPO / "CLAUDE_REVIEW_REQUEST.md").write_text(request, encoding="utf-8")


def run_smoke(spec: AdaptiveSpec, device) -> None:
    if not review_authorized():
        raise SystemExit("review authorization or C1-C4 amendment missing; smoke forbidden")
    started = time.perf_counter()
    with keep_awake():
        prepare_seed(SMOKE_SEED, OUTPUT_ROOT, spec, device)
        results = [run_condition(SMOKE_SEED, condition, OUTPUT_ROOT, spec, device) for condition in CONDITIONS]
        checks = assert_smoke(spec, results, device, time.perf_counter() - started)
    payload = {"passed": True, "seed": SMOKE_SEED, "spec_digest": spec.digest(), "checks": checks}
    SMOKE_RESULT.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_RESULT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"J6-AR001 smoke {SMOKE_SEED}: PASS", flush=True)


def run_campaign(spec: AdaptiveSpec, device, review_accepted: bool) -> None:
    authorized, reason = campaign_authorized(review_accepted, spec)
    if not authorized:
        raise SystemExit(f"reserved campaign forbidden: {reason}")
    used = completed_campaign_seconds()
    remaining = MAX_CAMPAIGN_SECONDS - used
    if remaining <= 0:
        raise TimeoutError("J6-AR001 cumulative 75-minute cap reached")
    deadline = time.perf_counter() + remaining
    results = []
    with keep_awake():
        for seed in RESERVED_SEEDS:
            prepare_seed(seed, OUTPUT_ROOT, spec, device, deadline)
            for condition in CONDITIONS:
                result = run_condition(seed, condition, OUTPUT_ROOT, spec, device, deadline)
                results.append(result)
                print(f"J6-AR001 {seed} {condition}: complete", flush=True)
    if len(results) != 48:
        raise RuntimeError("J6-AR001 run cap diverged")
    analysis = analyze_results(results)
    elapsed = completed_campaign_seconds()
    local_analysis = OUTPUT_ROOT / "analysis.json"
    payload = json.dumps(analysis, indent=2, sort_keys=True) + "\n"
    local_analysis.write_text(payload, encoding="utf-8")
    (REPO / "docs" / "research" / "j6_adaptive_replay_001_analysis.json").write_text(payload, encoding="utf-8")
    (REPO / "docs" / "research" / "j6_adaptive_replay_001_runs.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_results_documents(analysis, results, elapsed / 60.0)
    print(f"J6-AR001 campaign complete: {local_analysis}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen J6-AR001")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--review-accepted", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    spec = AdaptiveSpec()
    device = resolve_device(args.device)
    print(f"J6-AR001 device={device} spec={spec.digest()[:12]}", flush=True)
    if args.smoke:
        run_smoke(spec, device)
    else:
        run_campaign(spec, device, args.review_accepted)


if __name__ == "__main__":
    main()
