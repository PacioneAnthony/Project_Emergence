"""Run the C1 margin probe, version 3 (D-060, step 3).

    python -m scripts.research.c1_probe_v3 --subspace dev      # debugging, as often as needed
    python -m scripts.research.c1_probe_v3 --freeze            # before the bank: hash and archive the sources
    python -m scripts.research.c1_probe_v3 --subspace bank     # once, after the freeze

Definitions and thresholds: docs/research/c1_journal.md, entry 7, committed in
5be9c8b before any version 3 code existed. The bank refuses to run unless every
frozen source still matches its hash, and refuses to run a second time.

The freeze covers all fifteen sources of the three versions. The nine of version
1 and the three of version 2 are not used any differently -- they are hashed to
certify that version 3 ran against a substrate whose bytes never moved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from learning.c1_probe_v3 import POLICIES, WITNESSES, play_episode, probe_seeds, verdict
from learning.c1_task import C1Config

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/processed/experiments/c1_probe_v3"
MANIFEST = ROOT / "docs/research/c1_probe_v3_manifest.json"
PUBLISHED = ROOT / "docs/research/c1_probe_v3_results.json"
COUNTS = {"dev": 10, "bank": 300}
THRESHOLD_COMMIT = "5be9c8b"
FROZEN = (
    # Version 3's own sources.
    "learning/c1_probe_v3.py",
    "learning/c1_task_v3.py",
    "scripts/research/c1_probe_v3.py",
    # Version 2's, reused unchanged.
    "learning/c1_probe_v2.py",
    "learning/c1_task_v2.py",
    "scripts/research/c1_probe_v2.py",
    # Version 1's, reused unchanged.
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
NAMES = {"oracle_perceptif": "oracle perceptif", "dernier_angle": "dernier angle vu", "balayage": "balayage exhaustif"}


def _sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def freeze() -> None:
    """Hash every source the bank depends on and copy it beside the results (D-061)."""

    archive = OUT / "source_v1"
    for relative in FROZEN:
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)  # byte for byte
    _write_json(MANIFEST, {
        "namespace": "c1-margin-probe/v3",
        "threshold_commit": THRESHOLD_COMMIT,
        "journal": "docs/research/c1_journal.md",
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "files": {relative: _sha(relative) for relative in FROZEN},
        "archive": archive.relative_to(ROOT).as_posix(),
        "seeds": {"dev": probe_seeds("dev", COUNTS["dev"]), "bank": probe_seeds("bank", COUNTS["bank"])},
    })
    print(f"gel : {len(FROZEN)} sources hachees dans {MANIFEST.relative_to(ROOT).as_posix()}, "
          f"copiees sous {archive.relative_to(ROOT).as_posix()}")


def _check_frozen() -> dict:
    if not MANIFEST.exists():
        raise SystemExit("banque refusee : aucun manifeste, lancer --freeze d'abord")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    drift = [relative for relative, digest in manifest["files"].items() if _sha(relative) != digest]
    if drift:
        raise SystemExit(f"banque refusee : sources modifiees depuis le gel : {drift}")
    return manifest


def run(subspace: str, count: int) -> dict:
    results_path = OUT / subspace / "results.json"
    manifest = None
    if subspace == "bank":
        manifest = _check_frozen()
        if results_path.exists() or PUBLISHED.exists():
            raise SystemExit("banque refusee : deja jouee -- une banque jouee deux fois est une banque choisie")

    config = C1Config()
    seeds = probe_seeds(subspace, count)
    rows, rejected = [], []
    start = time.monotonic()
    for i, seed in enumerate(seeds, start=1):
        try:
            row = play_episode(config, seed)
        except RuntimeError as exc:
            rejected.append({"seed": seed, "reason": str(exc)})
            print(f"  [{i:3d}/{count}] piece {seed} ecartee par un garde : {exc}", flush=True)
            continue
        rows.append(row)
        marks = "   ".join(
            f"{name} {'reussi' if row['outcomes'][name]['success'] else 'rate '} ({row['outcomes'][name]['cost']:2d})"
            for name in POLICIES
        )
        print(f"  [{i:3d}/{count}] piece {seed:>10}{' brassee' if row['moved'] else '        '}  {marks}", flush=True)

    summary = verdict(rows, len(rejected))
    payload = {
        "subspace": subspace,
        "seeds": seeds,
        "rows": rows,
        "rejected": rejected,
        "summary": summary,
        "seconds": round(time.monotonic() - start, 1),
        "task": {"object_count": config.object_count, "shuffle_probability": config.shuffle_probability,
                 "delay_moves": config.delay_moves, "image_size": config.image_size,
                 "min_visible_fraction": config.min_visible_fraction},
    }
    _write_json(results_path, payload)
    if subspace == "bank":
        _write_json(PUBLISHED, {
            "summary": summary,
            "threshold_commit": THRESHOLD_COMMIT,
            "manifest_sha256": _sha(MANIFEST.relative_to(ROOT).as_posix()),
            "frozen_at": manifest["frozen_at"],
            "rooms": count,
            "seconds": payload["seconds"],
            "full_results": results_path.relative_to(ROOT).as_posix(),
        })
    report(summary, payload["seconds"])
    return payload


def _pct(x: float) -> str:
    return f"{100 * x:5.1f} %".replace(".", ",")


def report(summary: dict, seconds: float) -> None:
    f = summary["feasibility"]
    print()
    if f.get("episodes"):
        low, high = f["wilson_95"]
        print(f"FAISABILITE   oracle perceptif {f['successes']}/{f['episodes']} = {_pct(f['success_rate'])}"
              f"   Wilson 95 % [{_pct(low)} ; {_pct(high)}]   pieces ecartees {f['rejected_rooms']}"
              f"   -> {'passe' if f['passes'] else 'ECHOUE'}")
        print("MARGE, contre l'oracle perceptif")
        for name in WITNESSES:
            w = summary["witnesses"][name]
            gl, gh = w["success_gap_bca_95"]
            axes = [label for label, ok in (("succes", w["success_margin"]), ("cout", w["cost_margin"])) if ok]
            print(f"   {NAMES[name]:18}  succes {_pct(w['success_rate'])}   ecart {100 * w['success_gap']:+6.1f} pts"
                  f" [BCa {100 * gl:+.1f} ; {100 * gh:+.1f}]   cout {w['cost_mean']:5.1f} ({w['cost_gap']:+.1f})"
                  f"   -> {'marge en ' + ' et '.join(axes) if axes else 'PROCHE DE L ORACLE'}")
        print(f"controle de notation (oracle de cellule) : {_pct(summary['cell_oracle_control'])}"
              f"   episodes brasses : {_pct(summary['moved_fraction'])}")
    print(f"VERDICT : {summary['verdict']} -- {summary['reason']}   ({seconds:.0f} s)")


def main() -> int:
    # UTF-8 so the verdict's accents survive the Windows console.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--subspace", choices=tuple(COUNTS))
    group.add_argument("--freeze", action="store_true")
    parser.add_argument("--count", type=int, default=None)
    args = parser.parse_args()

    if args.freeze:
        freeze()
        return 0
    count = args.count or COUNTS[args.subspace]
    if args.subspace == "bank" and count != COUNTS["bank"]:
        raise SystemExit("la banque compte 300 pieces, fixees dans le journal")
    if count > COUNTS[args.subspace]:
        raise SystemExit(f"seulement {COUNTS[args.subspace]} graines reservees pour {args.subspace}")
    run(args.subspace, count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
