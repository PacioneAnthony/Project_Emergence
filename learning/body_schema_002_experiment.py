"""Development-only MuJoCo runner for the fixed r2 manifest."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import numpy as np

from learning.body_schema_002 import Observation,TrainingRow,Ridge,Learner,canonical,digest,rollout
from learning.body_schema_001 import IMPULSE_DURATIONS,REVERSAL_DURATIONS,MICRO_DURATIONS,IMPULSE_WAYPOINTS,REVERSAL_WAYPOINTS,MICRO_WAYPOINTS
from learning.life_010 import Life010Organism,life010_bench_config
from sim3d.bench_env import BenchHeadEnv
from cognitive.kernel import CognitiveKernel
from cognitive.body_forecast import BodyForecastStore

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/research/body_schema_002_dev_manifest.json'
OUTPUT=ROOT/'data/processed/experiments/body_schema_002_r2_dev_v1'
BUDGET_ROOT=OUTPUT
SOURCE_FILES=['learning/body_schema_002.py','learning/body_schema_002_budget.py','learning/body_schema_002_experiment.py','cognitive/body_forecast.py','tests/test_body_schema_002.py',
              'sim3d/bench_env.py','sim3d/bench_model.py','learning/body_schema_001.py','learning/life_010.py','cognitive/memory.py','cognitive/kernel.py']


def source_receipt():
    import mujoco
    return {'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_FILES},
            'python':platform.python_version(),'numpy':np.__version__,'mujoco':mujoco.__version__,
            'manifest':hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}


def plans():
    result=[]
    impulses=list(IMPULSE_DURATIONS)+[(5,9,11,7),(11,7,5,9),(7,5,11,9),(9,11,7,5)]
    reversals=list(REVERSAL_DURATIONS)+[(1,3,5,7,7,5,3,1),(3,5,7,7,5,3,1,1),(5,7,7,5,3,1,1,3),(7,7,5,3,1,1,3,5)]
    micros=list(MICRO_DURATIONS)
    for i in range(4):
        d=[2]*16; d[i]=d[i+8]=3; d[i+4]=d[i+12]=1; micros.append(d)
    for motif,waypoints,durations in [('impulse',IMPULSE_WAYPOINTS,impulses),('reversal',REVERSAL_WAYPOINTS,reversals),('micro',MICRO_WAYPOINTS,micros)]:
        for index,ds in enumerate(durations):
            targets=[float(w) for w,d in zip(waypoints,ds) for _ in range(d)]
            if len(targets)!=32 or targets[-1]!=90 or not all(30<=x<=150 for x in targets): raise ValueError('plan envelope')
            if sum(abs(b-a) for a,b in zip([90]+targets,targets))!=240: raise ValueError('plan cost')
            role='protection' if index==0 else ('calibration' if index<=2 else ('learning' if index<=10 else 'evaluation'))
            result.append({'id':f'{motif}-{index:02d}','motif':motif,'index':index,'role':role,'targets':targets})
    return result


def organism(identity,seeds):
    regime=identity.split('/')[0]; rng=np.random.default_rng(seeds['organism'])
    params={'seed':seeds['organism'],'regime':regime}
    if regime=='speed_dominant': params['max_speed_deg_s']=float(rng.uniform(240,720))
    elif regime=='settling_dominant': params.update(position_gain=float(rng.uniform(7,13)),velocity_damping=float(rng.uniform(.08,.24)))
    else: params.update(joint_frictionloss=float(rng.uniform(.006,.030)),joint_armature=float(rng.uniform(1e-4,4e-4)))
    return Life010Organism(**params)


def execute(org,plan,seed,model=None):
    env=BenchHeadEnv(life010_bench_config(org,seed))
    rows=[]; emissions=[]; angles=[90.]; last_target=90.; last_command_delta=0.
    try:
        for i,target in enumerate(plan['targets']):
            o=Observation(angles[-1],0. if i==0 else angles[-1]-angles[-2],last_target,target,last_command_delta)
            # Prediction really occurs before env.step, not from a post-step object.
            if model is not None:
                emissions.append({'sequence':i,'phase':'before_step','mean':model.predict(o),
                                  'model_version':model.version,'observation':asdict(o)})
            observed=env.step(target).as5600_deg
            rows.append(TrainingRow(o,observed)); angles.append(observed)
            last_command_delta=target-last_target; last_target=target
        return rows,emissions
    finally: env.close()


def content_checks(trials,definitions):
    collisions=[]; nearest=[]
    for channel in ['commands','angles']:
        arrays={p['id']:np.array(([90.]+p['targets']) if channel=='commands' else ([90.]+[r.next_angle for r in trials[p['id']]]),dtype=np.float64) for p in definitions}
        for i,a in enumerate(definitions):
            distances=[]
            for b in definitions[i+1:]:
                if a['role']==b['role']: continue
                av,bv=arrays[a['id']],arrays[b['id']]
                if digest(av.tolist())==digest(bv.tolist()): collisions.append([channel,a['id'],b['id']])
                distances.append(float(np.mean(abs(av-bv))))
            if distances: nearest.append({'channel':channel,'trial':a['id'],'nearest_other_role_mae':min(distances)})
    return {'passed':not collisions,'collisions':collisions,'distances':nearest,
            'anchors':{p['id']:digest([r.payload() for r in trials[p['id']]]) for p in definitions if p['role']=='protection'}}


def score(model,rows,h):
    values=[]
    for origin in range(len(rows)-h+1):
        commands=[r.observation.target for r in rows[origin:origin+h]]
        predicted=rollout(model,rows[origin].observation,commands)[-1]
        values.append(abs(predicted-rows[origin+h-1].next_angle))
    return float(np.mean(values))


def evaluate(models,trials,definitions):
    result={}
    for name,model in models.items():
        horizons={}
        for h in [1,5,25]:
            by_motif={m:[] for m in ['impulse','reversal','micro']}
            for p in definitions:
                if p['role']=='evaluation': by_motif[p['motif']].append(score(model,trials[p['id']],h))
            per={m:float(np.mean(v)) for m,v in by_motif.items()}
            horizons[str(h)]={'mae_deg':float(np.mean(list(per.values()))),'by_motif':per,'origins_per_trial':33-h}
        common=[]
        for p in definitions:
            if p['role']=='evaluation':
                rows=trials[p['id']]
                common.append(float(np.mean([abs(model.predict(r.observation)-r.next_angle) for r in rows[:8]])))
        result[name]={'horizons':horizons,'one_step_on_25step_origins':float(np.mean(common)),
                      'saturation_fraction':float(np.mean([model.predict(r.observation) in (10.,170.) for p in definitions if p['role']=='evaluation' for r in trials[p['id']]]))}
    return result


def restore_probe(request_path,response_path):
    request=json.loads(Path(request_path).read_text())
    with CognitiveKernel(request['database']) as kernel:
        store=BodyForecastStore(kernel,request['artifacts'],request['run'],request['contract'])
        learner=store.load()
        before={'payload_digest':digest(learner.payload()),'prediction':learner.active.predict(Observation(**request['observation']))}
        rows=[TrainingRow.restore(r) for r in request['next_rows']]
        learner.update(rows)  # branch only, no mutation of the persistent/live learner
        before['next_payload_digest']=digest(learner.payload())
    Path(response_path).write_bytes(canonical(before))


def run_one(identity,seed_map,manifest,receipt):
    definitions=plans(); org=organism(identity,seed_map)
    folder=OUTPUT/identity.replace('/','-'); folder.mkdir(parents=True,exist_ok=True)
    if (folder/'report.json').exists(): raise ValueError('completed organism is immutable; use resume verification, not overwrite')
    contract=digest(receipt)
    binding=folder/'binding.json'
    if binding.exists() and json.loads(binding.read_bytes())!=receipt: raise ValueError('source/environment changed: new variant required')
    binding.write_bytes(canonical(receipt))
    start=time.monotonic(); trials={}
    for p in definitions:
        trials[p['id']],_=execute(org,p,seed_map['execution'][p['id']])
    integrity=content_checks(trials,definitions)
    (folder/'integrity.json').write_bytes(canonical(integrity))
    if not integrity['passed']: raise ValueError(f'content integrity failed: {integrity["collisions"]}')
    (folder/'trials.json').write_bytes(canonical({p['id']:[r.payload() for r in trials[p['id']]] for p in definitions}))
    anchors={p['motif']:trials[p['id']] for p in definitions if p['role']=='protection'}
    ordered=sorted([p for p in definitions if p['role']=='learning'],key=lambda p:(p['index'],['impulse','reversal','micro'].index(p['motif'])))
    learners={}; persistence={}
    for kind in ['F','B13','B3']:
        database=folder/(kind+'.sqlite'); artifacts=folder/(kind+'-artifacts'); run_id=manifest['variant']+'/'+identity+'/'+kind
        with CognitiveKernel(database) as kernel:
            store=BodyForecastStore(kernel,artifacts,run_id,contract)
            store.initialize(Learner(kind,anchors,manifest['selection']))
            for p in ordered:
                learner,_=store.apply(run_id+'/'+str(ordered.index(p)),trials[p['id']])
            first=learner.payload(); old_cursor=len(learner.trials)
            old_replay,applied=store.apply(run_id+'/0',trials[ordered[0]['id']])
            if applied or len(old_replay.trials)!=old_cursor or digest(old_replay.payload())!=digest(first): raise ValueError('old replay not idempotent')
            learners[kind]=learner
        # True process boundary: coefficients AND the next update must match exactly.
        probe_rows=trials[ordered[-1]['id']]
        obs=probe_rows[0].observation
        request={'database':str(database),'artifacts':str(artifacts),'run':run_id,'contract':contract,
                 'observation':asdict(obs),'next_rows':[r.payload() for r in probe_rows]}
        request_path=folder/(kind+'-restore-request.json'); response_path=folder/(kind+'-restore-result.json')
        request_path.write_bytes(canonical(request))
        subprocess.run([sys.executable,'-m','learning.body_schema_002_experiment','--restore-probe',str(request_path),str(response_path)],check=True,timeout=60)
        response=json.loads(response_path.read_bytes())
        branch=Learner.restore(first); branch.update(probe_rows)
        expected={'payload_digest':digest(first),'prediction':learners[kind].active.predict(obs),'next_payload_digest':digest(branch.payload())}
        if response!=expected: raise ValueError('cross-process continuation mismatch')
        persistence[kind]={'passed':True,'old_trial_replay_no_effect':True,**response}
    models={kind:l.active for kind,l in learners.items()}; models['B0']=Ridge.initial('B3'); models['B1']=Ridge.initial('F')
    metrics=evaluate(models,trials,definitions)
    emissions=[]
    for p in definitions:
        if p['role']=='evaluation':
            replay,trace=execute(org,p,seed_map['execution'][p['id']],learners['F'].active)
            if replay!=trials[p['id']]: raise ValueError('physical replay mismatch')
            emissions.extend([{'trial':p['id'],**t,'observed_after_step':r.next_angle} for t,r in zip(trace,replay)])
    (folder/'pre_step_predictions.json').write_bytes(canonical(emissions))
    f=metrics['F']['horizons']['1']['mae_deg']; b=metrics['B1']['horizons']['1']['mae_deg']
    usage=f<=manifest['F_development_use']['final_mae_max_deg'] and (b-f)/max(b,1e-12)>=manifest['F_development_use']['relative_gain_vs_prior_min']
    report={'organism':identity,'parameters_judge_only':asdict(org),'contract':contract,'level':'development',
            'integrity_passed':True,'metrics':metrics,'persistence':persistence,'F_usage_passed':usage,
            'model_diagnostics':{k:l.diagnostics for k,l in learners.items()},
            'promotions':{k:[h for h in l.history if h['due']] for k,l in learners.items()},
            'seconds':time.monotonic()-start,'activation':'pending_reception_receipt','calibration':'not_qualified','agency':'not_qualified'}
    (folder/'report.json').write_bytes(canonical(report))
    return report


def main():
    global OUTPUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--restore-probe',nargs=2)
    parser.add_argument('--organism',choices=['first','remaining','all'],default='first')
    args=parser.parse_args()
    if args.restore_probe:
        restore_probe(*args.restore_probe); return
    manifest=json.loads(MANIFEST.read_text())
    OUTPUT=ROOT/'data/processed/experiments'/manifest['output_directory']
    if manifest['phase']!='development' or not manifest['namespace'].endswith('/dev/v1'): raise ValueError('only development access implemented')
    receipt=source_receipt(); OUTPUT.mkdir(parents=True,exist_ok=True)
    reception=json.loads((BUDGET_ROOT/'contracts_receipt.json').read_bytes())
    if reception['source']!=receipt or reception['exit_code']!=0:
        raise ValueError('current code must pass causal and persistence contracts before simulation')
    chosen=list(manifest['seeds'])
    if args.organism=='first': chosen=chosen[:1]
    if args.organism=='remaining': chosen=chosen[1:]
    all_reports=[]
    for identity in chosen:
        print('Starting',identity,flush=True)
        report=run_one(identity,manifest['seeds'][identity],manifest,receipt)
        all_reports.append(report)
        print(json.dumps({'organism':identity,'F_mae':report['metrics']['F']['horizons']['1']['mae_deg'],
                          'prior_mae':report['metrics']['B1']['horizons']['1']['mae_deg'],'usage':report['F_usage_passed'],'seconds':report['seconds']}),flush=True)
    print('Completed',len(all_reports),'development organisms; no validation/confirmation opened.',flush=True)


if __name__=='__main__': main()
