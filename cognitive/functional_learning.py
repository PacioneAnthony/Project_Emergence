"""Atomic functional experience and endogenous decision attached to kernel memory."""
import hashlib
import json
from pathlib import Path
import torch
from cognitive.resilience import ResilienceStore
from learning.body_schema_002 import digest
from learning.resilience_002_agent import FunctionalAgent


class FunctionalStore(ResilienceStore):
    def predict(self, observations, horizons):
        return self.load().predict(observations, horizons)

    def load(self):
        row=self._state(); p=Path(row['artifact']).resolve()
        if p.parent!=self.folder or hashlib.sha256(p.read_bytes()).hexdigest()!=row['digest']: raise ValueError('checkpoint integrity')
        a=FunctionalAgent.restore(torch.load(p,map_location=self.device,weights_only=True),self.device)
        if a.trials!=row['cursor']: raise ValueError('cursor mismatch')
        return a

    def _register(self,db,path,sha,agent):
        import time
        metadata=json.dumps({'level':'experimental','contract':self.contract,'need_open':agent.need_open,'policy':agent.policy})
        db.execute("INSERT OR IGNORE INTO model_versions VALUES(?,?,'candidate',?,?,?,?)",
                   ('functional/'+self.run_id,sha,path,sha,time.time_ns(),metadata))

    def apply(self,logical_id,decision,episodes,interrupt=None):
        content=digest({'decision':decision,'episodes':episodes})
        seen=self.memory.connection.execute('SELECT * FROM resilience_experiences WHERE run_id=? AND logical_id=?',(self.run_id,logical_id)).fetchone()
        if seen:
            if seen['content']!=content: raise ValueError('changed experience content')
            return self.load(),json.loads(seen['event']),False
        before=self._state(); a=self.load()
        if a.select()!=decision: raise ValueError('decision did not originate in persisted state')
        if len(episodes)!=4 or any(e['band']!=decision['band'] for e in episodes):
            raise ValueError('experience does not match selected band')
        for e in episodes:
            from learning.body_schema_002 import Observation
            if a.announce(Observation(**e['observation']),e['horizon'])!=e['announcement']:
                raise ValueError('changed pre-action prediction')
        event=a.update(episodes); path,sha=self.publish(a)
        if interrupt: interrupt('after_publication')
        with self.memory.transaction() as db:
            current=db.execute('SELECT * FROM resilience_state WHERE run_id=?',(self.run_id,)).fetchone()
            if current['digest']!=before['digest']: raise RuntimeError('concurrent update')
            db.execute('INSERT INTO resilience_experiences VALUES(?,?,?,?,?,?)',(self.run_id,logical_id,content,json.dumps(event),sha,a.trials))
            db.execute('UPDATE resilience_state SET artifact=?,digest=?,cursor=? WHERE run_id=?',(path,sha,a.trials,self.run_id))
            self._register(db,path,sha,a)
            if interrupt: interrupt('before_commit')
        if interrupt: interrupt('after_commit')
        return a,event,True
