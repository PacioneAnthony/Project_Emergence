"""Frozen, closed-loop simulated orientation test of the cumulative models."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from dataclasses import replace
from learning.body_schema_002 import Observation,Ridge,canonical,digest
from learning.cumulative_001_data import ROOT,OUTPUT,seed,body
from learning.cumulative_001_neural import NeuralLearner
from learning.life_010 import life010_bench_config
from sim3d.bench_env import BenchHeadEnv


def plan_action(model,observation,goal):
    candidates=np.unique(np.clip(goal+np.array([-24,-12,-6,0,6,12,24]),30,150))
    branches=[replace(observation,target=float(c)) for c in candidates]
    path=[]
    for _ in range(5):
        predicted=model.predict(branches) if isinstance(model,NeuralLearner) else np.array([model.predict(o) for o in branches])
        path.append(np.abs(predicted-goal))
        branches=[Observation(float(p),float(p-o.angle),o.target,o.target,o.target-o.previous_target) for o,p in zip(branches,predicted)]
    movement=np.abs(candidates-observation.previous_target)
    costs=.7*path[-1]+.3*np.mean(path,axis=0)+.002*movement
    index=min(range(len(candidates)),key=lambda i:(costs[i],movement[i],candidates[i]))
    return float(candidates[index]),{'candidates':candidates.tolist(),'costs':costs.tolist()}


def episode(org,goals,execution_seed,model):
    env=BenchHeadEnv(life010_bench_config(org,execution_seed))
    trace=[]; angles=[90.]; previous_target=90.; previous_delta=0.
    try:
        for step in range(48):
            goal=goals[0 if step<24 else 1]
            o=Observation(angles[-1],0. if step==0 else angles[-1]-angles[-2],previous_target,goal,previous_delta)
            command,planning=(goal,None) if model is None else plan_action(model,o,goal)
            observed=env.step(command).as5600_deg
            trace.append({'step':step,'goal':goal,'before_angle':angles[-1],'command':command,
                          'observed':observed,'error':abs(observed-goal),'planning':planning})
            angles.append(observed); previous_delta=command-previous_target; previous_target=command
        delays=[]
        for start in [0,24]:
            hit=next((i+2 for i in range(23) if trace[start+i]['error']<=1 and trace[start+i+1]['error']<=1),None)
            delays.append(hit)
        return {'mae_deg':float(np.mean([x['error'] for x in trace])),
                'final_error_deg':float(np.mean([trace[23]['error'],trace[47]['error']])),
                'settling_steps':delays,'command_travel_deg':float(sum(abs(b-a) for a,b in zip([90.]+[x['command'] for x in trace],[x['command'] for x in trace]))),
                'observed_travel_deg':float(sum(abs(b-a) for a,b in zip(angles,angles[1:]))),'trace':trace}
    finally: env.close()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); args=p.parse_args()
    development=json.loads(Path(args.manifest).read_bytes())
    destination=OUTPUT/'control'/'v1'
    if destination.exists(): raise ValueError('control v1 already exposed; new variant required')
    destination.mkdir(parents=True)
    manifest={'namespace':'cumulative-001/control/v1','development_digest':digest(development),
              'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'episodes':{}}
    for identity in development['lives']:
        definitions=[]
        for i in range(12):
            target_seed=seed(manifest['namespace'],'targets',identity,i)
            execution_seed=seed(manifest['namespace'],'execution',identity,i)
            if min(target_seed,execution_seed)<=100000: raise ValueError('reserved numeric range')
            rng=np.random.default_rng(target_seed); first=float(rng.choice(np.arange(42.5,138,5)))
            allowed=[float(x) for x in np.arange(42.5,138,5) if abs(x-first)>=20]
            definitions.append({'goals':[first,float(rng.choice(allowed))],'target_seed':target_seed,'execution_seed':execution_seed})
        manifest['episodes'][identity]=definitions
    (destination/'manifest.json').write_bytes(canonical(manifest))
    reports={}; started=time.monotonic()
    for identity,definition in development['lives'].items():
        folder=OUTPUT/development['bank']/development['variant']/identity.replace('/','-')
        source_report=json.loads((folder/'report.json').read_bytes())
        ridge=Ridge.restore(json.loads((folder/'C/ridge.json').read_bytes())['models']['ridge_cumulative'])
        neural=NeuralLearner.load(folder/'C/neural_replay.pt')
        models={'direct':None,'prior_planner':Ridge.initial('F'),'ridge_planner':ridge,'neural_planner':neural}
        org=body(identity,definition['body']); cases={}
        for name,model in models.items():
            before=neural.parameter_digest() if name=='neural_planner' else None
            runs=[episode(org,e['goals'],e['execution_seed'],model) for e in manifest['episodes'][identity]]
            if before and before!=neural.parameter_digest(): raise ValueError('evaluation mutated learner')
            cases[name]={k:float(np.mean([r[k] for r in runs])) for k in ['mae_deg','final_error_deg','command_travel_deg','observed_travel_deg']}
            delays=[v for r in runs for v in r['settling_steps']]
            cases[name]['settled_fraction']=sum(x is not None for x in delays)/len(delays)
            cases[name]['median_steps_conditional']=float(np.median([x for x in delays if x is not None])) if any(x is not None for x in delays) else None
            (destination/(identity.replace('/','-')+'-'+name+'.json')).write_bytes(canonical(runs))
        reports[identity]=cases
        print(json.dumps({'life':identity,'control':cases}),flush=True)
    aggregate={name:{metric:float(np.mean([r[name][metric] for r in reports.values()])) for metric in ['mae_deg','final_error_deg','command_travel_deg','observed_travel_deg','settled_fraction']} for name in models}
    (destination/'summary.json').write_bytes(canonical({'per_life':reports,'aggregate':aggregate,'seconds':time.monotonic()-started}))
    print(json.dumps({'aggregate':aggregate,'seconds':time.monotonic()-started}),flush=True)


if __name__=='__main__': main()
