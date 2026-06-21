"""A compact Liquid Neural Network style controller skeleton."""

from __future__ import annotations


try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError:
    torch = None
    nn = None


def _require_torch() -> None:
    if torch is None or nn is None:
        raise ModuleNotFoundError("learning.lnn requires PyTorch. Install torch in the training environment.")


if nn is not None:

    class SimpleLNN(nn.Module):
        def __init__(
            self,
            state_dim: int,
            input_dim: int,
            action_dim: int = 3,
            hidden_dim: int = 128,
            tau_min: float = 0.05,
            tau_max: float = 1.5,
        ):
            super().__init__()
            self.state_dim = state_dim
            self.tau_min = tau_min
            self.tau_max = tau_max
            xu_dim = state_dim + input_dim
            self.tau_net = nn.Sequential(nn.Linear(xu_dim, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, state_dim))
            self.drive_net = nn.Sequential(nn.Linear(xu_dim, hidden_dim), nn.GELU(), nn.Linear(hidden_dim, state_dim))
            self.policy = nn.Sequential(
                nn.Linear(state_dim + input_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, action_dim),
                nn.Tanh(),
            )

        def f(self, x, u):
            xu = torch.cat([x, u], dim=-1)
            tau = self.tau_min + (self.tau_max - self.tau_min) * torch.sigmoid(self.tau_net(xu))
            drive = torch.tanh(self.drive_net(xu))
            return -x / tau + drive

        def step(self, x, u, dt: float):
            return x + dt * self.f(x, u)

        def act(self, x, u):
            return self.policy(torch.cat([x, u], dim=-1))


    class AuxiliaryLatentHead(nn.Module):
        """Training-only projection from LNN hidden state to a JEPA target latent."""

        def __init__(self, state_dim: int, latent_dim: int, hidden_dim: int = 128):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, latent_dim),
            )

        def forward(self, state):
            return self.net(state)

else:

    class SimpleLNN:
        def __init__(self, *args, **kwargs):
            _require_torch()


    class AuxiliaryLatentHead:
        def __init__(self, *args, **kwargs):
            _require_torch()
