"""Run a longer JEPA data -> train -> evaluate experiment.

This is intentionally a thin orchestrator around the existing CLIs so every
artifact can still be reproduced manually.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a full JEPA overnight experiment.")
    parser.add_argument("--tag", default=None)
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=404)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--pwm-period", type=float, default=None)
    parser.add_argument("--scan-hz", type=float, default=0.5)
    parser.add_argument("--epochs", type=int, default=10000)
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument("--context-steps", type=int, default=4)
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--obs-loss-weight", type=float, default=0.05)
    parser.add_argument("--distance-loss-weight", type=float, default=4.0)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--eval-every", type=int, default=1000)
    parser.add_argument("--eval-samples", type=int, default=131072)
    parser.add_argument("--log-every", type=int, default=250)
    parser.add_argument("--early-stopping-patience", type=int, default=5)
    parser.add_argument("--early-stopping-min-delta", type=float, default=0.0)
    parser.add_argument("--refine-decoder", action="store_true")
    parser.add_argument("--refine-decoder-epochs", type=int, default=2000)
    parser.add_argument("--refine-decoder-lr", type=float, default=1e-3)
    parser.add_argument("--refine-decoder-distance-loss-weight", type=float, default=1.0)
    parser.add_argument("--refine-decoder-eval-every", type=int, default=25)
    parser.add_argument("--refine-decoder-patience", type=int, default=20)
    parser.add_argument("--skip-sim", action="store_true")
    parser.add_argument("--log", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    tag = args.tag or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("data/processed/experiments") / tag
    run_dir.mkdir(parents=True, exist_ok=True)

    sim_log = args.log or Path("data/raw") / f"sim2d_{tag}.csv"
    checkpoint = Path("models") / f"sensor_jepa_{tag}.pth"
    refined_checkpoint = Path("models") / f"sensor_jepa_{tag}_decoder_refined.pth"
    eval_checkpoint = refined_checkpoint if args.refine_decoder else checkpoint
    eval_dir = run_dir / "eval"

    commands = []
    if not args.skip_sim:
        simulate_argv = [
            sys.executable,
            "-u",
            "-m",
            "scripts.research.simulate",
            "--episodes",
            str(args.episodes),
            "--steps",
            str(args.steps),
            "--seed",
            str(args.seed),
            "--output",
            str(sim_log),
        ]
        simulate_argv.extend(["--scan-hz", str(args.scan_hz)])
        if args.dt is not None:
            simulate_argv.extend(["--dt", str(args.dt)])
        if args.pwm_period is not None:
            simulate_argv.extend(["--pwm-period", str(args.pwm_period)])
        commands.append(("simulate", simulate_argv))

    commands.append(
        (
            "train",
            [
                sys.executable,
                "-u",
                "-m",
                "learning.train_jepa",
                "--log",
                str(sim_log),
                "--epochs",
                str(args.epochs),
                "--batch-size",
                str(args.batch_size),
                "--context-steps",
                str(args.context_steps),
                "--latent-dim",
                str(args.latent_dim),
                "--hidden-dim",
                str(args.hidden_dim),
                "--lr",
                str(args.lr),
                "--obs-loss-weight",
                str(args.obs_loss_weight),
                "--distance-loss-weight",
                str(args.distance_loss_weight),
                "--device",
                args.device,
                "--eval-every",
                str(args.eval_every),
                "--eval-samples",
                str(args.eval_samples),
                "--log-every",
                str(args.log_every),
                "--early-stopping-patience",
                str(args.early_stopping_patience),
                "--early-stopping-min-delta",
                str(args.early_stopping_min_delta),
                "--output",
                str(checkpoint),
            ],
        )
    )
    if args.refine_decoder:
        commands.append(
            (
                "refine_decoder",
                [
                    sys.executable,
                    "-u",
                    "-m",
                    "learning.refine_jepa_decoder",
                    "--log",
                    str(sim_log),
                    "--checkpoint",
                    str(checkpoint),
                    "--output",
                    str(refined_checkpoint),
                    "--epochs",
                    str(args.refine_decoder_epochs),
                    "--batch-size",
                    str(args.batch_size),
                    "--lr",
                    str(args.refine_decoder_lr),
                    "--distance-loss-weight",
                    str(args.refine_decoder_distance_loss_weight),
                    "--eval-every",
                    str(args.refine_decoder_eval_every),
                    "--early-stopping-patience",
                    str(args.refine_decoder_patience),
                    "--device",
                    args.device,
                ],
            )
        )
    commands.append(
        (
            "evaluate",
            [
                sys.executable,
                "-u",
                "-m",
                "learning.evaluate_jepa",
                "--log",
                str(sim_log),
                "--checkpoint",
                str(eval_checkpoint),
                "--output-dir",
                str(eval_dir),
            ],
        )
    )

    summary = {
        "tag": tag,
        "run_dir": str(run_dir),
        "sim_log": str(sim_log),
        "checkpoint": str(checkpoint),
        "refined_checkpoint": str(refined_checkpoint) if args.refine_decoder else None,
        "eval_checkpoint": str(eval_checkpoint),
        "eval_dir": str(eval_dir),
        "commands": [{"name": name, "argv": argv} for name, argv in commands],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    for name, argv in commands:
        run_and_log(name, argv, run_dir / f"{name}.log")

    print(f"Experiment complete: {run_dir}")


def run_and_log(name: str, argv: list[str], log_path: Path) -> None:
    print(f"\n=== {name}: {' '.join(argv)} ===")
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            handle.write(line)
            handle.flush()
        code = process.wait()
    if code != 0:
        raise subprocess.CalledProcessError(code, argv)


if __name__ == "__main__":
    main()
