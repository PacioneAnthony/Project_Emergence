"""Predeclared life-level cumulative statistics, no selection or model changes."""
import argparse,json
from pathlib import Path
import numpy as np
from learning.body_schema_002 import canonical
from learning.cumulative_001_data import OUTPUT
from learning.cumulative_001 import source
from learning.paired_stats import bca_bootstrap_ci


def summarize(manifest_path):
    m=json.loads(Path(manifest_path).read_bytes())
    if m.get('source_frozen',source())!=source(): raise ValueError('model/data source changed after freeze')
    reports=[json.loads((OUTPUT/m['bank']/m['variant']/identity.replace('/','-')/'report.json').read_bytes()) for identity in m['lives']]
    if len(reports)!=len(m['lives']): raise ValueError('incomplete bank')
    methods=['neural_naive','neural_replay','ridge_short','ridge_cumulative','prior']
    final=[{phase:next(x['scores'] for x in r['history'] if x['phase']==phase and x['trial']==12) for phase in ['A','B','A_return','C']} for r in reports]
    result={'bank':m['bank'],'lives':len(reports),'methods':{},'per_life':{}}
    for method in methods:
        errors=[float(np.mean([f['C'][method][d] for d in ['A','B','C']])) for f in final]
        forgetting=[r['forgetting_A_after_B'][method] for r in reports]
        result['methods'][method]={'final_ABC_mean_deg':float(np.mean(errors)),'final_C_mean_deg':float(np.mean([f['C'][method]['C'] for f in final])),
            'forgetting_A_after_B_mean_deg':float(np.mean(forgetting)),'forgetting_A_after_B_max_deg':max(forgetting),
            'forgetting_gt_point2_lives':sum(x>.2 for x in forgetting)}
    recovery=[]; acquired=[]; retained=[]
    for r,f in zip(reports,final):
        rec=r['recovery']['neural_replay']; gain=1-rec['mean_checkpoint_error']/rec['fresh_mean_checkpoint_error']; recovery.append(gain)
        acquisition=all(f[p]['neural_replay'][d]<=1 and f[p]['neural_replay'][d]<=.7*f[p]['prior'][d] for p,d in [('A','A'),('B','B'),('C','C')])
        retention=(f['B']['neural_replay']['A']<=f['A']['neural_replay']['A']+.2 and f['C']['neural_replay']['A']<=f['A']['neural_replay']['A']+.2 and f['C']['neural_replay']['B']<=f['B']['neural_replay']['B']+.2)
        acquired.append(acquisition); retained.append(retention)
        cumulative_curve=[x['scores']['neural_replay']['A'] for x in r['history'] if x['phase']=='A_return']
        fresh_curve=[x['scores']['fresh_replay']['A'] for x in r['fresh_history']]
        auc=float(np.trapezoid(cumulative_curve,dx=3)); fresh_auc=float(np.trapezoid(fresh_curve,dx=3))
        result['per_life'][r['life']]={'acquisition':acquisition,'retention':retention,'recovery_gain':gain,'recovery_auc':auc,'fresh_auc':fresh_auc,
            'restart':all(v['bit_exact'] for v in r['restart'].values())}
    result['recovery']={'mean_relative_gain':float(np.mean(recovery)),'favorable_lives':sum(x>0 for x in recovery),
        'mean_checkpoint_error':float(np.mean([r['recovery']['neural_replay']['mean_checkpoint_error'] for r in reports])),
        'fresh_mean_checkpoint_error':float(np.mean([r['recovery']['neural_replay']['fresh_mean_checkpoint_error'] for r in reports]))}
    n=len(reports)
    result['gates']={'acquisition':all(acquired),'retention':all(retained),'recovery':float(np.mean(recovery))>=.2 and sum(x>0 for x in recovery)>=int(np.ceil(.75*n)),
                     'restart':all(x['restart'] for x in result['per_life'].values())}
    result['paired_effects']={}
    for comparator,key in [('neural_naive','vs_naive'),('ridge_cumulative','vs_ridge')]:
        ref=np.array([np.mean([f['C'][comparator][d] for d in ['A','B','C']]) for f in final])
        chosen=np.array([np.mean([f['C']['neural_replay'][d] for d in ['A','B','C']]) for f in final])
        diffs=ref-chosen
        entry={'mean_advantage_deg':float(diffs.mean()),'relative_reduction_of_means':float(1-chosen.mean()/ref.mean()),'favorable_lives':int((diffs>0).sum())}
        if 'statistics' in m: entry['paired_difference_bca95']=list(bca_bootstrap_ci(diffs,n_boot=10000,seed=m['statistics'][key]))
        result['paired_effects'][key]=entry
    result['compute']={'life_wall_seconds':float(sum(r['seconds'] for r in reports)),
        'ridge_cpu_seconds':float(sum(r['cpu_ridge_seconds'] for r in reports)),
        'neural_cuda_event_seconds':{k:float(sum(r['neural_time'][k]['gpu_seconds'] for r in reports)) for k in ['neural_naive','neural_replay']},
        'gpu':reports[0]['gpu'],'maximum_torch_allocated_bytes':max(r['peak_gpu_allocated_bytes'] for r in reports)}
    p=OUTPUT/m['bank']/m['variant']/'summary.json'; p.write_bytes(canonical(result))
    print(json.dumps({k:v for k,v in result.items() if k!='per_life'},indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True)
    summarize(p.parse_args().manifest)
