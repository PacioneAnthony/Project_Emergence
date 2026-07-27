#!/usr/bin/env python3
"""Review-gated runner for the amended REF-002 protocol."""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from learning.reafference_002 import (  # noqa: E402
    BANKS,
    CONDITIONS,
    MOBILE_MATCHED_BANKS,
    RESERVED_SEEDS,
    SMOKE_SEED,
    STRUCTURED_CENTERS_DEG,
    Ref2Bank,
    Ref2Spec,
    _correlation,
    _frame_hashes,
    analyze_evaluations,
    bank_path,
    build_matched_motion_plans,
    build_motor_input,
    encoder_digest,
    evaluation_path,
    evaluate_seed,
    make_learner,
    matched_motion_signature,
    parameter_counts,
    prepare_seed,
    ref2_bench_config,
    run_path,
    state_digest,
    train_condition,
)
from learning.train_visual_jepa import resolve_device  # noqa: E402
from sim3d import bench_model  # noqa: E402


OUTPUT_ROOT = REPO / "data" / "processed" / "experiments" / "reafference_002"
PREREG = REPO / "docs" / "research" / "reafference_002_preregistration.md"
REVIEW = REPO / "docs" / "research" / "reafference_002_review.md"
SMOKE_RESULT = OUTPUT_ROOT / "smoke_13991.json"
SMOKE_FAILURE = OUTPUT_ROOT / "smoke_13991_failure.json"
CAMPAIGN_FAILURE = OUTPUT_ROOT / "campaign_failure.json"
ORIGINAL_CAP_SECONDS = 75 * 60


def protocol_digest() -> str:
    return hashlib.sha256(PREREG.read_bytes()).hexdigest()


def amendments_integrated() -> bool:
    if not PREREG.exists():
        return False
    text = PREREG.read_text(encoding="utf-8")
    fragments = [f"### C{index}" for index in range(1, 9)]
    fragments += ["SANITY-EXTERNAL", "six passes H5", "`215` tests existants"]
    return all(fragment in text for fragment in fragments)


def review_authorized() -> bool:
    if not REVIEW.exists() or not amendments_integrated():
        return False
    return (
        "AUTORISER AVEC CORRECTIONS BLOQUANTES"
        in REVIEW.read_text(encoding="utf-8").upper()
    )


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

    effects = []
    for angle_bin, center in enumerate(STRUCTURED_CENTERS_DEG):
        env = BenchHeadEnv(
            ref2_bench_config(
                171_000_000 + seed * 10 + angle_bin,
                bearing_deg=center + 8.0,
                context=angle_bin % 2,
            )
        )
        try:
            if env.model.joint(bench_model.JOINT_EXTERNAL).id < 0:
                raise AssertionError("REF2 world lacks the external joint")
            if env.model.geom(bench_model.GEOM_EXTERNAL).id < 0:
                raise AssertionError("REF2 world lacks the external object")
            for _ in range(25):
                env.step(center)
            env.set_external_object_displacement(-0.20)
            left = env.render_camera(64, 64)
            env.set_external_object_displacement(0.20)
            right = env.render_camera(64, 64)
            effect = float(
                np.mean(np.abs(left.astype(np.float64) - right.astype(np.float64)))
                / 255.0
            )
            if effect < 0.05:
                raise AssertionError(
                    f"REF2 visibility below 0.05 in bin {angle_bin}: {effect}"
                )
            effects.append(effect)
        finally:
            env.close()
    return {"real_geom_and_joint": True, "counterfactual_visibility_by_bin": effects}


def initial_fairness_checks(seed: int, spec: Ref2Spec, device) -> dict:
    import torch

    models = {}
    for condition in CONDITIONS:
        model, _ = make_learner(seed, condition, spec, device)
        models[condition] = model
    encoder_digests = {condition: encoder_digest(model) for condition, model in models.items()}
    state_digests = {condition: state_digest(model) for condition, model in models.items()}
    counts = {condition: parameter_counts(model) for condition, model in models.items()}
    if len(set(encoder_digests.values())) != 1 or len(set(state_digests.values())) != 1:
        raise AssertionError("REF2 initial weights differ")
    if len({json.dumps(value, sort_keys=True) for value in counts.values()}) != 1:
        raise AssertionError("REF2 parameter capacities differ")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed + 1)
    frames = torch.rand((8, 3, 64, 64), generator=generator).to(device)
    motor = torch.zeros((8, 7), device=device)
    motor[:, 0] = torch.linspace(-0.8, 0.8, 8, device=device)
    motor[:, -1] = 1.0
    with torch.no_grad():
        concat = models["concat_relative_jepa"](frames, motor)
        no_command = models["no_command_jepa"](frames, motor)
        transport = models["transport_jepa"](frames, motor)
    if not all(torch.equal(left, right) for left, right in zip(concat, no_command)):
        raise AssertionError("REF2 concat-zero/no-command initialization parity failed")
    if not all(torch.equal(left, right) for left, right in zip(concat, transport)):
        raise AssertionError("REF2 zero-displacement transport is not identity")
    return {
        "encoder_digest": next(iter(encoder_digests.values())),
        "state_digest": next(iter(state_digests.values())),
        "parameter_counts": next(iter(counts.values())),
        "zero_command_forward_bit_identical": True,
    }


def benchmark_fairness(seed: int, spec: Ref2Spec, device) -> dict:
    import torch

    times = {}
    for condition in CONDITIONS:
        model, optimizer = make_learner(seed, condition, spec, device)
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed + 2)
        frames = torch.rand((32, 3, 64, 64), generator=generator).to(device)
        target = torch.rand((32, 128, 8, 8), generator=generator).to(device)
        motor = torch.rand((32, 7), generator=generator).to(device)
        durations = []
        for step in range(120):
            started = time.perf_counter()
            current, prediction = model(frames, motor)
            loss = torch.mean((prediction - target) ** 2) + 0.01 * torch.mean(current**2)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            if step >= 20:
                durations.append(elapsed)
        times[condition] = float(np.median(durations))
    ratio = max(times.values()) / min(times.values())
    if ratio > 1.25:
        raise AssertionError(f"REF2 per-step wall-time ratio exceeds 1.25: {ratio}")
    return {"median_seconds_per_step": times, "max_min_ratio": ratio}


def data_integrity_checks(seed: int, root: Path, spec: Ref2Spec) -> dict:
    banks = {kind: Ref2Bank.load(bank_path(root, seed, kind)) for kind in BANKS}
    planned = build_matched_motion_plans(seed, spec)
    for angle_bin in range(6):
        signatures = [
            matched_motion_signature(planned[kind], angle_bin)
            for kind in MOBILE_MATCHED_BANKS
        ]
        if signatures[1:] != signatures[:-1]:
            raise AssertionError("REF2 mobile schedule multiset mismatch")
    seen: set[bytes] = set()
    diversity = {}
    for kind, bank in banks.items():
        start_hashes = _frame_hashes(bank.frames_start)
        end_hashes = _frame_hashes(bank.frames_end)
        current = set(start_hashes) | set(end_hashes)
        if seen & current:
            raise AssertionError(f"REF2 inter-bank image collision involving {kind}")
        seen |= current
        pair_hashes = [
            hashlib.sha256(left + right).digest()
            for left, right in zip(start_hashes, end_hashes)
        ]
        if len(set(pair_hashes)) != len(pair_hashes):
            raise AssertionError(f"REF2 duplicated pair inside {kind}")
        diversity[kind] = {
            "distinct_start_frames": len(set(start_hashes)),
            "distinct_end_frames": len(set(end_hashes)),
            "distinct_pairs": len(set(pair_hashes)),
        }
        recomputed = build_motor_input(
            bank.current_angle_deg,
            bank.command_targets_deg,
            bank.horizon,
        )
        if not np.array_equal(recomputed, bank.motor_input):
            raise AssertionError(f"REF2 future-free motor reconstruction failed for {kind}")
    for kind in ("moving_self_calibration", "moving_self_test", "micro_self_calibration", "micro_self_test", "mixed"):
        bank = banks[kind]
        for angle_bin in range(6):
            selected = bank.angle_bins == angle_bin
            variance = float(np.var(bank.motor_input[selected, 1:6]))
            if variance <= 0:
                raise AssertionError(f"REF2 zero action variance in {kind} bin {angle_bin}")
    mixed_corr = _correlation(
        banks["mixed"].head_delta_deg,
        banks["mixed"].object_delta_m,
    )
    if abs(mixed_corr) > 0.05:
        raise AssertionError(f"REF2 mixed independence failed: {mixed_corr}")
    if np.any(banks["external_only"].head_delta_deg != 0):
        raise AssertionError("REF2 external-only head is not constant")
    return {
        "matched_mobile_schedules": True,
        "future_free_motor_inputs": True,
        "image_and_pair_diversity": diversity,
        "action_variance_positive": True,
        "mixed_correlation": mixed_corr,
        "external_head_constant": True,
    }


def result_integrity_checks(
    results: list[dict],
    evaluation: dict,
    spec: Ref2Spec,
    *,
    root: Path,
    seed: int,
    require_learner: bool = True,
) -> dict:
    if len(results) != 3 or {item["condition"] for item in results} != set(CONDITIONS):
        raise AssertionError("REF2 smoke requires three complete conditions")
    for key in (
        "corpus_sha256",
        "initial_state_digest",
        "initial_encoder_digest",
        "batch_order_digest",
        "parameter_count",
        "trainable_parameter_count",
        "nonzero_gradient_parameter_count",
    ):
        values = {
            json.dumps(item[key], sort_keys=True)
            for item in results
        }
        if len(values) != 1:
            raise AssertionError(f"REF2 fairness mismatch: {key}")
    if any(
        item["nonzero_gradient_parameter_count"] != item["trainable_parameter_count"]
        for item in results
    ):
        raise AssertionError("REF2 contains a trainable parameter without gradient")
    if len({item["h5"]["mapping_sha256"] for item in results}) != 1:
        raise AssertionError("REF2 H5 mappings differ between conditions")
    for condition in CONDITIONS:
        if require_learner and not evaluation["learner_guard"][condition]["passed"]:
            raise AssertionError(f"REF2 learner guard failed for {condition}")
        for calibration in ("moving_self_calibration", "micro_self_calibration"):
            minimum = evaluation["copy_diagnostics"][condition][calibration]["minimum"]
            if not np.isfinite(minimum) or minimum <= 0:
                raise AssertionError(
                    f"REF2 copy MSE calibration guard failed: {condition}/{calibration}"
                )
    fractions = evaluation["warp"]["valid_fraction_by_bank"]
    banks = {
        kind: Ref2Bank.load(bank_path(root, seed, kind))
        for kind in MOBILE_MATCHED_BANKS
    }
    for angle_bin in range(6):
        signatures = []
        for kind in MOBILE_MATCHED_BANKS:
            values = np.asarray(fractions[kind])[banks[kind].angle_bins == angle_bin]
            signatures.append(np.sort(values).tolist())
        if signatures[1:] != signatures[:-1]:
            raise AssertionError(f"REF2 valid-mask multiset mismatch in bin {angle_bin}")
    return {
        "shared_data_initialization_batches": True,
        "equal_total_trainable_and_active_parameters": True,
        "learner_guards": all(
            evaluation["learner_guard"][condition]["passed"] for condition in CONDITIONS
        ),
        "positive_calibration_copy_mse": True,
        "shared_h5_mapping": True,
        "matched_warp_valid_masks": True,
    }


def frozen_time_manifest(shared_seconds: float, condition_seconds: list[float]) -> dict:
    mean_condition = float(np.mean(condition_seconds))
    projection = 48.0 * (shared_seconds / 3.0 + mean_condition)
    effective = (
        ORIGINAL_CAP_SECONDS
        if projection <= ORIGINAL_CAP_SECONDS
        else math.ceil((projection * 1.10) / 300.0) * 300
    )
    return {
        "shared_smoke_seconds": shared_seconds,
        "condition_complete_seconds": condition_seconds,
        "mean_condition_seconds": mean_condition,
        "projected_seconds": projection,
        "original_cap_seconds": ORIGINAL_CAP_SECONDS,
        "effective_cap_seconds": effective,
        "amended": projection > ORIGINAL_CAP_SECONDS,
        "margin_fraction_if_amended": 0.10 if projection > ORIGINAL_CAP_SECONDS else 0.0,
        "formula": "48 * (shared_smoke_seconds / 3 + mean_condition_seconds)",
    }


def run_smoke(spec: Ref2Spec, device) -> None:
    if not review_authorized():
        raise SystemExit("REF2 review authorization or C1-C8 amendment missing")
    started = time.perf_counter()
    with keep_awake():
        manipulation = manipulation_checks(SMOKE_SEED)
        initial_fairness = initial_fairness_checks(SMOKE_SEED, spec, device)
        benchmark = benchmark_fairness(SMOKE_SEED, spec, device)
        shared_started = time.perf_counter()
        prepare_seed(SMOKE_SEED, OUTPUT_ROOT, spec)
        data_checks = data_integrity_checks(SMOKE_SEED, OUTPUT_ROOT, spec)
        preparation_seconds = time.perf_counter() - shared_started
        results = []
        for condition in CONDITIONS:
            result = train_condition(SMOKE_SEED, condition, OUTPUT_ROOT, spec, device)
            results.append(result)
            print(f"REF-002 smoke {condition}: complete", flush=True)
        evaluation_started = time.perf_counter()
        evaluation = evaluate_seed(SMOKE_SEED, OUTPUT_ROOT, spec)
        result_checks = result_integrity_checks(
            results,
            evaluation,
            spec,
            root=OUTPUT_ROOT,
            seed=SMOKE_SEED,
        )
        shared_evaluation_seconds = time.perf_counter() - evaluation_started
    shared_seconds = preparation_seconds + shared_evaluation_seconds
    condition_seconds = [
        float(item["timing"]["complete_condition_seconds"]) for item in results
    ]
    time_gate = frozen_time_manifest(shared_seconds, condition_seconds)
    payload = {
        "passed": True,
        "seed": SMOKE_SEED,
        "spec_digest": spec.digest(),
        "preregistration_sha256": protocol_digest(),
        "elapsed_seconds": time.perf_counter() - started,
        "phase_seconds": {
            "preparation_and_data_guards": preparation_seconds,
            "shared_analytic_evaluation": shared_evaluation_seconds,
            "conditions": {
                item["condition"]: item["timing"] for item in results
            },
        },
        "checks": {
            "manipulation": manipulation,
            "initial_fairness": initial_fairness,
            "benchmark_fairness": benchmark,
            "data": data_checks,
            "results": result_checks,
        },
        "time_gate": time_gate,
        "reserved_seeds_opened": False,
    }
    SMOKE_RESULT.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_RESULT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if SMOKE_FAILURE.exists():
        SMOKE_FAILURE.unlink()
    print(
        f"REF-002 smoke {SMOKE_SEED}: PASS; "
        f"projection={time_gate['projected_seconds'] / 60:.2f} min; "
        f"cap={time_gate['effective_cap_seconds'] / 60:.0f} min",
        flush=True,
    )


def campaign_authorized(spec: Ref2Spec, review_accepted: bool) -> tuple[bool, str]:
    if not review_accepted:
        return False, "explicit --review-accepted is required"
    if not review_authorized():
        return False, "REF2 review or C1-C8 amendments are missing"
    if not SMOKE_RESULT.exists():
        return False, "REF2 smoke 13991 has not passed"
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    if not smoke.get("passed") or smoke.get("spec_digest") != spec.digest():
        return False, "REF2 smoke is red or belongs to another specification"
    if smoke.get("preregistration_sha256") != protocol_digest():
        return False, "REF2 protocol changed after the smoke"
    time_gate = smoke.get("time_gate", {})
    if float(time_gate.get("effective_cap_seconds", 0)) < float(
        time_gate.get("projected_seconds", math.inf)
    ):
        return False, "REF2 time projection exceeds its frozen cap"
    if smoke.get("reserved_seeds_opened"):
        return False, "REF2 smoke manifest reports premature reserved-seed access"
    return True, "authorized"


def completed_campaign_seconds() -> float:
    total = 0.0
    for seed in RESERVED_SEEDS:
        manifest = OUTPUT_ROOT / "manifests" / f"seed_{seed}.json"
        if manifest.exists():
            total += float(
                json.loads(manifest.read_text(encoding="utf-8")).get(
                    "elapsed_seconds",
                    0.0,
                )
            )
        for condition in CONDITIONS:
            result_file = run_path(OUTPUT_ROOT, seed, condition)
            if result_file.exists():
                result = json.loads(result_file.read_text(encoding="utf-8"))
                total += float(result.get("timing", {}).get("complete_condition_seconds", 0.0))
        evaluation_file = evaluation_path(OUTPUT_ROOT, seed)
        if evaluation_file.exists():
            total += float(
                json.loads(evaluation_file.read_text(encoding="utf-8")).get(
                    "elapsed_seconds",
                    0.0,
                )
            )
    return total


def write_results(analysis: dict, evaluations: list[dict], elapsed_seconds: float) -> None:
    analysis_path = REPO / "docs" / "research" / "reafference_002_analysis.json"
    evaluations_path = REPO / "docs" / "research" / "reafference_002_evaluations.json"
    results_path = REPO / "docs" / "research" / "reafference_002_results.md"
    write_integrity_export()
    analysis_path.write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evaluations_path.write_text(
        json.dumps(evaluations, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    eligible = analysis["decision"]["eligible_for_contradictory_review"]
    lines = [
        "# Résultats REF-002 — transport sensorimoteur spatial",
        "",
        "Simulation uniquement sous D-008. Variante close après cette campagne.",
        "Aucune promotion avant revue contradictoire des résultats.",
        "",
        "## Intégrité",
        "",
        "- 16 triplets apprenants / 48 runs complets, graines 13301..13316.",
        "- Smoke 13991 vert et protocole amendé C1–C8 gelé avant 13301.",
        f"- Temps mural cumulé consigné: `{elapsed_seconds / 60:.2f}` minutes.",
        "",
        "## Portes mécaniques",
        "",
        f"- H1, transport du mouvement propre: `{analysis['h1_passed']}`.",
        f"- H3, détection externe en mixte: `{analysis['h3_passed']}`.",
        f"- H4, spécificité mobile/micro: `{analysis['h4_passed']}`.",
        f"- H5, non-dégénérescence: `{analysis['h5_passed']}`.",
        f"- SANITY-EXTERNAL finie: `{analysis['guards']['sanity_external_finite']}`.",
        f"- Garde apprenant: `{analysis['guards']['learner']}`.",
        f"- Éligible à la revue contradictoire: `{eligible}`.",
        "",
        "## Portée",
        "",
        "H3 est l'unique porte de détection réafférente. SANITY-EXTERNAL est",
        "descriptive et ne soutient aucune revendication. H5 prouve seulement que le",
        "transport n'est pas dégénéré, pas un modèle causal général.",
        "",
        "## Analyse complète",
        "",
        "```json",
        json.dumps(analysis, indent=2, sort_keys=True),
        "```",
        "",
    ]
    results_path.write_text("\n".join(lines), encoding="utf-8")
    prompt = (
        "Tu es le relecteur contradictoire des résultats REF-002. Lis intégralement "
        "docs/research/reafference_002_preregistration.md, "
        "docs/research/reafference_002_review.md, "
        "docs/research/reafference_002_results.md, "
        "docs/research/reafference_002_analysis.json et "
        "docs/research/reafference_002_evaluations.json ainsi que "
        "docs/research/reafference_002_integrity.json. Recalcule H1, H3 et H5 "
        "sous Holm commun à huit tests, H4 sur les strates mobile et micro, et "
        "SANITY-EXTERNAL depuis les 16 graines. Audite C1–C8, les gardes de copie "
        "strictement positive, équité effective, non-fuite motrice, unicité, "
        "appariement des masques, apprenant et plafond. Réponds par AUTORISER, "
        "AUTORISER AVEC CORRECTIONS ou NE PAS AUTORISER, puis dis explicitement "
        "si le transport spatial peut être promu comme mécanisme minimal dans ce "
        "monde. Ne propose aucun retuning sur 13301..13316. Écris uniquement "
        "docs/research/reafference_002_results_review.md et ne lance aucun nouvel "
        "entraînement."
    )
    (REPO / "CLAUDE_REVIEW_REQUEST.md").write_text(
        "\n".join(
            [
                "# Demande de revue contradictoire Claude Opus 5 — résultats REF-002",
                "",
                "La campagne réservée est terminée. Aucune promotion n'a été faite.",
                "Sortie attendue: `docs/research/reafference_002_results_review.md`.",
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
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    seeds = []
    for seed in RESERVED_SEEDS:
        manifest_path = OUTPUT_ROOT / "manifests" / f"seed_{seed}.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        evaluation = json.loads(
            evaluation_path(OUTPUT_ROOT, seed).read_text(encoding="utf-8")
        )
        conditions = {}
        for condition in CONDITIONS:
            result = json.loads(
                run_path(OUTPUT_ROOT, seed, condition).read_text(encoding="utf-8")
            )
            conditions[condition] = {
                key: value
                for key, value in result.items()
                if key not in {"scores", "h5", "checkpoint"}
            }
        checks = data_integrity_checks(seed, OUTPUT_ROOT, Ref2Spec())
        result_checks = result_integrity_checks(
            [
                json.loads(
                    run_path(OUTPUT_ROOT, seed, condition).read_text(encoding="utf-8")
                )
                for condition in CONDITIONS
            ],
            evaluation,
            Ref2Spec(),
            root=OUTPUT_ROOT,
            seed=seed,
            require_learner=False,
        )
        seeds.append(
            {
                "seed": seed,
                "manifest": manifest,
                "conditions": conditions,
                "data_checks": checks,
                "result_checks": result_checks,
                "learner_guard": evaluation["learner_guard"],
                "copy_diagnostics": evaluation["copy_diagnostics"],
            }
        )
    payload = {
        "spec_digest": smoke["spec_digest"],
        "preregistration_sha256": smoke["preregistration_sha256"],
        "smoke": smoke,
        "reserved_seeds": seeds,
        "totals": {
            "paired_seeds": len(seeds),
            "learner_runs": len(seeds) * len(CONDITIONS),
            "recorded_seconds": completed_campaign_seconds(),
            "effective_cap_seconds": smoke["time_gate"]["effective_cap_seconds"],
        },
    }
    target = REPO / "docs" / "research" / "reafference_002_integrity.json"
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def run_campaign(spec: Ref2Spec, device, review_accepted: bool) -> None:
    authorized, reason = campaign_authorized(spec, review_accepted)
    if not authorized:
        raise SystemExit(f"REF2 reserved campaign forbidden: {reason}")
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    cap = float(smoke["time_gate"]["effective_cap_seconds"])
    used = completed_campaign_seconds()
    if used >= cap:
        raise TimeoutError("REF2 frozen cumulative wall-time cap already reached")
    deadline = time.perf_counter() + cap - used
    evaluations = []
    with keep_awake():
        for seed in RESERVED_SEEDS:
            if time.perf_counter() >= deadline:
                raise TimeoutError("REF2 cap reached before seed preparation")
            prepare_seed(seed, OUTPUT_ROOT, spec)
            if time.perf_counter() >= deadline:
                raise TimeoutError("REF2 cap reached during seed preparation")
            data_integrity_checks(seed, OUTPUT_ROOT, spec)
            results = []
            for condition in CONDITIONS:
                results.append(
                    train_condition(
                        seed,
                        condition,
                        OUTPUT_ROOT,
                        spec,
                        device,
                        deadline,
                    )
                )
                print(f"REF-002 {seed} {condition}: complete", flush=True)
            evaluation = evaluate_seed(seed, OUTPUT_ROOT, spec)
            result_integrity_checks(
                results,
                evaluation,
                spec,
                root=OUTPUT_ROOT,
                seed=seed,
                require_learner=False,
            )
            evaluations.append(evaluation)
            print(f"REF-002 {seed}: evaluation complete", flush=True)
    analysis = analyze_evaluations(evaluations)
    elapsed = completed_campaign_seconds()
    write_results(analysis, evaluations, elapsed)
    print(
        "REF-002 campaign complete; "
        f"eligible={analysis['decision']['eligible_for_contradictory_review']}",
        flush=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run amended REF-002")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--review-accepted", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    spec = Ref2Spec()
    device = resolve_device(args.device)
    print(f"REF-002 device={device} spec={spec.digest()[:12]}", flush=True)
    try:
        if args.smoke:
            run_smoke(spec, device)
        else:
            run_campaign(spec, device, args.review_accepted)
    except Exception as error:
        failure_path = SMOKE_FAILURE if args.smoke else CAMPAIGN_FAILURE
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        failure_path.write_text(
            json.dumps(
                {
                    "passed": False,
                    "seed": SMOKE_SEED if args.smoke else None,
                    "spec_digest": spec.digest(),
                    "preregistration_sha256": protocol_digest(),
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "reserved_seeds_opened": not args.smoke,
                    "timestamp_ns": time.time_ns(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()
