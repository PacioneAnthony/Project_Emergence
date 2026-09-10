"""Audit persisted resilience evidence and create a standalone research figure."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cognitive.kernel import CognitiveKernel
from cognitive.resilience import ResilienceStore
from learning.body_schema_002 import canonical, digest
from learning.cumulative_001_data import ROOT
from learning.resilience_001 import KINDS, PHASES
from learning.resilience_001_agent import state_digest
from learning.resilience_001_budget import OUTPUT


def publish(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest['source'] == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in manifest['source']}
    store_class = ResilienceStore
    if manifest['variant'] == 'v3':
        from cognitive.resilience_plastic import PlasticResilienceStore
        store_class = PlasticResilienceStore
    folder = OUTPUT / manifest['bank'] / manifest['variant']
    summary = json.loads((folder / 'summary.json').read_bytes())
    reports = []; hashes = {}; count = 0
    def record(p): hashes[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    record(manifest_path); record(folder / 'summary.json')
    for name in manifest['lives']:
        life = folder / name
        r = json.loads((life / 'report.json').read_bytes())
        contract = digest({'manifest': digest(manifest), 'life': name})
        with CognitiveKernel(life / 'kernel.sqlite') as kernel:
            store = store_class(kernel, life / 'artifacts', name, contract)
            a = store.load()
            assert state_digest(a.state()) == r['final_state_digest']
            assert a.trials == 36
            assert len(a.archives) <= 6 and len(a.learner.memory_x) <= 256
            assert kernel.memory.connection.execute('SELECT count(*) FROM resilience_experiences').fetchone()[0] == 36
            assert kernel.memory.validated_model('resilience/' + name) is None
            record(Path(store._state()['artifact']))
        training = json.loads((life / 'training.json').read_bytes())
        seen_commands, seen_angles = set(), set()
        corpus = [t['rows'] for t in training]
        for phase in PHASES:
            evaluation_path = life / (phase + '-evaluation.json')
            evaluation = json.loads(evaluation_path.read_bytes())
            corpus.extend([evaluation[i:i+64] for i in range(0, len(evaluation), 64)])
            record(evaluation_path)
        for trial in corpus:
            assert len(trial) == 64
            for seen, values in [(seen_commands, [r['observation']['target'] for r in trial]),
                                 (seen_angles, [trial[0]['observation']['angle']] + [r['next_angle'] for r in trial])]:
                fingerprint = digest(values)
                assert fingerprint not in seen, 'duplicate complete training/evaluation trajectory'
                seen.add(fingerprint)
        for before, after in zip(training, training[1:]):
            assert before['rows'][-1]['next_angle'] == after['rows'][0]['observation']['angle']
        for c in r['checkpoints']:
            if 'behavior' not in c: continue
            path = life / f"{c['phase']}-{c['trial']}-choices.json"
            cases = json.loads(path.read_bytes())
            assert len(cases) == 12
            for case in cases:
                rewards = [abs(t - case['initial_observation']['angle']) if abs(t-y) <= 2 else 0.
                           for t,y in zip(case['candidates'], case['observed_terminal'])]
                assert max(rewards) == case['oracle_utility_deg']
                for kind, score in case['scores'].items():
                    i = case['candidates'].index(score['chosen'])
                    assert score['utility_deg'] == rewards[i]
                    assert score['success'] == (abs(score['chosen'] - case['observed_terminal'][i]) <= 2)
                    assert score['regret_deg'] == max(rewards) - rewards[i]
            for kind in KINDS:
                for field, raw in [('utility', 'utility_deg'), ('success', 'success'), ('regret', 'regret_deg')]:
                    assert np.isclose(c['behavior'][kind][field], np.mean([case['scores'][kind][raw] for case in cases]))
            count += len(cases)
            record(path)
        record(life / 'report.json'); record(life / 'training.json')
        reports.append(r)
    for filename in manifest['source']: record(ROOT / filename)
    with sqlite3.connect(OUTPUT / 'budget.sqlite') as db:
        budget = [dict(zip(['category','status','count','seconds'], row)) for row in db.execute('SELECT category,status,count(*),sum(charged) FROM attempts GROUP BY category,status')]
    output = ROOT / 'docs/research' / ('resilience_001_' + manifest['bank'] + '_' + manifest['variant'] + '_results')
    output.with_suffix('.json').write_bytes(canonical({'summary': summary, 'sha256': hashes, 'audited_behavior_situations': count,
                                                     'budget_snapshot_includes_current_reservation': budget}))
    colors = {'adaptive': '#147e67', 'recent': '#3888bd', 'replay': '#c48534', 'naive': '#9461a7', 'frozen': '#888888'}
    labels = {'adaptive': 'Superviseur + archives', 'recent': 'Mémoire récente', 'replay': 'Rejeu cumulatif', 'naive': 'Sans rejeu', 'frozen': 'Modèle figé'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    for kind in KINDS:
        for panel in range(2):
            curves = []
            for r in reports:
                cs = [c for c in r['checkpoints'] if panel == 1 or 'behavior' in c]
                x = [PHASES.index(c['phase']) * 12 + c['trial'] for c in cs]
                curves.append([c['mae'][kind] if panel == 1 else c['behavior'][kind]['utility'] / c['oracle_utility'] for c in cs])
            axes[panel].plot(x, np.mean(curves, axis=0), label=labels[kind], color=colors[kind], linewidth=2)
    for ax in axes:
        ax.axvline(12, color='#777', linestyle=':', linewidth=1)
        ax.axvline(24, color='#777', linestyle=':', linewidth=1)
        ax.set_xlabel('Essais successifs · rupture à 12 · retour à 24')
        ax.set_xticks([0, 6, 12, 18, 24, 30, 36])
        ax.grid(axis='y', alpha=.15)
    axes[0].set(title='Fonctionnement après changement', ylabel="Fraction de l'utilité atteignable (oracle du juge)", ylim=(0, 1.06))
    axes[0].legend(loc='lower right', fontsize=8)
    axes[1].set(title='Diagnostic prédictif secondaire', ylabel='Erreur à un pas (°)', ylim=(0, None))
    fig.suptitle(f"RESILIENCE-001 · {manifest['bank']} {manifest['variant']} · {len(reports)} vies", fontsize=15)
    fig.savefig(output.with_suffix('.png'), dpi=170)
    plt.close(fig)
    print(json.dumps({'verified_files': len(hashes), 'situations': count, 'gates': summary['gates'], 'output': str(output)}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--manifest',required=True)
    publish(p.parse_args().manifest)
