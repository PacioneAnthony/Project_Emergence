"""Whole-bank resilience summaries, with failures retained and life as unit."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from learning.body_schema_002 import canonical, digest
from learning.resilience_001 import KINDS, PHASES
from learning.cumulative_001_data import ROOT
from learning.resilience_001_budget import OUTPUT


def analyze(manifest_path):
    manifest = json.loads(Path(manifest_path).read_bytes())
    actual_source = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in manifest['source']}
    assert manifest['source'] == actual_source, 'source changed after freeze'
    folder = OUTPUT / manifest['bank'] / manifest['variant']
    reports = [json.loads((folder / name / 'report.json').read_bytes()) for name in manifest['lives']]
    for r in reports:
        assert r['manifest'] == digest(manifest) and r['source'] == actual_source
        assert r['restart']['bit_exact']
        assert [x['steps'] for x in r['phase_continuity']] == [0, 768, 1536]
        assert all(v == (768 if k == 'frozen' else 2304) for k, v in r['updates'].items())
    result = {'bank': manifest['bank'], 'lives': len(reports), 'phases': {}, 'per_life': {}, 'gates': {}}
    for phase in PHASES:
        result['phases'][phase] = {}
        for kind in KINDS:
            post = [[c for c in r['checkpoints'] if c['phase'] == phase and c['trial'] in [3, 6, 12]] for r in reports]
            final = [next(c for c in r['checkpoints'] if c['phase'] == phase and c['trial'] == 12) for r in reports]
            curves = [[c['mae'][kind] for c in r['checkpoints'] if c['phase'] == phase] for r in reports]
            result['phases'][phase][kind] = {
                'post_utility': float(np.mean([np.mean([c['behavior'][kind]['utility'] for c in cs]) for cs in post])),
                'post_success': float(np.mean([np.mean([c['behavior'][kind]['success'] for c in cs]) for cs in post])),
                'final_utility': float(np.mean([c['behavior'][kind]['utility'] for c in final])),
                'final_success': float(np.mean([c['behavior'][kind]['success'] for c in final])),
                'final_mae': float(np.mean([c['mae'][kind] for c in final])),
                'error_auc': float(np.mean([np.trapezoid(curve, dx=3) for curve in curves]))}
    for r in reports:
        post = [c for c in r['checkpoints'] if c['phase'] == 'perturbed' and c['trial'] in [3, 6, 12]]
        result['per_life'][r['life']] = {'delays': r['detection_delays'], 'false_alarms_initial': r['false_alarms_initial'],
            'goals_opened': sum(e['goal_opened'] for e in r['events']), 'goals_closed': sum(e['goal_closed'] for e in r['events']),
            'recalls': sum(e['response'] == 'recall' for e in r['events']), 'final_goal_open': r['final_subgoal_open'],
            'post_perturbation_utility': {k: float(np.mean([c['behavior'][k]['utility'] for c in post])) for k in KINDS}}
    a = result['phases']['perturbed']
    best = max(a[k]['post_utility'] for k in ['naive', 'replay', 'recent'])
    ratio = a['adaptive']['post_utility'] / a['frozen']['post_utility'] if a['frozen']['post_utility'] else None
    result['effects'] = {'utility_gain_vs_frozen': ratio - 1 if ratio is not None else None,
                         'utility_gain_vs_best_adaptive_baseline': a['adaptive']['post_utility'] / best - 1 if best else None}
    result['gates'] = {
        'detect_by_three': sum(r['detection_delays'][0] is not None and r['detection_delays'][0] <= 3 for r in reports) >= int(np.ceil(5 * len(reports) / 6)),
        'false_alarms': all(r['false_alarms_initial'] <= 1 for r in reports),
        'functional_gain_vs_frozen': a['adaptive']['post_utility'] >= 1.1 * a['frozen']['post_utility'] and a['adaptive']['post_utility'] > a['frozen']['post_utility'],
        'within_five_percent_best_adaptive': a['adaptive']['post_utility'] >= .95 * best,
        'restart': all(r['restart']['bit_exact'] for r in reports)}
    result['seconds'] = sum(r['seconds'] for r in reports)
    (folder / 'summary.json').write_bytes(canonical(result))
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--manifest', required=True)
    analyze(p.parse_args().manifest)
