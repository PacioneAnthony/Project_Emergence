"""Run the complementary probe demanded by correction B1 (D-060, step 3).

    python -m scripts.research.c1_probe_hybrid --subspace dev    # every variant, as often as needed
    python -m scripts.research.c1_probe_hybrid --freeze          # after the family is fixed
    python -m scripts.research.c1_probe_hybrid --subspace bank   # once, after the freeze

Thresholds and design: docs/research/c1_journal.md, entry 10, committed in
3fbac61 before any of this code existed.

Three refusals are enforced here rather than promised. The bank refuses to run
while `BANK_RULES` is None, so no bank can be played against an unfrozen family.
It refuses unless every frozen source still matches its hash. And it refuses to
run twice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from learning import c1_probe_hybrid
from learning.c1_probe_hybrid import (
    ALL_RULES,
    HISTORIC,
    ORACLE,
    non_dominated,
    play_episode,
    probe_seeds,
    rules_named,
    verdict,
)
from learning.c1_task import C1Config

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/processed/experiments/c1_probe_hybrid"
MANIFEST = ROOT / "docs/research/c1_probe_hybrid_manifest.json"
PUBLISHED = ROOT / "docs/research/c1_probe_hybrid_results.json"
COUNTS = {"dev": 10, "bank": 100}
THRESHOLD_COMMIT = "3fbac61"
FROZEN = (
    # The complementary probe's own sources.
    "learning/c1_probe_hybrid.py",
    "scripts/research/c1_probe_hybrid.py",
    # Version 3's, reused strictly unchanged -- correction B1 requires it.
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
NAMES = {"oracle_perceptif": "oracle perceptif", "dernier_angle": "dernier angle vu",
         "balayage": "balayage exhaustif"}


def _sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def _bank_rules():
    if c1_probe_hybrid.BANK_RULES is None:
        raise SystemExit(
            "banque refusee : les variantes non dominees ne sont pas figees. "
            "Jouer d'abord --subspace dev, puis inscrire BANK_RULES dans "
            "learning/c1_probe_hybrid.py et le commiter, avant --freeze."
        )
    return rules_named(c1_probe_hybrid.BANK_RULES)


def freeze() -> None:
    """Hash every source the bank depends on and copy it beside the results (D-061)."""

    rules = _bank_rules()
    archive = OUT / "source_v1"
    for relative in FROZEN:
        target = archive / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)  # byte for byte
    _write_json(MANIFEST, {
        "namespace": "c1-margin-hybrid/v1",
        "threshold_commit": THRESHOLD_COMMIT,
        "journal": "docs/research/c1_journal.md",
        "review": "docs/research/c1_margin_review.md",
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "bank_rules": [rule.name for rule in rules],
        "files": {relative: _sha(relative) for relative in FROZEN},
        "archive": archive.relative_to(ROOT).as_posix(),
        "seeds": {"dev": probe_seeds("dev", COUNTS["dev"]),
                  "bank": probe_seeds("bank", COUNTS["bank"])},
    })
    print(f"gel : {len(FROZEN)} sources hachees dans {MANIFEST.relative_to(ROOT).as_posix()}, "
          f"copiees sous {archive.relative_to(ROOT).as_posix()}")
    print(f"variantes emportees : {', '.join(rule.name for rule in rules)}")


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
        rules = _bank_rules()
        manifest = _check_frozen()
        if results_path.exists() or PUBLISHED.exists():
            raise SystemExit("banque refusee : deja jouee -- une banque jouee deux fois est une banque choisie")
    else:
        rules = ALL_RULES

    witnesses = tuple(HISTORIC) + tuple(rule.name for rule in rules)
    config = C1Config()
    seeds = probe_seeds(subspace, count)
    rows, rejected = [], []
    start = time.monotonic()
    for i, seed in enumerate(seeds, start=1):
        try:
            row = play_episode(config, seed, rules=rules)
        except RuntimeError as exc:
            rejected.append({"seed": seed, "reason": str(exc)})
            print(f"  [{i:3d}/{count}] piece {seed} ecartee par un garde : {exc}", flush=True)
            continue
        rows.append(row)
        oracle = "reussi" if row["outcomes"][ORACLE]["success"] else "rate "
        adaptive = " ".join(
            f"{'O' if row['outcomes'][r.name]['success'] else '.'}{row['outcomes'][r.name]['cost']:2d}"
            for r in rules
        )
        print(f"  [{i:3d}/{count}] piece {seed:>10}{' brassee' if row['moved'] else '        '}"
              f"  oracle {oracle}  adaptatifs {adaptive}", flush=True)

    summary = verdict(rows, len(rejected), witnesses)
    payload = {
        "subspace": subspace,
        "seeds": seeds,
        "rules": [rule.name for rule in rules],
        "rows": rows,
        "rejected": rejected,
        "summary": summary,
        "seconds": round(time.monotonic() - start, 1),
    }
    if subspace == "dev":
        payload["non_dominated"] = non_dominated(summary["witnesses"])
    _write_json(results_path, payload)
    if subspace == "bank":
        _write_json(PUBLISHED, {
            "summary": summary,
            "threshold_commit": THRESHOLD_COMMIT,
            "bank_rules": [rule.name for rule in rules],
            "manifest_sha256": _sha(MANIFEST.relative_to(ROOT).as_posix()),
            "frozen_at": manifest["frozen_at"],
            "rooms": count,
            "seconds": payload["seconds"],
            "full_results": results_path.relative_to(ROOT).as_posix(),
        })
    report(summary, payload, witnesses)
    return payload


def _pct(x: float) -> str:
    return f"{100 * x:5.1f} %".replace(".", ",")


def report(summary: dict, payload: dict, witnesses) -> None:
    f = summary["feasibility"]
    print()
    if f.get("episodes"):
        low, high = f["wilson_95"]
        print(f"FAISABILITE   oracle perceptif {f['successes']}/{f['episodes']} = {_pct(f['success_rate'])}"
              f"   Wilson 95 % [{_pct(low)} ; {_pct(high)}]   pieces ecartees {f['rejected_rooms']}"
              f"   -> {'passe' if f['passes'] else 'ECHOUE'}")
        print("MARGE, contre l'oracle perceptif   (regle de cout durcie : borne basse >= 3)")
        for name in witnesses:
            w = summary["witnesses"][name]
            gl, _ = w["success_gap_bca_95"]
            cl, _ = w["cost_gap_bca_95"]
            axes = [label for label, ok in (("succes", w["success_margin"]), ("cout", w["cost_margin"])) if ok]
            print(f"   {NAMES.get(name, name):22} succes {_pct(w['success_rate'])}"
                  f"  ecart {100 * w['success_gap']:+6.1f} pts (BCa {100 * gl:+.1f})"
                  f"  cout {w['cost_mean']:5.2f} ({w['cost_gap']:+.2f}, BCa {cl:+.2f})"
                  f"  -> {'marge en ' + ' et '.join(axes) if axes else 'PROCHE DE L ORACLE'}")
        c = summary.get("conditional", {})
        for key in ("stable", "brassee"):
            if key in c:
                block = c[key]
                print(f"   [{key:8}] {block['episodes']:3d} pieces   "
                      + "   ".join(f"{n} {_pct(block[n])}" for n in (ORACLE, *witnesses) if n in block))
        print(f"controle de notation : {_pct(summary['cell_oracle_control'])}"
              f"   episodes brasses : {_pct(summary['moved_fraction'])}")
    if "non_dominated" in payload:
        print(f"VARIANTES NON DOMINEES (developpement) : {', '.join(payload['non_dominated'])}")
    print(f"VERDICT : {summary['verdict']} -- {summary['reason']}   ({payload['seconds']:.0f} s)")


def main() -> int:
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
        raise SystemExit("la banque compte 100 pieces, fixees dans le journal")
    if count > COUNTS[args.subspace]:
        raise SystemExit(f"seulement {COUNTS[args.subspace]} graines reservees pour {args.subspace}")
    run(args.subspace, count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
