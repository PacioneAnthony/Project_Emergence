"""Descriptive diagnostics only; no additional qualification or feedback to agents."""
import argparse
import json
from pathlib import Path
import numpy as np
from learning.body_schema_002 import canonical,digest
from learning.cumulative_001_data import ROOT
from learning.resilience_002_budget import OUTPUT


def diagnose(manifest_path):
    m=json.loads(Path(manifest_path).read_bytes()); folder=OUTPUT/m['bank']/m['variant']; lives={}
    for name in m['lives']:
        r=json.loads((folder/name/'report.json').read_bytes()); training=json.loads((folder/name/'training.json').read_bytes())
        checkpoints=r['checkpoints']; initial,changed,returned=r['lengths']; policies={}
        for p in ['cycle','uniform','need']:
            alarms=[e['trial'] for e in r['events'][p] if e['alarm']]
            groups={phase:[0,0,0] for phase in ['initial','perturbed','return']}
            for row in training: groups[row['phase']][row['policies'][p]['decision']['band']]+=1
            policies[p]={'initial_alarms':sum(t<=initial for t in alarms),'alarms':alarms,
                         'detection_delays':[min([t-boundary for t in alarms if boundary<t<=boundary+length],default=None)
                                            for boundary,length in [(initial,changed),(initial+changed,returned)]],
                         'choices_by_phase':groups,'recovery_seconds_simulated':changed*128*.02}
        post={p:float(np.mean([c['policies'][p]['utility'] for c in checkpoints if c['phase']=='perturbed' and c['label']!='0'])) for p in policies}
        lives[name]={'policies':policies,'speed_initial':r['bodies'][0]['max_speed_deg_s'],'speed_perturbed':r['bodies'][1]['max_speed_deg_s'],
                     'post_rupture_utility':post,'need_minus_cycle':post['need']-post['cycle']}
    curves={}
    for phase in ['initial','perturbed','return']:
        curves[phase]={}
        for label in ['0','6','final']:
            measures=[]
            for name in m['lives']:
                r=json.loads((folder/name/'report.json').read_bytes())
                measures.append(next(c for c in r['checkpoints'] if c['phase']==phase and c['label']==label))
            curves[phase][label]={p:{metric:float(np.mean([c['policies'][p][metric] for c in measures])) for metric in
                                     ['success','utility','oracle_fraction','terminal_mae']} for p in ['cycle','uniform','need']}
    differences=[v['need_minus_cycle'] for v in lives.values()]
    result={'manifest':digest(m),'status':'descriptive only; not used to alter any gate','per_life':lives,'curves':curves,
            'paired_life_comparison':{'need_better':sum(d>1e-9 for d in differences),'tie':sum(abs(d)<=1e-9 for d in differences),
                                      'need_worse':sum(d< -1e-9 for d in differences),'min_difference':min(differences),'max_difference':max(differences)}}
    path=ROOT/f'docs/research/resilience_002_{m["bank"]}_{m["variant"]}_diagnostics.json'; path.write_bytes(canonical(result))
    print(json.dumps({'paired_life_comparison':result['paired_life_comparison'],'perturbed_curves':curves['perturbed']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); diagnose(p.parse_args().manifest)
