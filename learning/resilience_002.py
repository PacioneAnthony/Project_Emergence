"""Frozen functional-learning bench; hidden bodies and futures stay in the judge."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from cognitive.kernel import CognitiveKernel
from cognitive.functional_learning import FunctionalStore
from learning.body_schema_002 import Observation, canonical, digest
from learning.cumulative_001_data import ROOT, seed
from learning.cumulative_001_choice import prepare
from learning.resilience_001_v3 import source as previous_source
from learning.resilience_001_agent import state_digest
from learning.resilience_002_agent import FunctionalAgent, torch
from learning.resilience_002_budget import OUTPUT
from learning.life_010 import Life010Organism, life010_bench_config
from sim3d.bench_env import BenchHeadEnv

PHASES=['initial','perturbed','return']
POLICIES=['cycle','uniform','need']
PROTOCOL='docs/research/resilience_002_preregistration.md'


def source():
    return {**previous_source(),**{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ['learning/resilience_002.py','learning/resilience_002_agent.py','cognitive/functional_learning.py',
         'learning/resilience_002_analysis.py','tests/test_resilience_002.py',PROTOCOL]}}


def create_manifest(path,bank='dev',count=6,variant='v1'):
    path=Path(path)
    if path.exists(): raise ValueError('manifest already exists')
    namespace=f'resilience-002/{bank}/{variant}'
    labels=['body','initialization','batches','selection','continuous_execution','schedule']
    labels += [f'command/{t}' for t in range(52)]
    labels += [f'choice/{p}/{t}/{i}' for p in PHASES for t in ['0','6','final'] for i in range(12)]
    lives={f'life-{i:02d}':{label:seed(namespace,f'life-{i:02d}',label) for label in labels} for i in range(count)}
    values=[v for life in lives.values() for v in life.values()]
    prior=set()
    def collect(x):
        if isinstance(x,dict):
            for value in x.values(): collect(value)
        elif isinstance(x,list):
            for value in x: collect(value)
        elif isinstance(x,int) and x>100000: prior.add(x)
    paths=set((ROOT/'docs/research').glob('*manifest*.json'))
    paths.update((ROOT/'docs/research').glob('cumulative_001_*v1.json'))
    for old in paths: collect(json.loads(old.read_bytes()))
    if min(values)<=100000 or len(set(values))!=len(values) or set(values)&prior: raise ValueError('seed collision')
    manifest={'namespace':namespace,'bank':bank,'variant':variant,'lives':lives,'source':source(),
              'protocol':PROTOCOL,'seed_count':len(values),'prior_numeric_inventory':len(prior),'collision_count':0,
              'analysis_convention':{'post_learning':'checkpoints 6 and final in all three phases',
                                     'post_rupture_utility':'mean of perturbed checkpoints 6 and final',
                                     'oracle_fraction':'mean utility / mean oracle utility per checkpoint',
                                     'independent_unit':'life'},'created_date':'2026-09-10'}
    path.write_bytes(canonical(manifest)); print('Manifest frozen',path,digest(manifest),flush=True)


def situation(org,start,horizon,execution_seed,agents):
    env,o=prepare(org,start,execution_seed); env.close()
    candidates=sorted({o.angle+s*d for s in [-1,1] for d in [5,10,15,20,30,40,50,60] if 30<=o.angle+s*d<=150})
    obs=[replace(o,target=c) for c in candidates]
    predictions={p:a.predict(obs,[horizon]*len(obs)).tolist() for p,a in agents.items()}
    margins={p:a.margin() for p,a in agents.items()}; choices={}; promises={}
    for p,predicted in predictions.items():
        feasible=[i for i,c in enumerate(candidates) if abs(predicted[i]-c)+margins[p]<=2]
        promises[p]=bool(feasible)
        choices[p]=min(feasible,key=lambda i:(-abs(candidates[i]-o.angle),candidates[i]<o.angle,candidates[i])) if feasible else min(
            range(len(candidates)),key=lambda i:(abs(candidates[i]-o.angle),candidates[i]<o.angle,candidates[i]))
    # No future is opened until ALL policy choices are fixed. No judge result enters agents.
    observed=[]
    for c in candidates:
        env,check=prepare(org,start,execution_seed)
        try:
            if check!=o: raise ValueError('counterfactual preparation mismatch')
            trace=[env.step(c).as5600_deg for _ in range(horizon)]
            observed.append(trace[-1])
        finally: env.close()
    rewards=[abs(c-o.angle) if abs(y-c)<=2 else 0. for c,y in zip(candidates,observed)]
    return {'start':start,'horizon':horizon,'observation':asdict(o),'candidates':candidates,
            'predictions':predictions,'margins':margins,'observed_terminal':observed,'oracle_utility':max(rewards),
            'scores':{p:{'chosen':candidates[i],'predicted':predictions[p][i],'promised':promises[p],
                         'success':abs(observed[i]-candidates[i])<=2,'utility':rewards[i],
                         'terminal_mae':float(np.mean(abs(np.array(predictions[p])-observed)))} for p,i in choices.items()}}


def lived_trial(env,history,value,agent,decision):
    rng=np.random.default_rng(value); episodes=[]
    angle,delta,previous,previous_delta=history
    def move(target):
        nonlocal angle,delta,previous,previous_delta
        actual=env.step(target).as5600_deg
        angle,delta,previous_delta,previous=actual,actual-angle,target-previous,target
        return actual
    low,high=[(5,15),(15,30),(30,60)][decision['band']]
    for _ in range(4):
        start=float(rng.uniform(75,105)); fraction=float(rng.random()); sign=int(rng.choice([-1,1])); horizon=int(rng.choice([4,6,8]))
        for _ in range(24): move(start)
        distance=low+(high-low)*fraction; target=angle+sign*distance
        if not 30<=target<=150: target=angle-sign*distance
        if not 30<=target<=150: raise ValueError('catalog outside physical range')
        o=Observation(angle,delta,previous,target,previous_delta)
        announcement=agent.announce(o,horizon)
        angles=[move(target) for _ in range(8)]
        episodes.append({'observation':asdict(o),'band':decision['band'],'horizon':horizon,
                         'announcement':announcement,'angles':angles})
    return episodes,(angle,delta,previous,previous_delta)


def branch_probe(a,episodes):
    result={'state':state_digest(a.state()),'decision':a.select()}
    a.update(episodes); result['next_state']=state_digest(a.state())
    return result


def probe(request,response):
    p=json.loads(Path(request).read_bytes())
    with CognitiveKernel(p['database']) as kernel:
        store=FunctionalStore(kernel,p['artifacts'],p['run_id'],p['contract'])
        result=branch_probe(store.load(),p['episodes'])
    Path(response).write_bytes(canonical(result))


def run_life(name,seeds,manifest,destination):
    if destination.exists(): raise ValueError('exposed life cannot be overwritten')
    destination.mkdir(parents=True); started=time.monotonic()
    rng=np.random.default_rng(seeds['body'])
    base=Life010Organism(seed=seeds['body'],regime='combined',max_speed_deg_s=float(rng.uniform(420,720)),
                         position_gain=float(rng.uniform(8,12)),velocity_damping=float(rng.uniform(.1,.2)))
    changed=replace(base,max_speed_deg_s=float(rng.uniform(90,240))); bodies=[base,changed,base]
    rng=np.random.default_rng(seeds['schedule']); lengths=[int(rng.integers(14,19)),int(rng.integers(14,19)),16]
    agents={p:FunctionalAgent(seeds['initialization'],seeds['batches'],seeds['selection'],p) for p in POLICIES}
    envs={p:BenchHeadEnv(life010_bench_config(base,seeds['continuous_execution'])) for p in POLICIES}
    history={p:(90.,0.,90.,0.) for p in POLICIES}
    database=destination/'kernel.sqlite'; artifacts=destination/'artifacts'; contract=digest({'manifest':digest(manifest),'life':name})
    kernel=CognitiveKernel(database); store=FunctionalStore(kernel,artifacts,name,contract)
    agents['need']=store.initialize(agents['need'])
    checkpoints=[]; training=[]; witnesses=[]; restart=None; absolute=0
    try:
        for phase,org,length in zip(PHASES,bodies,lengths):
            for p,env in envs.items():
                assert env.step_count==absolute*128
                witnesses.append({'phase':phase,'policy':p,'steps':env.step_count,'time':env.time,'angle':history[p][0],
                                  'speed':org.max_speed_deg_s})
                env.config.servo.max_speed_deg_s=org.max_speed_deg_s
            def checkpoint(label):
                before={p:state_digest(a.state()) for p,a in agents.items()}
                cases=[situation(org,s,h,seeds[f'choice/{phase}/{label}/{i}'],agents)
                       for i,(s,h) in enumerate((s,h) for s in [55.,80.,100.,130.] for h in [4,6,8])]
                assert before=={p:state_digest(a.state()) for p,a in agents.items()},'judge mutated learner'
                path=destination/f'{phase}-{label}-choices.json'; path.write_bytes(canonical(cases))
                oracle=float(np.mean([c['oracle_utility'] for c in cases])); measures={}
                for p,a in agents.items():
                    utility=float(np.mean([c['scores'][p]['utility'] for c in cases]))
                    success=float(np.mean([c['scores'][p]['success'] for c in cases]))
                    fraction=utility/oracle if oracle>0 else None
                    measures[p]={'utility':utility,'success':success,'oracle_fraction':fraction,
                                 'terminal_mae':float(np.mean([c['scores'][p]['terminal_mae'] for c in cases])),
                                 'need_open':a.need_open,'closure_contradicted':not a.need_open and (success<.8 or fraction is None or fraction<.7),
                                 'margin':a.margin(),'promises':sum(c['scores'][p]['promised'] for c in cases)}
                checkpoints.append({'phase':phase,'label':label,'absolute_trial':absolute,'oracle_utility':oracle,'policies':measures})
            checkpoint('0')
            for t in range(length):
                record={'absolute':absolute,'phase':phase,'policies':{}}
                for p,a in agents.items():
                    if p=='need': a=store.load()
                    decision=a.select()
                    episodes,history[p]=lived_trial(envs[p],history[p],seeds[f'command/{absolute}'],a,decision)
                    if p=='need':
                        agents[p],event,applied=store.apply(str(absolute),decision,episodes); assert applied
                    else: event=a.update(episodes)
                    record['policies'][p]={'decision':decision,'episodes':episodes,'event':event}
                training.append(record); absolute+=1
                if phase=='perturbed' and t==1:
                    request=destination/'restart-request.json'; response=destination/'restart-response.json'
                    request.write_bytes(canonical({'database':str(database.resolve()),'artifacts':str(artifacts.resolve()),
                                                    'run_id':name,'contract':contract,'episodes':episodes}))
                    expected=branch_probe(store.load(),episodes)
                    physical_before={p:e.step_count for p,e in envs.items()}
                    kernel.close()
                    subprocess.run([sys.executable,'-m','learning.resilience_002','--probe',str(request),str(response)],check=True,timeout=90)
                    assert json.loads(response.read_bytes())==expected,'software restart mismatch'
                    assert physical_before=={p:e.step_count for p,e in envs.items()}
                    kernel=CognitiveKernel(database); store=FunctionalStore(kernel,artifacts,name,contract); agents['need']=store.load()
                    restart={'exact':True,'after_trial':absolute,'physical_steps':physical_before,
                             'scope':'complete state, next decision and next update on a noncommitted branch of already lived data'}
                if t+1==6: checkpoint('6')
            checkpoint('final')
            (destination/f'{phase}-progress.json').write_bytes(canonical(checkpoints))
            for p,a in agents.items(): torch.save(a.state(),destination/f'{phase}-{p}.pt')
            print(json.dumps({'life':name,'phase':phase,'checkpoint':checkpoints[-1]}),flush=True)
        (destination/'training.json').write_bytes(canonical(training))
        report={'life':name,'bank':manifest['bank'],'manifest':digest(manifest),'source':source(),'lengths':lengths,
                'bodies':[asdict(b) for b in bodies],'checkpoints':checkpoints,'phase_continuity':witnesses,'restart':restart,
                'events':{p:a.events for p,a in agents.items()},'decisions':{p:a.decisions for p,a in agents.items()},
                'updates':{p:a.total_updates for p,a in agents.items()},'physical_steps':{p:e.step_count for p,e in envs.items()},
                'final_state':{p:state_digest(a.state()) for p,a in agents.items()},'seconds':time.monotonic()-started}
        assert len(set(report['updates'].values()))==len(set(report['physical_steps'].values()))==1
        (destination/'report.json').write_bytes(canonical(report))
        print(json.dumps({'life':name,'seconds':report['seconds'],'restart':restart}),flush=True)
    finally:
        for env in envs.values(): env.close()
        kernel.close()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest'); p.add_argument('--create',action='store_true')
    p.add_argument('--bank',choices=['dev','validation'],default='dev'); p.add_argument('--variant',default='v1'); p.add_argument('--count',type=int,default=6)
    p.add_argument('--life',choices=['first','remaining','all'],default='first'); p.add_argument('--probe',nargs=2); a=p.parse_args()
    if a.probe: return probe(*a.probe)
    if a.create: return create_manifest(a.manifest,a.bank,a.count,a.variant)
    manifest=json.loads(Path(a.manifest).read_bytes())
    if manifest['source']!=source(): raise ValueError('source changed; new variant required')
    identities=list(manifest['lives'])
    if a.life=='first': identities=identities[:1]
    elif a.life=='remaining': identities=identities[1:]
    for name in identities: run_life(name,manifest['lives'][name],manifest,OUTPUT/manifest['bank']/manifest['variant']/name)


if __name__=='__main__': main()
