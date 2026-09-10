"""Versioned recovery service; historical v2 stores keep their own loader."""
import hashlib
from pathlib import Path
import torch
from cognitive.resilience import ResilienceStore
from learning.resilience_001_plastic import PlasticRecoveryAgent


class PlasticResilienceStore(ResilienceStore):
    def load(self):
        row = self._state()
        path = Path(row['artifact']).resolve()
        if path.parent != self.folder or hashlib.sha256(path.read_bytes()).hexdigest() != row['digest']:
            raise ValueError('checkpoint integrity')
        agent = PlasticRecoveryAgent.restore(torch.load(path, map_location=self.device, weights_only=True), self.device)
        if agent.trials != row['cursor']: raise ValueError('cursor mismatch')
        return agent
