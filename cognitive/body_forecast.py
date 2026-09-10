"""Exactly-once body learning attached to the existing cognitive memory."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from learning.body_schema_002 import Learner, Ridge, canonical, digest


class BodyForecastStore:
    """Small additive tables, separately versioned, inside the kernel's SQLite DB.

    Does not wrap existing transaction-opening methods. The composed operation uses
    exactly one memory.transaction(). Physical mid-trial replay is not claimed.
    """
    def __init__(self,kernel,artifacts,run_id,contract_digest):
        self.memory=kernel.memory; self.artifacts=Path(artifacts).resolve()
        self.artifacts.mkdir(parents=True,exist_ok=True)
        self.run_id=run_id; self.contract_digest=contract_digest
        with self.memory.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS body_r2_meta(version INTEGER PRIMARY KEY)')
            if not db.execute('SELECT * FROM body_r2_meta').fetchall(): db.execute('INSERT INTO body_r2_meta VALUES(1)')
            if [r[0] for r in db.execute('SELECT version FROM body_r2_meta')]!=[1]: raise ValueError('unsupported body schema')
            db.execute('CREATE TABLE IF NOT EXISTS body_r2_state(run_id TEXT PRIMARY KEY,contract TEXT,artifact TEXT,digest TEXT,cursor INTEGER,active TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS body_r2_applications(run_id TEXT,logical_id TEXT,content_digest TEXT,artifact TEXT,digest TEXT,cursor INTEGER,PRIMARY KEY(run_id,logical_id))')
            db.execute('CREATE TABLE IF NOT EXISTS body_r2_proofs(run_id TEXT,package TEXT,capability TEXT,level TEXT,status TEXT,evidence TEXT,PRIMARY KEY(run_id,package,capability))')
            db.execute('CREATE TABLE IF NOT EXISTS body_r2_cycles(run_id TEXT PRIMARY KEY,cursor INTEGER)')

    def publish(self,payload):
        content=canonical(payload); sha=hashlib.sha256(content).hexdigest()
        path=self.artifacts/(sha+'.json')
        if path.exists():
            if path.read_bytes()!=content: raise ValueError('artifact collision or corruption')
        else:
            temporary=self.artifacts/(uuid.uuid4().hex+'.tmp')
            with temporary.open('xb') as f: f.write(content); f.flush(); os.fsync(f.fileno())
            # Unique content-addressed publication; never interpret orphan files as state.
            os.replace(temporary,path)
        return str(path),sha

    def read(self,path,expected):
        path=Path(path).resolve()
        if path.parent!=self.artifacts: raise ValueError('artifact outside store')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected: raise ValueError('artifact digest mismatch')
        return json.loads(raw)

    def initialize(self,learner):
        existing=self.memory.connection.execute('SELECT * FROM body_r2_state WHERE run_id=?',(self.run_id,)).fetchone()
        if existing:
            if existing['contract']!=self.contract_digest: raise ValueError('changed run contract')
            return self.load()
        path,sha=self.publish(learner.payload())
        with self.memory.transaction() as db:
            db.execute('INSERT INTO body_r2_state VALUES(?,?,?,?,0,NULL)',(self.run_id,self.contract_digest,path,sha))
            db.execute('INSERT INTO body_r2_cycles VALUES(?,0)',(self.run_id,))
        return learner

    def load(self):
        row=self.memory.connection.execute('SELECT * FROM body_r2_state WHERE run_id=?',(self.run_id,)).fetchone()
        if row is None or row['contract']!=self.contract_digest: raise ValueError('missing or changed run contract')
        learner=Learner.restore(self.read(row['artifact'],row['digest']))
        if len(learner.trials)!=row['cursor']: raise ValueError('inconsistent cursor')
        return learner

    def reconcile(self):
        with self.memory.transaction() as db:
            row=db.execute('SELECT cursor FROM body_r2_state WHERE run_id=?',(self.run_id,)).fetchone()
            db.execute('UPDATE body_r2_cycles SET cursor=? WHERE run_id=?',(row['cursor'],self.run_id))
        return row['cursor']

    def apply(self,logical_id,rows,*,interrupt=None):
        """logical_id = variant/organism/planned-position, not attempt UUID."""
        content=digest([r.payload() for r in rows])
        seen=self.memory.connection.execute('SELECT * FROM body_r2_applications WHERE run_id=? AND logical_id=?',(self.run_id,logical_id)).fetchone()
        if seen:
            if seen['content_digest']!=content: raise ValueError('logical trial replay has changed content')
            self.reconcile()
            return self.load(),False
        before=self.load(); previous_count=len(before.trials)
        before.update(rows)
        path,sha=self.publish(before.payload())
        if interrupt: interrupt('after_publication')
        with self.memory.transaction() as db:
            current=db.execute('SELECT * FROM body_r2_state WHERE run_id=?',(self.run_id,)).fetchone()
            if current['cursor']!=previous_count: raise RuntimeError('concurrent writer; retry from persistent state')
            db.execute('INSERT INTO body_r2_applications VALUES(?,?,?,?,?,?)',(self.run_id,logical_id,content,path,sha,previous_count+1))
            db.execute('UPDATE body_r2_state SET artifact=?,digest=?,cursor=? WHERE run_id=?',(path,sha,previous_count+1,self.run_id))
            if interrupt: interrupt('before_trial_commit')
        if interrupt: interrupt('after_trial_commit')
        self.reconcile()
        if interrupt: interrupt('after_cycle_progress')
        return before,True

    def activate(self,evidence,*,interrupt=None):
        """Activation is explicit and separate from internal candidate selection."""
        learner=self.load(); model=learner.active
        if evidence.get('model_version')!=model.version or evidence.get('level')!='development':
            raise ValueError('proof does not identify the evaluated package and level')
        if not evidence.get('usage_passed') or not evidence.get('reception_passed'):
            raise ValueError('activation requires usage and reception evidence')
        payload={'model':model.payload(),'evidence':evidence,'contract':self.contract_digest}
        path,sha=self.publish(payload); module='body_forecast/'+self.run_id
        # Package identity includes proof and dependencies, so no proof can be silently replaced.
        package=digest(payload)
        if interrupt: interrupt('after_activation_publication')
        with self.memory.transaction() as db:
            state=db.execute('SELECT * FROM body_r2_state WHERE run_id=?',(self.run_id,)).fetchone()
            if state['active']==package: return package
            db.execute("UPDATE model_versions SET state='retired' WHERE module=? AND state='validated'",(module,))
            db.execute("INSERT INTO model_versions VALUES(?,?,'validated',?,?,?,?) ON CONFLICT(module,version) DO UPDATE SET state='validated'",
                       (module,package,path,sha,time.time_ns(),json.dumps({'level':'development','model_version':model.version})))
            statuses={'body_forecast_one_step':'qualified','body_forecast_persistence':'qualified',
                      'body_forecast_rollout':'not_qualified','body_forecast_calibration':'not_qualified','body_forecast_detection':'not_qualified'}
            for capability,status in statuses.items():
                db.execute('INSERT OR IGNORE INTO body_r2_proofs VALUES(?,?,?,?,?,?)',
                           (self.run_id,package,capability,'development',status,json.dumps(evidence,sort_keys=True)))
            db.execute('UPDATE body_r2_state SET active=? WHERE run_id=?',(package,self.run_id))
            if interrupt: interrupt('before_activation_commit')
        if interrupt: interrupt('after_activation_commit')
        return package

    def active_prediction(self,observation):
        record=self.memory.validated_model('body_forecast/'+self.run_id)
        if record is None: raise ValueError('no active qualified package')
        payload=self.read(record['artifact_ref'],record['artifact_digest'])
        if payload['contract']!=self.contract_digest: raise ValueError('active contract mismatch')
        model=Ridge.restore(payload['model'])
        if model.version!=payload['evidence']['model_version']: raise ValueError('proof/model mismatch')
        return {'prediction':model.predict(observation),'package':record['version'],'model':model.version,'level':'development'}

    def capabilities(self):
        row=self.memory.connection.execute('SELECT active FROM body_r2_state WHERE run_id=?',(self.run_id,)).fetchone()
        if not row or not row['active']: return {}
        return {r['capability']:r['status'] for r in self.memory.connection.execute('SELECT * FROM body_r2_proofs WHERE run_id=? AND package=?',(self.run_id,row['active']))}

