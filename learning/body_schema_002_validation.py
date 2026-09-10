"""Freeze/read-once validation and explicit development activation for BODY r2.

This driver never changes the model recipe, and never opens confirmation banks.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

from learning import body_schema_002_experiment as experiment
from learning.body_schema_002 import Observation,canonical,digest
from cognitive.kernel import CognitiveKernel
from cognitive.body_forecast import BodyForecastStore

ROOT=experiment.ROOT
DEV=ROOT/'data/processed/experiments/body_schema_002_r2_dev_v2'
VALID=ROOT/'data/processed/experiments/body_schema_002_r2_validation_v1'
FROZEN=ROOT/'docs/research/body_schema_002_validation_manifest.json'
SELF=Path(__file__)


def current_tests():
    source=experiment.source_receipt()
    receipts={}
    for name in ['contracts_receipt.json','full_suite_receipt.json']:
        p=experiment.BUDGET_ROOT/name; receipt=json.loads(p.read_bytes())
        if receipt['source']!=source or receipt['exit_code']!=0 or receipt['timeout']:
            raise ValueError('current implementation lacks reception evidence')
        receipts[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    return source,receipts


def development_reports():
    manifest=json.loads(experiment.MANIFEST.read_bytes())
    reports=[json.loads((DEV/key.replace('/','-')/'report.json').read_bytes()) for key in manifest['seeds']]
    if len(reports)!=6 or any(not r['integrity_passed'] for r in reports): raise ValueError('incomplete development')
    return reports


def observed_timescales():
    """63.2% requested step response, only uninterrupted holds >=5 transitions.

    This describes the observed response, including rate limiting; not a fitted
    physical time constant. Unreached responses are explicitly right-censored.
    """
    result={}
    for folder in sorted(DEV.iterdir()):
        if not folder.is_dir(): continue
        trials=json.loads((folder/'trials.json').read_bytes()); hits=[]; censored=0
        for rows in trials.values():
            start=0
            while start<len(rows):
                target=rows[start]['observation']['target']; stop=start+1
                while stop<len(rows) and rows[stop]['observation']['target']==target: stop+=1
                initial=rows[start]['observation']['angle']; gap=target-initial
                if stop-start>=5 and abs(gap)>=15:
                    crossing=next((i for i in range(start,stop) if (rows[i]['next_angle']-initial)/gap>=.632),None)
                    if crossing is None: censored+=1
                    else: hits.append((crossing-start+1)*.02)
                start=stop
        result[folder.name]={'observed_63pct_median_seconds':float(np.median(hits)) if hits else None,
                             'reached':len(hits),'right_censored':censored}
    return result


def freeze():
    if FROZEN.exists(): raise ValueError('validation freeze is immutable; do not replace after exposure')
    source,receipts=current_tests(); reports=development_reports()
    base=json.loads(experiment.MANIFEST.read_bytes())
    comparison={k:float(np.mean([r['metrics'][k]['horizons']['1']['mae_deg'] for r in reports])) for k in ['B3','B13']}
    selected=min(comparison,key=comparison.get)
    namespace='body-schema-002-r2/validation/v1'
    def seed(*parts):
        return int.from_bytes(hashlib.sha256(json.dumps([namespace,*parts],separators=(',',':'),ensure_ascii=False).encode()).digest()[:4],'big')
    seeds={}
    for regime in ['speed_dominant','settling_dominant','friction_dominant']:
        for index in range(2):
            key=f'{regime}/{index}'
            seeds[key]={'organism':seed('organism',key),'bootstrap':seed('bootstrap',key),
                        'execution':{f'{motif}-{i:02d}':seed('execution',key,motif,i) for motif in ['impulse','reversal','micro'] for i in range(16)}}
    values=[v for s in seeds.values() for v in [s['organism'],s['bootstrap'],*s['execution'].values()]]
    old=[v for s in base['seeds'].values() for v in [s['organism'],s['bootstrap'],*s['execution'].values()]]
    import re
    inventory=set(old)
    for folder in ['learning','scripts','tests','docs/research']:
        for path in (ROOT/folder).rglob('*'):
            if path.suffix in ('.md','.py','.json'):
                inventory.update(int(x) for x in re.findall(r'(?<![\w.])\d{4,10}(?![\w.])',path.read_text(encoding='utf-8',errors='replace')))
    if len(set(values))!=300 or min(values)<=100000 or set(values)&inventory: raise ValueError('validation provenance collision')
    manifest=copy.deepcopy(base)
    manifest.update(phase='configuration_validation',variant='body-schema-002-r2-validation-v1',namespace=namespace,seeds=seeds,
        output_directory=VALID.name,source_frozen=source,tests_frozen=receipts,
        driver_sha256=hashlib.sha256(SELF.read_bytes()).hexdigest(),frozen_at_ns=time.time_ns(),
        initialization='fresh learner per organism; no inherited coefficients; only own training/selection/calibration roles',
        primary_without_action=selected,development_baseline_comparison=comparison,
        observed_timescales=observed_timescales(),
        horizon_reason='Keep 5/25 transitions to sample observed response and accumulated error; 25-step evaluated on eight origins; no control-success claim.',
        qualification={'one_step':{'max_mae_deg':1.,'relative_gain_vs_prior_min':.15,'relative_gain_vs_selected_without_action_min':.15,'all_six_required':True},
                       'rollout':{'max_terminal_mae_deg':2.,'horizons':[5,25],'must_beat_persistence_each_organism':True},
                       'persistence':{'bit_exact_predictions_and_next_update':True},
                       'calibration':'not_evaluated','agency':'not_evaluated'},
        threshold_reason='Engineering targets fixed before validation: one degree at next step, two degrees after 0.1/0.5s; not physical safety tolerances. Relative gain 15% follows development contract.',
        validation_policy='Single full bank; scientific failures retained; no selective replacement. Any recipe change reclassifies all six as development.',
        confirmation='forbidden',budget={'shared_ledger':str(experiment.BUDGET_ROOT/'budget.sqlite'),'invocation_seconds':900,'iteration_seconds':3600})
    # Keep validation provenance distinct; no inherited statement that it is closed.
    manifest.pop('variant_change',None); manifest.pop('validation',None)
    FROZEN.write_bytes(canonical(manifest))
    print(json.dumps({'frozen':str(FROZEN),'sha256':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),'selected_without_action':selected,'development_means':comparison,'timescales':manifest['observed_timescales']},indent=2))


def run_validation():
    manifest=json.loads(FROZEN.read_bytes()); source,receipts=current_tests()
    if source!=manifest['source_frozen'] or receipts!=manifest['tests_frozen'] or hashlib.sha256(SELF.read_bytes()).hexdigest()!=manifest['driver_sha256']:
        raise ValueError('code or reception changed since validation freeze')
    if manifest['phase']!='configuration_validation' or manifest['namespace']!='body-schema-002-r2/validation/v1': raise ValueError('unexpected bank')
    if VALID.exists(): raise ValueError('validation already exposed; no implicit repeat or selection')
    VALID.mkdir(parents=True)
    (VALID/'exposure.json').write_bytes(canonical({'manifest_sha256':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),'started_at_ns':time.time_ns()}))
    receipt={**source,'validation_manifest':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),'driver':manifest['driver_sha256']}
    experiment.OUTPUT=VALID
    reports=[]
    for identity,seed_map in manifest['seeds'].items():
        print('Validation',identity,flush=True)
        report=experiment.run_one(identity,seed_map,manifest,receipt)
        report['level']='configuration_validation'
        f=report['metrics']['F']['horizons']; prior=report['metrics']['B1']['horizons']['1']['mae_deg']
        baseline=report['metrics'][manifest['primary_without_action']]['horizons']['1']['mae_deg']
        one=f['1']['mae_deg']<=1 and f['1']['mae_deg']<=.85*prior and f['1']['mae_deg']<=.85*baseline
        multi=all(f[str(h)]['mae_deg']<=2 and f[str(h)]['mae_deg']<report['metrics']['B0']['horizons'][str(h)]['mae_deg'] for h in [5,25])
        report['frozen_capability_gates']={'one_step':one,'rollout':multi,'persistence':all(p['passed'] for p in report['persistence'].values())}
        (VALID/identity.replace('/','-')/'report.json').write_bytes(canonical(report))
        reports.append(report)
        print(json.dumps({'organism':identity,'F_one_step':f['1']['mae_deg'],'F_25':f['25']['mae_deg'],'gates':report['frozen_capability_gates']}),flush=True)
    summary={'level':'configuration_validation','manifest_sha256':hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
             'passed':{k:all(r['frozen_capability_gates'][k] for r in reports) for k in ['one_step','rollout','persistence']},
             'organisms':[r['organism'] for r in reports],'calibration':'not_qualified','agency':'not_qualified','confirmation':'not_opened'}
    (VALID/'summary.json').write_bytes(canonical(summary)); print(json.dumps(summary,indent=2))


def serving_probe(request_path,response_path):
    request=json.loads(Path(request_path).read_bytes())
    with CognitiveKernel(request['database']) as kernel:
        store=BodyForecastStore(kernel,request['artifacts'],request['run'],request['contract'])
        response={'prediction':store.active_prediction(Observation(**request['observation'])),'capabilities':store.capabilities()}
    Path(response_path).write_bytes(canonical(response))


def activate_development():
    source,receipts=current_tests(); reports=development_reports(); manifest=json.loads(experiment.MANIFEST.read_bytes())
    contract=digest(source); result=[]
    for report in reports:
        if report['contract']!=contract or not report['F_usage_passed'] or not report['persistence']['F']['passed']:
            raise ValueError('development package not eligible')
        identity=report['organism']; folder=DEV/identity.replace('/','-'); run=manifest['variant']+'/'+identity+'/F'
        database=folder/'F.sqlite'; artifacts=folder/'F-artifacts'
        with CognitiveKernel(database) as kernel:
            store=BodyForecastStore(kernel,artifacts,run,contract); model=store.load().active
            evidence={'model_version':model.version,'level':'development','usage_passed':True,'reception_passed':True,
                      'report_digest':hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),'reception_receipts':receipts,
                      'dependency':'F mean only; no calibration or agency inherited','activation_driver':hashlib.sha256(SELF.read_bytes()).hexdigest()}
            package=store.activate(evidence)
            o=Observation(90.,0.,90.,120.,0.)
            expected={'prediction':store.active_prediction(o),'capabilities':store.capabilities()}
        request={'database':str(database),'artifacts':str(artifacts),'run':run,'contract':contract,'observation':o.__dict__}
        request_path=folder/'serving-request.json'; response_path=folder/'serving-result.json'; request_path.write_bytes(canonical(request))
        subprocess.run([sys.executable,'-m','learning.body_schema_002_validation','--serving-probe',str(request_path),str(response_path)],check=True,timeout=30)
        if json.loads(response_path.read_bytes())!=expected: raise ValueError('active serving restart mismatch')
        result.append({'organism':identity,'package':package,'serving_restart_exact':True,'level':'development'})
    (DEV/'activation_receipt.json').write_bytes(canonical(result)); print(json.dumps(result,indent=2))


def main():
    p=argparse.ArgumentParser(); p.add_argument('mode',nargs='?',choices=['freeze','run','activate-development']); p.add_argument('--serving-probe',nargs=2)
    args=p.parse_args()
    if args.serving_probe: return serving_probe(*args.serving_probe)
    if args.mode=='freeze': freeze()
    elif args.mode=='run': run_validation()
    elif args.mode=='activate-development': activate_development()
    else: p.error('mode required')


if __name__=='__main__': main()
