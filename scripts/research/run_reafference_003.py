#!/usr/bin/env python3
"""Review-gated runner for amended REF-003."""

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

from learning import reafference_002 as ref2  # noqa: E402
from learning.reafference_003 import (  # noqa: E402
    ANALYSIS_SEED,
    BANKS,
    CONDITIONS,
    INHERITED_DIGESTS,
    REF3_OBJECT_HALF_HEIGHT_M,
    REF3_OBJECT_HALF_WIDTH_M,
    REF3_SANITY_EXTERNAL_MINIMUM,
    REF3_TRAVEL_M,
    RESERVED_SEEDS,
    SMOKE_SEED,
    Ref3Spec,
    analyze_evaluations,
    configure_external_object,
    data_integrity_checks,
    evaluate_seed,
    field_envelope,
    prepare_seed,
    ref3_bench_config,
    train_condition,
    verify_inherited_digests,
)
from learning.train_visual_jepa import resolve_device  # noqa: E402
from sim3d import bench_model  # noqa: E402
from sim3d.bench_env import BenchHeadEnv  # noqa: E402


OUTPUT_ROOT = REPO / "data" / "processed" / "experiments" / "reafference_003"
PREREG = REPO / "docs" / "research" / "reafference_003_preregistration.md"
REVIEW = REPO / "docs" / "research" / "reafference_003_review.md"
SMOKE_RESULT = OUTPUT_ROOT / "smoke_14991.json"
SMOKE_FAILURE = OUTPUT_ROOT / "smoke_14991_failure.json"
CAMPAIGN_FAILURE = OUTPUT_ROOT / "campaign_failure.json"
ORIGINAL_CAP_SECONDS = 90 * 60


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_digest() -> str:
    return _sha256(PREREG)


def implementation_digests() -> dict[str, str]:
    paths = (
        "learning/reafference_003.py",
        "scripts/research/run_reafference_003.py",
        "tests/test_reafference_003.py",
    )
    return {
        relative: _sha256(REPO / relative)
        for relative in paths
        if (REPO / relative).exists()
    }


def amendments_integrated() -> bool:
    if not PREREG.exists():
        return False
    text = PREREG.read_text(encoding="utf-8")
    fragments = [f"**C{index}:**" for index in range(1, 9)]
    fragments += [
        "SANITY-EXTERNAL",
        "cfd8946cceb4ce88bb9d24171b1f5db7561f5b540cb78cf4d3d5f2fdf7bd2210",
        "REF3 fixe `d=1,05 m`, `t=0,36 m`, `w=0,32 m`",
        "`236` tests existants",
    ]
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
    envelope = field_envelope()
    if not envelope["passed"]:
        raise AssertionError("REF3 field envelope failed before rendering")
    env = BenchHeadEnv(ref3_bench_config(281_000_000 + seed, 60.0, 0))
    try:
        configure_external_object(env, bearing_deg=63.0)
        joint = env.model.joint(bench_model.JOINT_EXTERNAL)
        geom = env.model.geom(bench_model.GEOM_EXTERNAL)
        if not np.allclose(
            geom.size,
            (
                REF3_OBJECT_HALF_WIDTH_M,
                0.018,
                REF3_OBJECT_HALF_HEIGHT_M,
            ),
        ):
            raise AssertionError("REF3 external object dimensions diverge")
        expected_range = np.asarray(
            [-REF3_TRAVEL_M / 2.0, REF3_TRAVEL_M / 2.0]
        )
        if not np.allclose(joint.range, expected_range):
            raise AssertionError("REF3 external rail range diverges")
        env.set_external_object_displacement(-REF3_TRAVEL_M / 2.0)
        for _ in range(20):
            env.step(56.0)
        left = env.render_camera(64, 64)
        env.set_external_object_displacement(REF3_TRAVEL_M / 2.0)
        right = env.render_camera(64, 64)
        endpoint_effect = float(
            np.mean(np.abs(left.astype(np.float64) - right.astype(np.float64)))
            / 255.0
        )
        if endpoint_effect <= 0:
            raise AssertionError("REF3 external object endpoint effect is null")
    finally:
        env.close()
    return {
        "field_envelope": envelope,
        "real_geom_and_joint": True,
        "endpoint_counterfactual_effect": endpoint_effect,
    }


def frozen_time_manifest(
    shared_seconds: float,
    condition_seconds: list[float],
    counterfactual_seconds: float,
) -> dict:
    if len(condition_seconds) != 3:
        raise ValueError("REF3 projection requires three complete conditions")
    mean_condition = float(np.mean(condition_seconds))
    projection = 48.0 * (shared_seconds / 3.0 + mean_condition)
    effective = (
        ORIGINAL_CAP_SECONDS
        if projection <= ORIGINAL_CAP_SECONDS
        else math.ceil((projection * 1.10) / 300.0) * 300
    )
    return {
        "shared_smoke_seconds": shared_seconds,
        "counterfactual_render_seconds": counterfactual_seconds,
        "condition_complete_seconds": condition_seconds,
        "mean_condition_seconds": mean_condition,
        "projected_seconds": projection,
        "original_cap_seconds": ORIGINAL_CAP_SECONDS,
        "effective_cap_seconds": effective,
        "amended": projection > ORIGINAL_CAP_SECONDS,
        "margin_fraction_if_amended": 0.10 if projection > ORIGINAL_CAP_SECONDS else 0.0,
        "formula": "48 * (shared_smoke_seconds / 3 + mean_condition_seconds)",
    }


def run_smoke(spec: Ref3Spec, device) -> None:
    if not review_authorized():
        raise SystemExit("REF3 review authorization or C1-C8 amendment missing")
    inherited = verify_inherited_digests(REPO)
    started = time.perf_counter()
    with keep_awake():
        manipulation = manipulation_checks(SMOKE_SEED)
        initial_fairness = ref2_runner_initial_fairness(SMOKE_SEED, spec, device)
        benchmark = ref2_runner_benchmark(SMOKE_SEED, spec, device)
        shared_started = time.perf_counter()
        manifest = prepare_seed(SMOKE_SEED, OUTPUT_ROOT, spec)
        data_checks = data_integrity_checks(SMOKE_SEED, OUTPUT_ROOT, spec)
        preparation_seconds = time.perf_counter() - shared_started
        results = []
        for condition in CONDITIONS:
            result = train_condition(
                SMOKE_SEED,
                condition,
                OUTPUT_ROOT,
                spec,
                device,
            )
            results.append(result)
            print(f"REF-003 smoke {condition}: complete", flush=True)
        evaluation_started = time.perf_counter()
        evaluation = evaluate_seed(SMOKE_SEED, OUTPUT_ROOT, spec)
        result_checks = ref2_runner_result_checks(
            results,
            evaluation,
            spec,
            root=OUTPUT_ROOT,
            seed=SMOKE_SEED,
        )
        shared_evaluation_seconds = time.perf_counter() - evaluation_started
    shared_seconds = preparation_seconds + shared_evaluation_seconds
    condition_seconds = [
        float(item["timing"]["complete_condition_seconds"])
        for item in results
    ]
    time_gate = frozen_time_manifest(
        shared_seconds,
        condition_seconds,
        float(manifest["counterfactual_instrumented_bank_seconds"]),
    )
    payload = {
        "passed": True,
        "seed": SMOKE_SEED,
        "spec_digest": spec.digest(),
        "preregistration_sha256": protocol_digest(),
        "review_sha256": _sha256(REVIEW),
        "inherited_digests": inherited,
        "implementation_digests": implementation_digests(),
        "elapsed_seconds": time.perf_counter() - started,
        "phase_seconds": {
            "preparation_and_data_guards": preparation_seconds,
            "counterfactual_renders": manifest[
                "counterfactual_instrumented_bank_seconds"
            ],
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
        f"REF-003 smoke {SMOKE_SEED}: PASS; "
        f"projection={time_gate['projected_seconds'] / 60:.2f} min; "
        f"cap={time_gate['effective_cap_seconds'] / 60:.0f} min",
        flush=True,
    )


def _load_ref2_runner():
    from scripts.research import run_reafference_002

    return run_reafference_002


def ref2_runner_initial_fairness(seed: int, spec: Ref3Spec, device) -> dict:
    return _load_ref2_runner().initial_fairness_checks(seed, spec, device)


def ref2_runner_benchmark(seed: int, spec: Ref3Spec, device) -> dict:
    import torch

    models = {}
    optimizers = {}
    batches = {}
    for condition in CONDITIONS:
        model, optimizer = ref2.make_learner(seed, condition, spec, device)
        generator = torch.Generator(device="cpu")
        generator.manual_seed(seed + 2)
        batches[condition] = {
            "frames": torch.rand(
                (32, 3, 64, 64),
                generator=generator,
            ).to(device),
            "target": torch.rand(
                (32, 128, 8, 8),
                generator=generator,
            ).to(device),
            "motor": torch.rand(
                (32, 7),
                generator=generator,
            ).to(device),
        }
        models[condition] = model
        optimizers[condition] = optimizer

    durations = {condition: [] for condition in CONDITIONS}
    for step in range(120):
        offset = step % len(CONDITIONS)
        order = CONDITIONS[offset:] + CONDITIONS[:offset]
        for condition in order:
            model = models[condition]
            optimizer = optimizers[condition]
            batch = batches[condition]
            if device.type == "cuda":
                torch.cuda.synchronize()
            started = time.perf_counter()
            current, prediction = model(batch["frames"], batch["motor"])
            loss = torch.mean((prediction - batch["target"]) ** 2)
            loss = loss + 0.01 * torch.mean(current**2)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize()
            if step >= 20:
                durations[condition].append(time.perf_counter() - started)

    times = {
        condition: float(np.median(values))
        for condition, values in durations.items()
    }
    ratio = max(times.values()) / min(times.values())
    if ratio > 1.25:
        raise AssertionError(
            f"REF3 interleaved per-step wall-time ratio exceeds 1.25: {ratio}"
        )
    return {
        "median_seconds_per_step": times,
        "max_min_ratio": ratio,
        "measurements_per_condition": 100,
        "warmup_steps_per_condition": 20,
        "ordering": "rotating_interleaved",
        "cuda_synchronized_before_and_after": device.type == "cuda",
    }


def ref2_runner_result_checks(*args, **kwargs) -> dict:
    return _load_ref2_runner().result_integrity_checks(*args, **kwargs)


def campaign_authorized(
    spec: Ref3Spec,
    review_accepted: bool,
) -> tuple[bool, str]:
    if not review_accepted:
        return False, "explicit --review-accepted is required"
    if not review_authorized():
        return False, "REF3 review or C1-C8 amendments are missing"
    if not SMOKE_RESULT.exists():
        return False, "REF3 smoke 14991 has not passed"
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    if not smoke.get("passed") or smoke.get("spec_digest") != spec.digest():
        return False, "REF3 smoke is red or belongs to another specification"
    if smoke.get("preregistration_sha256") != protocol_digest():
        return False, "REF3 protocol changed after the smoke"
    if smoke.get("inherited_digests") != verify_inherited_digests(REPO):
        return False, "REF3 inherited implementation changed after the smoke"
    if smoke.get("implementation_digests") != implementation_digests():
        return False, "REF3 implementation changed after the smoke"
    time_gate = smoke.get("time_gate", {})
    if float(time_gate.get("effective_cap_seconds", 0)) < float(
        time_gate.get("projected_seconds", math.inf)
    ):
        return False, "REF3 time projection exceeds its frozen cap"
    if smoke.get("reserved_seeds_opened"):
        return False, "REF3 smoke reports premature reserved-seed access"
    return True, "authorized"


def completed_campaign_seconds() -> float:
    total = 0.0
    for seed in RESERVED_SEEDS:
        manifest_path = OUTPUT_ROOT / "manifests" / f"seed_{seed}.json"
        if manifest_path.exists():
            total += float(
                json.loads(manifest_path.read_text(encoding="utf-8")).get(
                    "elapsed_seconds",
                    0.0,
                )
            )
        for condition in CONDITIONS:
            result_path = ref2.run_path(OUTPUT_ROOT, seed, condition)
            if result_path.exists():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                total += float(
                    result.get("timing", {}).get("complete_condition_seconds", 0.0)
                )
        evaluation_path = ref2.evaluation_path(OUTPUT_ROOT, seed)
        if evaluation_path.exists():
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
            total += float(evaluation.get("elapsed_seconds", 0.0))
    return total


def write_integrity_export() -> dict:
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    seeds = []
    for seed in RESERVED_SEEDS:
        manifest = json.loads(
            (OUTPUT_ROOT / "manifests" / f"seed_{seed}.json").read_text(
                encoding="utf-8"
            )
        )
        evaluation = json.loads(
            ref2.evaluation_path(OUTPUT_ROOT, seed).read_text(encoding="utf-8")
        )
        checks = data_integrity_checks(seed, OUTPUT_ROOT, Ref3Spec())
        seeds.append(
            {
                "seed": seed,
                "manifest": manifest,
                "data_checks": checks,
                "learner_guard": evaluation["learner_guard"],
                "copy_diagnostics": evaluation["copy_diagnostics"],
            }
        )
    payload = {
        "spec_digest": smoke["spec_digest"],
        "preregistration_sha256": smoke["preregistration_sha256"],
        "inherited_digests": smoke["inherited_digests"],
        "implementation_digests": smoke["implementation_digests"],
        "smoke": smoke,
        "reserved_seeds": seeds,
        "totals": {
            "paired_seeds": len(seeds),
            "learner_runs": len(seeds) * len(CONDITIONS),
            "recorded_seconds": completed_campaign_seconds(),
            "effective_cap_seconds": smoke["time_gate"]["effective_cap_seconds"],
        },
    }
    target = REPO / "docs" / "research" / "reafference_003_integrity.json"
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def write_results(
    analysis: dict,
    evaluations: list[dict],
    elapsed_seconds: float,
) -> None:
    analysis_path = REPO / "docs" / "research" / "reafference_003_analysis.json"
    evaluations_path = REPO / "docs" / "research" / "reafference_003_evaluations.json"
    results_path = REPO / "docs" / "research" / "reafference_003_results.md"
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
    sanity = analysis["sanity_external"]["transport_jepa"]
    lines = [
        "# Résultats REF-003 — transport spatial sous visibilité contrôlée",
        "",
        "Simulation uniquement sous D-008. Variante close après cette campagne.",
        "Aucune promotion avant revue contradictoire des résultats.",
        "",
        "## Intégrité",
        "",
        "- 16 triplets / 48 runs complets, graines 14301..14316.",
        "- Smoke 14991 vert et protocole C1–C8 gelé avant 14301.",
        f"- Temps mural cumulé consigné: `{elapsed_seconds / 60:.2f}` minutes.",
        "",
        "## Portes mécaniques",
        "",
        f"- H1: `{analysis['h1_passed']}`.",
        f"- H3: `{analysis['h3_passed']}`.",
        f"- H4: `{analysis['h4_passed']}`.",
        f"- H5: `{analysis['h5_passed']}`.",
        f"- SANITY-EXTERNAL ≥{REF3_SANITY_EXTERNAL_MINIMUM:.2f}: `{sanity['passed']}`.",
        f"- Éligible à la revue contradictoire: `{eligible}`.",
        "",
        "## Analyse complète",
        "",
        "```json",
        json.dumps(analysis, indent=2, sort_keys=True),
        "```",
        "",
    ]
    results_path.write_text("\n".join(lines), encoding="utf-8")


def run_campaign(spec: Ref3Spec, device, review_accepted: bool) -> None:
    authorized, reason = campaign_authorized(spec, review_accepted)
    if not authorized:
        raise SystemExit(f"REF3 reserved campaign forbidden: {reason}")
    smoke = json.loads(SMOKE_RESULT.read_text(encoding="utf-8"))
    cap = float(smoke["time_gate"]["effective_cap_seconds"])
    used = completed_campaign_seconds()
    if used >= cap:
        raise TimeoutError("REF3 frozen cumulative wall-time cap already reached")
    deadline = time.perf_counter() + cap - used
    evaluations = []
    with keep_awake():
        for seed in RESERVED_SEEDS:
            if time.perf_counter() >= deadline:
                raise TimeoutError("REF3 cap reached before seed preparation")
            prepare_seed(seed, OUTPUT_ROOT, spec)
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
                print(f"REF-003 {seed} {condition}: complete", flush=True)
            evaluation = evaluate_seed(seed, OUTPUT_ROOT, spec)
            ref2_runner_result_checks(
                results,
                evaluation,
                spec,
                root=OUTPUT_ROOT,
                seed=seed,
                require_learner=False,
            )
            evaluations.append(evaluation)
            print(f"REF-003 {seed}: evaluation complete", flush=True)
    analysis = analyze_evaluations(evaluations)
    write_results(analysis, evaluations, completed_campaign_seconds())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run amended REF-003")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--review-accepted", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    spec = Ref3Spec()
    device = resolve_device(args.device)
    print(f"REF-003 device={device} spec={spec.digest()[:12]}", flush=True)
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
                    "inherited_digests_expected": INHERITED_DIGESTS,
                    "analysis_seed": ANALYSIS_SEED,
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
