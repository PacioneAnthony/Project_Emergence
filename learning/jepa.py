"""Minimal JEPA building blocks for simulator observations."""

from __future__ import annotations


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ModuleNotFoundError:
    torch = None
    nn = None
    F = None


def _require_torch() -> None:
    if torch is None or nn is None or F is None:
        raise ModuleNotFoundError("learning.jepa requires PyTorch. Install torch in the training environment.")


if nn is not None:

    class MLP(nn.Module):
        def __init__(self, input_dim: int, output_dim: int, hidden_dim: int = 128):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, output_dim),
            )

        def forward(self, x):
            return self.net(x)


    class SensorJEPA(nn.Module):
        def __init__(
            self,
            obs_dim: int = 3,
            action_dim: int = 3,
            latent_dim: int = 32,
            hidden_dim: int = 128,
            decoded_obs_dim: int | None = None,
        ):
            super().__init__()
            self.encoder = MLP(obs_dim, latent_dim, hidden_dim)
            self.predictor = MLP(latent_dim + action_dim, latent_dim, hidden_dim)
            self.obs_decoder = MLP(latent_dim, decoded_obs_dim, hidden_dim) if decoded_obs_dim is not None else None

        def forward(self, obs_t, action_t):
            s_t = self.encoder(obs_t)
            pred_s_next = self.predictor(torch.cat([s_t, action_t], dim=-1))
            return s_t, pred_s_next

        def encode(self, obs):
            return self.encoder(obs)

        def decode_observation(self, latent):
            if self.obs_decoder is None:
                raise RuntimeError("This SensorJEPA checkpoint has no observation decoder.")
            return self.obs_decoder(latent)

else:

    class MLP:
        def __init__(self, *args, **kwargs):
            _require_torch()

    class SensorJEPA:
        def __init__(self, *args, **kwargs):
            _require_torch()


def jepa_loss(pred_s_next, target_s_next):
    _require_torch()
    return F.mse_loss(pred_s_next, target_s_next.detach())


def variance_loss(latents, gamma: float = 1.0, eps: float = 1e-4):
    _require_torch()
    std = torch.sqrt(latents.var(dim=0) + eps)
    return torch.mean(F.relu(gamma - std))


def covariance_loss(latents):
    _require_torch()
    batch_size, latent_dim = latents.shape
    if batch_size <= 1:
        return latents.new_tensor(0.0)
    centered = latents - latents.mean(dim=0, keepdim=True)
    cov = centered.T @ centered / (batch_size - 1)
    off_diag = cov - torch.diag(torch.diag(cov))
    return (off_diag.pow(2).sum()) / latent_dim


def weighted_observation_loss(prediction, target, distance_weight: float = 1.0):
    _require_torch()
    weights = torch.ones(target.shape[-1], dtype=target.dtype, device=target.device)
    if target.shape[-1] > 0:
        weights[0] = float(distance_weight)
    return torch.mean(((prediction - target) ** 2) * weights)
