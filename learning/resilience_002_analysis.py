"""Life-level analysis, fixed before opening RESILIENCE-002 outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from learning.body_schema_002 import canonical, digest
from learning.resilience_002_budget import OUTPUT
from learning.cumulative_001_data import ROOT


def analyze(manifest_path):
    m=json.loads(Path(manifest_path).read_bytes()); folder=OUTPUT/m['bank']/m['variant']
    reports={name:json.loads((folder/name/'report.json').read_bytes()) for name in m['lives']}
    for r in reports.values():
        if r['manifest']!=digest(m) or r['source']!=m['source']: raise ValueError('provenance mismatch')
        if not r['restart']['exact']: raise ValueError('restart failed')
    per_life={}; aggregate={}
    for name,r in reports.items():
        per_life[name]={}
        for policy in ['cycle','uniform','need']:
            learned=[c['policies'][policy] for c in r['checkpoints'] if c['label']!='0']
            closed=[c for c in learned if not c['need_open']]
            final=next(c['policies'][policy] for c in r['checkpoints'] if c['phase']=='perturbed' and c['label']=='final')
            post=[c['policies'][policy]['utility'] for c in r['checkpoints'] if c['phase']=='perturbed' and c['label']!='0']
            per_life[name][policy]={'closed':len(closed),'contradicted':sum(c['closure_contradicted'] for c in closed),
                                    'post_learning_count':len(learned),'final_success':final['success'],'final_oracle_fraction':final['oracle_fraction'],
                                    'post_rupture_utility':float(np.mean(post)),
                                    'alarms':sum(e['alarm'] for e in r['events'][policy]),
                                    'opened':sum(e['opened'] for e in r['events'][policy]),'closed_events':sum(e['closed'] for e in r['events'][policy])}
    for policy in ['cycle','uniform','need']:
        values=[r[policy] for r in per_life.values()]
        closed=sum(v['closed'] for v in values); contradicted=sum(v['contradicted'] for v in values)
        a={'closed':closed,'contradicted':contradicted,'contradiction_rate':contradicted/closed if closed else None,
           'closure_coverage':closed/sum(v['post_learning_count'] for v in values),
           'final_success':float(np.mean([v['final_success'] for v in values])),
           'worst_life_success':min(v['final_success'] for v in values),
           'final_oracle_fraction':float(np.mean([v['final_oracle_fraction'] for v in values])),
           'post_rupture_utility':float(np.mean([v['post_rupture_utility'] for v in values]))}
        a['gates']={'honesty':a['contradiction_rate'] is not None and a['contradiction_rate']<.1,
                    'closure_coverage':a['closure_coverage']>=.5,'mean_recovery':a['final_success']>=.9,
                    'worst_recovery':a['worst_life_success']>=.7,'functional_utility':a['final_oracle_fraction']>=.8}
        a['monitor_pass']=a['gates']['honesty'] and a['gates']['closure_coverage']
        a['recovery_pass']=all(a['gates'][g] for g in ['mean_recovery','worst_recovery','functional_utility'])
        aggregate[policy]=a
    cycle=aggregate['cycle']['post_rupture_utility']; active=aggregate['need']['post_rupture_utility']
    gain=active/cycle-1 if cycle>0 else None
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*'))
           if p.is_file() and p.suffix in ['.json','.pt']}
    output={'level':m['bank'],'variant':m['variant'],'manifest':digest(m),'source':m['source'],'aggregate':aggregate,
            'per_life':per_life,'active_gain_vs_cycle':gain,'active_selection_pass':gain is not None and gain>=.1,
            'exact_restarts':sum(r['restart']['exact'] for r in reports.values()),
            'interaction_steps':{p:sum(r['physical_steps'][p] for r in reports.values()) for p in aggregate},
            'updates':{p:sum(r['updates'][p] for r in reports.values()) for p in aggregate},'artifact_sha256':files,
            'heldout_cases':len(reports)*9*12,'policy_evaluations':len(reports)*9*12*3}
    target=ROOT/f'docs/research/resilience_002_{m["bank"]}_{m["variant"]}_results'
    target.with_suffix('.json').write_bytes(canonical(output))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.5)); colors={'cycle':'#5b7188','uniform':'#b89040','need':'#147d73'}
    for policy in aggregate:
        checkpoints=next(iter(reports.values()))['checkpoints']
        means=[np.mean([r['checkpoints'][i]['policies'][policy]['utility'] for r in reports.values()]) for i in range(9)]
        axes[0].plot(range(9),means,'o-',label=policy,color=colors[policy])
        axes[1].plot(range(len(reports)),[v[policy]['final_success']*100 for v in per_life.values()],'o-',label=policy,color=colors[policy])
    axes[0].set_xticks(range(9),['I0','I6','If','P0','P6','Pf','R0','R6','Rf']); axes[0].set_ylabel('Utilité moyenne (°)'); axes[0].set_title('Initial / perturbation / retour'); axes[0].legend()
    axes[1].axhline(70,color='red',ls=':',label='Seuil pire vie'); axes[1].set_ylim(-3,103); axes[1].set_title('Réussite finale après rupture'); axes[1].set_ylabel('% des 12 situations'); axes[1].set_xlabel('Vie de développement'); axes[1].legend()
    positions=np.arange(3); policies=list(aggregate)
    axes[2].bar(positions-.18,[aggregate[p]['closure_coverage']*100 for p in policies],.36,label='Besoin clos',color='#147d73')
    axes[2].bar(positions+.18,[(aggregate[p]['contradiction_rate'] or 0)*100 for p in policies],.36,label='Clôtures contredites*',color='#b85a55')
    axes[2].set_xticks(positions,policies); axes[2].set_ylim(0,103); axes[2].set_ylabel('%'); axes[2].set_title('Fonctionnement du moniteur'); axes[2].legend(fontsize=8)
    fig.suptitle(f'RESILIENCE-002 {m["variant"]} — {len(reports)} vies ({m["bank"]})',fontweight='bold')
    fig.text(.5,.01,'* Dénominateur : checkpoints clos ; sans clôture, le taux est indéfini (barre à zéro).',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.045,1,.95]); fig.savefig(target.with_suffix('.png'),dpi=160); plt.close(fig)
    print(json.dumps({k:v for k,v in output.items() if k not in ['source','artifact_sha256','per_life']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); analyze(p.parse_args().manifest)
