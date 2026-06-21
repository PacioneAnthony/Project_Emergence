"""Comparative mechanical stability report for J0 servo qualification runs."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import median

from j0.replay import SessionReplay


def _rms(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values) / len(values)) if values else 0.0


def _window(samples: list[dict], start_ns: int, end_ns: int) -> list[dict]:
    return [sample for sample in samples if start_ns <= sample["timestamp_ns"] < end_ns]


def _window_metrics(samples: list[dict], gyro_center: tuple[float, float, float]) -> dict:
    gyro_deviation = [
        math.sqrt(sum((float(axis) - gyro_center[index]) ** 2 for index, axis in enumerate(sample["gyro_raw"])))
        for sample in samples
    ]
    accel_magnitudes = [
        math.sqrt(sum(float(axis) ** 2 for axis in sample["accel_raw"])) for sample in samples
    ]
    accel_jerk = [
        abs(accel_magnitudes[index] - accel_magnitudes[index - 1])
        for index in range(1, len(accel_magnitudes))
    ]
    return {
        "sample_count": len(samples),
        "gyro_deviation_rms_raw": _rms(gyro_deviation),
        "gyro_deviation_p95_raw": (
            sorted(gyro_deviation)[round(0.95 * (len(gyro_deviation) - 1))] if gyro_deviation else 0.0
        ),
        "accel_jerk_rms_raw": _rms(accel_jerk),
        "accel_jerk_p95_raw": (
            sorted(accel_jerk)[round(0.95 * (len(accel_jerk) - 1))] if accel_jerk else 0.0
        ),
    }


def analyze_mechanics(session_dir: str | Path, *, write_report: bool = True) -> dict:
    session_path = Path(session_dir)
    events = list(SessionReplay(session_path).events())
    sync_path = session_path / "reports" / "sync.json"
    sync = json.loads(sync_path.read_text(encoding="utf-8")) if sync_path.exists() else {}
    device_offset_ns = int(sync.get("median_offset_ns") or 0)

    imu_samples = []
    commands = []
    for event in events:
        if event.event_type == "imu_sample":
            accel_raw = event.payload.get("accel_raw")
            gyro_raw = event.payload.get("gyro_raw")
            if accel_raw and gyro_raw and len(accel_raw) == 3 and len(gyro_raw) == 3:
                imu_samples.append(
                    {
                        "timestamp_ns": event.source_timestamp_ns + device_offset_ns,
                        "accel_raw": accel_raw,
                        "gyro_raw": gyro_raw,
                    }
                )
        elif event.event_type == "servo_command":
            commands.append(
                {
                    "timestamp_ns": event.source_timestamp_ns,
                    "requested_angle_deg": float(event.payload["requested_angle_deg"]),
                }
            )

    if not imu_samples or not commands:
        report = {
            "schema_version": 1,
            "status": "insufficient_data",
            "reason": "mechanical analysis requires IMU samples and servo commands",
            "command_count": len(commands),
            "imu_sample_count": len(imu_samples),
        }
    else:
        first_command_ns = commands[0]["timestamp_ns"]
        baseline_samples = _window(imu_samples, first_command_ns - 4_000_000_000, first_command_ns - 500_000_000)
        if len(baseline_samples) < 100:
            baseline_samples = imu_samples[: min(300, len(imu_samples))]
        gyro_center = tuple(
            median(float(sample["gyro_raw"][axis]) for sample in baseline_samples) for axis in range(3)
        )
        baseline = _window_metrics(baseline_samples, gyro_center)
        baseline_gyro = max(baseline["gyro_deviation_rms_raw"], 1.0)
        baseline_jerk = max(baseline["accel_jerk_rms_raw"], 1.0)

        command_reports = []
        previous_angle = commands[0]["requested_angle_deg"]
        for index, command in enumerate(commands):
            timestamp_ns = command["timestamp_ns"]
            movement = _window_metrics(_window(imu_samples, timestamp_ns, timestamp_ns + 500_000_000), gyro_center)
            settling = _window_metrics(
                _window(imu_samples, timestamp_ns + 500_000_000, timestamp_ns + 1_500_000_000),
                gyro_center,
            )
            settling_gyro_ratio = settling["gyro_deviation_rms_raw"] / baseline_gyro
            settling_jerk_ratio = settling["accel_jerk_rms_raw"] / baseline_jerk
            command_reports.append(
                {
                    "command_index": index,
                    "requested_angle_deg": command["requested_angle_deg"],
                    "step_deg": command["requested_angle_deg"] - previous_angle if index else 0.0,
                    "movement_0_to_500ms": movement,
                    "settling_500_to_1500ms": settling,
                    "settling_gyro_ratio_to_baseline": settling_gyro_ratio,
                    "settling_jerk_ratio_to_baseline": settling_jerk_ratio,
                    "passes_provisional_settling_limit": (
                        settling_gyro_ratio <= 3.0 and settling_jerk_ratio <= 3.0
                    ),
                }
            )
            previous_angle = command["requested_angle_deg"]

        evaluated = [command for command in command_reports if abs(command["step_deg"]) > 0]
        report = {
            "schema_version": 1,
            "status": "complete",
            "method": "IMU raw gyro deviation and acceleration-magnitude jerk relative to pre-command baseline",
            "device_clock_offset_ns": device_offset_ns,
            "baseline": {**baseline, "gyro_center_raw": list(gyro_center)},
            "commands": command_reports,
            "provisional_settling_limit_ratio": 3.0,
            "passes_provisional_stability_check": bool(
                evaluated and all(command["passes_provisional_settling_limit"] for command in evaluated)
            ),
            "limitations": [
                "This is a comparative bench metric, not an absolute vibration calibration.",
                "AS5600 angle truth is still required for position repeatability and backlash measurements.",
            ],
        }

    if write_report:
        output = session_path / "reports" / "mechanics.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
