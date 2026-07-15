"""Mechanical qualification of the bench twin using the exact j0 metric.

The window math (`_window_metrics`, `_window`) is imported from
`j0.mechanics` so the simulated report and the physical
`python -m j0.cli mechanics <session>` report are computed by the same code.
The result is comparative only: the rigid-body twin does not model PLA
structural vibration, it exposes the servo/inertia settling dynamics.
"""

from __future__ import annotations

from statistics import median
from typing import Sequence

from j0.mechanics import _window, _window_metrics

from sim3d.bench_env import BenchHeadEnv


def analyze_bench_mechanics(imu_samples: list[dict], commands: list[dict]) -> dict:
    """Mirror of j0.mechanics.analyze_mechanics operating on in-memory lists."""

    if not imu_samples or not commands:
        return {
            "schema_version": 1,
            "status": "insufficient_data",
            "reason": "mechanical analysis requires IMU samples and servo commands",
            "command_count": len(commands),
            "imu_sample_count": len(imu_samples),
        }

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
    return {
        "schema_version": 1,
        "status": "complete",
        "source": "sim3d bench v1.0 digital twin (rigid-body, comparative only)",
        "method": "IMU raw gyro deviation and acceleration-magnitude jerk relative to pre-command baseline",
        "baseline": {**baseline, "gyro_center_raw": list(gyro_center)},
        "commands": command_reports,
        "provisional_settling_limit_ratio": 3.0,
        "passes_provisional_stability_check": bool(
            evaluated and all(command["passes_provisional_settling_limit"] for command in evaluated)
        ),
        "limitations": [
            "Rigid-body twin: PLA structural vibration and print tolerances are not modeled.",
            "Use as a comparative baseline for servo/inertia settling, not as bench acceptance.",
        ],
    }


def run_qualification(
    env: BenchHeadEnv,
    sequence: Sequence[float] = (90.0, 80.0, 100.0, 90.0),
    rest_seconds: float = 5.0,
    dwell_seconds: float = 2.0,
    seed: int | None = 0,
) -> dict:
    """Replay the J0 runbook servo sequence on the twin and grade it like j0."""

    env.reset(seed=seed)
    neutral = env.config.servo.neutral_deg
    rest_steps = max(1, round(rest_seconds / env.config.control_dt))
    dwell_steps = max(1, round(dwell_seconds / env.config.control_dt))

    for _ in range(rest_steps):
        env.step(neutral)

    # Force a logged command entry for the first (zero-displacement) command,
    # like the physical runbook which sends an explicit 90.
    env.command_log.append(
        {"timestamp_ns": int(round(env.time * 1e9)), "requested_angle_deg": float(sequence[0])}
    )
    for target in sequence:
        for _ in range(dwell_steps):
            env.step(float(target))

    report = analyze_bench_mechanics(env.imu_samples, env.command_log)
    report["sequence_deg"] = [float(v) for v in sequence]
    report["rest_seconds"] = float(rest_seconds)
    report["dwell_seconds"] = float(dwell_seconds)
    return report
