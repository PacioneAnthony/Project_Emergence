"""Observation-driven recovery supervisor; no phase or hidden physics inputs."""
from copy import deepcopy
import hashlib
import json
import numpy as np
import torch
from learning.cumulative_001_neural import NeuralLearner


def restore_neural(state, device):
    # Adam may reuse tensors from load_state_dict on the same device.
    # A recalled learner must never mutate the memory it was recalled from.
    state = deepcopy(state)
    obj = NeuralLearner(state['initialization'], state['batches'], state['replay'], device=device, updates=state['updates'])
    obj.model.load_state_dict(state['model'])
    obj.optimizer.load_state_dict(state['optimizer'])
    obj.generator.set_state(state['rng'].cpu())
    obj.memory_x = state['memory_x'].to(device).clone()
    obj.memory_y = state['memory_y'].to(device).clone()
    obj.trials = state['trials']
    obj.update_count = state['update_count']
    return obj


def state_digest(value):
    h = hashlib.sha256()
    def visit(x):
        if isinstance(x, torch.Tensor):
            h.update(str((x.dtype, tuple(x.shape))).encode())
            h.update(x.detach().cpu().contiguous().numpy().tobytes())
        elif isinstance(x, dict):
            h.update(b'dict')
            for k in sorted(x, key=str):
                visit(k); visit(x[k])
        elif isinstance(x, (list, tuple)):
            h.update(str((type(x).__name__, len(x))).encode())
            for v in x: visit(v)
        else:
            h.update(json.dumps(x, sort_keys=True, allow_nan=False).encode())
        h.update(b'\x00')
    visit(value)
    return h.hexdigest()


class RecoveryAgent:
    def __init__(self, initialization, batches, kind='adaptive', device='cuda', updates=64):
        if kind not in ['adaptive', 'recent', 'replay', 'naive', 'frozen']:
            raise ValueError('unknown policy')
        self.kind = kind
        self.learner = NeuralLearner(initialization, batches, kind != 'naive', device=device, updates=updates)
        self.trials = 0
        self.total_updates = 0
        self.reference = []
        self.streak = 0
        self.cooldown = 0
        self.recovering = False
        self.recovery_errors = []
        self.stable = 0
        self.archives = []
        self.events = []

    def predict(self, observations):
        return self.learner.predict(observations)

    def update(self, rows):
        obs = [r.observation for r in rows]
        target = np.array([r.next_angle for r in rows])
        error = float(np.mean(abs(self.predict(obs) - target)))
        threshold = max(.35, 3 * float(np.median(self.reference[-6:]))) if self.reference else .35
        event = {'trial': self.trials + 1, 'prequential_mae': error, 'threshold': threshold,
                 'alarm': False, 'response': None, 'goal_opened': False, 'goal_closed': False}
        if self.kind == 'adaptive':
            self._observe(error, threshold, obs, target, event)
        self.learner.update(rows)
        self.total_updates += self.learner.updates
        self.trials += 1
        if self.kind in ['adaptive', 'recent']:
            self.learner.memory_x = self.learner.memory_x[-256:].clone()
            self.learner.memory_y = self.learner.memory_y[-256:].clone()
        if self.kind == 'adaptive' and self.trials >= 8 and self.trials % 4 == 0 and not self.recovering and not self.streak:
            self.archives.append(deepcopy(self.learner.state()))
            self.archives = self.archives[-6:]
        event.update({'recovering': self.recovering, 'buffer_rows': len(self.learner.memory_x), 'archives': len(self.archives)})
        self.events.append(event)
        return event

    def _observe(self, error, threshold, obs, target, event):
        if self.trials < 8:
            self.reference.append(error)
            return
        if self.cooldown:
            self.cooldown -= 1
        high = error > threshold
        self.streak = self.streak + 1 if high else 0
        if self.recovering:
            self.recovery_errors.append(error)
            self.stable = 0 if high else self.stable + 1
            if self.stable >= 3:
                self.recovering = False
                self.reference = self.recovery_errors[-6:]
                self.recovery_errors = []
                event['goal_closed'] = True
        elif self.streak >= 2 and not self.cooldown:
            event.update({'alarm': True, 'goal_opened': True})
            self.recovering = True
            self.recovery_errors = []
            self.stable = 0
            self.cooldown = 3
            self.streak = 0
            scores = []
            for snapshot in self.archives:
                old = restore_neural(snapshot, self.learner.device)
                scores.append(float(np.mean(abs(old.predict(obs) - target))))
            if scores and min(scores) <= .7 * error:
                index = int(np.argmin(scores))
                self.learner = restore_neural(self.archives[index], self.learner.device)
                event.update({'response': 'recall', 'archive_index': index, 'archive_error': scores[index]})
            else:
                self.learner.memory_x = self.learner.memory_x[:0].clone()
                self.learner.memory_y = self.learner.memory_y[:0].clone()
                event['response'] = 'discard_stale_replay'
        elif not high:
            self.reference = (self.reference + [error])[-6:]

    def state(self):
        return {'format': 'recovery-agent-v1', 'kind': self.kind, 'learner': self.learner.state(),
                **{k: deepcopy(getattr(self, k)) for k in ['trials', 'total_updates', 'reference', 'streak', 'cooldown',
                    'recovering', 'recovery_errors', 'stable', 'archives', 'events']}}

    @classmethod
    def restore(cls, state, device='cuda'):
        if state['format'] != 'recovery-agent-v1': raise ValueError('agent format')
        obj = cls.__new__(cls)
        obj.kind = state['kind']
        obj.learner = restore_neural(state['learner'], device)
        for k in ['trials', 'total_updates', 'reference', 'streak', 'cooldown', 'recovering', 'recovery_errors', 'stable', 'archives', 'events']:
            setattr(obj, k, deepcopy(state[k]))
        return obj
