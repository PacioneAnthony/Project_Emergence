"""Run BODY-SCHEMA-001 smoke without opening test seeds."""

from __future__ import annotations

import json
from pathlib import Path

from learning.body_schema_001_campaign import run_body_schema_001_smoke


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "processed" / "experiments" / "body_schema_001_smoke"


def main() -> None:
    result = run_body_schema_001_smoke(OUTPUT)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if not result["smoke_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
