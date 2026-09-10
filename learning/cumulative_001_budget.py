"""Common 90-minute ledger for cumulative development, variants and tests."""
import argparse,json,sys,uuid
from pathlib import Path
from learning.body_schema_002_budget import Budget
from learning.cumulative_001_data import OUTPUT


def main():
    p=argparse.ArgumentParser(); p.add_argument('--kind',choices=['tests','development','analysis'],required=True); p.add_argument('command',nargs=argparse.REMAINDER)
    args=p.parse_args(); command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command: p.error('Python command required')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    budget=Budget(OUTPUT/'budget.sqlite',total=5400,per_invocation=900)
    log=OUTPUT/(args.kind+'-'+uuid.uuid4().hex+'.log')
    result=budget.run([sys.executable,*command],args.kind,log)
    print(log.read_text(encoding='utf-8',errors='replace')[-16000:]); print(json.dumps(result,indent=2))
    if result['exit_code']==0 and not result['timeout']:
        if command==['-m','pytest','tests/test_cumulative_001.py','-q']:
            from learning.cumulative_001 import source
            (OUTPUT/'contracts.json').write_text(json.dumps({'source':source(),**result},indent=2),encoding='utf-8')
    return result['exit_code'] if result['exit_code'] is not None and not result['timeout'] else 124


if __name__=='__main__': raise SystemExit(main())
