"""Load J0 JSONL session logs into numpy arrays for offline training."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from j0.replay import SessionReplay


GYRO_SCALE: float = (500.0 / 32768.0) * (np.pi / 180.0)  # rad/s per raw LSB  (±500 dps, int16)
ACCEL_SCALE: float = (4.0 / 32768.0) * 9.80665            # m/s² per raw LSB   (±4 g, int16)


def load_j0_session(session_dir: str | Path) -> dict[str, np.ndarray]:
    """Read a J0 session and return aligned numpy arrays.

    Alignment: one row per valid IMU sample (100 Hz).  Range and servo data are
    forward-filled from the most recent event received before each IMU sample.

    Returns
    -------
    obs          (N, 3)  float32  [distance_m, servo_angle_deg, gyro_z_rad_s]
    action       (N, 1)  float32  [servo_target_deg]
    next_obs     (N, 3)  float32  (obs shifted forward by one row; last row repeated)
    state        (N, 7)  float32  [ax, ay, az m/s², gx, gy, gz rad/s, servo_deg]
    reward       (N,)    float32  zeros (not computed during hardware sessions)
    done         (N,)    bool     False everywhere except the final row
    timestamp_ns (N,)    int64    host_receive_timestamp_ns of each IMU event
    """
    replay = SessionReplay(session_dir)

    last_range: dict[str, float] = {"distance_m": 0.0, "servo_target_deg": 90.0}
    last_servo: dict[str, float] = {"applied_deg": 90.0}
    imu_rows: list[dict[str, Any]] = []

    for event in replay.events():
        et = event.event_type
        p = event.payload

        if et == "range_sample" and (p.get("status", 0) & 1):
            last_range["distance_m"] = p["distance_mm"] / 1000.0
            last_range["servo_target_deg"] = p["servo_target_cdeg"] / 100.0

        elif et == "servo_state":
            last_servo["applied_deg"] = p["applied_cdeg"] / 100.0

        elif et == "imu_sample":
            if not (p.get("status", 0) & 1):
                continue
            gr = p["gyro_raw"]
            ar = p["accel_raw"]
            imu_rows.append(
                {
                    "timestamp_ns": event.host_receive_timestamp_ns,
                    "ax": ar[0] * ACCEL_SCALE,
                    "ay": ar[1] * ACCEL_SCALE,
                    "az": ar[2] * ACCEL_SCALE,
                    "gx": gr[0] * GYRO_SCALE,
                    "gy": gr[1] * GYRO_SCALE,
                    "gz": gr[2] * GYRO_SCALE,
                    "distance_m": last_range["distance_m"],
                    "servo_target_deg": last_range["servo_target_deg"],
                    "servo_applied_deg": last_servo["applied_deg"],
                }
            )

    if not imu_rows:
        raise ValueError(f"no valid IMU samples found in {session_dir}")

    N = len(imu_rows)
    timestamps = np.array([r["timestamp_ns"] for r in imu_rows], dtype=np.int64)
    gyro_z = np.array([r["gz"] for r in imu_rows], dtype=np.float32)
    servo_deg = np.array([r["servo_applied_deg"] for r in imu_rows], dtype=np.float32)
    dist_m = np.array([r["distance_m"] for r in imu_rows], dtype=np.float32)
    servo_target = np.array([r["servo_target_deg"] for r in imu_rows], dtype=np.float32)
    ax = np.array([r["ax"] for r in imu_rows], dtype=np.float32)
    ay = np.array([r["ay"] for r in imu_rows], dtype=np.float32)
    az = np.array([r["az"] for r in imu_rows], dtype=np.float32)
    gx = np.array([r["gx"] for r in imu_rows], dtype=np.float32)
    gy = np.array([r["gy"] for r in imu_rows], dtype=np.float32)

    obs = np.column_stack([dist_m, servo_deg, gyro_z])
    state = np.column_stack([ax, ay, az, gx, gy, gyro_z, servo_deg])
    action = servo_target.reshape(-1, 1)
    next_obs = np.vstack([obs[1:], obs[-1:]])

    reward = np.zeros(N, dtype=np.float32)
    done = np.zeros(N, dtype=bool)
    done[-1] = True

    return {
        "obs": obs,
        "action": action,
        "next_obs": next_obs,
        "state": state,
        "reward": reward,
        "done": done,
        "timestamp_ns": timestamps,
    }
