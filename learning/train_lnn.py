"""Train a standalone LNN controller by imitating simulator actuator actions."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from common.types import Action
from learning.datasets import load_simulation_csv
from learning.lnn import AuxiliaryLatentHead, SimpleLNN
from sim2d.config import RobotConfig, SimConfig
from sim2d.environment import RobotSimEnv

try:
    import torch
except ModuleNotFoundError:
    torch = None


ACTION_FIELD_NAMES = ("v_cmd", "omega_cmd", "servo_target")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a standalone LNN controller from sim2d logs.")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("models/lnn_controller.pth"))
    parser.add_argument("--metrics-output", type=Path, default=Path("data/processed/lnn_metrics.json"))
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=256, help="Number of random sequences per optimization step.")
    parser.add_argument("--sequence-length", type=int, default=64)
    parser.add_argument("--state-dim", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--tau-min", type=float, default=0.05)
    parser.add_argument("--tau-max", type=float, default=1.5)
    parser.add_argument("--state-smooth-weight", type=float, default=1e-3)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--eval-every", type=int, default=25)
    parser.add_argument("--max-eval-sequences", type=int, default=2048)
    parser.add_argument("--early-stopping-patience", type=int, default=20)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument(
        "--jepa-checkpoint",
        type=Path,
        default=None,
        help="Optional frozen JEPA checkpoint. When set, LNN input becomes [current obs, JEPA latent context].",
    )
    parser.add_argument("--jepa-batch-size", type=int, default=4096)
    parser.add_argument(
        "--jepa-aux-checkpoint",
        type=Path,
        default=None,
        help="Frozen JEPA target used only as an auxiliary hidden-state training loss.",
    )
    parser.add_argument("--jepa-aux-weight", type=float, default=0.0)
    parser.add_argument(
        "--jepa-aux-final-weight",
        type=float,
        default=None,
        help="Optional final auxiliary weight. Enables a cosine schedule from --jepa-aux-weight.",
    )
    parser.add_argument("--jepa-aux-head-hidden-dim", type=int, default=128)
    parser.add_argument(
        "--rollout-select",
        action="store_true",
        help="Select the best checkpoint with nominal and randomized mini-rollouts instead of offline RMSE.",
    )
    parser.add_argument("--rollout-eval-every", type=int, default=250)
    parser.add_argument("--rollout-eval-episodes", type=int, default=5)
    parser.add_argument("--rollout-eval-steps", type=int, default=2000)
    parser.add_argument("--rollout-nominal-seed", type=int, default=3101)
    parser.add_argument("--rollout-randomized-seed", type=int, default=3201)
    parser.add_argument(
        "--rollout-min-mean-forward-speed",
        type=float,
        default=0.05,
        help="Minimum mean forward command required before a mini-rollout checkpoint is eligible.",
    )
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser


def main() -> None:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required to train the LNN controller.")

    args = build_parser().parse_args()
    validate_args(args)
    device = resolve_device(args.device)
    set_training_seed(args.seed)

    arrays, input_meta = load_lnn_training_arrays(args, device)
    obs_np = arrays["obs"].astype(np.float32)
    actions_np = arrays["action"].astype(np.float32)
    episodes = arrays.get("episode")
    if episodes is None:
        episodes = np.zeros(len(obs_np), dtype=np.int64)
    else:
        episodes = episodes.astype(np.int64)

    dt = float(args.dt if args.dt is not None else infer_dt(arrays))
    train_eps, val_eps = split_episode_ids(episodes, args.val_fraction)
    train_starts = sequence_start_indices(episodes, args.sequence_length, train_eps)
    val_starts = sequence_start_indices(episodes, args.sequence_length, val_eps)
    if len(train_starts) == 0 or len(val_starts) == 0:
        raise ValueError("Not enough same-episode samples to build train/validation LNN sequences.")

    scales = action_scales_from_config(RobotConfig())
    actions_norm_np = normalize_actions(actions_np, scales)
    aux_targets_np, aux_meta = prepare_auxiliary_targets(arrays, episodes, train_eps, input_meta)

    obs = torch.from_numpy(obs_np).float().to(device)
    actions_norm = torch.from_numpy(actions_norm_np).float().to(device)
    actions_physical = torch.from_numpy(actions_np).float().to(device)
    train_starts_t = torch.from_numpy(train_starts).long().to(device)
    val_starts_t = torch.from_numpy(val_starts).long().to(device)
    offsets = torch.arange(args.sequence_length, device=device).long()
    scales_t = torch.from_numpy(scales).float().to(device)
    aux_targets = torch.from_numpy(aux_targets_np).float().to(device) if aux_targets_np is not None else None

    model = SimpleLNN(
        state_dim=args.state_dim,
        input_dim=obs.shape[-1],
        action_dim=actions_norm.shape[-1],
        hidden_dim=args.hidden_dim,
        tau_min=args.tau_min,
        tau_max=args.tau_max,
    ).to(device)
    aux_head = None
    if aux_targets is not None:
        aux_head = AuxiliaryLatentHead(
            state_dim=args.state_dim,
            latent_dim=aux_targets.shape[-1],
            hidden_dim=args.jepa_aux_head_hidden_dim,
        ).to(device)
    optimizer_parameters = list(model.parameters()) + (list(aux_head.parameters()) if aux_head is not None else [])
    optimizer = torch.optim.AdamW(optimizer_parameters, lr=args.lr, weight_decay=args.weight_decay)

    print(
        f"[i] LNN device={device} samples={len(obs_np)} train_sequences={len(train_starts)} "
        f"val_sequences={len(val_starts)} seq_len={args.sequence_length} dt={dt:.5f}",
        flush=True,
    )

    best_rmse = float("inf")
    best_offline_rmse = float("inf")
    best_offline_epoch = 0
    best_selection_key = (float("inf"), float("inf"), float("inf"), float("inf"), float("inf"))
    best_rollout_metrics: dict[str, Any] | None = None
    rollout_history: list[dict[str, Any]] = []
    best_epoch = 0
    best_state = None
    best_aux_state = None
    checks_since_improvement = 0
    early_stopped = False
    stopped_epoch = 0
    last_metrics: dict[str, Any] | None = None

    for epoch in range(1, args.epochs + 1):
        stopped_epoch = epoch
        model.train()
        current_aux_weight = auxiliary_weight_for_epoch(
            epoch,
            args.epochs,
            args.jepa_aux_weight,
            args.jepa_aux_final_weight,
        )
        batch_starts = sample_starts(train_starts_t, args.batch_size)
        idx = batch_starts[:, None] + offsets[None, :]
        loss, action_mse, smooth_loss, aux_loss = lnn_sequence_loss(
            model,
            obs[idx],
            actions_norm[idx],
            dt=dt,
            state_smooth_weight=args.state_smooth_weight,
            aux_head=aux_head,
            aux_target_seq=aux_targets[idx] if aux_targets is not None else None,
            aux_weight=current_aux_weight,
        )

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(optimizer_parameters, 1.0)
        optimizer.step()

        if epoch == 1 or epoch % args.eval_every == 0:
            metrics = evaluate_lnn_sequences(
                model,
                obs,
                actions_norm,
                actions_physical,
                val_starts_t,
                offsets,
                scales_t,
                dt=dt,
                batch_size=args.batch_size,
                max_sequences=args.max_eval_sequences,
                aux_head=aux_head,
                aux_targets=aux_targets,
                aux_target_mean=aux_meta.get("target_mean") if aux_meta else None,
                aux_target_std=aux_meta.get("target_std") if aux_meta else None,
            )
            last_metrics = metrics
            val_rmse = float(metrics["rmse_mean"])
            if val_rmse < best_offline_rmse:
                best_offline_rmse = val_rmse
                best_offline_epoch = epoch

            selection_improved = False
            rollout_metrics = None
            rollout_due = args.rollout_select and (epoch == 1 or epoch % args.rollout_eval_every == 0)
            if rollout_due:
                rollout_metrics = evaluate_lnn_mini_rollouts(
                    model,
                    scales,
                    dt=dt,
                    device=device,
                    episodes=args.rollout_eval_episodes,
                    steps=args.rollout_eval_steps,
                    nominal_seed=args.rollout_nominal_seed,
                    randomized_seed=args.rollout_randomized_seed,
                    min_mean_forward_speed=args.rollout_min_mean_forward_speed,
                )
                rollout_metrics["epoch"] = int(epoch)
                rollout_metrics["validation_rmse"] = val_rmse
                rollout_history.append(rollout_metrics)
                selection_key = rollout_selection_key(rollout_metrics)
                if selection_key < best_selection_key:
                    best_selection_key = selection_key
                    best_rollout_metrics = rollout_metrics
                    selection_improved = True
            elif not args.rollout_select and val_rmse < best_rmse:
                selection_improved = True

            if selection_improved:
                best_rmse = val_rmse
                best_epoch = epoch
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                best_aux_state = (
                    {key: value.detach().cpu().clone() for key, value in aux_head.state_dict().items()}
                    if aux_head is not None
                    else None
                )
                checks_since_improvement = 0
            elif not args.rollout_select or rollout_due:
                checks_since_improvement += 1

            message = (
                f"epoch={epoch:04d} loss={loss.item():.6f} action_mse={action_mse:.6f} "
                f"smooth={smooth_loss:.6f} aux={aux_loss:.6f} aux_weight={current_aux_weight:.6f} "
                f"val_rmse={val_rmse:.6f} offline_best={best_offline_rmse:.6f}@{best_offline_epoch}"
            )
            if rollout_metrics is not None:
                message += (
                    f" rollout_worst={rollout_metrics['selection']['worst_collision_rate']:.6f}"
                    f" rollout_mean={rollout_metrics['selection']['mean_collision_rate']:.6f}"
                    f" rollout_speed={rollout_metrics['selection']['minimum_mean_forward_speed']:.6f}"
                    f" rollout_best={best_selection_key[1]:.6f}@{best_epoch}"
                )
            else:
                message += f" best={best_rmse:.6f}@{best_epoch}"
            message += f" early_stop_wait={checks_since_improvement}/{args.early_stopping_patience}"
            print(message, flush=True)
            early_stop_check = not args.rollout_select or rollout_due
            if (
                early_stop_check
                and args.early_stopping_patience > 0
                and checks_since_improvement >= args.early_stopping_patience
            ):
                early_stopped = True
                print(
                    f"Early stopping LNN training at epoch={epoch} best_epoch={best_epoch}",
                    flush=True,
                )
                break

    if best_state is not None:
        model.load_state_dict(best_state)
        if aux_head is not None and best_aux_state is not None:
            aux_head.load_state_dict(best_aux_state)
    if last_metrics is None or stopped_epoch != best_epoch:
        last_metrics = evaluate_lnn_sequences(
            model,
            obs,
            actions_norm,
            actions_physical,
            val_starts_t,
            offsets,
            scales_t,
            dt=dt,
            batch_size=args.batch_size,
            max_sequences=args.max_eval_sequences,
            aux_head=aux_head,
            aux_targets=aux_targets,
            aux_target_mean=aux_meta.get("target_mean") if aux_meta else None,
            aux_target_std=aux_meta.get("target_std") if aux_meta else None,
        )

    metrics = {
        "log": str(args.log),
        "checkpoint": str(args.output),
        "input": input_meta,
        "auxiliary": serializable_aux_meta(aux_meta, args),
        "n_samples": int(len(obs_np)),
        "n_train_sequences": int(len(train_starts)),
        "n_val_sequences": int(len(val_starts)),
        "sequence_length": int(args.sequence_length),
        "dt": float(dt),
        "state_dim": int(args.state_dim),
        "hidden_dim": int(args.hidden_dim),
        "seed": int(args.seed),
        "best_epoch": int(best_epoch),
        "best_offline_epoch": int(best_offline_epoch),
        "best_offline_validation_rmse": float(best_offline_rmse),
        "stopped_epoch": int(stopped_epoch),
        "early_stopped": bool(early_stopped),
        "action_scales": {name: float(value) for name, value in zip(ACTION_FIELD_NAMES, scales)},
        "validation": last_metrics,
        "selection": {
            "mode": "mini_rollout" if args.rollout_select else "offline_rmse",
            "best_rollout": best_rollout_metrics,
            "rollout_history": rollout_history,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": {key: value.detach().cpu().clone() for key, value in model.state_dict().items()},
            "state_dim": int(args.state_dim),
            "input_dim": int(obs.shape[-1]),
            "action_dim": int(actions_norm.shape[-1]),
            "hidden_dim": int(args.hidden_dim),
            "tau_min": float(args.tau_min),
            "tau_max": float(args.tau_max),
            "dt": float(dt),
            "sequence_length": int(args.sequence_length),
            "seed": int(args.seed),
            "action_scales": scales.astype(float).tolist(),
            "best_epoch": int(best_epoch),
            "best_validation_rmse": float(best_rmse),
            "best_offline_epoch": int(best_offline_epoch),
            "best_offline_validation_rmse": float(best_offline_rmse),
            "selection_mode": "mini_rollout" if args.rollout_select else "offline_rmse",
            "best_rollout_metrics": best_rollout_metrics,
            "jepa_auxiliary": serializable_aux_meta(aux_meta, args),
            "auxiliary_head_state_dict": (
                {key: value.detach().cpu().clone() for key, value in aux_head.state_dict().items()}
                if aux_head is not None
                else None
            ),
            **checkpoint_input_meta(input_meta),
        },
        args.output,
    )
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Saved LNN checkpoint to {args.output} (best_epoch={best_epoch}, best_rmse={best_rmse:.6f})", flush=True)
    print(f"Saved LNN metrics to {args.metrics_output}", flush=True)


def validate_args(args: argparse.Namespace) -> None:
    if args.epochs <= 0:
        raise ValueError("--epochs must be > 0.")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be > 0.")
    if args.sequence_length <= 0:
        raise ValueError("--sequence-length must be > 0.")
    if args.eval_every <= 0:
        raise ValueError("--eval-every must be > 0.")
    if args.early_stopping_patience < 0:
        raise ValueError("--early-stopping-patience must be >= 0.")
    if args.jepa_batch_size <= 0:
        raise ValueError("--jepa-batch-size must be > 0.")
    if args.jepa_checkpoint is not None and not args.jepa_checkpoint.exists():
        raise FileNotFoundError(f"JEPA checkpoint not found: {args.jepa_checkpoint}")
    if args.jepa_aux_checkpoint is not None and not args.jepa_aux_checkpoint.exists():
        raise FileNotFoundError(f"JEPA auxiliary checkpoint not found: {args.jepa_aux_checkpoint}")
    if args.jepa_checkpoint is not None and args.jepa_aux_checkpoint is not None:
        raise ValueError("--jepa-checkpoint and --jepa-aux-checkpoint are mutually exclusive.")
    if args.jepa_aux_weight < 0.0:
        raise ValueError("--jepa-aux-weight must be >= 0.")
    if args.jepa_aux_final_weight is not None and args.jepa_aux_final_weight < 0.0:
        raise ValueError("--jepa-aux-final-weight must be >= 0.")
    if args.jepa_aux_checkpoint is None and args.jepa_aux_weight > 0.0:
        raise ValueError("--jepa-aux-weight requires --jepa-aux-checkpoint.")
    if args.jepa_aux_final_weight is not None and args.jepa_aux_checkpoint is None:
        raise ValueError("--jepa-aux-final-weight requires --jepa-aux-checkpoint.")
    if args.jepa_aux_checkpoint is not None and args.jepa_aux_weight <= 0.0:
        raise ValueError("--jepa-aux-checkpoint requires --jepa-aux-weight > 0.")
    if args.jepa_aux_head_hidden_dim <= 0:
        raise ValueError("--jepa-aux-head-hidden-dim must be > 0.")
    if args.rollout_eval_every <= 0:
        raise ValueError("--rollout-eval-every must be > 0.")
    if args.rollout_eval_episodes <= 0 or args.rollout_eval_steps <= 0:
        raise ValueError("Rollout evaluation episodes and steps must be > 0.")
    if args.rollout_min_mean_forward_speed < 0.0:
        raise ValueError("--rollout-min-mean-forward-speed must be >= 0.")
    if args.rollout_select and args.jepa_checkpoint is not None:
        raise ValueError("--rollout-select currently supports raw-observation LNN inputs only.")


def evaluate_lnn_mini_rollouts(
    model,
    action_scales: np.ndarray,
    *,
    dt: float,
    device,
    episodes: int,
    steps: int,
    nominal_seed: int,
    randomized_seed: int,
    min_mean_forward_speed: float,
) -> dict[str, Any]:
    was_training = model.training
    model.eval()
    results: dict[str, Any] = {}
    scales_t = torch.from_numpy(action_scales.astype(np.float32)).to(device)

    with torch.no_grad():
        for name, randomized, base_seed in (
            ("nominal", False, nominal_seed),
            ("randomized", True, randomized_seed),
        ):
            config = SimConfig(
                dt=float(dt),
                max_steps=int(steps),
                seed=int(base_seed),
                domain_randomization=bool(randomized),
            )
            config.robot.pwm_period = 0.02
            env = RobotSimEnv(config)
            total_steps = 0
            collision_ticks = 0
            collision_events = 0
            reward_total = 0.0
            forward_command_total = 0.0

            for episode in range(episodes):
                obs = env.reset(seed=base_seed + episode)
                state = torch.zeros((1, int(model.state_dim)), device=device)
                in_collision = False
                for _ in range(steps):
                    obs_t = torch.from_numpy(obs.as_array()).float().unsqueeze(0).to(device)
                    action = (model.act(state, obs_t) * scales_t).squeeze(0).detach().cpu().numpy()
                    next_obs, reward, done, info = env.step(Action.from_array(action.tolist()))
                    state = model.step(state, obs_t, dt)
                    collision = bool(info.get("collision", False))
                    total_steps += 1
                    collision_ticks += int(collision)
                    collision_events += int(collision and not in_collision)
                    reward_total += float(reward)
                    forward_command_total += float(action[0])
                    in_collision = collision
                    obs = next_obs
                    if done:
                        break

            denominator = max(1, total_steps)
            results[name] = {
                "episodes": int(episodes),
                "steps": int(total_steps),
                "base_seed": int(base_seed),
                "collision_ticks": int(collision_ticks),
                "collision_rate": float(collision_ticks / denominator),
                "collision_events": int(collision_events),
                "collision_events_per_1000_steps": float(1000.0 * collision_events / denominator),
                "reward_total": float(reward_total),
                "reward_mean_per_step": float(reward_total / denominator),
                "mean_forward_speed": float(forward_command_total / denominator),
            }

    if was_training:
        model.train()
    nominal_rate = float(results["nominal"]["collision_rate"])
    randomized_rate = float(results["randomized"]["collision_rate"])
    nominal_events = float(results["nominal"]["collision_events_per_1000_steps"])
    randomized_events = float(results["randomized"]["collision_events_per_1000_steps"])
    worst_reward = min(
        float(results["nominal"]["reward_mean_per_step"]),
        float(results["randomized"]["reward_mean_per_step"]),
    )
    minimum_forward_speed = min(
        float(results["nominal"]["mean_forward_speed"]),
        float(results["randomized"]["mean_forward_speed"]),
    )
    activity_shortfall = max(0.0, float(min_mean_forward_speed) - minimum_forward_speed)
    results["selection"] = {
        "eligible": activity_shortfall <= 0.0,
        "required_mean_forward_speed": float(min_mean_forward_speed),
        "minimum_mean_forward_speed": minimum_forward_speed,
        "activity_shortfall": activity_shortfall,
        "worst_collision_rate": max(nominal_rate, randomized_rate),
        "mean_collision_rate": 0.5 * (nominal_rate + randomized_rate),
        "worst_events_per_1000_steps": max(nominal_events, randomized_events),
        "worst_reward_mean_per_step": worst_reward,
    }
    return results


def rollout_selection_key(metrics: dict[str, Any]) -> tuple[float, float, float, float, float]:
    selection = metrics["selection"]
    return (
        float(selection.get("activity_shortfall", 0.0)),
        float(selection["worst_collision_rate"]),
        float(selection["mean_collision_rate"]),
        float(selection["worst_events_per_1000_steps"]),
        -float(selection["worst_reward_mean_per_step"]),
    )


def load_lnn_training_arrays(args: argparse.Namespace, device) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if args.jepa_aux_checkpoint is not None:
        from learning.jepa_lnn_features import build_jepa_auxiliary_arrays

        return build_jepa_auxiliary_arrays(
            args.log,
            args.jepa_aux_checkpoint,
            device=device,
            batch_size=args.jepa_batch_size,
        )
    if args.jepa_checkpoint is None:
        return load_simulation_csv(args.log), {"input_mode": "raw_observation", "lnn_input_dim": 3}

    from learning.jepa_lnn_features import build_jepa_lnn_arrays

    arrays, meta = build_jepa_lnn_arrays(
        args.log,
        args.jepa_checkpoint,
        device=device,
        batch_size=args.jepa_batch_size,
    )
    return arrays, meta


def prepare_auxiliary_targets(
    arrays: dict[str, np.ndarray],
    episodes: np.ndarray,
    train_eps: set[int],
    input_meta: dict[str, Any],
) -> tuple[np.ndarray | None, dict[str, Any] | None]:
    targets = arrays.get("jepa_aux_target")
    if targets is None:
        return None, None
    train_mask = np.array([int(episode) in train_eps for episode in episodes], dtype=bool)
    mean = targets[train_mask].mean(axis=0).astype(np.float32)
    std = np.maximum(targets[train_mask].std(axis=0), 1e-4).astype(np.float32)
    normalized = ((targets.astype(np.float32) - mean) / std).astype(np.float32)
    return normalized, {
        "enabled": True,
        "checkpoint": input_meta.get("jepa_aux_checkpoint"),
        "context_steps": input_meta.get("jepa_aux_context_steps"),
        "latent_dim": int(targets.shape[-1]),
        "target_encoder": input_meta.get("jepa_aux_target_encoder"),
        "target_mean": mean,
        "target_std": std,
    }


def serializable_aux_meta(aux_meta: dict[str, Any] | None, args: argparse.Namespace) -> dict[str, Any]:
    if aux_meta is None:
        return {"enabled": False}
    return {
        "enabled": True,
        "checkpoint": aux_meta["checkpoint"],
        "context_steps": int(aux_meta["context_steps"]),
        "latent_dim": int(aux_meta["latent_dim"]),
        "target_encoder": aux_meta["target_encoder"],
        "weight": float(args.jepa_aux_weight),
        "final_weight": (
            float(args.jepa_aux_final_weight) if args.jepa_aux_final_weight is not None else float(args.jepa_aux_weight)
        ),
        "weight_schedule": "cosine" if args.jepa_aux_final_weight is not None else "constant",
        "head_hidden_dim": int(args.jepa_aux_head_hidden_dim),
        "head_removed_at_inference": True,
        "target_mean": aux_meta["target_mean"].astype(float).tolist(),
        "target_std": aux_meta["target_std"].astype(float).tolist(),
    }


def auxiliary_weight_for_epoch(
    epoch: int,
    total_epochs: int,
    initial_weight: float,
    final_weight: float | None,
) -> float:
    if final_weight is None or total_epochs <= 1:
        return float(initial_weight if final_weight is None else final_weight)
    progress = min(1.0, max(0.0, (float(epoch) - 1.0) / (float(total_epochs) - 1.0)))
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
    return float(final_weight + (initial_weight - final_weight) * cosine)


def checkpoint_input_meta(input_meta: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "input_mode",
        "jepa_checkpoint",
        "jepa_context_steps",
        "jepa_obs_dim",
        "jepa_action_dim",
        "jepa_latent_dim",
        "jepa_hidden_dim",
        "jepa_decoded_obs_dim",
        "context_action_source",
    )
    return {key: input_meta[key] for key in keys if key in input_meta}


def resolve_device(name: str):
    if name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is False.")
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def set_training_seed(seed: int) -> None:
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def infer_dt(arrays: dict[str, np.ndarray]) -> float:
    t = arrays.get("t")
    if t is None or len(t) < 2:
        return 0.02
    deltas = np.diff(t.astype(np.float64))
    deltas = deltas[deltas > 0.0]
    if len(deltas) == 0:
        return 0.02
    return float(np.median(deltas))


def action_scales_from_config(config: RobotConfig) -> np.ndarray:
    return np.array(
        [
            float(config.max_linear_speed),
            float(config.max_angular_speed),
            float(max(abs(config.servo_min), abs(config.servo_max))),
        ],
        dtype=np.float32,
    )


def normalize_actions(actions: np.ndarray, scales: np.ndarray) -> np.ndarray:
    normalized = actions.astype(np.float32) / scales.astype(np.float32)
    return np.clip(normalized, -1.0, 1.0).astype(np.float32)


def split_episode_ids(episodes: np.ndarray, val_fraction: float) -> tuple[set[int], set[int]]:
    unique = np.unique(episodes.astype(np.int64))
    if len(unique) <= 1:
        return {int(unique[0])}, {int(unique[0])}
    val_fraction = float(np.clip(val_fraction, 0.05, 0.95))
    train_count = max(1, int(round(len(unique) * (1.0 - val_fraction))))
    train_count = min(train_count, len(unique) - 1)
    val_count = len(unique) - train_count
    if val_count == 1:
        val_indices = {len(unique) - 1}
    else:
        val_indices = {int((i + 1) * len(unique) / (val_count + 1)) for i in range(val_count)}
    val_eps = {int(unique[i]) for i in sorted(val_indices)}
    train_eps = {int(value) for i, value in enumerate(unique) if i not in val_indices}
    return train_eps, val_eps


def sequence_start_indices(episodes: np.ndarray, sequence_length: int, allowed_episodes: set[int]) -> np.ndarray:
    starts: list[int] = []
    run_start = 0
    episodes = episodes.astype(np.int64)
    for i in range(1, len(episodes) + 1):
        if i == len(episodes) or episodes[i] != episodes[run_start]:
            episode = int(episodes[run_start])
            run_end = i
            if episode in allowed_episodes and run_end - run_start >= sequence_length:
                starts.extend(range(run_start, run_end - sequence_length + 1))
            run_start = i
    return np.array(starts, dtype=np.int64)


def sample_starts(starts: "torch.Tensor", batch_size: int) -> "torch.Tensor":
    local = torch.randint(0, len(starts), (min(batch_size, len(starts)),), device=starts.device)
    return starts[local]


def lnn_sequence_loss(
    model,
    obs_seq,
    action_seq_norm,
    dt: float,
    state_smooth_weight: float,
    aux_head=None,
    aux_target_seq=None,
    aux_weight: float = 0.0,
):
    batch_size = obs_seq.shape[0]
    x = obs_seq.new_zeros((batch_size, model.state_dim))
    action_loss = obs_seq.new_tensor(0.0)
    smooth_loss = obs_seq.new_tensor(0.0)
    aux_loss = obs_seq.new_tensor(0.0)
    for step in range(obs_seq.shape[1]):
        u = obs_seq[:, step, :]
        pred = model.act(x, u)
        action_loss = action_loss + torch.mean((pred - action_seq_norm[:, step, :]) ** 2)
        x_next = model.step(x, u, dt)
        smooth_loss = smooth_loss + torch.mean((x_next - x) ** 2)
        if aux_head is not None and aux_target_seq is not None:
            aux_prediction = aux_head(x_next)
            aux_loss = aux_loss + torch.mean((aux_prediction - aux_target_seq[:, step, :]) ** 2)
        x = x_next
    action_loss = action_loss / obs_seq.shape[1]
    smooth_loss = smooth_loss / obs_seq.shape[1]
    aux_loss = aux_loss / obs_seq.shape[1]
    total = action_loss + state_smooth_weight * smooth_loss + float(aux_weight) * aux_loss
    return total, float(action_loss.item()), float(smooth_loss.item()), float(aux_loss.item())


def evaluate_lnn_sequences(
    model,
    obs,
    actions_norm,
    actions_physical,
    starts,
    offsets,
    scales,
    dt: float,
    batch_size: int,
    max_sequences: int,
    aux_head=None,
    aux_targets=None,
    aux_target_mean=None,
    aux_target_std=None,
) -> dict[str, Any]:
    model.eval()
    if aux_head is not None:
        aux_head.eval()
    if len(starts) > max_sequences:
        local = torch.linspace(0, len(starts) - 1, max_sequences, device=starts.device).long()
        starts = starts[local]

    squared_sum = torch.zeros(actions_physical.shape[-1], device=obs.device)
    absolute_sum = torch.zeros(actions_physical.shape[-1], device=obs.device)
    normalized_squared_sum = torch.zeros(actions_norm.shape[-1], device=obs.device)
    count = 0
    aux_squared_sum = 0.0
    aux_raw_squared_sum = 0.0
    aux_count = 0
    with torch.no_grad():
        for start in range(0, len(starts), batch_size):
            batch_starts = starts[start : start + batch_size]
            idx = batch_starts[:, None] + offsets[None, :]
            obs_seq = obs[idx]
            target_norm = actions_norm[idx]
            target_physical = actions_physical[idx]
            pred_norm, state_seq = predict_lnn_sequence_with_states(model, obs_seq, dt)
            pred_physical = pred_norm * scales
            error = pred_physical - target_physical
            norm_error = pred_norm - target_norm
            squared_sum += torch.sum(error.pow(2), dim=(0, 1))
            absolute_sum += torch.sum(torch.abs(error), dim=(0, 1))
            normalized_squared_sum += torch.sum(norm_error.pow(2), dim=(0, 1))
            count += int(error.shape[0] * error.shape[1])
            if aux_head is not None and aux_targets is not None:
                aux_prediction = aux_head(state_seq)
                aux_target = aux_targets[idx]
                aux_error = aux_prediction - aux_target
                aux_squared_sum += float(torch.sum(aux_error.pow(2)).item())
                if aux_target_mean is not None and aux_target_std is not None:
                    mean_t = torch.from_numpy(aux_target_mean).float().to(obs.device)
                    std_t = torch.from_numpy(aux_target_std).float().to(obs.device)
                    raw_error = (aux_prediction * std_t + mean_t) - (aux_target * std_t + mean_t)
                    aux_raw_squared_sum += float(torch.sum(raw_error.pow(2)).item())
                aux_count += int(aux_error.numel())

    rmse = torch.sqrt(squared_sum / count).cpu().numpy()
    mae = (absolute_sum / count).cpu().numpy()
    norm_rmse = torch.sqrt(normalized_squared_sum / count).cpu().numpy()
    model.train()
    if aux_head is not None:
        aux_head.train()
    result = {
        "rmse_mean": float(np.mean(rmse)),
        "normalized_rmse_mean": float(np.mean(norm_rmse)),
        "per_action": {
            name: {
                "rmse": float(rmse[i]),
                "mae": float(mae[i]),
                "normalized_rmse": float(norm_rmse[i]),
            }
            for i, name in enumerate(ACTION_FIELD_NAMES)
        },
    }
    if aux_count > 0:
        result["auxiliary"] = {
            "normalized_mse": float(aux_squared_sum / aux_count),
            "normalized_rmse": float(np.sqrt(aux_squared_sum / aux_count)),
            "latent_rmse": float(np.sqrt(aux_raw_squared_sum / aux_count)) if aux_raw_squared_sum > 0.0 else None,
        }
    return result


def predict_lnn_sequence(model, obs_seq, dt: float):
    predictions, _ = predict_lnn_sequence_with_states(model, obs_seq, dt)
    return predictions


def predict_lnn_sequence_with_states(model, obs_seq, dt: float):
    batch_size = obs_seq.shape[0]
    x = obs_seq.new_zeros((batch_size, model.state_dim))
    predictions = []
    states = []
    for step in range(obs_seq.shape[1]):
        u = obs_seq[:, step, :]
        predictions.append(model.act(x, u))
        x = model.step(x, u, dt)
        states.append(x)
    return torch.stack(predictions, dim=1), torch.stack(states, dim=1)


if __name__ == "__main__":
    main()
