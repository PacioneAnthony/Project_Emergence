"""Bounded cumulative development runner and independent checkpoint verification."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from learning.cumulative_001_data import ROOT,OUTPUT,PHASES,generate_life,encode,payload,restore
from learning.cumulative_001_neural import NeuralLearner,torch
from learning.body_schema_002 import Ridge,fit,canonical,digest,TrainingRow

SOURCE=['learning/cumulative_001_data.py','learning/cumulative_001_neural.py','learning/cumulative_001.py',
        'learning/body_schema_002.py','learning/life_010.py','sim3d/bench_env.py','sim3d/bench_model.py']


def source():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE}


def evaluate(neural,ridges,evaluation):
    result={name:{} for name in [*neural,*ridges]}
    for domain,trials in evaluation.items():
        flat=[r for trial in trials for r in trial]; y=np.array([r.next_angle for r in flat]); obs=[r.observation for r in flat]
        for name,model in neural.items(): result[name][domain]=float(np.mean(abs(model.predict(obs)-y)))
        for name,model in ridges.items(): result[name][domain]=float(np.mean(abs(np.array([model.predict(o) for o in obs])-y)))
    return result


def probe(request,response):
    p=json.loads(Path(request).read_bytes()); rows=[TrainingRow.restore(x) for x in p['rows']]
    model=NeuralLearner.load(p['checkpoint'])
    before={'parameters':model.parameter_digest(),'predictions':model.predict([r.observation for r in rows]).tolist()}
    model.update(rows); before['next_parameters']=model.parameter_digest()
    before['next_rng_digest']=hashlib.sha256(model.generator.get_state().cpu().numpy().tobytes()).hexdigest()
    Path(response).write_bytes(canonical(before))


def run_life(identity,definition,manifest,folder):
    if (folder/'report.json').exists(): raise ValueError('finished life is immutable')
    folder.mkdir(parents=True,exist_ok=True); started=time.monotonic()
    binding={'source':source(),'manifest':digest(manifest)}
    (folder/'binding.json').write_bytes(canonical(binding))
    t=time.monotonic(); trials=generate_life(identity,definition); generation_seconds=time.monotonic()-t
    (folder/'trials.json').write_bytes(canonical(payload(trials)))
    evaluation={d:[trials[f'evaluation/{d}/{i}'] for i in range(8)] for d in ['A','B','C']}
    initial=definition['initialization']; batchseed=definition['batches']
    neural={'neural_naive':NeuralLearner(initial,batchseed,False,updates=manifest['updates']),
            'neural_replay':NeuralLearner(initial,batchseed,True,updates=manifest['updates'])}
    ridges={'ridge_short':Ridge.initial('F'),'ridge_cumulative':Ridge.initial('F'),'prior':Ridge.initial('F')}
    history=[]; training=[]; cpu_seconds=0.; restart={}
    neural_time={name:{'wall_seconds':0.,'gpu_seconds':0.} for name in neural}
    for phase in PHASES:
        history.append({'phase':phase,'trial':0,'scores':evaluate(neural,ridges,evaluation)})
        if phase=='A_return':
            fresh={'fresh_naive':NeuralLearner(initial,batchseed,False,updates=manifest['updates']),
                   'fresh_replay':NeuralLearner(initial,batchseed,True,updates=manifest['updates'])}
            fresh_ridges={'fresh_ridge':Ridge.initial('F')}; fresh_rows=[]
            fresh_history=[{'trial':0,'scores':evaluate(fresh,fresh_ridges,evaluation)}]
        for index in range(12):
            key=f'learning/{phase}/{index}'; rows=trials[key]; training.append(rows)
            for name,model in neural.items():
                wall,gpu=model.wall_seconds,model.gpu_seconds
                model.update(rows)
                neural_time[name]['wall_seconds']+=model.wall_seconds-wall
                neural_time[name]['gpu_seconds']+=model.gpu_seconds-gpu
            t=time.monotonic()
            ridges['ridge_short'],_=fit([r for trial in training[-4:] for r in trial],'F')
            ridges['ridge_cumulative'],_=fit([r for trial in training for r in trial],'F')
            cpu_seconds+=time.monotonic()-t
            if phase=='A_return':
                fresh_rows.extend(rows)
                for model in fresh.values(): model.update(rows)
                fresh_ridges['fresh_ridge'],_=fit(fresh_rows,'F')
            if (index+1)%3==0:
                history.append({'phase':phase,'trial':index+1,'scores':evaluate(neural,ridges,evaluation)})
                if phase=='A_return': fresh_history.append({'trial':index+1,'scores':evaluate(fresh,fresh_ridges,evaluation)})
        checkpoint=folder/phase; checkpoint.mkdir(exist_ok=True)
        (checkpoint/'ridge.json').write_bytes(canonical({'models':{k:m.payload() for k,m in ridges.items()},
                    'training':[[r.payload() for r in trial] for trial in training]}))
        for name,model in neural.items():
            path=checkpoint/(name+'.pt'); model.save(path)
            if phase=='B':
                request=checkpoint/(name+'-request.json'); response=checkpoint/(name+'-response.json')
                nextrows=trials['learning/A_return/0']
                request.write_bytes(canonical({'checkpoint':str(path.resolve()),'rows':[r.payload() for r in nextrows]}))
                subprocess.run([sys.executable,'-m','learning.cumulative_001','--probe',str(request),str(response)],check=True,timeout=90)
                before={'parameters':model.parameter_digest(),'predictions':model.predict([r.observation for r in nextrows]).tolist()}
                branch=NeuralLearner.load(path); branch.update(nextrows)
                before['next_parameters']=branch.parameter_digest()
                before['next_rng_digest']=hashlib.sha256(branch.generator.get_state().cpu().numpy().tobytes()).hexdigest()
                if json.loads(response.read_bytes())!=before: raise ValueError('GPU continuation mismatch across process')
                # The living instance actually continues from the saved model after B.
                neural[name]=NeuralLearner.load(path)
                restart[name]={'bit_exact':True,'checkpoint_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        (folder/'progress.json').write_bytes(canonical({'completed_phase':phase,'history':history}))
    finals={p:next(x['scores'] for x in history if x['phase']==p and x['trial']==12) for p in PHASES}
    learning={name:{d:finals[p][name][d] for p,d in [('A','A'),('B','B'),('C','C')]} for name in [*neural,*ridges]}
    forgetting={name:finals['B'][name]['A']-finals['A'][name]['A'] for name in [*neural,*ridges]}
    recovery={}
    for old,new in [('neural_naive','fresh_naive'),('neural_replay','fresh_replay'),('ridge_cumulative','fresh_ridge')]:
        continuing=[x['scores'][old]['A'] for x in history if x['phase']=='A_return']
        fresh_values=[x['scores'][new]['A'] for x in fresh_history]
        recovery[old]={'mean_checkpoint_error':float(np.mean(continuing)),'fresh_mean_checkpoint_error':float(np.mean(fresh_values))}
    report={'life':identity,'level':manifest['level'],'manifest':digest(manifest),'source':source(),
            'history':history,'fresh_history':fresh_history,'learning':learning,'forgetting_A_after_B':forgetting,
            'recovery':recovery,'restart':restart,'cpu_ridge_seconds':cpu_seconds,'generation_seconds':generation_seconds,
            'neural_time':neural_time,
            'neural_counters':{name:{'updates':m.update_count,'trials':m.trials,'buffer_rows':len(m.memory_x)} for name,m in neural.items()},
            'gpu':torch.cuda.get_device_name(0),'peak_gpu_allocated_bytes':torch.cuda.max_memory_allocated(),
            'seconds':time.monotonic()-started}
    (folder/'report.json').write_bytes(canonical(report))
    print(json.dumps({'life':identity,'seconds':report['seconds'],'learning':learning,'forgetting_A_after_B':forgetting,'recovery':recovery}),flush=True)
    return report


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest'); p.add_argument('--life',choices=['first','remaining','all'],default='first'); p.add_argument('--probe',nargs=2)
    args=p.parse_args()
    if args.probe: return probe(*args.probe)
    manifest=json.loads(Path(args.manifest).read_bytes())
    if manifest['bank'] not in ['dev','validation']: raise ValueError('confirmation not supported')
    if not torch.cuda.is_available(): raise RuntimeError('CUDA required for this preregistered neural comparison')
    identities=list(manifest['lives'])
    if args.life=='first': identities=identities[:1]
    elif args.life=='remaining': identities=identities[1:]
    for identity in identities:
        folder=OUTPUT/manifest['bank']/manifest['variant']/identity.replace('/','-')
        print('Starting',identity,flush=True)
        run_life(identity,manifest['lives'][identity],manifest,folder)


if __name__=='__main__': main()
