"""Durable 90-minute budget for functional learning and experiment selection."""
import argparse,json,sys,uuid
from pathlib import Path
from learning.body_schema_002_budget import Budget

OUTPUT=Path(__file__).resolve().parents[1]/'data/processed/experiments/resilience_002'

def main():
    p=argparse.ArgumentParser(); p.add_argument('--kind',choices=['tests','development','analysis'],required=True); p.add_argument('command',nargs=argparse.REMAINDER)
    a=p.parse_args(); command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:p.error('Python command required')
    budget=Budget(OUTPUT/'budget.sqlite',total=5400,per_invocation=900); log=OUTPUT/(a.kind+'-'+uuid.uuid4().hex+'.log')
    result=budget.run([sys.executable,*command],a.kind,log)
    print(log.read_text(encoding='utf-8',errors='replace')[-10000:]);print(json.dumps(result,indent=2))
    return result['exit_code'] if result['exit_code'] is not None and not result['timeout'] else 124

if __name__=='__main__':raise SystemExit(main())
