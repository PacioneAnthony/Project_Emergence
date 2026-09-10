"""Independent accounting of stored experiences and all monitor checkpoints."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from learning.body_schema_002 import canonical,digest
from learning.cumulative_001_data import ROOT
from learning.resilience_002_budget import OUTPUT


def audit(manifest_path):
    m=json.loads(Path(manifest_path).read_bytes()); folder=OUTPUT/m['bank']/m['variant']
    closed={p:{'all_closed':0,'all_contradicted':0,'phase_zero_closed':0,'phase_zero_contradicted':0,
               'post_learning_closed':0,'post_learning_contradicted':0} for p in ['cycle','uniform','need']}
    details=[]; trials=0
    for name in m['lives']:
        r=json.loads((folder/name/'report.json').read_bytes()); training=json.loads((folder/name/'training.json').read_bytes())
        assert len(training)==sum(r['lengths'])
        with sqlite3.connect((folder/name/'kernel.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
            rows=db.execute('SELECT logical_id,content,cursor FROM resilience_experiences').fetchall()
            assert len(rows)==len(training)
            for logical,content,cursor in rows:
                t=training[int(logical)]['policies']['need']
                assert content==digest({'decision':t['decision'],'episodes':t['episodes']}) and cursor==int(logical)+1
        for policy in closed:
            assert r['updates'][policy]==len(training)*64 and r['physical_steps'][policy]==len(training)*128
            for i,t in enumerate(training):
                entry=t['policies'][policy]; assert entry['decision']['trial']==i and len(entry['episodes'])==4
                for episode in entry['episodes']:
                    assert len(episode['angles'])==8 and episode['band']==entry['decision']['band']
                    assert episode['horizon'] in [4,6,8] and 30<=episode['observation']['target']<=150
                    assert set(episode['observation'])=={'angle','delta','previous_target','target','previous_command_delta','dt'}
            for c in r['checkpoints']:
                metrics=c['policies'][policy]
                if not metrics['need_open']:
                    prefix='phase_zero' if c['label']=='0' else 'post_learning'
                    closed[policy]['all_closed']+=1; closed[policy][prefix+'_closed']+=1
                    if metrics['closure_contradicted']:
                        closed[policy]['all_contradicted']+=1; closed[policy][prefix+'_contradicted']+=1
                        details.append({'life':name,'policy':policy,'phase':c['phase'],'label':c['label'],
                                        'success':metrics['success'],'oracle_fraction':metrics['oracle_fraction']})
        trials+=len(training)
    for counts in closed.values():
        counts['all_contradiction_rate']=counts['all_contradicted']/counts['all_closed'] if counts['all_closed'] else None
        counts['strict_honesty_pass']=counts['all_contradiction_rate'] is not None and counts['all_contradiction_rate']<.1
    result={'manifest':digest(m),'life_count':len(m['lives']),'trials_per_policy':trials,'kernel_experiences_checked':trials,
            'equal_interaction_and_update_budgets':True,'causal_observation_schema_checked':True,'monitor_all_checkpoints':closed,
            'contradicted_checkpoints':details,'audit_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope_note':'Frozen analysis restricts honesty to post-learning checkpoints. This audit also reports phase 0, which the prose protocol did not explicitly exclude. No unconditional monitor qualification may rely on the restricted rate.'}
    path=ROOT/f'docs/research/resilience_002_{m["bank"]}_{m["variant"]}_audit.json'
    path.write_bytes(canonical(result)); print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True); audit(p.parse_args().manifest)
