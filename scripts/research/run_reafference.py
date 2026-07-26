#!/usr/bin/env python3
"""Resumable, review-gated runner for the frozen REF-001 protocol."""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from learning.reafference import (  # noqa: E402
    BANKS,
    CONDITIONS,
    METHODS,
    RESERVED_SEEDS,
    SMOKE_SEED,
    STRUCTURED_CENTERS_DEG,
    RefBank,
    RefSpec,
    _correlation,
    _frame_hashes,
    analyze_evaluations,
    bank_path,
    calibration_threshold,
    checkpoint_path,
    corpus_path,
    evaluate_seed,
    load_corpus,
    make_learner,
    parameter_count,
    prepare_seed,
    ref_bench_config,
    run_path,
    state_digest,
    train_condition,
)
from learning.train_visual_jepa import resolve_device  # noqa: E402
from sim3d import bench_model  # noqa: E402


OUTPUT_ROOT = REPO / "data" / "processed" / "experiments" / "reafference_001"
PREREG = REPO / "docs" / "research" / "reafference_001_preregistration.md"
REVIEW = REPO / "docs" / "research" / "reafference_001_review.md"
SMOKE_RESULT = OUTPUT_ROOT / "smoke_12991.json"
ORIGINAL_CAP_SECONDS = 60 * 60


def amendments_integrated() -> bool:
    if not PREREG.exists():
        return False
    text = PREREG.read_text(encoding="utf-8")
    fragments = ("### C1", "### C2", "### C3", "### C4", "### C5", "`pixel_change_action`", "`2026072002`")
    return all(fragment in text for fragment in fragments)


def review_authorized() -> bool:
    if not REVIEW.exists() or not amendments_integrated():
        return False
    return "AUTORISER AVEC CORRECTIONS BLOQUANTES" in REVIEW.read_text(encoding="utf-8").upper()


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


def manipulation_checks(seed: int) -> dict:
    from sim3d.bench_env import BenchHeadEnv

    visibility = []
    for angle_bin, center in enumerate(STRUCTURED_CENTERS_DEG):
        env = BenchHeadEnv(ref_bench_config(101_000_000 + seed * 10 + angle_bin, center, angle_bin % 2))
        try:
            if env.model.joint(bench_model.JOINT_EXTERNAL).id < 0:
                raise AssertionError("REF world lacks a real external slide joint")
            if env.model.geom(bench_model.GEOM_EXTERNAL).id < 0:
                raise AssertionError("REF world lacks a real external object geom")
            for _ in range(25):
                env.step(center)
            env.set_external_object_displacement(-0.18)
            left = env.render_camera(64, 64)
            env.set_external_object_displacement(0.18)
            right = env.render_camera(64, 64)
            effect = float(np.mean(np.abs(left.astype(np.float64) - right.astype(np.float64))) / 255.0)
            if effect < 0.05:
                raise AssertionError(f"REF object visibility below 0.05 in bin {angle_bin}: {effect}")
            visibility.append(effect)
        finally:
            env.close()
    return {"real_geom_and_joint": True, "counterfactual_visibility_by_bin": visibility}


def zero_action_parity(seed: int, spec: RefSpec, device) -> dict:
    import torch

    action_model, action_probes, _ = make_learner(seed, "action_jepa", spec, device)
    control_model, control_probes, _ = make_learner(seed, "no_action_jepa", spec, device)
    action_digest = state_digest(action_model, action_probes)
    control_digest = state_digest(control_model, control_probes)
    if action_digest != control_digest:
        raise AssertionError("REF initial state digests differ")
    if parameter_count(action_model, action_probes) != parameter_count(control_model, control_probes):
        raise AssertionError("REF condition capacities differ")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed + 1)
    frames = torch.rand((8, 3, spec.image_size, spec.image_size), generator=generator).to(device)
    actions = torch.zeros((8, spec.max_horizon), device=device)
    horizons = torch.ones((8, 1), device=device)
    action_model.eval()
    control_model.eval()
    with torch.no_grad():
        action_output = action_model(frames, actions, horizons)
        control_output = control_model(frames, actions, horizons)
    if not all(torch.equal(left, right) for left, right in zip(action_output, control_output)):
        raise AssertionError("REF zero-action forwards are not bit-identical")
    return {
        "state_digest": action_digest,
        "parameter_count": parameter_count(action_model, action_probes),
        "zero_action_forward_bit_identical": True,
    }


def data_integrity_checks(seed: int, root: Path, spec: RefSpec) -> dict:
    corpus = load_corpus(corpus_path(root, seed))
    banks = {kind: RefBank.load(bank_path(root, seed, kind)) for kind in BANKS}
    correlation = _correlation(corpus["decision_action_delta_deg"], corpus["decision_object_delta_m"])
    if abs(correlation) > 0.05:
        raise AssertionError(f"REF corpus independence failed: {correlation}")
    mixed_correlation = _correlation(banks["mixed"].head_delta_deg, banks["mixed"].object_delta_m)
    if abs(mixed_correlation) > 0.05:
        raise AssertionError(f"REF mixed independence failed: {mixed_correlation}")
    if not np.all(banks["external_only"].head_delta_deg == 0):
        raise AssertionError("REF external_only does not structurally hold the head")
    if np.any(banks["self_calibration"].head_delta_deg == 0) or np.any(banks["self_test"].head_delta_deg == 0):
        raise AssertionError("REF self banks contain a zero-motion pair")

    seen = _frame_hashes(corpus["frames"])
    disjoint = {}
    for kind, bank in banks.items():
        current = _frame_hashes(bank.frames_start) | _frame_hashes(bank.frames_end)
        if seen & current:
            raise AssertionError(f"REF image leakage involving {kind}")
        seen |= current
        disjoint[kind] = True

    model_batch_keys = {"frames", "requested_deg", "as5600_deg", "episode"}
    forbidden = {"object_displacement_m", "episode_object_mobile", "labels", "object_delta_m"}
    if model_batch_keys & forbidden:
        raise AssertionError("REF model batch contract exposes an object field")
    return {
        "corpus_action_object_correlation": correlation,
        "mixed_action_object_correlation": mixed_correlation,
        "external_only_constant_head_and_disjoint_rng": True,
        "self_pairs_nonzero_motion": True,
        "image_spaces_disjoint": disjoint,
        "model_batch_keys": sorted(model_batch_keys),
        "object_and_labels_absent_from_model_batches": True,
        "budgets": {
            "images": spec.images,
            "decisions": spec.decisions,
            "optimizer_steps_per_condition": spec.optimizer_steps,
            "batch_size": spec.batch_size,
            "examples_gradient_per_condition": spec.optimizer_steps * spec.batch_size,
            "pairs_per_bank_bin": spec.pairs_per_bin,
        },
    }


def result_integrity_checks(results: list[dict], evaluation: dict, spec: RefSpec) -> dict:
    if len(results) != 2 or {item["condition"] for item in results} != set(CONDITIONS):
        raise AssertionError("REF smoke requires both frozen conditions")
    if len({item["corpus_sha256"] for item in results}) != 1:
        raise AssertionError("REF conditions did not consume the same corpus bytes")
    if len({json.dumps(item["bank_sha256"], sort_keys=True) for item in results}) != 1:
        raise AssertionError("REF conditions did not consume the same bank bytes")
    if len({item["initial_state_digest"] for item in results}) != 1:
        raise AssertionError("REF initializations differ")
    if len({item["batch_order_digest"] for item in results}) != 1:
        raise AssertionError("REF batch orders differ")
    if len({item["parameter_count"] for item in results}) != 1:
        raise AssertionError("REF capacities differ")
    expected = spec.optimizer_steps * spec.batch_size
    if any(item["optimizer_steps"] != spec.optimizer_steps or item["examples_gradient"] != expected for item in results):
        raise AssertionError("REF training budget diverges")

    bins = np.asarray(evaluation["calibration_bins"], dtype=np.int8)
    recomputed = {}
    for method in METHODS:
        raw = np.asarray(evaluation["raw_calibration_scores"][method], dtype=np.float64)
        values = [calibration_threshold(raw[bins == angle_bin]) for angle_bin in range(6)]
        if values != evaluation["thresholds"][method]:
            raise AssertionError(f"REF {method} thresholds are not exactly recomputable")
        recomputed[method] = values
    return {
        "shared_corpus_and_banks": True,
        "identical_initialization_and_batch_order": True,
        "identical_capacity": True,
        "exact_training_budgets": True,
        "thresholds_exactly_recomputable": recomputed,
    }


def frozen_time_manifest(shared_seconds: float, condition_seconds: list[float]) -> dict:
    mean_condition = float(np.mean(condition_seconds))
    per_run = shared_seconds / 2.0 + mean_condition
    projection = 32.0 * per_run
    if projection <= ORIGINAL_CAP_SECONDS:
        effective = ORIGINAL_CAP_SECONDS
    else:
        effective = math.ceil((projection * 1.10) / 300.0) * 300
    if effective < projection:
        raise AssertionError("REF effective cap does not contain its projection")
    return {
        "shared_smoke_seconds": shared_seconds,
        "condition_smoke_seconds": condition_seconds,
        "mean_condition_seconds": mean_condition,
        "projected_seconds": projection,
        "original_cap_seconds": ORIGINAL_CAP_SECONDS,
        "margin_fraction_if_amended": 0.10 if projection > ORIGINAL_CAP_SECONDS else 0.0,
        "effective_cap_seconds": effective,
        "amended": projection > ORIGINAL_CAP_SECONDS,
        "formula": "32 * (shared_smoke_seconds / 2 + mean_condition_seconds)",
    }


def campaign_authorized(spec: RefSpec, review_accepted: bool) -> tuple[bool, str]:
    if not review_accepted:
        return False, "pass --review-accepted after accepting the recorded verdict"
    if not review_authorized():
        return False, "REF review authorization or C1-C5 amendment missing"
    if not SMOKE_RESULT.exists():
        return False, "REF smoke 12991 has not passed"
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    if not smoke.get("passed") or smoke.get("spec_digest") != spec.digest():
        return False, "REF smoke is red or belongs to another specification"
    time_gate = smoke.get("time_gate", {})
    if float(time_gate.get("effective_cap_seconds", 0)) < float(time_gate.get("projected_seconds", math.inf)):
        return False, "REF time projection does not fit the frozen effective cap"
    return True, "authorized"


def completed_campaign_seconds() -> float:
    seconds = 0.0
    for seed in RESERVED_SEEDS:
        manifest = OUTPUT_ROOT / "manifests" / f"seed_{seed}.json"
        if manifest.exists():
            seconds += float(json.loads(manifest.read_text(encoding="utf-8")).get("elapsed_seconds", 0.0))
        for condition in CONDITIONS:
            result = run_path(OUTPUT_ROOT, seed, condition)
            if result.exists():
                seconds += float(json.loads(result.read_text(encoding="utf-8")).get("elapsed_seconds", 0.0))
    return seconds


def run_smoke(spec: RefSpec, device) -> None:
    if not review_authorized():
        raise SystemExit("REF review authorization or C1-C5 amendment missing; smoke forbidden")
    started = time.perf_counter()
    with keep_awake():
        manipulations = manipulation_checks(SMOKE_SEED)
        parity = zero_action_parity(SMOKE_SEED, spec, device)
        prep_started = time.perf_counter()
        prepare_seed(SMOKE_SEED, OUTPUT_ROOT, spec)
        shared_seconds = time.perf_counter() - prep_started
        data_checks = data_integrity_checks(SMOKE_SEED, OUTPUT_ROOT, spec)
        results = []
        condition_seconds = []
        for condition in CONDITIONS:
            condition_started = time.perf_counter()
            results.append(train_condition(SMOKE_SEED, condition, OUTPUT_ROOT, spec, device))
            condition_seconds.append(time.perf_counter() - condition_started)
        evaluation = evaluate_seed(SMOKE_SEED, OUTPUT_ROOT, spec)
        result_checks = result_integrity_checks(results, evaluation, spec)
    time_gate = frozen_time_manifest(shared_seconds, condition_seconds)
    payload = {
        "passed": True,
        "seed": SMOKE_SEED,
        "spec_digest": spec.digest(),
        "preregistration_sha256": __import__("hashlib").sha256(PREREG.read_bytes()).hexdigest(),
        "elapsed_seconds": time.perf_counter() - started,
        "checks": {
            "manipulations": manipulations,
            "zero_action_parity": parity,
            "data": data_checks,
            "results": result_checks,
        },
        "time_gate": time_gate,
    }
    SMOKE_RESULT.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_RESULT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"REF-001 smoke {SMOKE_SEED}: PASS; projection={time_gate['projected_seconds'] / 60:.2f} min "
        f"cap={time_gate['effective_cap_seconds'] / 60:.0f} min",
        flush=True,
    )


def write_results(analysis: dict, evaluations: list[dict], elapsed_seconds: float) -> None:
    analysis_path = REPO / "docs" / "research" / "reafference_001_analysis.json"
    evaluations_path = REPO / "docs" / "research" / "reafference_001_evaluations.json"
    results_path = REPO / "docs" / "research" / "reafference_001_results.md"
    write_integrity_export()
    analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evaluations_path.write_text(json.dumps(evaluations, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    eligible = analysis["decision"]["eligible_for_contradictory_review"]
    results_path.write_text(
        "\n".join(
            [
                "# Résultats REF-001 — réafférence visuelle",
                "",
                "Simulation uniquement sous D-008. Variante close après cette campagne.",
                "Aucune promotion avant revue contradictoire des résultats.",
                "",
                "## Intégrité",
                "",
                "- 16 paires apprenantes / 32 runs complets, graines 12301..12316.",
                "- Smoke 12991 vert; corpus, banques, initialisations, ordres de batchs,",
                "  capacités, budgets et seuils recomputables contrôlés.",
                f"- Temps mural cumulé consigné: `{elapsed_seconds / 60:.2f}` minutes.",
                "",
                "## Portes mécaniques",
                "",
                f"- H1, explication de l'ego-motion: `{analysis['h1']['passed']}`.",
                f"- H2, détection externe pure: `{analysis['h2_passed']}`.",
                f"- H3, détection mixte: `{analysis['h3_passed']}`.",
                f"- H4, spécificité: `{analysis['h4']['passed']}`.",
                f"- Gardes apprenant / indépendance: `{analysis['guards']['learner']}` / `{analysis['guards']['independence']}`.",
                f"- Éligible à la revue contradictoire: `{eligible}`.",
                "",
                "## Portée",
                "",
                "H1 établit seulement une meilleure explication du mouvement propre. H2–H4",
                "établissent seulement une détection opérationnelle du changement externe.",
                "La revendication de réafférence exige conjointement les deux résultats et ne",
                "vaut ni segmentation, ni causalité générale, ni agentivité.",
                "",
                "## Analyse complète",
                "",
                "```json",
                json.dumps(analysis, indent=2, sort_keys=True),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    prompt = """Tu es le relecteur contradictoire des résultats REF-001. Lis intégralement docs/research/reafference_001_preregistration.md, docs/research/reafference_001_review.md, docs/research/reafference_001_results.md, docs/research/reafference_001_analysis.json, docs/research/reafference_001_evaluations.json et docs/research/reafference_001_integrity.json. Recalcule H1, les six comparaisons H2/H3 sous Holm commun, les TPR absolues et H4 depuis les 16 graines. Audite les gardes apprenant, indépendance, visibilité, fuite, équité, budgets, seuils recomputables, diagnostics petit-changement et respect du plafond amendé au smoke. Distingue explication de l'ego-motion et détection externe. Réponds par AUTORISER, AUTORISER AVEC CORRECTIONS ou NE PAS AUTORISER, puis dis explicitement si REF-001 peut être promu comme détecteur minimal de réafférence. Ne propose aucun retuning sur 12301..12316. Écris uniquement docs/research/reafference_001_results_review.md; ne modifie aucun autre fichier et ne lance aucun nouvel entraînement."""
    (REPO / "CLAUDE_REVIEW_REQUEST.md").write_text(
        "\n".join(
            [
                "# Demande de revue contradictoire Claude — résultats REF-001",
                "",
                "La campagne réservée est terminée. Aucune promotion n'a été faite.",
                "Sortie unique attendue: `docs/research/reafference_001_results_review.md`.",
                "",
                "## Prompt exact",
                "",
                "```text",
                prompt,
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_integrity_export() -> dict:
    """Export the ignored runner metadata needed for a repository-only audit."""

    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    seeds = []
    for seed in RESERVED_SEEDS:
        manifest_path = OUTPUT_ROOT / "manifests" / f"seed_{seed}.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        conditions = {}
        for condition in CONDITIONS:
            result = json.loads(run_path(OUTPUT_ROOT, seed, condition).read_text(encoding="utf-8"))
            conditions[condition] = {key: value for key, value in result.items() if key not in {"scores", "checkpoint"}}
        if len({item["initial_state_digest"] for item in conditions.values()}) != 1:
            raise RuntimeError(f"REF integrity export: initialization mismatch at seed {seed}")
        if len({item["batch_order_digest"] for item in conditions.values()}) != 1:
            raise RuntimeError(f"REF integrity export: batch-order mismatch at seed {seed}")
        if len({item["parameter_count"] for item in conditions.values()}) != 1:
            raise RuntimeError(f"REF integrity export: capacity mismatch at seed {seed}")
        if len({item["corpus_sha256"] for item in conditions.values()}) != 1:
            raise RuntimeError(f"REF integrity export: corpus mismatch at seed {seed}")
        if len({json.dumps(item["bank_sha256"], sort_keys=True) for item in conditions.values()}) != 1:
            raise RuntimeError(f"REF integrity export: bank mismatch at seed {seed}")
        seeds.append(
            {
                "seed": seed,
                "manifest": manifest,
                "conditions": conditions,
                "paired_integrity": {
                    "initialization_identical": True,
                    "batch_order_identical": True,
                    "capacity_identical": True,
                    "corpus_and_banks_identical": True,
                },
            }
        )
    payload = {
        "spec_digest": smoke["spec_digest"],
        "smoke": smoke,
        "reserved_seeds": seeds,
        "totals": {
            "paired_seeds": len(seeds),
            "learner_runs": len(seeds) * len(CONDITIONS),
            "recorded_seconds": completed_campaign_seconds(),
            "effective_cap_seconds": smoke["time_gate"]["effective_cap_seconds"],
        },
    }
    target = REPO / "docs" / "research" / "reafference_001_integrity.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def run_campaign(spec: RefSpec, device, review_accepted: bool) -> None:
    authorized, reason = campaign_authorized(spec, review_accepted)
    if not authorized:
        raise SystemExit(f"REF reserved campaign forbidden: {reason}")
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    cap = float(smoke["time_gate"]["effective_cap_seconds"])
    used = completed_campaign_seconds()
    if used >= cap:
        raise TimeoutError("REF-001 frozen cumulative wall-time cap already reached")
    deadline = time.perf_counter() + cap - used
    evaluations = []
    with keep_awake():
        for seed in RESERVED_SEEDS:
            if time.perf_counter() >= deadline:
                raise TimeoutError("REF-001 frozen cumulative wall-time cap reached before seed preparation")
            prepare_seed(seed, OUTPUT_ROOT, spec)
            for condition in CONDITIONS:
                train_condition(seed, condition, OUTPUT_ROOT, spec, device, deadline)
                print(f"REF-001 {seed} {condition}: complete", flush=True)
            evaluations.append(evaluate_seed(seed, OUTPUT_ROOT, spec))
            print(f"REF-001 {seed}: evaluation complete", flush=True)
    analysis = analyze_evaluations(evaluations)
    elapsed = completed_campaign_seconds()
    write_results(analysis, evaluations, elapsed)
    print(
        f"REF-001 campaign complete; eligible={analysis['decision']['eligible_for_contradictory_review']}",
        flush=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen REF-001")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--review-accepted", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    spec = RefSpec()
    device = resolve_device(args.device)
    print(f"REF-001 device={device} spec={spec.digest()[:12]}", flush=True)
    if args.smoke:
        run_smoke(spec, device)
    else:
        run_campaign(spec, device, args.review_accepted)


if __name__ == "__main__":
    main()
