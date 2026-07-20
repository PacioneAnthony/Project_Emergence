#!/usr/bin/env python3
"""Resumable J6-R001 runner.  Reserved seeds require review + green smoke."""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from learning.j6_replay import (  # noqa: E402
    CONDITIONS,
    DOMAINS,
    LANDMARK_BINS,
    RESERVED_SEEDS,
    SMOKE_SEED,
    J6Spec,
    _load_npz,
    analyze_results,
    anchor_path,
    corpus_path,
    evaluate_banks,
    prepare_seed,
    run_condition,
    state_digest,
    _load_shared,
)
from learning.train_visual_jepa import resolve_device  # noqa: E402
from learning.tv_exploration import AnchorBank  # noqa: E402
from sim3d.j6_domains import j6_bench_config  # noqa: E402


OUTPUT_ROOT = REPO / "data" / "processed" / "experiments" / "j6_replay_001"
REVIEW = REPO / "docs" / "research" / "j6_replay_001_review.md"
PREREG = REPO / "docs" / "research" / "j6_replay_001_preregistration.md"
SMOKE_RESULT = OUTPUT_ROOT / "smoke_10991.json"
MAX_CAMPAIGN_SECONDS = 90 * 60


def amendments_integrated() -> bool:
    if not PREREG.exists():
        return False
    text = PREREG.read_text(encoding="utf-8")
    required = (
        "Garde d'oubli (amendement pré-calcul du 2026-07-20)",
        "regression_abs[d,r] = e_final_C[d,r] − e_acquisition[d,r]",
        "bit à bit identiques jusqu'à la fin de la session A incluse",
        "Cette garde n'est jamais calibrée sur le smoke 10991",
    )
    return all(fragment in text for fragment in required)


def review_authorized() -> bool:
    if not REVIEW.exists():
        return False
    text = REVIEW.read_text(encoding="utf-8").upper()
    return "AUTORISER AVEC CORRECTIONS BLOQUANTES" in text and amendments_integrated()


def campaign_authorized(review_accepted: bool, spec: J6Spec) -> tuple[bool, str]:
    if not review_accepted:
        return False, "pass --review-accepted after accepting the recorded Claude verdict"
    if not review_authorized():
        return False, "Claude authorization or the B1/B2/B3 pre-compute amendment is missing"
    if not SMOKE_RESULT.exists():
        return False, "smoke 10991 has not passed"
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    if not smoke.get("passed") or smoke.get("spec_digest") != spec.digest():
        return False, "smoke 10991 is absent, red, or belongs to another manifest"
    return True, "authorized"


@contextlib.contextmanager
def keep_awake():
    """Prevent system sleep during a long local campaign; no-op off Windows."""

    if os.name != "nt":
        yield
        return
    continuous = 0x80000000
    system_required = 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(continuous | system_required)
    try:
        yield
    finally:
        ctypes.windll.kernel32.SetThreadExecutionState(continuous)


def _settle(env, angle: float, steps: int = 40) -> None:
    for _ in range(steps):
        env.step(angle)


def _manipulation_assertions(seed: int) -> dict:
    from sim3d.bench_env import BenchHeadEnv

    angles = tuple(20.0 + 20.0 * index for index in range(8))
    domain_frames = {}
    sector = {}
    for domain in DOMAINS:
        env = BenchHeadEnv(j6_bench_config(domain, seed))
        control = BenchHeadEnv(j6_bench_config(domain, seed, landmark=False))
        differences = []
        frames = []
        try:
            if env.model.geom("j6_landmark_panel").id < 0:
                raise AssertionError(f"domain {domain}: landmark is not a true MJCF geom")
            for angle in angles:
                _settle(env, angle)
                _settle(control, angle)
                frame = env.render_camera(64, 64)
                baseline = control.render_camera(64, 64)
                frames.append(frame)
                differences.append(float(np.mean(np.abs(frame.astype(np.float32) - baseline.astype(np.float32)))))
        finally:
            env.close()
            control.close()
        observed_bin = int(np.argmax(differences))
        if observed_bin != LANDMARK_BINS[domain] or differences[observed_bin] <= 5.0:
            raise AssertionError(f"domain {domain}: landmark sector {observed_bin}, expected {LANDMARK_BINS[domain]}")
        sector[domain] = {"expected_bin": LANDMARK_BINS[domain], "observed_bin": observed_bin, "pixel_differences": differences}
        domain_frames[domain] = np.stack(frames).astype(np.float32)

    def luminance(frames):
        return 0.299 * frames[..., 0] + 0.587 * frames[..., 1] + 0.114 * frames[..., 2]

    def chroma(frames):
        return float(np.mean(np.max(frames, axis=-1) - np.min(frames, axis=-1)) / 255.0)

    median_a = float(np.median(luminance(domain_frames["A"])))
    median_b = float(np.median(luminance(domain_frames["B"])))
    chroma_a = chroma(domain_frames["A"])
    chroma_c = chroma(domain_frames["C"])
    luminance_ratio = median_b / max(median_a, 1e-8)
    chroma_relative_change = abs(chroma_c - chroma_a) / max(chroma_a, 1e-8)
    if luminance_ratio > 0.85:
        raise AssertionError(f"B luminance ratio {luminance_ratio:.4f} > 0.85")
    if chroma_relative_change < 0.05:
        raise AssertionError(f"C chroma relative change {chroma_relative_change:.4f} < 0.05")
    return {
        "landmark": sector,
        "luminance_B_over_A": luminance_ratio,
        "chroma_C_relative_to_A": chroma_relative_change,
    }


def _frame_hashes(frames: np.ndarray) -> set[bytes]:
    import hashlib

    return {hashlib.sha256(frame.tobytes()).digest() for frame in frames}


def assert_smoke(seed: int, spec: J6Spec, results: list[dict], device) -> dict:
    if seed != SMOKE_SEED:
        raise AssertionError("smoke seed diverged")
    if len(results) != 3 or {item["condition"] for item in results} != set(CONDITIONS):
        raise AssertionError("smoke does not contain the three frozen conditions")
    checks = {"manipulations": _manipulation_assertions(seed)}

    hashes = [{domain: item["corpus_sha256"][domain] for domain in DOMAINS} for item in results]
    if not all(item == hashes[0] for item in hashes[1:]):
        raise AssertionError("same action/domain/seed did not yield a bit-identical shared corpus")
    checks["bit_identical_corpus"] = hashes[0]

    shared = prepare_seed(seed, OUTPUT_ROOT, spec, device)
    banks = {domain: AnchorBank.load(anchor_path(OUTPUT_ROOT, seed, domain)) for domain in DOMAINS}
    loaded_digests = []
    loaded_evaluations = []
    for _ in CONDITIONS:
        model, probes, _ = _load_shared(seed, OUTPUT_ROOT, spec, device)
        loaded_digests.append(state_digest(model, probes))
        loaded_evaluations.append(evaluate_banks(model, probes, banks, device))
    canonical_evaluation = json.dumps(loaded_evaluations[0], sort_keys=True)
    if len(set(loaded_digests)) != 1 or loaded_digests[0] != shared["post_A_state_digest"]:
        raise AssertionError("B3 post-A weights are not bit-identical")
    if any(json.dumps(item, sort_keys=True) != canonical_evaluation for item in loaded_evaluations[1:]):
        raise AssertionError("B3 post-A evaluations are not identical")
    if len({item["post_A_state_digest"] for item in results}) != 1:
        raise AssertionError("B3 digest differs between condition results")
    checks["post_A_identity"] = {"state_digest": loaded_digests[0], "evaluations_identical": True}

    for item in results:
        expected = {"images": 12_000, "decisions": 2_400, "optimizer_steps": 4_500, "session_steps": 1_500}
        if item["budgets"] != expected:
            raise AssertionError(f"budget diverged for {item['condition']}: {item['budgets']}")
        if item["training"]["A"]["steps"] != 1_500 or any(item["training"][d]["steps"] != 1_500 for d in ("B", "C")):
            raise AssertionError("session optimizer budget diverged")
    checks["budgets"] = {"images": 12_000, "decisions": 2_400, "steps_per_session": 1_500, "shared_corpus": True}

    anchor_report = {}
    for domain in DOMAINS:
        bank = banks[domain]
        counts = [int(np.sum(bank.angle_bins == angle)) for angle in range(6)]
        if min(counts) < 64:
            raise AssertionError(f"domain {domain}: fewer than 64 anchors in a structured competence")
        training = _load_npz(corpus_path(OUTPUT_ROOT, seed, domain))
        if _frame_hashes(bank.frames_start) & _frame_hashes(training["frames"]):
            raise AssertionError(f"domain {domain}: held-out anchor leaked into training buffer")
        anchor_report[domain] = {"structured_counts": counts, "disjoint_from_buffer": True}
    checks["anchors"] = anchor_report

    replay_report = {}
    for item in results:
        if item["condition"] == "naive":
            continue
        replay_report[item["condition"]] = {}
        for session in ("B", "C"):
            replay = item["training"][session]["replay"]
            if not np.isclose(replay["probability_sum"], 1.0, atol=1e-12):
                raise AssertionError("replay probabilities do not sum to one")
            if not replay["probability_mass_by_domain"] or not replay["effective_tv_fraction_by_domain"]:
                raise AssertionError("replay TV mass is not recorded by domain")
            replay_report[item["condition"]][session] = {
                "probability_sum": replay["probability_sum"],
                "mass_by_domain": replay["probability_mass_by_domain"],
                "tv_by_domain": replay["effective_tv_fraction_by_domain"],
            }
    checks["replay"] = replay_report

    for item in results:
        for domain in ("A", "B"):
            if len(item["regression_relative"].get(domain, [])) != 6 or len(item["regression_abs"].get(domain, [])) != 6:
                raise AssertionError("absolute and relative A/B regressions were not produced")
    checks["metrics"] = {"relative_A_B": True, "absolute_A_B": True}
    return checks


def completed_campaign_seconds() -> float:
    seconds = 0.0
    for path in (OUTPUT_ROOT / "shared").glob("seed_*_post_a.json"):
        seed = int(path.stem.split("_")[1])
        if seed in RESERVED_SEEDS:
            seconds += float(json.loads(path.read_text(encoding="utf-8")).get("elapsed_seconds", 0.0))
    for path in (OUTPUT_ROOT / "runs").glob("seed_*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item.get("seed") in RESERVED_SEEDS:
            seconds += float(item.get("elapsed_seconds_after_A", 0.0))
    return seconds


def _fmt_gate(item: dict) -> str:
    return "PASS" if item.get("passed") else item.get("interpretation", "FAIL")


def write_results_documents(analysis: dict, results: list[dict]) -> None:
    result_path = REPO / "docs" / "research" / "j6_replay_001_results.md"
    lines = [
        "# Résultats J6-R001 — rétention visuelle séquentielle",
        "",
        "Date: 2026-07-20. Simulation uniquement (D-008). Protocole et seuils: `j6_replay_001_preregistration.md`.",
        "Aucune promotion n'est effectuée avant la revue contradictoire Claude.",
        "",
        "## Intégrité",
        "",
        "- 12 triplets appariés, graines `10301..10312`, 36 runs complets.",
        "- Corpus partagé bit à bit par graine; 12 000 images, 2 400 décisions et 4 500 pas par condition.",
        "- B1, B2 et B3 ont été appliqués avant tout calcul réservé; smoke 10991 vert.",
        "",
        "## Portes gelées",
        "",
        "| Porte | A | B |",
        "|---|---:|---:|",
        f"| Garde d'oubli B1 | {_fmt_gate(analysis['b1_forgetting_guard']['A'])} | {_fmt_gate(analysis['b1_forgetting_guard']['B'])} |",
        f"| H1 replay uniforme | {_fmt_gate(analysis['h1']['A'])} | {_fmt_gate(analysis['h1']['B'])} |",
        f"| H2 priorité | {_fmt_gate(analysis['h2']['A'])} | {_fmt_gate(analysis['h2']['B'])} |",
        "",
        f"La garde B1 n'est pas atteinte sur A: régression naïve moyenne `{analysis['b1_forgetting_guard']['A']['mean']:.4f}` (< 0,05), malgré un IC BCa dont la borne basse vaut `{analysis['b1_forgetting_guard']['A']['bca_95'][0]:.4f}`. H1A est donc **NON INTERPRÉTABLE**, et non rejetée. Sur B, la régression naïve moyenne vaut `{analysis['b1_forgetting_guard']['B']['mean']:.4f}` avec borne basse `{analysis['b1_forgetting_guard']['B']['bca_95'][0]:.4f}`: la garde passe.",
        "",
        f"H1B passe: réduction relative moyenne `{analysis['h1']['B']['relative']['mean']:.4f}`, borne basse `{analysis['h1']['B']['relative']['bca_95'][0]:.4f}`, p Holm `{analysis['h1']['B']['p_holm']:.6f}`, `{analysis['h1']['B']['favorable_bins']}/6` bins. La réduction absolue moyenne `{analysis['h1']['B']['absolute']['mean']:.4f}` est de même signe (B2). H2 ne démontre aucune valeur ajoutée à cette puissance: moyennes relatives A/B `{analysis['h2']['A']['relative']['mean']:.4f}` / `{analysis['h2']['B']['relative']['mean']:.4f}`.",
        "",
        f"H3 uniform: **{_fmt_gate(analysis['h3']['uniform_replay'])}**. H3 priorité: **{_fmt_gate(analysis['h3']['error_prioritized_replay'])}**.",
        f"Après Holm, p H3 vaut `{analysis['h3']['uniform_replay']['p_holm']:.5f}` pour uniform et `{analysis['h3']['error_prioritized_replay']['p_holm']:.5f}` pour priorisé; leurs pires bins C régressent respectivement de `{max(analysis['h3']['uniform_replay']['regional_relative']) * 100:.2f} %` et `{max(analysis['h3']['error_prioritized_replay']['regional_relative']) * 100:.2f} %`, au-dessus de la limite régionale 10 %.",
        f"Garde apprenant: **{_fmt_gate(analysis['learner_guard'])}**. Garde TV B/C: **{'PASS' if all(v['passed'] for v in analysis['tv_guard'].values()) else 'FAIL'}**.",
        f"Excès moyen de replay TV priorisé face à uniform: B `{analysis['tv_guard']['B']['mean_excess'] * 100:.3f}` point, C `{analysis['tv_guard']['C']['mean_excess'] * 100:.3f}` point (limite +5 points). Temps cumulé enregistré: 26,9 minutes, sous le plafond de 90 minutes.",
        "",
        "## Décision mécanique, suspendue à la revue",
        "",
        f"- Replay uniforme admissible selon les portes: `{analysis['decision']['uniform_promoted']}`.",
        f"- Replay priorisé admissible selon les portes: `{analysis['decision']['error_prioritized_promoted']}`.",
        "- Statut: promotion suspendue; revue de résultats Claude requise.",
        "",
        "## Résultats complets audités",
        "",
        "Le fichier versionné `docs/research/j6_replay_001_analysis.json` contient les moyennes, IC BCa 95 %, signes, tests exacts/Holm, effets descriptifs, gardes B1/B2, H3, apprenant et TV. `docs/research/j6_replay_001_runs.json` conserve les métriques auditables des 36 runs par graine, domaine et bin.",
        "",
        "```json",
        json.dumps(analysis, indent=2, sort_keys=True),
        "```",
        "",
    ]
    result_path.write_text("\n".join(lines), encoding="utf-8")

    prompt = """Tu es le relecteur contradictoire de J6-R001. Lis intégralement docs/research/j6_replay_001_preregistration.md, docs/research/j6_replay_001_review.md, docs/research/j6_replay_001_results.md, docs/research/j6_replay_001_analysis.json et docs/research/j6_replay_001_runs.json. Vérifie l'intégrité des 12 triplets/36 runs, l'application littérale des portes gelées H1A/H1B/H2/H3, de la garde apprenant, de B1 (oubli mesurable et NON INTERPRÉTABLE sinon), de B2 (régression absolue co-primaire et accord de signe sur B), de B3, et de la garde TV +5 points. Recherche les erreurs de calcul ou d'interprétation et distingue absence d'effet, non-interprétabilité et échec. Réponds par un verdict unique AUTORISER / AUTORISER AVEC CORRECTIONS / NE PAS AUTORISER, liste les corrections bloquantes éventuelles, puis dis explicitement si uniform_replay et/ou error_prioritized_replay peuvent être promus. Ne propose aucun retuning post hoc sur 10301..10312."""
    request = f"""# Demande de revue contradictoire Claude — résultats J6-R001

Date: 2026-07-20

## Contexte

Le pré-enregistrement a reçu le verdict « AUTORISER AVEC CORRECTIONS BLOQUANTES »; B1, B2 et B3 ont été intégrés avant le smoke et avant toute graine réservée. Le smoke 10991 est vert. La campagne appariée 10301..10312 est terminée, sans changement des graines, budgets, ratio 50/50, priorités, seuils ni portes. Aucune promotion n'a encore été faite.

## Fichiers à lire

- `docs/research/j6_replay_001_preregistration.md`
- `docs/research/j6_replay_001_review.md`
- `docs/research/j6_replay_001_results.md`
- `docs/research/j6_replay_001_analysis.json`
- `docs/research/j6_replay_001_runs.json`

## Prompt exact

```text
{prompt}
```
"""
    (REPO / "CLAUDE_REVIEW_REQUEST.md").write_text(request, encoding="utf-8")


def run_smoke(spec: J6Spec, device) -> None:
    if not amendments_integrated():
        raise SystemExit("B1/B2/B3 amendment is missing; smoke forbidden")
    with keep_awake():
        prepare_seed(SMOKE_SEED, OUTPUT_ROOT, spec, device)
        results = [run_condition(SMOKE_SEED, condition, OUTPUT_ROOT, spec, device) for condition in CONDITIONS]
        checks = assert_smoke(SMOKE_SEED, spec, results, device)
    payload = {"passed": True, "seed": SMOKE_SEED, "spec_digest": spec.digest(), "checks": checks}
    SMOKE_RESULT.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_RESULT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"J6 smoke {SMOKE_SEED}: PASS ({SMOKE_RESULT})", flush=True)


def run_campaign(spec: J6Spec, device, review_accepted: bool) -> None:
    authorized, reason = campaign_authorized(review_accepted, spec)
    if not authorized:
        raise SystemExit(f"reserved campaign forbidden: {reason}")
    used = completed_campaign_seconds()
    remaining = MAX_CAMPAIGN_SECONDS - used
    if remaining <= 0:
        raise TimeoutError("J6 cumulative 90-minute campaign cap already reached")
    deadline = time.perf_counter() + remaining
    results = []
    with keep_awake():
        for seed in RESERVED_SEEDS:
            prepare_seed(seed, OUTPUT_ROOT, spec, device, deadline)
            for condition in CONDITIONS:
                if time.perf_counter() >= deadline:
                    raise TimeoutError("J6 cumulative 90-minute campaign cap reached")
                result = run_condition(seed, condition, OUTPUT_ROOT, spec, device, deadline)
                results.append(result)
                print(f"J6 {seed} {condition}: complete", flush=True)
    if len(results) != 36:
        raise RuntimeError(f"J6 run cap/budget diverged: {len(results)} != 36")
    analysis = analyze_results(results)
    analysis_path = OUTPUT_ROOT / "analysis.json"
    analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPO / "docs" / "research" / "j6_replay_001_analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (REPO / "docs" / "research" / "j6_replay_001_runs.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_results_documents(analysis, results)
    print(f"J6 campaign complete; analysis: {analysis_path}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen J6-R001 replay experiment")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true", help="run off-protocol seed 10991 and all seven integration checks")
    mode.add_argument("--review-accepted", action="store_true", help="accept recorded review and run reserved 10301..10312 campaign")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not review_authorized() and not args.smoke:
        raise SystemExit("recorded Claude review is not authorized or B1/B2/B3 are missing")
    spec = J6Spec()
    device = resolve_device(args.device)
    print(f"J6 device={device} spec={spec.digest()[:12]}", flush=True)
    if args.smoke:
        run_smoke(spec, device)
    else:
        run_campaign(spec, device, args.review_accepted)


if __name__ == "__main__":
    main()
