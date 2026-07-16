"""Visual JEPA blocks for the bench head camera.

Same philosophy as `learning.jepa.SensorJEPA`: one encoder, a predictor that
receives the current latent plus the motor action, a stop-gradient target and
VICReg-style variance/covariance regularization against collapse. The encoder
is convolutional because the observation is now a camera frame.
"""

from __future__ import annotations

try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError:
    torch = None
    nn = None


def _require_torch() -> None:
    if torch is None or nn is None:
        raise ModuleNotFoundError("learning.visual_jepa requires PyTorch.")


if nn is not None:

    class ConvEncoder(nn.Module):
        """(B, 3, S, S) uint8-normalized frames -> (B, latent_dim)."""

        def __init__(self, latent_dim: int = 128, width: int = 32):
            super().__init__()
            self.trunk = nn.Sequential(
                nn.Conv2d(3, width, kernel_size=4, stride=2, padding=1),
                nn.GELU(),
                nn.Conv2d(width, width * 2, kernel_size=4, stride=2, padding=1),
                nn.GELU(),
                nn.Conv2d(width * 2, width * 4, kernel_size=4, stride=2, padding=1),
                nn.GELU(),
                nn.Conv2d(width * 4, width * 8, kernel_size=4, stride=2, padding=1),
                nn.GELU(),
                nn.AdaptiveAvgPool2d(2),
                nn.Flatten(),
            )
            self.head = nn.Linear(width * 8 * 4, latent_dim)

        def forward(self, frames):
            return self.head(self.trunk(frames))


    class VisualJEPA(nn.Module):
        """Action-conditioned latent predictor over camera frames.

        With `use_action=False` the action input is zeroed, which is the
        pre-registered control variant: same capacity, no motor information.
        """

        def __init__(
            self,
            latent_dim: int = 128,
            action_dim: int = 1,
            hidden_dim: int = 512,
            encoder_width: int = 32,
            use_action: bool = True,
            horizon_dim: int = 0,
        ):
            super().__init__()
            self.latent_dim = latent_dim
            self.action_dim = action_dim
            self.horizon_dim = horizon_dim
            self.use_action = use_action
            self.encoder = ConvEncoder(latent_dim, encoder_width)
            self.predictor = nn.Sequential(
                nn.Linear(latent_dim + action_dim + horizon_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.GELU(),
                nn.Linear(hidden_dim, latent_dim),
            )

        def encode(self, frames):
            return self.encoder(frames)

        def predict_next(self, latent, action, horizon=None):
            # The control variant loses the motor commands but keeps the
            # horizon: both variants know how far to project.
            if not self.use_action:
                action = torch.zeros_like(action)
            parts = [latent, action]
            if self.horizon_dim > 0:
                if horizon is None:
                    raise ValueError("This model was built with horizon conditioning; pass `horizon`.")
                parts.append(horizon)
            return self.predictor(torch.cat(parts, dim=-1))

        def forward(self, frames_t, action_t, horizon_t=None):
            latent_t = self.encode(frames_t)
            return latent_t, self.predict_next(latent_t, action_t, horizon_t)

else:

    class ConvEncoder:
        def __init__(self, *args, **kwargs):
            _require_torch()

    class VisualJEPA:
        def __init__(self, *args, **kwargs):
            _require_torch()
