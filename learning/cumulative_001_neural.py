"""GPU residual learner with causally bounded replay and complete checkpoints."""
from __future__ import annotations
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import hashlib
from pathlib import Path
import time
import numpy as np
import torch
from learning.cumulative_001_data import encode
from learning.body_schema_002 import canonical, features, prior

torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32=False


class NeuralLearner:
    def __init__(self,initialization,batches,replay,*,device='cuda',updates=64):
        self.device=device; self.replay=bool(replay); self.updates=updates
        self.initialization=int(initialization); self.batches=int(batches)
        torch.manual_seed(initialization)
        self.model=torch.nn.Sequential(torch.nn.Linear(13,64),torch.nn.ReLU(),torch.nn.Linear(64,64),torch.nn.ReLU(),torch.nn.Linear(64,1)).to(device)
        torch.nn.init.zeros_(self.model[-1].weight); torch.nn.init.zeros_(self.model[-1].bias)
        self.optimizer=torch.optim.Adam(self.model.parameters(),lr=.001)
        self.generator=torch.Generator(device=device).manual_seed(batches)
        self.memory_x=torch.empty((0,13),device=device); self.memory_y=torch.empty((0,),device=device)
        self.trials=0; self.update_count=0; self.wall_seconds=0.; self.gpu_seconds=0.

    def update(self,rows):
        x,y,_,_=encode(rows); x=torch.as_tensor(x,device=self.device); y=torch.as_tensor(y,device=self.device)
        if self.device=='cuda': torch.cuda.synchronize()
        start=time.monotonic()
        events=None
        if self.device=='cuda':
            events=(torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)); events[0].record()
        self.model.train()
        for _ in range(self.updates):
            use_old=self.replay and len(self.memory_x)>0
            n=64 if use_old else 128
            index=torch.randint(len(x),(n,),generator=self.generator,device=self.device)
            bx,by=x[index],y[index]
            if use_old:
                old=torch.randint(len(self.memory_x),(64,),generator=self.generator,device=self.device)
                bx=torch.cat([bx,self.memory_x[old]]); by=torch.cat([by,self.memory_y[old]])
            self.optimizer.zero_grad(set_to_none=True)
            loss=torch.mean((self.model(bx).squeeze(-1)-by)**2)
            loss.backward(); self.optimizer.step(); self.update_count+=1
        if self.replay:
            self.memory_x=torch.cat([self.memory_x,x]); self.memory_y=torch.cat([self.memory_y,y])
        self.trials+=1
        if events:
            events[1].record(); torch.cuda.synchronize(); self.gpu_seconds+=events[0].elapsed_time(events[1])/1000
        self.wall_seconds+=time.monotonic()-start

    def predict(self,observations):
        x=np.stack([features(o,'F') for o in observations]).astype(np.float32)
        p=np.array([prior(o,'F') for o in observations],dtype=np.float32)
        self.model.eval()
        with torch.no_grad():
            residual=self.model(torch.as_tensor(x,device=self.device)).squeeze(-1).cpu().numpy()*12
        return np.clip(p+residual,10,170)

    def state(self):
        return {'format':'cumulative-neural-v1','initialization':self.initialization,'batches':self.batches,'replay':self.replay,'updates':self.updates,
                'model':self.model.state_dict(),'optimizer':self.optimizer.state_dict(),'rng':self.generator.get_state(),
                'memory_x':self.memory_x,'memory_y':self.memory_y,'trials':self.trials,'update_count':self.update_count}

    def save(self,path):
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp'); torch.save(self.state(),temp); os.replace(temp,path)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @classmethod
    def load(cls,path,device='cuda'):
        p=torch.load(path,map_location=device,weights_only=True)
        if p['format']!='cumulative-neural-v1': raise ValueError('checkpoint format')
        obj=cls(p['initialization'],p['batches'],p['replay'],device=device,updates=p['updates'])
        obj.model.load_state_dict(p['model']); obj.optimizer.load_state_dict(p['optimizer'])
        obj.generator.set_state(p['rng'].cpu()); obj.memory_x=p['memory_x']; obj.memory_y=p['memory_y']
        obj.trials=p['trials']; obj.update_count=p['update_count']
        return obj

    def parameter_digest(self):
        sha=hashlib.sha256()
        for key,value in sorted(self.model.state_dict().items()):
            sha.update(key.encode()); sha.update(value.detach().cpu().contiguous().numpy().tobytes())
        return sha.hexdigest()
