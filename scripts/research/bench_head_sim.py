"""Drive the bench v1.0 head digital twin.

Sub-commands:

- ``qualification``: replay the J0 runbook servo sequence (90-80-100-90) and
  grade it with the exact ``j0.mechanics`` window metric.
- ``corpus``: record head-camera frames plus a CSV index (servo command,
  AS5600 angle, gyro, ultrasonic distance) for visual JEPA bootstrapping.
- ``scan``: sweep the servo continuously, optionally in the interactive viewer.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time as time_module
from pathlib import Path

import numpy as np

from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_mechanics import run_qualification
from sim3d.bench_model import BenchConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bench v1.0 head digital twin runner.")
    sub = parser.add_subparsers(dest="command", required=True)

    qual = sub.add_parser("qualification", help="J0 runbook sequence graded like j0 mechanics.")
    qual.add_argument("--seed", type=int, default=0)
    qual.add_argument("--rest-seconds", type=float, default=5.0)
    qual.add_argument("--dwell-seconds", type=float, default=2.0)
    qual.add_argument("--output", type=Path, default=Path("data/processed/experiments/bench_sim_qualification/mechanics.json"))

    corpus = sub.add_parser("corpus", help="Head-camera frames + CSV index for visual learning.")
    corpus.add_argument("--episodes", type=int, default=4, help="Rooms (re-randomized per episode).")
    corpus.add_argument("--seconds", type=float, default=30.0, help="Simulated seconds per episode.")
    corpus.add_argument("--seed", type=int, default=0)
    corpus.add_argument("--size", type=int, default=128, help="Square frame size in pixels.")
    corpus.add_argument("--capture-hz", type=float, default=10.0)
    corpus.add_argument("--mode", choices=("random", "scan"), default="random", help="Servo target generator.")
    corpus.add_argument("--hold-seconds", type=float, default=0.6, help="random mode: dwell per target.")
    corpus.add_argument("--scan-hz", type=float, default=0.25, help="scan mode: sweep frequency.")
    corpus.add_argument("--output", type=Path, default=Path("data/raw/bench_corpus_001"))

    scan = sub.add_parser("scan", help="Continuous sweep, optionally rendered.")
    scan.add_argument("--seed", type=int, default=0)
    scan.add_argument("--seconds", type=float, default=20.0)
    scan.add_argument("--scan-hz", type=float, default=0.25)
    scan.add_argument("--render", action="store_true")
    scan.add_argument("--realtime", action="store_true")
    scan.add_argument("--save-final-frame", type=Path, default=None)
    return parser


def scan_target(config: BenchConfig, t: float, scan_hz: float) -> float:
    servo = config.servo
    span = min(servo.neutral_deg - servo.min_deg, servo.max_deg - servo.neutral_deg)
    return servo.neutral_deg + span * math.sin(2.0 * math.pi * scan_hz * t)


def cmd_qualification(args: argparse.Namespace) -> None:
    env = BenchHeadEnv(BenchConfig(seed=args.seed))
    try:
        report = run_qualification(
            env,
            rest_seconds=args.rest_seconds,
            dwell_seconds=args.dwell_seconds,
            seed=args.seed,
        )
    finally:
        env.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evaluated = [c for c in report.get("commands", []) if abs(c.get("step_deg", 0.0)) > 0]
    ratios = ", ".join(f"{c['settling_gyro_ratio_to_baseline']:.2f}" for c in evaluated)
    print(
        f"Qualification twin: gyro ratios [{ratios}] limite 3.0 "
        f"verdict={'PASS' if report.get('passes_provisional_stability_check') else 'FAIL'} report={args.output}"
    )


def cmd_corpus(args: argparse.Namespace) -> None:
    config = BenchConfig(seed=args.seed)
    env = BenchHeadEnv(config)
    frames_dir = args.output / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    import matplotlib.image

    rng = np.random.default_rng(args.seed)
    steps_per_episode = max(1, round(args.seconds / config.control_dt))
    capture_every = max(1, round(1.0 / (args.capture_hz * config.control_dt)))
    hold_steps = max(1, round(args.hold_seconds / config.control_dt))
    frame_count = 0

    index_path = args.output / "index.csv"
    with index_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["episode", "frame", "t", "requested_deg", "as5600_deg", "gyro_z_raw", "distance_m"]
        )
        try:
            for episode in range(args.episodes):
                obs = env.reset(seed=args.seed + episode)
                target = env.config.servo.neutral_deg
                for step in range(steps_per_episode):
                    if args.mode == "scan":
                        target = scan_target(config, env.time, args.scan_hz)
                    elif step % hold_steps == 0:
                        target = float(rng.uniform(config.servo.min_deg, config.servo.max_deg))
                    obs = env.step(target)

                    if step % capture_every == 0:
                        frame = env.render_camera(args.size, args.size)
                        name = f"frame_{episode:03d}_{step:06d}.png"
                        matplotlib.image.imsave(frames_dir / name, frame)
                        writer.writerow(
                            [
                                episode,
                                name,
                                f"{obs.time:.3f}",
                                f"{obs.requested_deg:.2f}",
                                f"{obs.as5600_deg:.3f}",
                                obs.gyro_raw[2],
                                f"{obs.distance_m:.4f}",
                            ]
                        )
                        frame_count += 1
        finally:
            env.close()

    print(
        f"Corpus complete: {frame_count} frames {args.size}x{args.size} sur {args.episodes} pieces, "
        f"index={index_path}"
    )


def cmd_scan(args: argparse.Namespace) -> None:
    config = BenchConfig(seed=args.seed)
    env = BenchHeadEnv(config)
    steps = max(1, round(args.seconds / config.control_dt))
    try:
        env.reset(seed=args.seed)
        for _ in range(steps):
            step_start = time_module.perf_counter()
            obs = env.step(scan_target(config, env.time, args.scan_hz))
            if args.render:
                env.sync_viewer()
                if args.realtime:
                    remaining = config.control_dt - (time_module.perf_counter() - step_start)
                    if remaining > 0.0:
                        time_module.sleep(remaining)
        if args.save_final_frame is not None:
            args.save_final_frame.parent.mkdir(parents=True, exist_ok=True)
            env.save_frame(str(args.save_final_frame))
        print(f"Scan complete: {steps} pas, angle final AS5600 {obs.as5600_deg:.2f} deg")
    finally:
        env.close()


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "qualification":
        cmd_qualification(args)
    elif args.command == "corpus":
        cmd_corpus(args)
    else:
        cmd_scan(args)


if __name__ == "__main__":
    main()
