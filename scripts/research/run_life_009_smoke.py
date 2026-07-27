"""Run the reviewed LIFE-009 smoke without opening reserved banks."""

from __future__ import annotations

import json
from pathlib import Path

from learning.life_009_campaign import run_life009_smoke


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "processed" / "experiments" / "life_009_smoke"


def main() -> None:
    report = run_life009_smoke(OUTPUT)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

