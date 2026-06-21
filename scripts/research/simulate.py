"""Run the Emergence 2D simulator and collect training logs."""

from __future__ import annotations

import argparse
from pathlib import Path

from sim2d.config import SimConfig
from sim2d.environment import RobotSimEnv
from sim2d.logger import CSVLogger
from sim2d.policies import RandomPolicy, WallAvoidancePolicy
from sim2d.renderer import MatplotlibRenderer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate 2D robot simulation logs.")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--pwm-period", type=float, default=None)
    parser.add_argument("--scan-hz", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path("data/raw/sim2d_log.csv"))
    parser.add_argument("--policy", choices=("avoid", "random"), default="avoid")
    parser.add_argument("--collision-ends-episode", action="store_true")
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--save-final-frame", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = SimConfig(
        max_steps=args.steps,
        seed=args.seed,
        domain_randomization=not args.no_domain_randomization,
    )
    if args.dt is not None:
        config.dt = args.dt
    if args.pwm_period is not None:
        config.robot.pwm_period = args.pwm_period
    config.reward.collision_ends_episode = args.collision_ends_episode
    env = RobotSimEnv(config)
    policy = (
        WallAvoidancePolicy(config.robot, scan_hz=args.scan_hz)
        if args.policy == "avoid"
        else RandomPolicy(config.robot, args.seed)
    )
    renderer = MatplotlibRenderer() if args.render or args.save_final_frame else None

    total_steps = 0
    collisions = 0
    completed_episodes = 0
    with CSVLogger(args.output) as logger:
        for episode in range(args.episodes):
            obs = env.reset(seed=args.seed + episode)
            for step in range(args.steps):
                action = policy(obs)
                next_obs, reward, done, info = env.step(action)
                logger.write(episode, step, obs, action, next_obs, reward, done, info)

                if args.render and renderer is not None and step % 2 == 0:
                    renderer.render(env, pause=0.001)

                total_steps += 1
                collisions += int(bool(info["collision"]))
                obs = next_obs
                if done:
                    completed_episodes += 1
                    break

    if renderer is not None and args.save_final_frame:
        renderer.render(env, save_path=args.save_final_frame)

    seconds = total_steps * config.dt
    print(
        f"Simulation complete: {total_steps} steps ({seconds:.1f}s simulated), "
        f"{collisions} collision ticks, {completed_episodes}/{args.episodes} episodes done, log={args.output}"
    )


if __name__ == "__main__":
    main()
