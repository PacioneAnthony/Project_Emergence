import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from learning.j0_loader import ACCEL_SCALE, GYRO_SCALE, load_j0_session


def _write_session(events: list[dict], tmp_path: Path) -> Path:
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    (session_dir / "manifest.json").write_text(
        json.dumps({"session_id": "test", "schema_version": 1})
    )
    with (session_dir / "events.jsonl").open("w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
    return session_dir


def _imu(seq: int, t_ns: int, gyro_raw: list[int] | None = None, status: int = 1) -> dict:
    return {
        "session_id": "test",
        "event_type": "imu_sample",
        "source_id": "arduino.imu",
        "sequence_id": seq,
        "source_timestamp_ns": t_ns,
        "host_receive_timestamp_ns": t_ns,
        "payload": {
            "accel_raw": [100, 200, 300],
            "gyro_raw": gyro_raw or [0, 0, 1000],
            "status": status,
        },
        "quality": {"payload_valid": True},
        "calibration_version": "imu-raw-v1",
        "schema_version": 1,
    }


def _range(seq: int, t_ns: int, distance_mm: int = 500, target_cdeg: int = 9000) -> dict:
    return {
        "session_id": "test",
        "event_type": "range_sample",
        "source_id": "arduino.range",
        "sequence_id": seq,
        "source_timestamp_ns": t_ns,
        "host_receive_timestamp_ns": t_ns,
        "payload": {
            "distance_mm": distance_mm,
            "piezo_raw": 0,
            "servo_target_cdeg": target_cdeg,
            "status": 1,
        },
        "quality": {"payload_valid": True},
        "calibration_version": "imu-raw-v1",
        "schema_version": 1,
    }


def _servo_state(seq: int, t_ns: int, applied_cdeg: int = 9000) -> dict:
    return {
        "session_id": "test",
        "event_type": "servo_state",
        "source_id": "arduino.servo",
        "sequence_id": seq,
        "source_timestamp_ns": t_ns,
        "host_receive_timestamp_ns": t_ns,
        "payload": {
            "command_sequence": seq,
            "requested_cdeg": applied_cdeg,
            "applied_cdeg": applied_cdeg,
            "status": 1,
        },
        "quality": {"payload_valid": True},
        "calibration_version": "imu-raw-v1",
        "schema_version": 1,
    }


def test_basic_shapes_and_dtypes(tmp_path):
    events = [
        _range(0, 1_000_000),
        _imu(0, 2_000_000),
        _imu(1, 12_000_000),
        _imu(2, 22_000_000),
    ]
    arrays = load_j0_session(_write_session(events, tmp_path))

    assert arrays["obs"].shape == (3, 3)
    assert arrays["obs"].dtype == np.float32
    assert arrays["action"].shape == (3, 1)
    assert arrays["next_obs"].shape == (3, 3)
    assert arrays["state"].shape == (3, 7)
    assert arrays["timestamp_ns"].dtype == np.int64
    assert arrays["done"].dtype == bool


def test_gyro_z_scaling(tmp_path):
    events = [_imu(0, 1_000_000, gyro_raw=[0, 0, 32767])]
    arrays = load_j0_session(_write_session(events, tmp_path))
    expected = 32767 * GYRO_SCALE
    assert abs(arrays["obs"][0, 2] - expected) < 1e-6


def test_range_forward_fill(tmp_path):
    events = [
        _range(0, 500_000, distance_mm=1234),
        _imu(0, 1_000_000),
        _imu(1, 2_000_000),  # no new range; must forward-fill
    ]
    arrays = load_j0_session(_write_session(events, tmp_path))
    assert abs(arrays["obs"][0, 0] - 1.234) < 1e-5
    assert abs(arrays["obs"][1, 0] - 1.234) < 1e-5


def test_servo_state_forward_fill(tmp_path):
    events = [
        _servo_state(0, 500_000, applied_cdeg=12000),
        _imu(0, 1_000_000),
    ]
    arrays = load_j0_session(_write_session(events, tmp_path))
    assert abs(arrays["obs"][0, 1] - 120.0) < 1e-4


def test_invalid_imu_status_skipped(tmp_path):
    events = [
        _imu(0, 1_000_000, status=0),   # VALID flag not set → skip
        _imu(1, 2_000_000, status=1),
    ]
    arrays = load_j0_session(_write_session(events, tmp_path))
    assert arrays["obs"].shape[0] == 1


def test_done_flag_set_on_last_row(tmp_path):
    events = [_imu(i, i * 10_000_000) for i in range(5)]
    arrays = load_j0_session(_write_session(events, tmp_path))
    assert not arrays["done"][:-1].any()
    assert arrays["done"][-1]


def test_next_obs_shifted(tmp_path):
    events = [_imu(i, i * 10_000_000, gyro_raw=[0, 0, i * 100]) for i in range(3)]
    arrays = load_j0_session(_write_session(events, tmp_path))
    # next_obs[0] should equal obs[1]
    np.testing.assert_array_equal(arrays["next_obs"][0], arrays["obs"][1])
    # last row: next_obs repeats obs
    np.testing.assert_array_equal(arrays["next_obs"][-1], arrays["obs"][-1])


def test_empty_session_raises(tmp_path):
    with pytest.raises(ValueError, match="no valid IMU"):
        load_j0_session(_write_session([], tmp_path))
