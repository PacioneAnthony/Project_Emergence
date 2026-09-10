"""Continuous-body perturbation bench, separated from observation-only learners."""
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
from cognitive.resilience_plastic import PlasticResilienceStore as ResilienceStore
from learning.body_schema_002 import Observation, TrainingRow, canonical, digest
from learning.cumulative_001_data import ROOT, seed
from learning.cumulative_001_choice import situation
from learning.cumulative_001 import source as cumulative_source
from learning.life_010 import Life010Organism, life010_bench_config
from learning.resilience_001_agent import state_digest
from learning.resilience_001_plastic import PlasticRecoveryAgent as RecoveryAgent
from learning.resilience_001_budget import OUTPUT
from sim3d.bench_env import BenchHeadEnv

PHASES = ['initial', 'perturbed', 'return']
KINDS = ['frozen', 'naive', 'replay', 'recent', 'adaptive']


def source():
    return {**cumulative_source(), **{p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
        ['learning/resilience_001_v3.py', 'learning/resilience_001.py', 'learning/resilience_001_agent.py', 'cognitive/resilience.py',
         'learning/resilience_001_plastic.py', 'cognitive/resilience_plastic.py',
         'learning/cumulative_001_choice.py', 'cognitive/memory.py', 'cognitive/kernel.py']}}


def create_manifest(path, bank='dev', count=6, variant='v3'):
    path = Path(path)
    if path.exists(): raise ValueError('manifest already exists')
    ns = f'resilience-001/{bank}/{variant}'
    lives = {}
    for i in range(count):
        name = f'life-{i:02d}'
        labels = ['body', 'initialization', 'batches', 'continuous_execution']
        labels += [f'command/{t}' for t in range(36)]
        labels += [f'{role}/{p}/{i}' for role in ['eval_command', 'eval_execution'] for p in PHASES for i in range(8)]
        labels += [f'choice/{p}/{t}/{i}' for p in PHASES for t in [0, 3, 6, 12] for i in range(12)]
        lives[name] = {label: seed(ns, name, label) for label in labels}
    values = [v for life in lives.values() for v in life.values()]
    if min(values) <= 100000 or len(set(values)) != len(values): raise ValueError('seed collision')
    prior_values = set()
    def collect(x):
        if isinstance(x, dict):
            for v in x.values(): collect(v)
        elif isinstance(x, list):
            for v in x: collect(v)
        elif isinstance(x, int) and x > 100000: prior_values.add(x)
    for old in (ROOT / 'docs/research').glob('*manifest*.json'): collect(json.loads(old.read_bytes()))
    for old in (ROOT / 'docs/research').glob('cumulative_001_*v1.json'): collect(json.loads(old.read_bytes()))
    if set(values) & prior_values: raise ValueError('historical seed collision')
    manifest = {'namespace': ns, 'bank': bank, 'variant': variant, 'lives': lives, 'source': source(),
                'created_date': '2026-09-10', 'protocol': 'docs/research/resilience_001_v3.md',
                'protocol_sha256': hashlib.sha256((ROOT / 'docs/research/resilience_001_v3.md').read_bytes()).hexdigest(),
                'seed_count': len(values), 'prior_numeric_inventory': len(prior_values), 'collision_count': 0}
    path.write_bytes(canonical(manifest))
    print('Manifest frozen', path, digest(manifest), flush=True)


def commands(value):
    rng = np.random.default_rng(value)
    result = []
    while len(result) < 64:
        target = float(rng.uniform(30, 150))
        result.extend([target] * min(int(rng.integers(3, 13)), 64 - len(result)))
    return result


def drive(env, targets, history):
    angle, delta, previous, previous_delta = history
    rows = []
    for target in targets:
        observation = Observation(angle, delta, previous, target, previous_delta)
        next_angle = env.step(target).as5600_deg
        rows.append(TrainingRow(observation, next_angle))
        angle, delta, previous_delta, previous = next_angle, next_angle - angle, target - previous, target
    return rows, (angle, delta, previous, previous_delta)


def evaluate(agents, evaluation):
    obs = [r.observation for r in evaluation]
    target = np.array([r.next_angle for r in evaluation])
    return {name: float(np.mean(abs(a.predict(obs) - target))) for name, a in agents.items()}


def probe(request, response):
    p = json.loads(Path(request).read_bytes())
    rows = [TrainingRow.restore(r) for r in p['rows']]
    with CognitiveKernel(p['database']) as kernel:
        store = ResilienceStore(kernel, p['artifacts'], p['run_id'], p['contract'])
        a = store.load()
        result = {'state': state_digest(a.state()), 'prediction': store.predict([r.observation for r in rows]).tolist()}
        a.update(rows)
        result['next_state'] = state_digest(a.state())
    Path(response).write_bytes(canonical(result))


def run_life(name, seeds, manifest, destination):
    if destination.exists(): raise ValueError('exposed life cannot be overwritten')
    destination.mkdir(parents=True)
    start = time.monotonic()
    rng = np.random.default_rng(seeds['body'])
    base = Life010Organism(seed=seeds['body'], regime='combined', max_speed_deg_s=float(rng.uniform(480, 720)),
                           position_gain=float(rng.uniform(8, 12)), velocity_damping=float(rng.uniform(.10, .20)))
    changed = replace(base, max_speed_deg_s=float(rng.uniform(120, 240)))
    bodies = [base, changed, base]
    agents = {kind: RecoveryAgent(seeds['initialization'], seeds['batches'], kind) for kind in KINDS}
    database = destination / 'kernel.sqlite'
    contract = digest({'manifest': digest(manifest), 'life': name})
    kernel = CognitiveKernel(database)
    store = ResilienceStore(kernel, destination / 'artifacts', name, contract)
    agents['adaptive'] = store.initialize(agents['adaptive'])
    env = BenchHeadEnv(life010_bench_config(base, seeds['continuous_execution']))
    physical_history = (90., 0., 90., 0.)
    checkpoints = []; training = []; phase_witnesses = []; restart = None
    try:
        for phase_index, (phase, organism) in enumerate(zip(PHASES, bodies)):
            before = {'steps': env.step_count, 'time': env.time, 'angle': physical_history[0]}
            env.config.servo.max_speed_deg_s = organism.max_speed_deg_s
            assert before['steps'] == phase_index * 12 * 64
            phase_witnesses.append({'phase': phase, **before, 'speed': organism.max_speed_deg_s})
            evaluation = []
            for i in range(8):
                judge = BenchHeadEnv(life010_bench_config(organism, seeds[f'eval_execution/{phase}/{i}']))
                try:
                    rows, _ = drive(judge, commands(seeds[f'eval_command/{phase}/{i}']), (90., 0., 90., 0.))
                    evaluation.extend(rows)
                finally: judge.close()
            (destination / (phase + '-evaluation.json')).write_bytes(canonical([r.payload() for r in evaluation]))

            def checkpoint(trial):
                record = {'phase': phase, 'trial': trial, 'mae': evaluate(agents, evaluation)}
                if trial in [0, 3, 6, 12]:
                    cases = []
                    for i, (angle, horizon) in enumerate((a, h) for a in [57.5, 77.5, 102.5, 132.5] for h in [4, 6, 8]):
                        cases.append(situation(organism, angle, horizon, seeds[f'choice/{phase}/{trial}/{i}'],
                                               {k: a.learner for k, a in agents.items()}))
                    (destination / f'{phase}-{trial}-choices.json').write_bytes(canonical(cases))
                    record['behavior'] = {kind: {'utility': float(np.mean([c['scores'][kind]['utility_deg'] for c in cases])),
                                                         'success': float(np.mean([c['scores'][kind]['success'] for c in cases])),
                                                         'regret': float(np.mean([c['scores'][kind]['regret_deg'] for c in cases]))}
                                          for kind in KINDS}
                    record['oracle_utility'] = float(np.mean([c['oracle_utility_deg'] for c in cases]))
                checkpoints.append(record)
            checkpoint(0)
            for trial in range(12):
                absolute = phase_index * 12 + trial
                rows, physical_history = drive(env, commands(seeds[f'command/{absolute}']), physical_history)
                record = {'index': absolute, 'phase': phase, 'rows': [r.payload() for r in rows], 'events': {}}
                for kind in KINDS:
                    if kind == 'frozen' and phase_index > 0:
                        record['events'][kind] = {'prequential_mae': evaluate({kind: agents[kind]}, rows)[kind]}
                    elif kind == 'adaptive':
                        agents[kind], event, applied = store.apply(str(absolute), rows)
                        assert applied
                        record['events'][kind] = event
                    else: record['events'][kind] = agents[kind].update(rows)
                training.append(record)
                if absolute == 13:
                    # Restart the cognitive service while its physical simulation host stays alive.
                    request = destination / 'restart-request.json'; response = destination / 'restart-response.json'
                    request.write_bytes(canonical({'database': str(database.resolve()), 'artifacts': str((destination / 'artifacts').resolve()),
                                                   'run_id': name, 'contract': contract, 'rows': [r.payload() for r in rows]}))
                    a = store.load()
                    expected = {'state': state_digest(a.state()), 'prediction': a.predict([r.observation for r in rows]).tolist()}
                    a.update(rows); expected['next_state'] = state_digest(a.state())
                    kernel.close()
                    subprocess.run([sys.executable, '-m', 'learning.resilience_001_v3', '--probe', str(request), str(response)],
                                   check=True, timeout=90)
                    assert json.loads(response.read_bytes()) == expected, 'cognitive restart mismatch'
                    kernel = CognitiveKernel(database)
                    store = ResilienceStore(kernel, destination / 'artifacts', name, contract)
                    agents['adaptive'] = store.load()
                    restart = {'bit_exact': True, 'after_trial': 14, 'simulation_steps': env.step_count}
                if (trial + 1) % 3 == 0: checkpoint(trial + 1)
            print(json.dumps({'life': name, 'phase': phase, 'checkpoint': checkpoints[-1],
                              'alarms': [e for e in agents['adaptive'].events if e['alarm']]}), flush=True)
            (destination / (phase + '-progress.json')).write_bytes(canonical(checkpoints))
        (destination / 'training.json').write_bytes(canonical(training))
        events = agents['adaptive'].events
        alarms = [e['trial'] for e in events if e['alarm']]
        delays = [min([t - boundary for t in alarms if boundary < t <= boundary + 12], default=None) for boundary in [12, 24]]
        report = {'life': name, 'bank': manifest['bank'], 'manifest': digest(manifest), 'source': source(),
                  'bodies': [asdict(b) for b in bodies], 'checkpoints': checkpoints, 'phase_continuity': phase_witnesses,
                  'events': events, 'detection_delays': delays, 'false_alarms_initial': sum(t <= 12 for t in alarms),
                  'restart': restart, 'seconds': time.monotonic() - start,
                  'updates': {k: a.total_updates for k, a in agents.items()},
                  'final_state_digest': state_digest(agents['adaptive'].state()), 'final_subgoal_open': agents['adaptive'].recovering}
        (destination / 'report.json').write_bytes(canonical(report))
        print(json.dumps({k: v for k, v in report.items() if k not in ['bodies', 'checkpoints', 'events', 'source']}), flush=True)
    finally:
        env.close(); kernel.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest')
    p.add_argument('--create', action='store_true')
    p.add_argument('--bank', default='dev', choices=['dev', 'validation'])
    p.add_argument('--count', type=int, default=6)
    p.add_argument('--variant', default='v3')
    p.add_argument('--life', choices=['first', 'remaining', 'all'], default='first')
    p.add_argument('--probe', nargs=2)
    args = p.parse_args()
    if args.probe: return probe(*args.probe)
    if args.create: return create_manifest(args.manifest, args.bank, args.count, args.variant)
    manifest = json.loads(Path(args.manifest).read_bytes())
    if manifest['source'] != source(): raise ValueError('frozen source changed; a new variant is required')
    identities = list(manifest['lives'])
    if args.life == 'first': identities = identities[:1]
    elif args.life == 'remaining': identities = identities[1:]
    for name in identities:
        run_life(name, manifest['lives'][name], manifest, OUTPUT / manifest['bank'] / manifest['variant'] / name)


if __name__ == '__main__': main()
