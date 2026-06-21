"""B3 – Ventral / dorsal visual decomposition for J0.

Reference: §13.B3 of DEVELOPMENTAL_ARCHITECTURE_REVIEW.md

DorsalEncoder  Farnebäck optical flow (deterministic, no GPU required).
               Output: (1 + n_bins,) float32 — mean magnitude + L1-normalised
               direction histogram.  Active from J2 / J2.5.

VentralEncoder DINOv2-Small (ViT-S/14) frozen CLS token.
               Output: (384,) float32.
               Requires torch; gated by D-002 until J3/J4.

The two streams MUST NOT be concatenated before milestone J4.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class DorsalEncoder:
    """Farnebäck optical flow → compact 9-D motion descriptor.

    Parameters match cv2.calcOpticalFlowFarneback defaults for real-time use
    at 640×480.  Reduce levels or winsize for smaller frames.
    """

    def __init__(
        self,
        *,
        pyr_scale: float = 0.5,
        levels: int = 3,
        winsize: int = 15,
        iterations: int = 3,
        poly_n: int = 5,
        poly_sigma: float = 1.2,
        n_bins: int = 8,
    ):
        try:
            import cv2  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "DorsalEncoder requires opencv-python. "
                "Install it in the training environment."
            ) from exc
        self._pyr_scale = pyr_scale
        self._levels = levels
        self._winsize = winsize
        self._iterations = iterations
        self._poly_n = poly_n
        self._poly_sigma = poly_sigma
        self._n_bins = n_bins

    @property
    def output_dim(self) -> int:
        return 1 + self._n_bins

    def encode(self, prev_gray: np.ndarray, curr_gray: np.ndarray) -> np.ndarray:
        """Return float32 (1 + n_bins,) from two uint8 grayscale frames."""
        import cv2

        flow = cv2.calcOpticalFlowFarneback(
            prev_gray,
            curr_gray,
            None,
            self._pyr_scale,
            self._levels,
            self._winsize,
            self._iterations,
            self._poly_n,
            self._poly_sigma,
            0,
        )
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        mean_mag = float(np.mean(mag))
        hist, _ = np.histogram(ang.ravel(), bins=self._n_bins, range=(0.0, 2.0 * np.pi))
        hist = hist.astype(np.float32)
        total = hist.sum()
        if total > 0:
            hist /= total
        return np.concatenate([[mean_mag], hist]).astype(np.float32)


class VentralEncoder:
    """DINOv2-Small frozen CLS token extractor (ViT-S/14, 384-D output).

    Model is lazy-loaded on first call to ``encode``.
    All parameters are frozen; this encoder is inference-only.
    """

    _MODEL_NAME = "dinov2_vits14"
    _OUTPUT_DIM = 384

    def __init__(self, *, device: str = "cpu"):
        self._device = device
        self._model: Any = None
        self._transform: Any = None

    @property
    def output_dim(self) -> int:
        return self._OUTPUT_DIM

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            import torchvision.transforms as T
        except ImportError as exc:
            raise ImportError(
                "VentralEncoder requires torch and torchvision."
            ) from exc

        model = torch.hub.load("facebookresearch/dinov2", self._MODEL_NAME, verbose=False)
        model.eval()
        model.to(self._device)
        for p in model.parameters():
            p.requires_grad_(False)
        self._model = model

        self._transform = T.Compose(
            [
                T.ToTensor(),
                T.Resize((224, 224), antialias=True),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

    def encode(self, frame_rgb: np.ndarray) -> np.ndarray:
        """Return float32 (384,) CLS token from a (H, W, 3) uint8 RGB frame."""
        import torch
        from PIL import Image

        self._load()
        img = Image.fromarray(frame_rgb)
        tensor = self._transform(img).unsqueeze(0).to(self._device)
        with torch.no_grad():
            feat = self._model(tensor)
        return feat.squeeze(0).cpu().numpy().astype(np.float32)
