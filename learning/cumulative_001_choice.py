"""Predeclared action-feasibility selection; hidden physics is used only by judge."""
from __future__ import annotations
import argparse
from dataclasses import replace
import hashlib,json,time
from pathlib import Path
import numpy as np
from learning.body_schema_002 import Observation,Ridge,canonical,digest
from learning.cumulative_001_data import ROOT,OUTPUT,seed,body
from learning.cumulative_001_neural import NeuralLearner
from learning.life_010 import life010_bench_config
from sim3d.bench_env import BenchHeadEnv


def prepare(org,start,execution_seed):
    env=BenchHeadEnv(life010_bench_config(org,execution_seed)); angles=[90.]
    for _ in range(32): angles.append(env.step(start).as5600_deg)
    return env,Observation(angles[-1],angles[-1]-angles[-2],start,start,0.)


def predict_candidates(model,o,candidates,horizon):
    branches=[replace(o,target=float(c)) for c in candidates]
    for _ in range(horizon):
        predicted=model.predict(branches) if isinstance(model,NeuralLearner) else np.array([model.predict(x) for x in branches])
        branches=[Observation(float(p),float(p-x.angle),x.target,x.target,x.target-x.previous_target) for p,x in zip(predicted,branches)]
    return [float(x) for x in predicted]


def choose(o,candidates,predicted):
    feasible=[i for i in range(len(candidates)) if abs(predicted[i]-candidates[i])<=2.]
    if not feasible:
        return min(range(len(candidates)),key=lambda i:(abs(candidates[i]-o.angle),candidates[i]<o.angle,candidates[i]))
    return min(feasible,key=lambda i:(-abs(candidates[i]-o.angle),candidates[i]<o.angle,candidates[i]))


def situation(org,start,horizon,execution_seed,models):
    env,o=prepare(org,start,execution_seed); env.close()
    candidates=sorted({o.angle+sign*distance for sign in [-1,1] for distance in [5,10,15,20,30,40,50,60] if 30<=o.angle+sign*distance<=150})
    predictions={name:predict_candidates(model,o,candidates,max(1,horizon-2) if name=='cautious_prior' else horizon) for name,model in models.items()}
    choices={name:choose(o,candidates,p) for name,p in predictions.items()}
    choices['nearest']=min(range(len(candidates)),key=lambda i:(abs(candidates[i]-o.angle),candidates[i]<o.angle,candidates[i]))
    # All decisions are fixed before the judge opens a counterfactual future.
    observed=[]; traces=[]
    for candidate in candidates:
        env,check=prepare(org,start,execution_seed)
        try:
            if check!=o: raise ValueError('counterfactual preparation mismatch')
            trace=[]
            for _ in range(horizon): trace.append(env.step(candidate).as5600_deg)
            observed.append(trace[-1]); traces.append(trace)
        finally: env.close()
    rewards=[abs(c-o.angle) if abs(y-c)<=2 else 0. for c,y in zip(candidates,observed)]
    oracle=max(rewards)
    scores={name:{'chosen':candidates[i],'success':abs(observed[i]-candidates[i])<=2,'utility_deg':rewards[i],
                  'regret_deg':oracle-rewards[i],'prediction_mae_deg':float(np.mean(abs(np.array(predictions[name])-observed))) if name in predictions else None} for name,i in choices.items()}
    return {'start':start,'horizon':horizon,'initial_observation':o.__dict__,'candidates':candidates,
            'predicted_terminal':predictions,'observed_terminal':observed,'traces':traces,'oracle_utility_deg':oracle,'scores':scores}


def run(manifest_path,variant='v2',starts=None,horizons=None):
    base=json.loads(Path(manifest_path).read_bytes())
    starts=starts or [45.,75.,90.,105.,135.]; horizons=horizons or [3,4,5,6,8]
    destination=OUTPUT/'control'/variant
    if destination.exists(): raise ValueError('finished/exposed control bank cannot be overwritten')
    destination.mkdir(parents=True)
    namespace='cumulative-001/control/'+variant
    manifest={'namespace':namespace,'base_digest':digest(base),'starts':starts,'horizons':horizons,
              'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'seeds':{}}
    for identity in base['lives']:
        manifest['seeds'][identity]=[seed(namespace,'execution',identity,start,h) for start in starts for h in horizons]
    values=[s for array in manifest['seeds'].values() for s in array]
    if min(values)<=100000 or len(values)!=len(set(values)): raise ValueError('provenance collision')
    (destination/'manifest.json').write_bytes(canonical(manifest)); started=time.monotonic(); per_life={}
    for identity,definition in base['lives'].items():
        folder=OUTPUT/base['bank']/base['variant']/identity.replace('/','-')
        ridge=Ridge.restore(json.loads((folder/'C/ridge.json').read_bytes())['models']['ridge_cumulative'])
        neural=NeuralLearner.load(folder/'C/neural_replay.pt'); before=neural.parameter_digest()
        models={'prior':Ridge.initial('F'),'cautious_prior':Ridge.initial('F'),'ridge':ridge,'neural':neural}
        org=body(identity,definition['body']); situations=[]
        for index,(start,h) in enumerate((s,h) for s in starts for h in horizons):
            situations.append(situation(org,start,h,manifest['seeds'][identity][index],models))
        if neural.parameter_digest()!=before: raise ValueError('judge changed neural parameters')
        (destination/(identity.replace('/','-')+'.json')).write_bytes(canonical(situations))
        summary={name:{'utility_deg':float(np.mean([s['scores'][name]['utility_deg'] for s in situations])),
                       'success_rate':float(np.mean([s['scores'][name]['success'] for s in situations])),
                       'regret_deg':float(np.mean([s['scores'][name]['regret_deg'] for s in situations]))} for name in [*models,'nearest']}
        summary['oracle']={'utility_deg':float(np.mean([s['oracle_utility_deg'] for s in situations]))}
        per_life[identity]=summary; print(json.dumps({'life':identity,'scores':summary}),flush=True)
    aggregate={name:{k:float(np.mean([v[name][k] for v in per_life.values()])) for k in next(iter(per_life.values()))[name]} for name in next(iter(per_life.values()))}
    baseline=max(aggregate[k]['utility_deg'] for k in ['prior','cautious_prior','nearest'])
    gates={'success':aggregate['neural']['success_rate']>=.9,'gain_over_best_baseline':aggregate['neural']['utility_deg']>=1.1*baseline,
           'regret':aggregate['neural']['regret_deg']<=.2*aggregate['oracle']['utility_deg']}
    report={'aggregate':aggregate,'per_life':per_life,'gates':gates,'seconds':time.monotonic()-started,'level':base['level']}
    (destination/'summary.json').write_bytes(canonical(report)); print(json.dumps(report['aggregate'],indent=2)); print('Gates',gates,flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); p.add_argument('--variant',default='v2'); p.add_argument('--validation',action='store_true')
    args=p.parse_args()
    run(args.manifest,args.variant,[52.5,82.5,97.5,127.5] if args.validation else None,[3,5,7,9] if args.validation else None)


if __name__=='__main__': main()
