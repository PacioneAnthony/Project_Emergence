"""Run reviewed LIFE-011 smoke seeds without opening reserved banks."""

from __future__ import annotations

import json
from pathlib import Path

from learning.life_011_campaign import run_life011_smoke


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "processed" / "experiments" / "life_011_smoke"


def main() -> None:
    report = run_life011_smoke(OUTPUT)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if not report.get("smoke_passed", report.get("margin_plate_passed", False)):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
