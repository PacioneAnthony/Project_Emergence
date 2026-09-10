"""Experimental neural service with atomic experience, recovery goal and model state."""
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
import torch
from learning.body_schema_002 import digest
from learning.resilience_001_agent import RecoveryAgent


class ResilienceStore:
    def __init__(self, kernel, artifacts, run_id, contract, device='cuda'):
        self.memory = kernel.memory
        self.folder = Path(artifacts).resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.run_id, self.contract, self.device = run_id, contract, device
        with self.memory.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS resilience_state(run_id TEXT PRIMARY KEY,contract TEXT,artifact TEXT,digest TEXT,cursor INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS resilience_experiences(run_id TEXT,logical_id TEXT,content TEXT,event TEXT,checkpoint TEXT,cursor INTEGER,PRIMARY KEY(run_id,logical_id))')

    def publish(self, agent):
        temp = self.folder / (uuid.uuid4().hex + '.tmp')
        with temp.open('xb') as stream:
            torch.save(agent.state(), stream)
            stream.flush(); os.fsync(stream.fileno())
        sha = hashlib.sha256(temp.read_bytes()).hexdigest()
        path = self.folder / (sha + '.pt')
        os.replace(temp, path)
        return str(path), sha

    def _state(self):
        row = self.memory.connection.execute('SELECT * FROM resilience_state WHERE run_id=?', (self.run_id,)).fetchone()
        if row is None or row['contract'] != self.contract: raise ValueError('missing or changed contract')
        return row

    def load(self):
        row = self._state()
        path = Path(row['artifact']).resolve()
        if path.parent != self.folder or hashlib.sha256(path.read_bytes()).hexdigest() != row['digest']:
            raise ValueError('checkpoint integrity')
        agent = RecoveryAgent.restore(torch.load(path, map_location=self.device, weights_only=True), self.device)
        if agent.trials != row['cursor']: raise ValueError('cursor mismatch')
        return agent

    def initialize(self, agent):
        existing = self.memory.connection.execute('SELECT 1 FROM resilience_state WHERE run_id=?', (self.run_id,)).fetchone()
        if existing: return self.load()
        path, sha = self.publish(agent)
        with self.memory.transaction() as db:
            db.execute('INSERT INTO resilience_state VALUES(?,?,?,?,?)', (self.run_id, self.contract, path, sha, agent.trials))
            self._register(db, path, sha, agent)
        return agent

    def _register(self, db, path, sha, agent):
        metadata = json.dumps({'level': 'experimental', 'contract': self.contract, 'trials': agent.trials,
                               'subgoal': 'restore_predictability' if agent.recovering else None,
                               'resilience_qualified': False}, sort_keys=True)
        db.execute("INSERT OR IGNORE INTO model_versions VALUES(?,?,'candidate',?,?,?,?)",
                   ('resilience/' + self.run_id, sha, path, sha, time.time_ns(), metadata))

    def apply(self, logical_id, rows, interrupt=None):
        content = digest([r.payload() for r in rows])
        seen = self.memory.connection.execute('SELECT * FROM resilience_experiences WHERE run_id=? AND logical_id=?', (self.run_id, logical_id)).fetchone()
        if seen:
            if seen['content'] != content: raise ValueError('changed experience content')
            return self.load(), json.loads(seen['event']), False
        before = self._state()
        agent = self.load()
        event = agent.update(rows)
        path, sha = self.publish(agent)
        if interrupt: interrupt('after_publication')
        with self.memory.transaction() as db:
            current = db.execute('SELECT * FROM resilience_state WHERE run_id=?', (self.run_id,)).fetchone()
            if current['digest'] != before['digest']: raise RuntimeError('concurrent write; retry')
            db.execute('INSERT INTO resilience_experiences VALUES(?,?,?,?,?,?)',
                       (self.run_id, logical_id, content, json.dumps(event, sort_keys=True), sha, agent.trials))
            db.execute('UPDATE resilience_state SET artifact=?,digest=?,cursor=? WHERE run_id=?', (path, sha, agent.trials, self.run_id))
            self._register(db, path, sha, agent)
            if interrupt: interrupt('before_commit')
        if interrupt: interrupt('after_commit')
        return agent, event, True

    def predict(self, observations):
        return self.load().predict(observations)
