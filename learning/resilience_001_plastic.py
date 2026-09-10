"""V3: short plasticity bursts after observation-driven large surprises."""
from copy import deepcopy
import numpy as np
import torch
from learning.cumulative_001_data import encode
from learning.resilience_001_agent import RecoveryAgent


class PlasticRecoveryAgent(RecoveryAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plastic_remaining = 0

    def _observe(self, error, threshold, obs, target, event):
        strong_threshold = max(1., 6 * float(np.median(self.reference[-6:]))) if self.reference else 1.
        event['strong_threshold'] = strong_threshold
        if self.trials >= 8 and error > strong_threshold and not self.recovering and not self.cooldown:
            self.streak = max(self.streak, 1)
        super()._observe(error, threshold, obs, target, event)
        if event['alarm']:
            self.plastic_remaining = 3
            self.learner.replay = False

    def update(self, rows):
        event = super().update(rows)
        if self.plastic_remaining:
            x, y, _, _ = encode(rows)
            self.learner.memory_x = torch.cat([self.learner.memory_x, torch.as_tensor(x, device=self.learner.device)])[-256:].clone()
            self.learner.memory_y = torch.cat([self.learner.memory_y, torch.as_tensor(y, device=self.learner.device)])[-256:].clone()
            self.plastic_remaining -= 1
            if not self.plastic_remaining: self.learner.replay = True
        event['plastic_remaining'] = self.plastic_remaining
        event['buffer_rows'] = len(self.learner.memory_x)
        return event

    def state(self):
        return {**super().state(), 'format': 'recovery-plastic-v1', 'plastic_remaining': self.plastic_remaining}

    @classmethod
    def restore(cls, state, device='cuda'):
        if state['format'] != 'recovery-plastic-v1': raise ValueError('plastic agent format')
        base = deepcopy(state)
        base['format'] = 'recovery-agent-v1'
        obj = RecoveryAgent.restore(base, device)
        obj.__class__ = cls
        obj.plastic_remaining = state['plastic_remaining']
        return obj
