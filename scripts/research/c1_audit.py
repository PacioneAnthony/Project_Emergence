"""Run the diagnostic correction C1 demands (D-060, before any mechanism code).

    python -m scripts.research.c1_audit --subspace tune    # 40 rooms, the twenty variants
    python -m scripts.research.c1_audit --freeze           # after the survivors are fixed
    python -m scripts.research.c1_audit --subspace diag    # 60 rooms, once, no new tuning

Protocol: docs/research/c1_prereg_audit_protocol.md, committed in 998637a before
the first measurement. Review that demands it: docs/research/c1_preregistration_review.md.

Three refusals are enforced rather than promised: the diagnostic phase refuses to
run while the surviving variants and the calibrated table are not frozen, it
refuses unless every frozen source still matches its hash, and it refuses to run
twice. A ten-minute simulation ceiling stops either phase and publishes the stop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from learning import c1_audit
from learning.c1_audit import (
    COUNTS,
    Variant,
    calibrate_table,
    declared_variants,
    non_dominated,
    play_episode,
    probe_seeds,
    summarise,
    table_variants,
    tuning_variants,
)
from learning.c1_task import C1Config

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/processed/experiments/c1_prereg_audit"
MANIFEST = ROOT / "docs/research/c1_prereg_audit_manifest.json"
PUBLISHED = ROOT / "docs/research/c1_prereg_audit_results.json"
PROTOCOL_COMMIT = "998637a"
CEILING_SECONDS = 600.0
FROZEN = (
    "learning/c1_audit.py",
    "scripts/research/c1_audit.py",
    # The seventeen of the hybrid freeze, reused strictly unchanged.
    "learning/c1_probe_hybrid.py",
    "scripts/research/c1_probe_hybrid.py",
    "learning/c1_probe_v3.py",
    "learning/c1_task_v3.py",
    "scripts/research/c1_probe_v3.py",
    "learning/c1_probe_v2.py",
    "learning/c1_task_v2.py",
    "scripts/research/c1_probe_v2.py",
    "learning/c1_probe.py",
    "learning/c1_task.py",
    "learning/paired_stats.py",
    "sim3d/bench_model.py",
    "sim3d/bench_env.py",
    "sim3d/bench2_model.py",
    "sim3d/bench2_env.py",
    "sim3d/bench2_content.py",
    "scripts/research/c1_probe.py",
)

# Fixed by the second commit, after the forty tuning rooms and before the freeze.
#
# The tuning front, on 40 rooms: raster|a100 at 85.0 % for 5.42 moves,
# raster|a150 at 82.5 % for 4.15, and memoire|a150 at 77.5 % for 3.95. Everything
# else is dominated. The two table variants join them out of sample, since the
# same forty rooms calibrated the table.
SURVIVORS: tuple[str, ...] | None = (
    "comparaison|raster|a100",
    "comparaison|raster|a150",
    "comparaison|memoire|a150",
)
CALIBRATED_TABLE: dict[str, float | None] | None = {
    "0": 1.0, "3": 0.25, "6": 1.5, "9": 0.25,
    "12": 1.25, "15": 0.25, "18": 0.5, "20": 1.25,
}


def _sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def _frozen_choices():
    """The survivors of the tuning phase, plus the two table variants by construction.

    The table is defined by the tuning rooms, so its variants cannot survive a
    selection there; they join the diagnostic set out of sample. Adding them can
    only raise the bar, never lower it.
    """

    if SURVIVORS is None or CALIBRATED_TABLE is None:
        raise SystemExit(
            "phase de diagnostic refusee : variantes survivantes et table non figees. "
            "Jouer d'abord --subspace tune, puis inscrire SURVIVORS et CALIBRATED_TABLE "
            "dans scripts/research/c1_audit.py et les commiter, avant --freeze."
        )
    by_name = {v.name: v for v in declared_variants()}
    chosen = tuple(by_name[name] for name in SURVIVORS)
    if any(v.stop == c1_audit.TABLE for v in chosen):
        raise SystemExit("SURVIVORS ne peut pas contenir une variante table : elle n'est pas "
                         "mesurable sur les pieces de reglage")
    table = {int(k): v for k, v in CALIBRATED_TABLE.items()}
    return chosen + table_variants(), table


def freeze() -> None:
    variants, table = _frozen_choices()
    archive = OUT / "source_v1"
    for relative in FROZEN:
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    _write_json(MANIFEST, {
        "namespace": c1_audit.NAMESPACE,
        "protocol": "docs/research/c1_prereg_audit_protocol.md",
        "protocol_commit": PROTOCOL_COMMIT,
        "review": "docs/research/c1_preregistration_review.md",
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "survivors": [v.name for v in variants],
        "table": {str(k): v for k, v in table.items()},
        "files": {relative: _sha(relative) for relative in FROZEN},
        "archive": archive.relative_to(ROOT).as_posix(),
        "seeds": {name: probe_seeds(name, count) for name, count in COUNTS.items()},
    })
    print(f"gel : {len(FROZEN)} sources hachees dans {MANIFEST.relative_to(ROOT).as_posix()}")
    print(f"variantes emportees : {', '.join(v.name for v in variants)}")


def _check_frozen() -> dict:
    if not MANIFEST.exists():
        raise SystemExit("diagnostic refuse : aucun manifeste, lancer --freeze d'abord")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    drift = [r for r, d in manifest["files"].items() if _sha(r) != d]
    if drift:
        raise SystemExit(f"diagnostic refuse : sources modifiees depuis le gel : {drift}")
    return manifest


def run(subspace: str) -> dict:
    count = COUNTS[subspace]
    results_path = OUT / subspace / "results.json"
    manifest = None
    if subspace == "diag":
        variants, table = _frozen_choices()
        manifest = _check_frozen()
        if results_path.exists() or PUBLISHED.exists():
            raise SystemExit("diagnostic refuse : deja joue -- une mesure rejouee est une mesure choisie")
    else:
        # The table is defined by these very rooms, so its variants are not
        # measurable here; they join the diagnostic set out of sample.
        variants, table = tuning_variants(), None

    config = C1Config()
    seeds = probe_seeds(subspace, count)
    rows, rejected, stopped = [], [], None
    start = time.monotonic()

    for i, seed in enumerate(seeds, start=1):
        if time.monotonic() - start > CEILING_SECONDS:
            stopped = f"plafond de {CEILING_SECONDS:.0f} s atteint apres {i - 1} pieces"
            print(f"  ARRET : {stopped}", flush=True)
            break
        try:
            row = play_episode(config, seed, variants, table)
        except RuntimeError as exc:
            rejected.append({"seed": seed, "reason": str(exc)})
            print(f"  [{i:3d}/{count}] piece {seed} ecartee par un garde : {exc}", flush=True)
            continue
        rows.append(row)
        if i % 10 == 0 or i == count:
            print(f"  [{i:3d}/{count}] {time.monotonic() - start:5.0f} s", flush=True)

    summary = summarise(rows, variants) if rows else {}
    payload = {
        "subspace": subspace,
        "protocol_commit": PROTOCOL_COMMIT,
        "seeds": seeds,
        "variants": [v.name for v in variants],
        "table": {str(k): v for k, v in table.items()} if table else None,
        "rows": rows,
        "rejected": rejected,
        "stopped": stopped,
        "summary": summary,
        "seconds": round(time.monotonic() - start, 1),
    }
    if subspace == "tune" and rows:
        payload["calibrated_table"] = {str(k): v for k, v in calibrate_table(rows).items()}
        payload["non_dominated"] = non_dominated(summary)
    if subspace == "diag" and rows:
        _write_json(PUBLISHED, {
            "summary": summary,
            "protocol_commit": PROTOCOL_COMMIT,
            "survivors": [v.name for v in variants],
            "table": payload["table"],
            "manifest_sha256": _sha(MANIFEST.relative_to(ROOT).as_posix()),
            "frozen_at": manifest["frozen_at"],
            "rooms": len(rows),
            "seconds": payload["seconds"],
            "full_results": results_path.relative_to(ROOT).as_posix(),
        })
    _write_json(results_path, payload)
    report(payload)
    return payload


def report(payload: dict) -> None:
    summary = payload["summary"]
    if not summary:
        print("aucune piece jouee")
        return
    print()
    print(f"{'variante':34} {'succes':>8} {'cout':>7} {'repli':>7} {'arret':>7} "
          f"{'ideal':>7} {'rang':>6}")
    print("-" * 84)
    for name in sorted(summary, key=lambda n: (summary[n]["cost_mean"], -summary[n]["success_rate"])):
        b = summary[name]
        rank = f"{b['rank_mean']:.2f}" if b["rank_mean"] is not None else "  -  "
        print(f"{name:34} {100 * b['success_rate']:7.1f}% {b['cost_mean']:7.2f} "
              f"{100 * b['fallback_rate']:6.0f}% {100 * b['stopped_rate']:6.0f}% "
              f"{b['ideal_cost_mean']:7.2f} {rank:>6}")
    if payload.get("calibrated_table"):
        print(f"\ntable calibree par classe apparente : {payload['calibrated_table']}")
    if payload.get("non_dominated"):
        print(f"\nvariantes non dominees ({len(payload['non_dominated'])}) :")
        for name in payload["non_dominated"]:
            print(f"   {name}")
    if payload.get("stopped"):
        print(f"\nARRET : {payload['stopped']}")
    print(f"\n{len(payload['rows'])} pieces, {payload['seconds']:.0f} s, "
          f"{len(payload['rejected'])} ecartees")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--subspace", choices=tuple(COUNTS))
    group.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze()
        return 0
    run(args.subspace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
