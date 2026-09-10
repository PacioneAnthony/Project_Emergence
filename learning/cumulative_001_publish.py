"""Verify saved evidence and render the final report without rerunning experiments."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from learning.body_schema_002 import canonical, digest
from learning.cumulative_001 import source
from learning.cumulative_001_data import ROOT, OUTPUT


def read(path):
    return json.loads(path.read_bytes())


def publish():
    docs = ROOT / 'docs/research'
    inventory = {}

    def record(path):
        inventory[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()

    banks = {}
    for bank in ['dev', 'validation']:
        manifest_path = docs / f'cumulative_001_{bank}_v1.json'
        manifest = read(manifest_path)
        record(manifest_path)
        if 'source_frozen' in manifest:
            assert manifest['source_frozen'] == source(), 'frozen source changed'
        folder = OUTPUT / bank / 'v1'
        reports = []
        for identity in manifest['lives']:
            life = folder / identity.replace('/', '-')
            report = read(life / 'report.json')
            assert report['manifest'] == digest(manifest)
            assert report['source'] == source()
            for name, receipt in report['restart'].items():
                checkpoint = life / 'B' / (name + '.pt')
                assert receipt['bit_exact']
                assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == receipt['checkpoint_sha256']
                record(checkpoint)
            for name in ['neural_naive', 'neural_replay']:
                record(life / 'C' / (name + '.pt'))
                assert report['neural_counters'][name]['updates'] == 48 * 64
                assert report['neural_counters'][name]['trials'] == 48
            record(life / 'report.json')
            record(life / 'C/ridge.json')
            reports.append(report)
        banks[bank] = {'summary': read(folder / 'summary.json'), 'reports': reports}
        record(folder / 'summary.json')

    controls = {}
    for variant, bank in [('v2', 'dev'), ('validation_v1', 'validation')]:
        folder = OUTPUT / 'control' / variant
        manifest = read(folder / 'manifest.json')
        assert manifest['base_digest'] == digest(read(docs / f'cumulative_001_{bank}_v1.json'))
        assert manifest['source_sha256'] == hashlib.sha256((ROOT / 'learning/cumulative_001_choice.py').read_bytes()).hexdigest()
        summary = read(folder / 'summary.json')
        for identity, life_scores in summary['per_life'].items():
            path = folder / (identity.replace('/', '-') + '.json')
            situations = read(path)
            assert len(situations) == len(manifest['starts']) * len(manifest['horizons'])
            for situation in situations:
                candidates = situation['candidates']
                observed = situation['observed_terminal']
                angle = situation['initial_observation']['angle']
                rewards = [abs(c - angle) if abs(c - y) <= 2 else 0. for c, y in zip(candidates, observed)]
                assert max(rewards) == situation['oracle_utility_deg']
                for name, score in situation['scores'].items():
                    index = candidates.index(score['chosen'])
                    assert score['success'] == (abs(candidates[index] - observed[index]) <= 2)
                    assert score['utility_deg'] == rewards[index]
                    assert score['regret_deg'] == max(rewards) - rewards[index]
            for name, score in life_scores.items():
                if name == 'oracle':
                    assert np.isclose(score['utility_deg'], np.mean([s['oracle_utility_deg'] for s in situations]))
                else:
                    for field, key in [('utility_deg', 'utility_deg'), ('success_rate', 'success'), ('regret_deg', 'regret_deg')]:
                        assert np.isclose(score[field], np.mean([s['scores'][name][key] for s in situations]))
            record(path)
        for name, score in summary['aggregate'].items():
            for field, value in score.items():
                assert np.isclose(value, np.mean([life[name][field] for life in summary['per_life'].values()]))
        controls[variant] = summary
        record(folder / 'manifest.json')
        record(folder / 'summary.json')

    old = docs / 'body_schema_002_validation_manifest.json'
    assert hashlib.sha256(old.read_bytes()).hexdigest() == '97edbe58fdeed02c861614eb5d5147d0872dd20d89efba8d8d59b282165f9647'
    archive = docs / 'body_schema_002_proposal_20260727.md'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == '20f95a967d07da65eaae3a7c4b37a2f7df441cd996efcc7543aee5493d4225c3'
    for path in source():
        record(ROOT / path)
    result = {'development': banks['dev']['summary'], 'validation': banks['validation']['summary'],
              'choice_development': controls['v2'], 'choice_validation': controls['validation_v1'],
              'control_v1_failure': read(OUTPUT / 'control/v1/summary.json'), 'verified_sha256': inventory}
    (docs / 'cumulative_001_results.json').write_bytes(canonical(result))

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), layout='constrained')
    colors = ['#b4bbc5', '#d48a37', '#2784b5', '#188166']
    methods = ['prior', 'ridge_cumulative', 'neural_naive', 'neural_replay']
    labels = ['Prior', 'Ridge\ncumulative', 'Réseau\nsans rejeu', 'Réseau\navec rejeu']
    val = banks['validation']['summary']
    values = [val['methods'][m]['final_ABC_mean_deg'] for m in methods]
    bars = axes[0].bar(labels, values, color=colors)
    axes[0].bar_label(bars, fmt='%.3f', padding=4)
    axes[0].set(title='Prédiction après A → B → A → C', ylabel='Erreur moyenne A/B/C (°)', ylim=(0, 1.1))
    for key, fresh, label, color in [('neural_replay', False, 'Mémoire conservée', colors[-1]), ('fresh_replay', True, 'Réseau neuf, même rejeu', colors[1])]:
        curves = [[x['scores'][key]['A'] for x in (r['fresh_history'] if fresh else r['history']) if fresh or x['phase'] == 'A_return'] for r in banks['validation']['reports']]
        axes[1].plot([0, 3, 6, 9, 12], np.mean(curves, axis=0), marker='o', label=label, color=color)
    axes[1].set(title='Retour dans le domaine A', xlabel='Nouveaux essais', ylabel='Erreur sur A (°)', ylim=(0, None))
    axes[1].legend(fontsize=9)
    choice = controls['validation_v1']['aggregate']
    names = ['prior', 'cautious_prior', 'ridge', 'neural']
    bars = axes[2].bar(['Prior', 'Prior\nprudent', 'Ridge', 'Réseau\navec rejeu'], [choice[m]['utility_deg'] for m in names], color=colors)
    axes[2].bar_label(bars, labels=[f"{choice[m]['utility_deg']:.1f}°\n{choice[m]['success_rate']:.1%}" for m in names], padding=4)
    axes[2].axhline(choice['oracle']['utility_deg'], color='#555', linestyle=':', label='Oracle (juge uniquement)')
    axes[2].set(title='Choix avant échéance · 192 situations', ylabel='Distance atteinte utile moyenne (°)', ylim=(0, 64))
    axes[2].legend(loc='upper left', fontsize=8)
    fig.suptitle('CUMULATIVE-001 · validation sur 12 corps simulés distincts', fontsize=15)
    fig.savefig(docs / 'cumulative_001_progress.png', dpi=170)
    plt.close(fig)
    print(json.dumps({'verified_files': len(inventory), 'validation_lives': len(banks['validation']['reports']),
                      'choice_gates': controls['validation_v1']['gates'], 'artifacts': ['cumulative_001_results.json', 'cumulative_001_progress.png']}))


if __name__ == '__main__':
    publish()
