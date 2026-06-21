import numpy as np
import pytest


def test_dorsal_output_shape_and_dtype():
    pytest.importorskip("cv2")
    from learning.vision_encoders import DorsalEncoder

    encoder = DorsalEncoder(n_bins=8)
    rng = np.random.default_rng(0)
    frame1 = rng.integers(0, 255, (120, 160), dtype=np.uint8)
    frame2 = rng.integers(0, 255, (120, 160), dtype=np.uint8)

    out = encoder.encode(frame1, frame2)
    assert out.shape == (9,)
    assert out.dtype == np.float32


def test_dorsal_direction_histogram_sums_to_one_for_moving_scene():
    pytest.importorskip("cv2")
    from learning.vision_encoders import DorsalEncoder

    encoder = DorsalEncoder(n_bins=8)
    rng = np.random.default_rng(1)
    frame1 = rng.integers(0, 255, (120, 160), dtype=np.uint8)
    frame2 = rng.integers(0, 255, (120, 160), dtype=np.uint8)

    out = encoder.encode(frame1, frame2)
    assert abs(out[1:].sum() - 1.0) < 1e-5


def test_dorsal_output_dim_property():
    pytest.importorskip("cv2")
    from learning.vision_encoders import DorsalEncoder

    enc = DorsalEncoder(n_bins=16)
    assert enc.output_dim == 17


def test_dorsal_zero_magnitude_for_identical_frames():
    pytest.importorskip("cv2")
    from learning.vision_encoders import DorsalEncoder

    encoder = DorsalEncoder()
    frame = np.full((120, 160), 64, dtype=np.uint8)
    out = encoder.encode(frame, frame)
    assert out[0] == pytest.approx(0.0, abs=1e-3)


def test_ventral_encoder_output_dim():
    pytest.importorskip("torch")
    from learning.vision_encoders import VentralEncoder

    enc = VentralEncoder(device="cpu")
    assert enc.output_dim == 384


def test_dorsal_encoder_raises_without_opencv(monkeypatch):
    import sys
    import unittest.mock as mock

    monkeypatch.setitem(sys.modules, "cv2", None)
    with pytest.raises(ImportError, match="opencv-python"):
        # Force re-import by importing the class directly without cached cv2
        from learning import vision_encoders
        import importlib
        importlib.reload(vision_encoders)
        vision_encoders.DorsalEncoder()
