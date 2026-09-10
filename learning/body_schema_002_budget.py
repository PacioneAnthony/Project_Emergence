"""External wall-time supervision with pessimistic durable reservations."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid


class Budget:
    def __init__(self,path,*,total=3600.,per_invocation=900.):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.total=float(total); self.per=float(per_invocation)
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS limits(singleton INTEGER PRIMARY KEY,total REAL,per REAL)')
            db.execute('INSERT OR IGNORE INTO limits VALUES(1,?,?)',(self.total,self.per))
            if db.execute('SELECT total,per FROM limits').fetchone()!=(self.total,self.per):
                raise ValueError('budget limits cannot change on restart')
            db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,started REAL,allowance REAL,charged REAL,status TEXT,command TEXT,category TEXT,exit_code INTEGER)')

    def used(self):
        with sqlite3.connect(self.path) as db:
            return float(db.execute('SELECT coalesce(sum(charged),0) FROM attempts').fetchone()[0])

    def reserve(self,command,category):
        identity=uuid.uuid4().hex
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA synchronous=FULL'); db.execute('BEGIN IMMEDIATE')
            remaining=self.total-db.execute('SELECT coalesce(sum(charged),0) FROM attempts').fetchone()[0]
            if remaining<=0: raise RuntimeError('iteration budget exhausted')
            allowance=min(self.per,remaining)
            # Unfinished attempts retain their FULL allowance, even after parent death.
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,NULL)',
                       (identity,time.time(),allowance,allowance,'reserved',json.dumps(command),category))
        return identity,allowance

    def run(self,command,category,log_path):
        identity,allowance=self.reserve(command,category)
        start=time.monotonic(); timed_out=False; returncode=None
        log_path=Path(log_path); log_path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with log_path.open('wb') as output:
                process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
                    start_new_session=os.name!='nt')
                try:
                    # Leave room for process-tree termination under the reserved limit.
                    process.wait(timeout=max(.001,allowance-.5))
                except subprocess.TimeoutExpired:
                    timed_out=True
                    if os.name=='nt':
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW,timeout=5)
                    else:
                        import signal
                        os.killpg(process.pid,signal.SIGKILL)
                    process.wait(timeout=5)
                except BaseException:
                    if os.name=='nt':
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW,timeout=5)
                    else:
                        import signal
                        os.killpg(process.pid,signal.SIGKILL)
                    process.wait(timeout=5)
                    raise
                returncode=process.returncode
        finally:
            elapsed=time.monotonic()-start
            # Preserve real overrun if OS termination itself was delayed.
            with sqlite3.connect(self.path) as db:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('UPDATE attempts SET charged=?,status=?,exit_code=? WHERE id=?',
                           (elapsed,'timeout' if timed_out else ('complete' if returncode is not None else 'failed'),returncode,identity))
        return {'attempt':identity,'seconds':elapsed,'allowance':allowance,'timeout':timed_out,
                'exit_code':returncode,'cumulative_seconds':self.used(),'log':str(log_path)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--kind',choices=['tests','development','verification'],required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command: parser.error('Python arguments required after --')
    root=Path(__file__).resolve().parents[1]
    os.chdir(root)
    manifest=json.loads((root/'docs/research/body_schema_002_dev_manifest.json').read_text(encoding='utf-8'))
    folder=root/'data/processed/experiments/body_schema_002_r2_dev_v1'
    budget=Budget(folder/'budget.sqlite',total=manifest['budget']['iteration_seconds'],per_invocation=manifest['budget']['invocation_seconds'])
    log=folder/f'{args.kind}-{uuid.uuid4().hex}.log'
    from learning.body_schema_002_experiment import source_receipt
    before=source_receipt()
    result=budget.run([sys.executable,*command],args.kind,log)
    if args.kind=='tests' and result['exit_code']==0 and not result['timeout'] and before==source_receipt():
        name=None
        if command==['-m','pytest','tests/test_body_schema_002.py','-q']:
            name='contracts_receipt.json'
        elif command==['-m','pytest','-q']:
            name='full_suite_receipt.json'
        if name:
            (folder/name).write_text(json.dumps({'source':before,**result},sort_keys=True,indent=2),encoding='utf-8')
    print(log.read_text(encoding='utf-8',errors='replace')[-12000:])
    print(json.dumps(result,indent=2))
    return result['exit_code'] if not result['timeout'] and result['exit_code'] is not None else 124


if __name__=='__main__': raise SystemExit(main())
