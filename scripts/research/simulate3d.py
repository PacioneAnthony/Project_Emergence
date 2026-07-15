"""Run the Emergence MuJoCo 3D simulator and collect training logs.

The CSV schema, policies and CLI mirror scripts/research/simulate.py so the
existing learning pipeline consumes 3D logs unchanged.
"""

from __future__ import annotations

import argparse
import time as time_module
from pathlib import Path

from sim2d.config import SimConfig
from sim2d.logger import CSVLogger
from sim2d.policies import RandomPolicy, WallAvoidancePolicy
from sim3d.config import Body3DConfig, Sim3DConfig
from sim3d.environment import RobotSim3DEnv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate 3D robot simulation logs.")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--pwm-period", type=float, default=None)
    parser.add_argument("--scan-hz", type=float, default=0.5)
    parser.add_argument("--cone-rays", type=int, default=1, help="Ultrasonic rays over the +/-15 deg cone (1 = sim2d parity).")
    parser.add_argument("--output", type=Path, default=Path("data/raw/sim3d_log.csv"))
    parser.add_argument("--policy", choices=("avoid", "random"), default="avoid")
    parser.add_argument("--collision-ends-episode", action="store_true")
    parser.add_argument("--no-domain-randomization", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--realtime", action="store_true", help="Pace the render loop at wall-clock speed.")
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

    env = RobotSim3DEnv(Sim3DConfig(base=config, body=Body3DConfig(cone_rays=args.cone_rays)))
    policy = (
        WallAvoidancePolicy(config.robot, scan_hz=args.scan_hz)
        if args.policy == "avoid"
        else RandomPolicy(config.robot, args.seed)
    )

    total_steps = 0
    collisions = 0
    completed_episodes = 0
    try:
        with CSVLogger(args.output) as logger:
            for episode in range(args.episodes):
                obs = env.reset(seed=args.seed + episode)
                for step in range(args.steps):
                    step_start = time_module.perf_counter()
                    action = policy(obs)
                    next_obs, reward, done, info = env.step(action)
                    logger.write(episode, step, obs, action, next_obs, reward, done, info)

                    if args.render:
                        env.sync_viewer()
                        if args.realtime:
                            remaining = env.config.dt - (time_module.perf_counter() - step_start)
                            if remaining > 0.0:
                                time_module.sleep(remaining)

                    total_steps += 1
                    collisions += int(bool(info["collision"]))
                    obs = next_obs
                    if done:
                        completed_episodes += 1
                        break

        if args.save_final_frame:
            args.save_final_frame.parent.mkdir(parents=True, exist_ok=True)
            env.save_frame(str(args.save_final_frame))
    finally:
        env.close()

    seconds = total_steps * env.config.dt
    print(
        f"Simulation 3D complete: {total_steps} steps ({seconds:.1f}s simulated), "
        f"{collisions} collision ticks, {completed_episodes}/{args.episodes} episodes done, log={args.output}"
    )


if __name__ == "__main__":
    main()
