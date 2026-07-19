"""Exploration policies for the visual bench-head learning loop.

Pre-registered protocol: docs/research/active_exploration_probe.md. The head
alternates collection rounds (choosing servo targets) and training rounds of
the horizon-conditioned VisualJEPA from v3. The `active` condition picks the
angle region whose prediction error decreases fastest (learning progress, IAC
style); the `babbling` control draws targets uniformly at the same cadence,
in the same rooms, with the same model and budgets. The later `developmental`
condition is continuous and documented separately in
docs/research/developmental_curiosity_probe.md; it is not part of the completed
pre-registered campaign.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import deque
from pathlib import Path

import numpy as np

from learning.developmental_curiosity import DevelopmentalCuriosity
from learning.jepa import covariance_loss, variance_loss
from learning.train_visual_jepa import (
    ProbeHeads,
    action_sequence,
    build_pairs_multi,
    evaluate,
    load_corpus,
    normalize_action,
    resolve_device,
)
from learning.visual_jepa import VisualJEPA

try:
    import torch
except ModuleNotFoundError:
    torch = None

CAPTURE_HZ = 10.0
DECISION_FRAMES = 5  # one servo decision every 0.5 s


class UniformChooser:
    """Babbling control: uniform target at every decision."""

    def __init__(self, min_deg: float, max_deg: float):
        self.min_deg = min_deg
        self.max_deg = max_deg

    def choose(self, rng: np.random.Generator, current_deg: float | None = None) -> float:
        return float(rng.uniform(self.min_deg, self.max_deg))

    def update(self, target_deg: float, error: float) -> None:
        pass

    def update_transition(self, start_deg: float, target_deg: float, error: float) -> None:
        self.update(target_deg, error)

    def diagnostics(self) -> dict:
        return {}

    def visit_counts(self) -> list[int]:
        return []


class LearningProgressChooser:
    """Regional learning progress over angle bins (IAC-style, minimal form)."""

    def __init__(
        self,
        min_deg: float,
        max_deg: float,
        bins: int = 8,
        window: int = 40,
        min_samples: int = 6,
        epsilon: float = 0.2,
    ):
        self.min_deg = min_deg
        self.max_deg = max_deg
        self.bins = bins
        self.min_samples = min_samples
        self.epsilon = epsilon
        self.histories: list[deque[float]] = [deque(maxlen=window) for _ in range(bins)]
        self.visits = [0] * bins

    def bin_of(self, target_deg: float) -> int:
        span = self.max_deg - self.min_deg
        index = int((target_deg - self.min_deg) / span * self.bins)
        return min(max(index, 0), self.bins - 1)

    def learning_progress(self, index: int) -> float:
        history = list(self.histories[index])
        if len(history) < self.min_samples:
            return math.inf  # optimistic: unexplored regions come first
        half = len(history) // 2
        older = history[:half]
        recent = history[half:]
        return float(np.mean(older) - np.mean(recent))

    def choose(self, rng: np.random.Generator, current_deg: float | None = None) -> float:
        if rng.random() < self.epsilon:
            index = int(rng.integers(0, self.bins))
        else:
            scores = [self.learning_progress(i) for i in range(self.bins)]
            best = max(scores)
            candidates = [i for i, score in enumerate(scores) if score == best]
            index = int(rng.choice(candidates))
        self.visits[index] += 1
        span = (self.max_deg - self.min_deg) / self.bins
        return float(self.min_deg + span * (index + rng.random()))

    def update(self, target_deg: float, error: float) -> None:
        self.histories[self.bin_of(target_deg)].append(float(error))

    def update_transition(self, start_deg: float, target_deg: float, error: float) -> None:
        self.update(target_deg, error)

    def visit_counts(self) -> list[int]:
        return list(self.visits)

    def diagnostics(self) -> dict:
        return {"bin_visits": self.visit_counts()}


class DevelopmentalCuriosityChooser:
    """Continuous state-action adapter for :class:`DevelopmentalCuriosity`.

    The descriptor is ``(current_angle, target_angle)`` normalized to [0, 1].
    Candidate targets are continuous samples, not authored difficulty bins.
    """

    def __init__(self, min_deg: float, max_deg: float, neutral_deg: float, seed: int):
        self.min_deg = float(min_deg)
        self.max_deg = float(max_deg)
        self.neutral_deg = float(neutral_deg)
        neutral = self._normalize(neutral_deg)
        self.scheduler = DevelopmentalCuriosity(
            descriptor_dim=2,
            home_descriptor=np.array([neutral, neutral]),
            bandwidth=0.16,
            initial_frontier=0.10,
            max_frontier=0.80,
            epsilon=0.05,
            seed=seed,
        )
        self.targets: list[float] = []

    def _normalize(self, angle: float) -> float:
        return float(np.clip((angle - self.min_deg) / (self.max_deg - self.min_deg), 0.0, 1.0))

    def descriptor(self, start_deg: float, target_deg: float) -> np.ndarray:
        return np.array([self._normalize(start_deg), self._normalize(target_deg)], dtype=np.float64)

    def choose(self, rng: np.random.Generator, current_deg: float | None = None) -> float:
        current = self.neutral_deg if current_deg is None else float(current_deg)
        span = self.max_deg - self.min_deg
        uniform = rng.uniform(self.min_deg, self.max_deg, size=32)
        local = np.clip(rng.normal(current, 0.12 * span, size=28), self.min_deg, self.max_deg)
        targets = np.concatenate(
            [uniform, local, np.array([self.neutral_deg, current, self.min_deg, self.max_deg])]
        )
        descriptors = np.stack([self.descriptor(current, target) for target in targets])
        selected = self.scheduler.choose(descriptors, rng)
        target = float(targets[selected])
        self.targets.append(target)
        return target

    def update(self, target_deg: float, error: float) -> None:
        self.update_transition(self.neutral_deg, target_deg, error)

    def update_transition(self, start_deg: float, target_deg: float, error: float) -> None:
        self.scheduler.observe(self.descriptor(start_deg, target_deg), error)

    def visit_counts(self) -> list[int]:
        if not self.targets:
            return []
        counts, _ = np.histogram(self.targets, bins=16, range=(self.min_deg, self.max_deg))
        return counts.astype(int).tolist()

    def diagnostics(self) -> dict:
        return {**self.scheduler.diagnostics(), "target_histogram": self.visit_counts()}


class ExperienceBuffer:
    def __init__(self):
        self.frames: list[np.ndarray] = []
        self.requested: list[np.ndarray] = []
        self.as5600: list[np.ndarray] = []
        self.distance: list[np.ndarray] = []
        self.episode: list[np.ndarray] = []
        self._episode_count = 0

    def add_episode(self, frames, requested, as5600, distance) -> None:
        count = len(frames)
        self.frames.append(np.stack(frames).astype(np.uint8))
        self.requested.append(np.asarray(requested, dtype=np.float32))
        self.as5600.append(np.asarray(as5600, dtype=np.float32))
        self.distance.append(np.asarray(distance, dtype=np.float32))
        self.episode.append(np.full(count, self._episode_count, dtype=np.int32))
        self._episode_count += 1

    def total_frames(self) -> int:
        return int(sum(chunk.shape[0] for chunk in self.frames))

    def to_data(self) -> dict[str, np.ndarray]:
        return {
            "frames": np.concatenate(self.frames, axis=0),
            "requested_deg": np.concatenate(self.requested, axis=0),
            "as5600_deg": np.concatenate(self.as5600, axis=0),
            "distance_m": np.concatenate(self.distance, axis=0),
            "episode": np.concatenate(self.episode, axis=0),
        }


def prediction_error(
    model,
    device,
    frames_start,
    frames_end,
    actions_norm_window,
    max_horizon: int,
    *,
    scale_invariant: bool = False,
) -> float:
    """Latent prediction error over the elapsed decision window."""

    k_span = min(len(actions_norm_window), max_horizon)
    with torch.no_grad():
        frame_t = torch.from_numpy(frames_start[None]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
        frame_next = torch.from_numpy(frames_end[None]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
        action = np.zeros((1, max_horizon), dtype=np.float32)
        action[0, :k_span] = actions_norm_window[:k_span]
        action_t = torch.from_numpy(action).to(device)
        horizon = torch.full((1, 1), k_span / max_horizon, device=device)
        latent_t = model.encode(frame_t)
        latent_next = model.encode(frame_next)
        prediction = model.predict_next(latent_t, action_t, horizon)
        pred_mse = torch.mean((prediction - latent_next) ** 2)
        if not scale_invariant:
            return float(pred_mse.item())
        copy_mse = torch.mean((latent_t - latent_next) ** 2)
        return float((pred_mse / torch.clamp(pred_mse + copy_mse, min=1e-8)).item())


def collect_episode(
    env,
    chooser,
    model,
    device,
    rng,
    frames_per_episode: int,
    image_size: int,
    room_seed: int,
    max_horizon: int,
    condition: str,
):
    env.reset(seed=room_seed)
    capture_every = max(1, round(1.0 / (CAPTURE_HZ * env.config.control_dt)))
    frames: list[np.ndarray] = []
    requested: list[float] = []
    as5600: list[float] = []
    distance: list[float] = []
    target = env.config.servo.neutral_deg

    for frame_index in range(frames_per_episode):
        if frame_index % DECISION_FRAMES == 0:
            if condition != "babbling" and frame_index >= DECISION_FRAMES:
                # Elapsed window: frames i-5 .. i-1 (span 4 transitions).
                window = slice(frame_index - DECISION_FRAMES, frame_index - 1)
                actions_norm = normalize_action(np.asarray(requested[window], dtype=np.float32))
                error = prediction_error(
                    model,
                    device,
                    frames[frame_index - DECISION_FRAMES],
                    frames[-1],
                    actions_norm,
                    max_horizon,
                    scale_invariant=condition == "developmental",
                )
                chooser.update_transition(as5600[frame_index - DECISION_FRAMES], target, error)
            current_deg = as5600[-1] if as5600 else env.config.servo.neutral_deg
            target = chooser.choose(rng, current_deg)

        obs = None
        for _ in range(capture_every):
            obs = env.step(target)
        frames.append(env.render_camera(image_size, image_size))
        requested.append(obs.requested_deg)
        as5600.append(obs.as5600_deg)
        distance.append(obs.distance_m)

    return frames, requested, as5600, distance


def coverage_entropy(as5600_deg: np.ndarray, min_deg: float, max_deg: float, bins: int = 16) -> float:
    histogram, _ = np.histogram(as5600_deg, bins=bins, range=(min_deg, max_deg))
    total = histogram.sum()
    if total == 0:
        return 0.0
    p = histogram[histogram > 0] / total
    return float(-(p * np.log(p)).sum() / math.log(bins))


def train_round(model, probes, optimizer, data, epochs: int, batch_size: int, rng, device, max_horizon: int, variance_weight: float, covariance_weight: float) -> float:
    action_norm = normalize_action(data["requested_deg"])
    pairs_by_k = build_pairs_multi(data["episode"], max_horizon)
    steps_per_epoch = max(1, len(pairs_by_k[1]) // batch_size)
    autocast_dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    model.train()
    probes.train()
    last_loss = float("nan")

    for _ in range(epochs):
        for _ in range(steps_per_epoch):
            k = int(rng.integers(1, max_horizon + 1))
            pool = pairs_by_k[k]
            if len(pool) == 0:
                continue
            index = pool[rng.integers(0, len(pool), size=min(batch_size, len(pool)))]
            frames_t = torch.from_numpy(data["frames"][index]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            frames_next = torch.from_numpy(data["frames"][index + k]).to(device).permute(0, 3, 1, 2).float().div_(255.0)
            action = torch.from_numpy(action_sequence(action_norm, index, k, max_horizon)).to(device)
            horizon = torch.full((index.shape[0], 1), k / max_horizon, device=device)

            with torch.autocast(device_type=device.type, dtype=autocast_dtype, enabled=device.type == "cuda"):
                latent_t = model.encode(frames_t)
                latent_next = model.encode(frames_next)
                prediction = model.predict_next(latent_t, action, horizon)

                pred_loss = torch.mean((prediction - latent_next.detach()) ** 2)
                reg = variance_weight * 0.5 * (variance_loss(latent_t) + variance_loss(latent_next))
                reg = reg + covariance_weight * 0.5 * (covariance_loss(latent_t) + covariance_loss(latent_next))

                detached = latent_next.detach()
                angle_out = probes.angle(detached)
                angle_true = torch.from_numpy(np.radians(data["as5600_deg"][index + k])).to(device).float()
                probe_loss = torch.mean((angle_out[:, 0] - torch.sin(angle_true)) ** 2)
                probe_loss = probe_loss + torch.mean((angle_out[:, 1] - torch.cos(angle_true)) ** 2)
                distance_true = torch.from_numpy(data["distance_m"][index + k]).to(device).float()
                probe_loss = probe_loss + torch.mean((probes.distance(detached).squeeze(-1) - distance_true) ** 2)

                loss = pred_loss + reg + probe_loss

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            last_loss = float(loss.item())
    return last_loss


def load_validation(corpus_dir: Path, image_size: int, max_horizon: int, val_fraction: float, subsample: int, seed: int = 0):
    data = load_corpus(corpus_dir, image_size)
    episodes = np.unique(data["episode"])
    val_count = max(1, int(round(len(episodes) * val_fraction)))
    val_episodes = set(episodes[-val_count:].tolist())
    mask = np.isin(data["episode"], list(val_episodes))
    val_data = {key: value[mask] for key, value in data.items()}

    full_by_k = build_pairs_multi(val_data["episode"], max_horizon)
    rng = np.random.default_rng(seed)
    sub_by_k = {
        k: (pairs if len(pairs) <= subsample else np.sort(rng.choice(pairs, size=subsample, replace=False)))
        for k, pairs in full_by_k.items()
    }
    return val_data, sub_by_k, full_by_k


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Active exploration vs babbling on the bench twin.")
    parser.add_argument("--condition", choices=("active", "babbling", "developmental"), required=True)
    parser.add_argument("--seed", type=int, default=4301)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--frames-per-round", type=int, default=2500)
    parser.add_argument("--frames-per-episode", type=int, default=250)
    parser.add_argument("--epochs-per-round", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--latent-dim", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=512)
    parser.add_argument("--encoder-width", type=int, default=32)
    parser.add_argument("--max-horizon", type=int, default=5)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--variance-weight", type=float, default=1.0)
    parser.add_argument("--covariance-weight", type=float, default=0.1)
    parser.add_argument("--val-corpus", type=Path, default=Path("data/raw/bench_visual_corpus"))
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--val-subsample", type=int, default=5000)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metrics-output", type=Path, required=True)
    return parser


def main() -> None:
    if torch is None:
        raise ModuleNotFoundError("active_exploration requires PyTorch.")
    args = build_parser().parse_args()
    device = resolve_device(args.device)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    from sim3d.bench_env import BenchHeadEnv
    from sim3d.bench_model import BenchConfig

    env = BenchHeadEnv(BenchConfig(seed=args.seed))
    servo = env.config.servo
    if args.condition == "active":
        chooser = LearningProgressChooser(servo.min_deg, servo.max_deg)
    elif args.condition == "developmental":
        chooser = DevelopmentalCuriosityChooser(servo.min_deg, servo.max_deg, servo.neutral_deg, args.seed)
    else:
        chooser = UniformChooser(servo.min_deg, servo.max_deg)

    model = VisualJEPA(
        latent_dim=args.latent_dim,
        action_dim=args.max_horizon,
        hidden_dim=args.hidden_dim,
        encoder_width=args.encoder_width,
        use_action=True,
        horizon_dim=1,
    ).to(device)
    probes = ProbeHeads(args.latent_dim).to(device)
    optimizer = torch.optim.AdamW(
        list(model.parameters()) + list(probes.parameters()), lr=args.lr, weight_decay=args.weight_decay
    )

    val_data, val_sub_by_k, val_full_by_k = load_validation(
        args.val_corpus, args.image_size, args.max_horizon, args.val_fraction, args.val_subsample
    )
    val_action_norm = normalize_action(val_data["requested_deg"])

    buffer = ExperienceBuffer()
    episodes_per_round = max(1, args.frames_per_round // args.frames_per_episode)
    rounds_report = []
    started = time.perf_counter()

    for round_index in range(args.rounds):
        round_as5600 = []
        for episode_index in range(episodes_per_round):
            global_episode = round_index * episodes_per_round + episode_index
            room_seed = 9_500_000 + args.seed * 10_000 + global_episode  # condition-independent rooms
            frames, requested, as5600, distance = collect_episode(
                env, chooser, model, device, rng,
                args.frames_per_episode, args.image_size, room_seed, args.max_horizon,
                condition=args.condition,
            )
            buffer.add_episode(frames, requested, as5600, distance)
            round_as5600.extend(as5600)

        data = buffer.to_data()
        train_loss = train_round(
            model, probes, optimizer, data, args.epochs_per_round, args.batch_size, rng, device,
            args.max_horizon, args.variance_weight, args.covariance_weight,
        )
        eval_metrics = evaluate(
            model, probes, val_data, val_sub_by_k, val_action_norm, device, args.batch_size,
            max_horizon=args.max_horizon,
        )
        entropy = coverage_entropy(np.asarray(round_as5600), servo.min_deg, servo.max_deg)
        rounds_report.append(
            {
                "round": round_index + 1,
                "frames_total": buffer.total_frames(),
                "train_loss": train_loss,
                "coverage_entropy": entropy,
                "bin_visits": chooser.visit_counts(),
                "curiosity": chooser.diagnostics(),
                "eval": eval_metrics,
            }
        )
        print(
            f"round {round_index + 1}/{args.rounds}: frames={buffer.total_frames()} "
            f"ratio_k3_moving={eval_metrics['per_horizon']['3']['pred_to_copy_ratio_moving']:.4f} "
            f"angle_mae={eval_metrics['angle_probe_mae_deg']:.2f}deg entropy={entropy:.3f}",
            flush=True,
        )

    final_eval = evaluate(
        model, probes, val_data, val_full_by_k, val_action_norm, device, args.batch_size,
        max_horizon=args.max_horizon,
    )
    env.close()
    elapsed = time.perf_counter() - started

    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": {k: v.detach().cpu() for k, v in model.state_dict().items()},
            "probes_state_dict": {k: v.detach().cpu() for k, v in probes.state_dict().items()},
            "latent_dim": args.latent_dim,
            "hidden_dim": args.hidden_dim,
            "encoder_width": args.encoder_width,
            "image_size": args.image_size,
            "max_horizon": args.max_horizon,
            "condition": args.condition,
            "seed": args.seed,
        },
        args.output,
    )

    metrics = {
        "status": "complete",
        "condition": args.condition,
        "seed": int(args.seed),
        "device": str(device),
        "frames_budget": int(buffer.total_frames()),
        "rounds": rounds_report,
        "final_eval": final_eval,
        "wall_seconds": float(elapsed),
        "checkpoint": str(args.output),
    }
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(
        f"Active exploration run done: condition={args.condition} seed={args.seed} "
        f"final_ratio_k3_moving={final_eval['per_horizon']['3']['pred_to_copy_ratio_moving']:.4f} "
        f"angle_mae={final_eval['angle_probe_mae_deg']:.2f} ({elapsed:.0f}s)",
        flush=True,
    )


if __name__ == "__main__":
    main()
