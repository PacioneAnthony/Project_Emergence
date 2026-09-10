"""New, phase-blind motor-domain data for cumulative learning experiments."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from learning.body_schema_002 import Observation, TrainingRow, canonical, digest, features, prior
from learning.life_010 import Life010Organism, life010_bench_config
from sim3d.bench_env import BenchHeadEnv

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/processed/experiments/cumulative_001'
PHASES=('A','B','A_return','C')
REGIMES=('speed_dominant','settling_dominant','friction_dominant')


def seed(namespace,*parts):
    return int.from_bytes(hashlib.sha256(canonical([namespace,*parts])).digest()[:4],'big')


def build_manifest(variant='v1',bank='dev',count=6):
    namespace=f'cumulative-001/{bank}/{variant}'
    lives={}
    for i in range(count):
        identity=f'{REGIMES[i%3]}/{i//3}'
        trials={}
        for role,domains,n in [('learning',PHASES,12),('evaluation',('A','B','C'),8)]:
            for domain in domains:
                for index in range(n):
                    key=f'{role}/{domain}/{index}'
                    trials[key]={'command':seed(namespace,'command',identity,key),'execution':seed(namespace,'execution',identity,key)}
        lives[identity]={'body':seed(namespace,'body',identity),'initialization':seed(namespace,'initialization',identity),
                         'batches':seed(namespace,'batches',identity),'trials':trials}
    return {'namespace':namespace,'variant':variant,'bank':bank,'lives':lives,'phases':list(PHASES),
            'steps':64,'trials_per_phase':12,'evaluation_trials':8,'updates':64,'batch':128,'lr':.001,
            'replay_fraction':.5,'hidden':64,'short_ridge_trials':4,'horizons':[1],
            'criteria':{'learning_mae_deg':1.,'relative_gain_vs_prior':.3,'retention_margin_deg':.2},
            'budget':{'total_seconds':5400,'per_invocation':900},'level':'development'}


def body(identity,body_seed):
    regime=identity.split('/')[0]; rng=np.random.default_rng(body_seed)
    p={'regime':regime,'seed':body_seed}
    if regime=='speed_dominant': p['max_speed_deg_s']=float(rng.uniform(240,720))
    elif regime=='settling_dominant': p.update(position_gain=float(rng.uniform(7,13)),velocity_damping=float(rng.uniform(.08,.24)))
    else: p.update(joint_frictionloss=float(rng.uniform(.006,.03)),joint_armature=float(rng.uniform(1e-4,4e-4)))
    return Life010Organism(**p)


def commands(domain,command_seed,steps=64):
    rng=np.random.default_rng(command_seed); domain='A' if domain=='A_return' else domain
    lo,hi={'A':(30,90),'B':(90,150),'C':(30,150)}[domain]
    values=[]
    while len(values)<steps-8:
        target=float(rng.choice(np.arange(lo,hi+1,5)))
        duration=int(rng.integers(2,11)); values.extend([target]*min(duration,steps-8-len(values)))
    return values+[90.]*8


def simulate(org,targets,execution_seed):
    env=BenchHeadEnv(life010_bench_config(org,execution_seed))
    rows=[]; angles=[90.]; last_target=90.; last_delta=0.
    try:
        for i,target in enumerate(targets):
            o=Observation(angles[-1],0. if i==0 else angles[-1]-angles[-2],last_target,target,last_delta)
            observed=env.step(target).as5600_deg
            rows.append(TrainingRow(o,observed)); angles.append(observed)
            last_delta=target-last_target; last_target=target
        return rows
    finally: env.close()


def generate_life(identity,definition):
    org=body(identity,definition['body']); trials={}; seen_command={}; seen_angle={}
    for key,s in definition['trials'].items():
        role,domain,_=key.split('/'); targets=commands(domain,s['command']); rows=simulate(org,targets,s['execution'])
        for seen,values in [(seen_command,[90.]+targets),(seen_angle,[90.]+[r.next_angle for r in rows])]:
            sha=digest(values)
            if sha in seen: raise ValueError(f'duplicate complete trajectory {key} / {seen[sha]}')
            seen[sha]=key
        trials[key]=rows
    return trials


def encode(rows):
    return (np.stack([features(r.observation,'F') for r in rows]).astype(np.float32),
            np.array([(r.next_angle-prior(r.observation,'F'))/12 for r in rows],dtype=np.float32),
            np.array([prior(r.observation,'F') for r in rows],dtype=np.float32),
            np.array([r.next_angle for r in rows],dtype=np.float32))


def payload(trials): return {k:[r.payload() for r in v] for k,v in trials.items()}
def restore(data): return {k:[TrainingRow.restore(r) for r in v] for k,v in data.items()}
