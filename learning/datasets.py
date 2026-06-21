"""Load simulator CSV logs into arrays usable by PyTorch later."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import numpy as np


OBS_COLUMNS = ("obs_distance", "obs_servo_angle", "obs_gyro_z")
NEXT_OBS_COLUMNS = ("next_obs_distance", "next_obs_servo_angle", "next_obs_gyro_z")
ACTION_COLUMNS = ("actuator_action_v_cmd", "actuator_action_omega_cmd", "actuator_action_servo_target")
FALLBACK_ACTION_COLUMNS = ("safe_action_v_cmd", "safe_action_omega_cmd", "safe_action_servo_target")
STATE_COLUMNS = ("state_x", "state_y", "state_heading", "state_servo_angle", "state_v", "state_omega")
META_COLUMNS = ("episode", "step", "t", "collision", "true_distance", "nearest_surface")


def load_simulation_csv(path: str | Path) -> dict[str, np.ndarray]:
    rows = list(_read_rows(path))
    if not rows:
        raise ValueError(f"No rows found in {path}")

    arrays = {
        "obs": _columns(rows, OBS_COLUMNS),
        "action": _columns(rows, _select_action_columns(rows[0])),
        "next_obs": _columns(rows, NEXT_OBS_COLUMNS),
        "state": _columns(rows, STATE_COLUMNS),
        "reward": _columns(rows, ("reward",)).reshape(-1),
        "done": _columns(rows, ("done",)).reshape(-1).astype(bool),
    }
    for name in META_COLUMNS:
        if name in rows[0]:
            values = _columns(rows, (name,)).reshape(-1)
            if name in ("episode", "step", "collision"):
                values = values.astype(np.int64)
            arrays[name] = values
    return arrays


def build_context_transitions(arrays: dict[str, np.ndarray], context_steps: int = 1) -> dict[str, np.ndarray]:
    """Build Markov-ish windows from instantaneous sensor transitions.

    A context at row i contains:
    - observations from i-context_steps+1 through i;
    - previous actions from i-context_steps+1 through i-1.

    The separate action remains action_i. The target context is shifted by one
    step and therefore contains next_obs_i as its final observation, without
    leaking action_{i+1}.
    """

    context_steps = int(context_steps)
    if context_steps <= 1:
        result = dict(arrays)
        result["target_obs"] = arrays["next_obs"]
        result["context_steps"] = np.array([1], dtype=np.int64)
        return result

    obs = arrays["obs"]
    actions = arrays["action"]
    next_obs = arrays["next_obs"]
    episodes = arrays.get("episode")

    context_rows = []
    next_context_rows = []
    keep_indices = []
    for i in range(context_steps - 1, len(obs)):
        start = i - context_steps + 1
        if episodes is not None and np.any(episodes[start : i + 1] != episodes[i]):
            continue

        obs_window = obs[start : i + 1].reshape(-1)
        previous_actions = actions[start:i].reshape(-1)
        context_rows.append(np.concatenate([obs_window, previous_actions]).astype(np.float32))

        shifted_obs_window = np.concatenate([obs[start + 1 : i + 1], next_obs[i : i + 1]], axis=0).reshape(-1)
        shifted_actions = actions[start + 1 : i + 1].reshape(-1)
        next_context_rows.append(np.concatenate([shifted_obs_window, shifted_actions]).astype(np.float32))
        keep_indices.append(i)

    if not keep_indices:
        raise ValueError(f"Not enough same-episode rows to build context_steps={context_steps}")

    keep = np.array(keep_indices, dtype=np.int64)
    result = dict(arrays)
    result["obs"] = np.vstack(context_rows).astype(np.float32)
    result["next_obs"] = np.vstack(next_context_rows).astype(np.float32)
    result["action"] = actions[keep]
    result["target_obs"] = next_obs[keep]
    original_length = len(obs)
    for key, value in arrays.items():
        if key in ("obs", "next_obs", "action"):
            continue
        if isinstance(value, np.ndarray) and len(value) == original_length:
            result[key] = value[keep]
    result["context_steps"] = np.array([context_steps], dtype=np.int64)
    return result


def _read_rows(path: str | Path) -> Iterable[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        yield from reader


def _columns(rows: list[dict[str, str]], names: tuple[str, ...]) -> np.ndarray:
    return np.array([[float(row[name]) for name in names] for row in rows], dtype=np.float32)


def _select_action_columns(first_row: dict[str, str]) -> tuple[str, ...]:
    if all(name in first_row for name in ACTION_COLUMNS):
        return ACTION_COLUMNS
    return FALLBACK_ACTION_COLUMNS


class TorchTransitionDataset:
    def __init__(self, path: str | Path):
        try:
            import torch
            from torch.utils.data import Dataset
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError("TorchTransitionDataset requires PyTorch in this environment.") from exc

        class _Dataset(Dataset):
            def __init__(self, arrays: dict[str, np.ndarray]):
                self.arrays = {key: torch.from_numpy(value) for key, value in arrays.items()}

            def __len__(self) -> int:
                return int(self.arrays["obs"].shape[0])

            def __getitem__(self, idx: int):
                return {
                    "obs": self.arrays["obs"][idx],
                    "action": self.arrays["action"][idx],
                    "next_obs": self.arrays["next_obs"][idx],
                    "reward": self.arrays["reward"][idx],
                    "done": self.arrays["done"][idx],
                }

        self._dataset = _Dataset(load_simulation_csv(path))

    def __len__(self) -> int:
        return len(self._dataset)

    def __getitem__(self, idx: int):
        return self._dataset[idx]
