"""Durable budget for the resilience cycle, separate from frozen cumulative banks."""
import argparse
import json
import sys
import uuid
from pathlib import Path
from learning.body_schema_002_budget import Budget

OUTPUT = Path(__file__).resolve().parents[1] / 'data/processed/experiments/resilience_001'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--kind', choices=['tests', 'development', 'analysis'], required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    args = p.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command: p.error('Python command required')
    budget = Budget(OUTPUT / 'budget.sqlite', total=5400, per_invocation=900)
    log = OUTPUT / (args.kind + '-' + uuid.uuid4().hex + '.log')
    result = budget.run([sys.executable, *command], args.kind, log)
    print(log.read_text(encoding='utf-8', errors='replace')[-12000:])
    print(json.dumps(result, indent=2))
    return result['exit_code'] if not result['timeout'] and result['exit_code'] is not None else 124


if __name__ == '__main__': raise SystemExit(main())
