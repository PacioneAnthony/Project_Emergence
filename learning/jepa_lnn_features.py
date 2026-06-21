"""Causal JEPA latent features for LNN controller training and rollout."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from common.types import Action, Observation
from learning.datasets import build_context_transitions, load_simulation_csv
from learning.evaluate_jepa import infer_checkpoint_dims, latest_observation_from_context, load_checkpoint
from learning.jepa import SensorJEPA

try:
    import torch
except ModuleNotFoundError:
    torch = None


OBS_DIM = 3
ACTION_DIM = 3
CANONICAL_ACTION_COLUMNS = (
    "actuator_action_v_cmd",
    "actuator_action_omega_cmd",
    "actuator_action_servo_target",
)
FALLBACK_ACTION_COLUMNS = (
    "safe_action_v_cmd",
    "safe_action_omega_cmd",
    "safe_action_servo_target",
)
STUDENT_ACTUATOR_ACTION_COLUMNS = (
    "student_actuator_action_v_cmd",
    "student_actuator_action_omega_cmd",
    "student_actuator_action_servo_target",
)


@dataclass
class JEPABundle:
    model: Any
    target_encoder: Any
    checkpoint_path: Path
    obs_dim: int
    action_dim: int
    latent_dim: int
    hidden_dim: int
    decoded_obs_dim: int | None
    context_steps: int


def load_jepa_bundle(checkpoint_path: str | Path, device) -> JEPABundle:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required for JEPA-LNN features.")

    path = Path(checkpoint_path)
    state_dict, target_encoder_state_dict, checkpoint_meta = load_checkpoint(path, torch)
    dims = infer_checkpoint_dims(state_dict)
    dims.update({key: int(value) for key, value in checkpoint_meta.items() if key in dims and value is not None})
    context_steps = int(checkpoint_meta.get("context_steps") or infer_context_steps(dims["obs_dim"], dims["action_dim"]))

    model = SensorJEPA(
        obs_dim=dims["obs_dim"],
        action_dim=dims["action_dim"],
        latent_dim=dims["latent_dim"],
        hidden_dim=dims["hidden_dim"],
        decoded_obs_dim=dims.get("decoded_obs_dim"),
    ).to(device)
    model.load_state_dict(state_dict)
    model.eval()
    target_encoder = None
    if target_encoder_state_dict is not None:
        import copy

        target_encoder = copy.deepcopy(model.encoder)
        target_encoder.load_state_dict(target_encoder_state_dict)
        target_encoder.eval()
    return JEPABundle(
        model=model,
        target_encoder=target_encoder,
        checkpoint_path=path,
        obs_dim=int(dims["obs_dim"]),
        action_dim=int(dims["action_dim"]),
        latent_dim=int(dims["latent_dim"]),
        hidden_dim=int(dims["hidden_dim"]),
        decoded_obs_dim=dims.get("decoded_obs_dim"),
        context_steps=context_steps,
    )


def infer_context_steps(obs_dim: int, action_dim: int) -> int:
    if obs_dim == OBS_DIM:
        return 1
    numerator = obs_dim + action_dim
    denominator = OBS_DIM + action_dim
    if numerator % denominator == 0:
        return max(1, int(numerator // denominator))
    return 1


def build_jepa_lnn_arrays(
    log_path: str | Path,
    jepa_checkpoint: str | Path,
    device,
    batch_size: int = 4096,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Build LNN arrays whose obs input is raw current obs plus frozen JEPA latent."""

    bundle = load_jepa_bundle(jepa_checkpoint, device)
    base_arrays = load_simulation_csv(log_path)
    context_source = dict(base_arrays)
    context_source["action"] = load_context_action_array(log_path)

    context_arrays = build_context_transitions(context_source, context_steps=bundle.context_steps)
    target_arrays = build_context_transitions(base_arrays, context_steps=bundle.context_steps)
    latest_obs = latest_observation_from_context(context_arrays["obs"], bundle.context_steps)
    latents = encode_contexts(bundle, context_arrays["obs"], device=device, batch_size=batch_size)

    result = dict(target_arrays)
    result["obs"] = np.concatenate([latest_obs, latents], axis=1).astype(np.float32)
    result["jepa_latest_obs"] = latest_obs.astype(np.float32)
    result["jepa_latent"] = latents.astype(np.float32)

    meta = {
        "input_mode": "obs_plus_jepa_latent",
        "jepa_checkpoint": str(bundle.checkpoint_path),
        "jepa_context_steps": int(bundle.context_steps),
        "jepa_obs_dim": int(bundle.obs_dim),
        "jepa_action_dim": int(bundle.action_dim),
        "jepa_latent_dim": int(bundle.latent_dim),
        "jepa_hidden_dim": int(bundle.hidden_dim),
        "jepa_decoded_obs_dim": int(bundle.decoded_obs_dim) if bundle.decoded_obs_dim is not None else None,
        "lnn_input_dim": int(result["obs"].shape[-1]),
        "context_action_source": "student_actuator_action_if_present_else_actuator_action",
    }
    return result, meta


def build_jepa_auxiliary_arrays(
    log_path: str | Path,
    jepa_checkpoint: str | Path,
    device,
    batch_size: int = 4096,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Build raw-observation LNN arrays plus a causal next-context JEPA target."""

    bundle = load_jepa_bundle(jepa_checkpoint, device)
    base_arrays = load_simulation_csv(log_path)
    context_source = dict(base_arrays)
    context_source["action"] = load_context_action_array(log_path)
    context_arrays = build_context_transitions(context_source, context_steps=bundle.context_steps)
    target_arrays = build_context_transitions(base_arrays, context_steps=bundle.context_steps)

    result = dict(target_arrays)
    result["obs"] = latest_observation_from_context(context_arrays["obs"], bundle.context_steps).astype(np.float32)
    result["jepa_aux_target"] = encode_target_contexts(
        bundle,
        context_arrays["next_obs"],
        device=device,
        batch_size=batch_size,
    )
    meta = {
        "input_mode": "raw_observation_with_jepa_auxiliary_loss",
        "jepa_aux_checkpoint": str(bundle.checkpoint_path),
        "jepa_aux_context_steps": int(bundle.context_steps),
        "jepa_aux_latent_dim": int(bundle.latent_dim),
        "jepa_aux_target_encoder": "ema" if bundle.target_encoder is not None else "online_fallback",
        "lnn_input_dim": int(result["obs"].shape[-1]),
        "context_action_source": "student_actuator_action_if_present_else_actuator_action",
    }
    return result, meta


def compute_jepa_latent_mean(
    log_path: str | Path,
    jepa_checkpoint: str | Path,
    device,
    batch_size: int = 4096,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Compute the mean frozen-JEPA latent over a simulator log."""

    bundle = load_jepa_bundle(jepa_checkpoint, device)
    base_arrays = load_simulation_csv(log_path)
    context_source = dict(base_arrays)
    context_source["action"] = load_context_action_array(log_path)
    context_arrays = build_context_transitions(context_source, context_steps=bundle.context_steps)
    latent_mean, n_samples = encode_context_mean(bundle, context_arrays["obs"], device=device, batch_size=batch_size)
    meta = {
        "latent_mean_log": str(log_path),
        "jepa_checkpoint": str(bundle.checkpoint_path),
        "jepa_context_steps": int(bundle.context_steps),
        "jepa_latent_dim": int(bundle.latent_dim),
        "n_latent_samples": int(n_samples),
    }
    return latent_mean, meta


def load_context_action_array(log_path: str | Path) -> np.ndarray:
    """Load actions for JEPA context, preferring actual student actuator actions per row.

    DAgger logs use canonical actuator_action_* columns as expert labels. For
    JEPA context, however, previous actions should describe the trajectory that
    actually produced the observations, so student_actuator_action_* is used
    when present and non-empty.
    """

    rows = []
    with Path(log_path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV log has no header: {log_path}")
        action_columns = CANONICAL_ACTION_COLUMNS if all(name in reader.fieldnames for name in CANONICAL_ACTION_COLUMNS) else FALLBACK_ACTION_COLUMNS
        for row in reader:
            rows.append(_context_action_from_row(row, action_columns))
    if not rows:
        raise ValueError(f"No rows found in {log_path}")
    return np.array(rows, dtype=np.float32)


def _context_action_from_row(row: dict[str, str], fallback_columns: tuple[str, str, str]) -> list[float]:
    if all(_has_float_value(row, name) for name in STUDENT_ACTUATOR_ACTION_COLUMNS):
        return [float(row[name]) for name in STUDENT_ACTUATOR_ACTION_COLUMNS]
    return [float(row[name]) for name in fallback_columns]


def _has_float_value(row: dict[str, str], name: str) -> bool:
    value = row.get(name)
    if value is None or value == "":
        return False
    try:
        float(value)
    except ValueError:
        return False
    return True


def encode_contexts(bundle: JEPABundle, contexts: np.ndarray, device, batch_size: int = 4096) -> np.ndarray:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required for JEPA-LNN features.")

    latents = []
    with torch.no_grad():
        for start in range(0, len(contexts), batch_size):
            batch = torch.from_numpy(contexts[start : start + batch_size]).float().to(device)
            latents.append(bundle.model.encode(batch).detach().cpu().numpy())
    return np.vstack(latents).astype(np.float32)


def encode_target_contexts(bundle: JEPABundle, contexts: np.ndarray, device, batch_size: int = 4096) -> np.ndarray:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required for JEPA-LNN features.")

    encoder = bundle.target_encoder or bundle.model.encoder
    latents = []
    with torch.no_grad():
        for start in range(0, len(contexts), batch_size):
            batch = torch.from_numpy(contexts[start : start + batch_size]).float().to(device)
            latents.append(encoder(batch).detach().cpu().numpy())
    return np.vstack(latents).astype(np.float32)


def encode_context_mean(bundle: JEPABundle, contexts: np.ndarray, device, batch_size: int = 4096) -> tuple[np.ndarray, int]:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required for JEPA-LNN features.")

    latent_sum = np.zeros(bundle.latent_dim, dtype=np.float64)
    count = 0
    with torch.no_grad():
        for start in range(0, len(contexts), batch_size):
            batch = torch.from_numpy(contexts[start : start + batch_size]).float().to(device)
            latent = bundle.model.encode(batch).detach().cpu().numpy()
            latent_sum += latent.astype(np.float64).sum(axis=0)
            count += len(latent)
    if count == 0:
        raise ValueError("Cannot compute JEPA latent mean from an empty context array.")
    return (latent_sum / count).astype(np.float32), count


def build_live_context_vector(
    obs_history: Sequence[Observation | np.ndarray],
    action_history: Sequence[Action | np.ndarray],
    current_obs: Observation,
    context_steps: int,
) -> np.ndarray:
    context_steps = int(context_steps)
    if context_steps <= 0:
        raise ValueError("context_steps must be > 0.")

    obs_values = [_obs_array(obs) for obs in obs_history]
    obs_values.append(current_obs.as_array())
    obs_values = obs_values[-context_steps:]
    if len(obs_values) < context_steps:
        pad_value = obs_values[0] if obs_values else current_obs.as_array()
        obs_values = [pad_value.copy() for _ in range(context_steps - len(obs_values))] + obs_values

    action_values = [_action_array(action) for action in action_history]
    action_values = action_values[-max(0, context_steps - 1) :]
    if len(action_values) < context_steps - 1:
        action_values = [np.zeros(ACTION_DIM, dtype=np.float32) for _ in range(context_steps - 1 - len(action_values))] + action_values

    return np.concatenate([np.concatenate(obs_values), np.concatenate(action_values)]).astype(np.float32)


def build_live_lnn_input(bundle: JEPABundle, context_vector: np.ndarray, current_obs: Observation, device) -> np.ndarray:
    if torch is None:
        raise ModuleNotFoundError("PyTorch is required for JEPA-LNN features.")

    with torch.no_grad():
        context = torch.from_numpy(context_vector).float().unsqueeze(0).to(device)
        latent = bundle.model.encode(context).squeeze(0).detach().cpu().numpy()
    return build_lnn_input_from_latent(current_obs, latent)


def build_lnn_input_from_latent(current_obs: Observation, latent: np.ndarray) -> np.ndarray:
    return np.concatenate([current_obs.as_array(), np.asarray(latent, dtype=np.float32)]).astype(np.float32)


def _obs_array(obs: Observation | np.ndarray) -> np.ndarray:
    if isinstance(obs, Observation):
        return obs.as_array()
    return np.asarray(obs, dtype=np.float32)


def _action_array(action: Action | np.ndarray) -> np.ndarray:
    if isinstance(action, Action):
        return action.as_array()
    return np.asarray(action, dtype=np.float32)
