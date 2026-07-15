"""Run large simulation campaigns across CPU workers (Phase C).

Examples:

    # 64 bootstrap episodes with the scripted avoidance policy, 12 workers
    python -m scripts.research.rollout_parallel --policy avoid --episodes 64 \
        --steps 6000 --workers 12 --output data/raw/sim3d_bootstrap_parallel.csv

    # Evaluate an LNN checkpoint on 30 nominal episodes
    python -m scripts.research.rollout_parallel --policy lnn \
        --checkpoint models/lnn_zoh_scan05_medium_dagger_002.pth \
        --episodes 30 --steps 6000 --seed 1001 --no-domain-randomization
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sim3d.parallel import CampaignSpec, run_campaign


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Episode-parallel simulation campaigns.")
    parser.add_argument("--policy", choices=("avoid", "random", "lnn"), default="avoid")
    parser.add_argument("--checkpoint", type=Path, default=None, help="Required for --policy lnn.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cpu", help="LNN inference device per worker.")
    parser.add_argument("--backend", choices=("sim3d", "sim2d"), default="sim3d")
    parser.add_argument("--episodes", type=int, default=16)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=1001)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--pwm-period", type=float, default=None)
    parser.add_argument("--scan-hz", type=float, default=0.5)
    parser.add_argument("--workers", type=int, default=None, help="Default: CPU count, capped at episodes.")
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--collision-ends-episode", action="store_true")
    parser.add_argument("--output", type=Path, default=None, help="Merged CSV log (omit to skip logging).")
    parser.add_argument("--metrics-output", type=Path, default=Path("data/processed/experiments/parallel_campaign/metrics.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.policy == "lnn" and args.checkpoint is None:
        raise ValueError("--policy lnn requires --checkpoint.")
    if args.episodes <= 0 or args.steps <= 0:
        raise ValueError("--episodes and --steps must be > 0.")

    spec = CampaignSpec(
        policy=args.policy,
        checkpoint=str(args.checkpoint) if args.checkpoint else None,
        device=args.device,
        backend=args.backend,
        episodes=args.episodes,
        steps=args.steps,
        base_seed=args.seed,
        dt=args.dt,
        pwm_period=args.pwm_period,
        scan_hz=args.scan_hz,
        domain_randomization=not args.no_domain_randomization,
        collision_ends_episode=args.collision_ends_episode,
    )
    metrics = run_campaign(spec, workers=args.workers, output=args.output, metrics_output=args.metrics_output)
    print(
        f"Campaign complete: {metrics['episodes']} episodes, {metrics['total_steps']} steps "
        f"({metrics['simulated_seconds']:.0f}s simules) en {metrics['wall_seconds']:.1f}s murale "
        f"avec {metrics['workers']} workers -> {metrics['steps_per_second']:.0f} pas/s agreges, "
        f"collision_ticks={metrics['collision_ticks']} ({100 * metrics['collision_rate']:.2f}%) "
        f"events={metrics['collision_events']} metrics={args.metrics_output}"
    )


if __name__ == "__main__":
    main()
