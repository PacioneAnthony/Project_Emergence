"""REF-003 world, provenance, and visibility guards.

The learner architecture, training budget, scoring, and statistical gates are
inherited from the frozen REF-002 implementation. This module changes only the
pre-registered REF3 world, seeds, data generation, and audit instrumentation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any

import mujoco
import numpy as np

from learning import reafference_002 as ref2
from sim3d import bench_model
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig, BenchRoomConfig


CONDITIONS = ref2.CONDITIONS
BANKS = ref2.BANKS
MOBILE_MATCHED_BANKS = ref2.MOBILE_MATCHED_BANKS
STRUCTURED_CENTERS_DEG = ref2.STRUCTURED_CENTERS_DEG
RESERVED_SEEDS = tuple(range(14301, 14317))
SMOKE_SEED = 14991
ANALYSIS_SEED = 2026072701

REF3_DISTANCE_M = 1.05
REF3_TRAVEL_M = 0.36
REF3_OBJECT_HALF_WIDTH_M = 0.32
REF3_OBJECT_HALF_HEIGHT_M = 0.24
REF3_BEARING_OFFSET_MAX_DEG = 3.0
REF3_START_OFFSET_MAX_DEG = 4.0
REF3_HEAD_AMPLITUDE_MAX_DEG = 10.0
REF3_HALF_FOV_DEG = 15.0
REF3_FIELD_MARGIN_DEG = 3.0
REF3_VISIBILITY_MINIMUM = 0.01
REF3_VISIBILITY_BIN_MEAN_MINIMUM = 0.05
REF3_SANITY_EXTERNAL_MINIMUM = 0.70

INHERITED_DIGESTS = {
    "docs/research/reafference_002_preregistration.md":
        "cfd8946cceb4ce88bb9d24171b1f5db7561f5b540cb78cf4d3d5f2fdf7bd2210",
    "learning/reafference_002.py":
        "d53ad5044c0be4384e2165422c2f01c27803aac417e22823526e01b2000b72b0",
    "scripts/research/run_reafference_002.py":
        "0ddb0e874a59aa8e6706371a79458f47a7727d5712d1fffd78333a375aa8cb5a",
    "tests/test_reafference_002.py":
        "b54ed41dc9eba42ff3408633e93e82abb331bd5048615e741a1ece18e32219ab",
    "sim3d/bench_model.py":
        "39e44711335deb2ade132be80c2cee79af233e671454a8b3b9cebaa73106ef46",
}


@dataclass(frozen=True)
class Ref3Spec(ref2.Ref2Spec):
    version: str = "ref-003-c1-c8-v1"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_inherited_digests(repo: Path) -> dict[str, str]:
    observed = {
        relative: _sha256_file(repo / relative)
        for relative in INHERITED_DIGESTS
    }
    mismatches = {
        relative: {"expected": INHERITED_DIGESTS[relative], "observed": digest}
        for relative, digest in observed.items()
        if digest != INHERITED_DIGESTS[relative]
    }
    if mismatches:
        raise AssertionError(f"REF3 inherited digest mismatch: {mismatches}")
    return observed


def field_envelope() -> dict[str, float | bool]:
    rail_angle = math.degrees(math.atan(REF3_TRAVEL_M / (2.0 * REF3_DISTANCE_M)))
    object_half_angle = math.degrees(
        math.atan(REF3_OBJECT_HALF_WIDTH_M / REF3_DISTANCE_M)
    )
    left = (
        REF3_BEARING_OFFSET_MAX_DEG
        + rail_angle
        + REF3_START_OFFSET_MAX_DEG
        + REF3_HEAD_AMPLITUDE_MAX_DEG
    )
    right = REF3_HALF_FOV_DEG + object_half_angle - REF3_FIELD_MARGIN_DEG
    return {
        "bearing_offset_max_deg": REF3_BEARING_OFFSET_MAX_DEG,
        "rail_half_angle_deg": rail_angle,
        "start_offset_max_deg": REF3_START_OFFSET_MAX_DEG,
        "head_amplitude_max_deg": REF3_HEAD_AMPLITUDE_MAX_DEG,
        "object_half_angle_deg": object_half_angle,
        "required_margin_deg": REF3_FIELD_MARGIN_DEG,
        "left_deg": left,
        "right_deg": right,
        "residual_margin_deg": right - left,
        "passed": left <= right,
    }


def ref3_bench_config(
    seed: int,
    bearing_deg: float = 90.0,
    context: int = 0,
) -> BenchConfig:
    if context not in (0, 1):
        raise ValueError("REF3 context must be 0 or 1")
    primary = (0.42, 0.66, 0.76) if context == 0 else (0.74, 0.58, 0.34)
    secondary = (0.72, 0.36, 0.44) if context == 0 else (0.36, 0.72, 0.52)
    room = BenchRoomConfig(
        width=3.6,
        depth=4.1,
        object_count=8,
        min_object_size=0.07,
        max_object_size=0.26,
        primary_light_rgb=primary,
        secondary_light_rgb=secondary,
        headlight_ambient_rgb=(0.24, 0.29, 0.34),
        headlight_diffuse_rgb=(0.68, 0.57, 0.48),
        reafference_object=True,
        reafference_bearing_deg=float(bearing_deg),
        reafference_distance_m=REF3_DISTANCE_M,
        reafference_travel_m=REF3_TRAVEL_M,
    )
    return BenchConfig(seed=int(seed), randomize_room=True, room=room)


def _z_quaternion(angle_rad: float) -> np.ndarray:
    return np.asarray(
        [math.cos(angle_rad / 2.0), 0.0, 0.0, math.sin(angle_rad / 2.0)],
        dtype=np.float64,
    )


def configure_external_object(
    env: BenchHeadEnv,
    *,
    bearing_deg: float,
) -> None:
    """Move and resize the REF object without rebuilding the room."""

    room = env.config.room
    heading = math.radians(float(bearing_deg) - 180.0)
    direction = np.asarray([math.cos(heading), math.sin(heading)], dtype=np.float64)
    tangent = np.asarray([-direction[1], direction[0]], dtype=np.float64)
    center = np.asarray(room.bench_position, dtype=np.float64) + REF3_DISTANCE_M * direction
    rotation = heading - math.pi / 2.0
    quaternion = _z_quaternion(rotation)

    body_id = env.model.body("ref_external_body").id
    joint_id = env.model.joint(bench_model.JOINT_EXTERNAL).id
    rail_id = env.model.geom("ref_external_rail").id
    object_id = env.model.geom(bench_model.GEOM_EXTERNAL).id

    env.model.body_pos[body_id] = (center[0], center[1], 0.0)
    env.model.jnt_axis[joint_id] = (tangent[0], tangent[1], 0.0)
    env.model.geom_pos[rail_id] = (center[0], center[1], 0.76)
    env.model.geom_quat[rail_id] = quaternion
    env.model.geom_size[rail_id] = (
        REF3_TRAVEL_M / 2.0 + 0.08,
        0.012,
        0.012,
    )
    env.model.geom_pos[object_id] = (0.0, 0.0, 1.0)
    env.model.geom_quat[object_id] = quaternion
    env.model.geom_size[object_id] = (
        REF3_OBJECT_HALF_WIDTH_M,
        0.018,
        REF3_OBJECT_HALF_HEIGHT_M,
    )

    for row in range(4):
        for column in range(4):
            geom_id = env.model.geom(f"ref_external_patch_{row}_{column}").id
            offset = (column - 1.5) * 0.135
            local = offset * tangent - 0.020 * direction
            z = 1.0 + (row - 1.5) * 0.105
            env.model.geom_pos[geom_id] = (local[0], local[1], z)
            env.model.geom_quat[geom_id] = quaternion
            env.model.geom_size[geom_id] = (0.060, 0.006, 0.048)

    mujoco.mj_forward(env.model, env.data)


def set_pretransition_head_pose(
    env: BenchHeadEnv,
    angle_deg: float,
):
    """Place every held-out pair at the exact planned causal start state."""

    servo = env.config.servo
    angle = float(np.clip(angle_deg, servo.min_deg, servo.max_deg))
    relative_rad = math.radians(angle - servo.neutral_deg)
    env.data.qpos[env._qpos_servo] = relative_rad
    env.data.qvel[env._qvel_servo] = 0.0
    env.data.ctrl[env._ctrl_servo] = relative_rad
    env._requested_deg = angle
    env._limited_deg = angle
    mujoco.mj_forward(env.model, env.data)
    return env._read_observation()


def _feasible_object_plan(
    seed: int,
    kind: str,
    motion: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    size = len(motion["horizon"])
    rng = np.random.default_rng(255_000_000 + seed * 10 + BANKS.index(kind))
    deltas = np.zeros(size, dtype=np.float32)
    if kind in {"external_only", "mixed"}:
        deltas = ref2._balanced_signed_values(
            rng.uniform(0.07, 0.18, size=size),
            rng,
        )
    elif kind == "learner_validation":
        selected = np.arange(size) % 3 != 0
        deltas[selected] = ref2._balanced_signed_values(
            rng.uniform(0.07, 0.18, size=int(np.sum(selected))),
            rng,
        )
    if kind == "mixed":
        for _ in range(10_000):
            correlation = ref2._correlation(
                motion["signed_amplitude_deg"],
                deltas,
            )
            if abs(correlation) <= 0.045:
                break
            rng.shuffle(deltas)
        else:
            raise RuntimeError("could not build independent REF3 mixed object motion")

    half_travel = REF3_TRAVEL_M / 2.0
    starts = np.empty(size, dtype=np.float32)
    for index, delta in enumerate(deltas):
        if delta > 0:
            low, high = -half_travel, half_travel - float(delta)
        elif delta < 0:
            low, high = -half_travel - float(delta), half_travel
        else:
            low, high = -half_travel, half_travel
        starts[index] = rng.uniform(low, high)
    ends = starts + deltas
    if np.any(starts < -half_travel) or np.any(starts > half_travel):
        raise RuntimeError("REF3 object start escaped the rail")
    if np.any(ends < -half_travel - 1e-7) or np.any(ends > half_travel + 1e-7):
        raise RuntimeError("REF3 object end escaped the rail")
    return starts, ends.astype(np.float32)


def _bearing_plan(seed: int, kind: str, size: int) -> np.ndarray:
    rng = np.random.default_rng(256_000_000 + seed * 10 + BANKS.index(kind))
    return rng.uniform(
        -REF3_BEARING_OFFSET_MAX_DEG,
        REF3_BEARING_OFFSET_MAX_DEG,
        size=size,
    ).astype(np.float32)


def _motion_seed(seed: int, kind: str) -> int:
    if kind in MOBILE_MATCHED_BANKS:
        return 142_000_000 + seed * 10 + MOBILE_MATCHED_BANKS.index(kind)
    if kind in {"micro_self_calibration", "micro_self_test"}:
        return 143_000_000 + seed * 10 + (
            ("micro_self_calibration", "micro_self_test").index(kind)
        )
    if kind == "external_only":
        return 144_000_000 + seed
    if kind == "learner_validation":
        return 145_000_000 + seed
    raise ValueError(f"unknown REF3 bank: {kind}")


def _corpus_plan(seed: int, spec: Ref3Spec) -> dict[str, np.ndarray]:
    action_rng = np.random.default_rng(251_000_000 + seed)
    episode_rng = np.random.default_rng(252_000_000 + seed)
    mobile_episodes = np.zeros(spec.episodes, dtype=bool)
    mobile_episodes[
        episode_rng.choice(spec.episodes, spec.episodes // 2, replace=False)
    ] = True
    targets = np.empty(spec.decisions, dtype=np.float32)
    current = 90.0
    for index in range(spec.decisions):
        current = ref2._bounded_reflect(
            current + float(action_rng.uniform(-18.0, 18.0)),
            12.0,
            168.0,
        )
        targets[index] = current
    action_delta = np.diff(np.concatenate(([90.0], targets.astype(np.float64))))
    decision_episode = np.repeat(
        np.arange(spec.episodes),
        spec.decisions_per_episode,
    )
    for attempt in range(10_000):
        object_rng = np.random.default_rng(253_000_000 + seed * 10_000 + attempt)
        positions = np.zeros(spec.decisions, dtype=np.float32)
        position = 0.0
        for index, episode in enumerate(decision_episode):
            if mobile_episodes[episode]:
                position = ref2._bounded_reflect(
                    position + float(object_rng.uniform(-0.045, 0.045)),
                    -REF3_TRAVEL_M / 2.0,
                    REF3_TRAVEL_M / 2.0,
                )
            positions[index] = position
        object_delta = np.diff(np.concatenate(([0.0], positions.astype(np.float64))))
        correlation = ref2._correlation(action_delta, object_delta)
        if abs(correlation) <= 0.045 and np.std(object_delta) > 0:
            bearing_rng = np.random.default_rng(254_000_000 + seed)
            return {
                "targets_deg": targets,
                "action_delta_deg": action_delta.astype(np.float32),
                "object_position_m": positions,
                "object_delta_m": object_delta.astype(np.float32),
                "mobile_episodes": mobile_episodes,
                "bearing_offset_deg": bearing_rng.uniform(
                    -REF3_BEARING_OFFSET_MAX_DEG,
                    REF3_BEARING_OFFSET_MAX_DEG,
                    size=spec.decisions,
                ).astype(np.float32),
            }
    raise RuntimeError("could not build independent REF3 corpus motion")


def generate_corpus(seed: int, path: Path, spec: Ref3Spec) -> dict[str, Any]:
    if path.exists():
        data = ref2.load_corpus(path)
        ref2._validate_corpus(data, spec)
        if "bearing_offset_deg" not in data:
            raise RuntimeError("REF3 corpus lacks bearing audit")
        return {"path": str(path), "sha256": _sha256_file(path), "images": spec.images}

    plan = _corpus_plan(seed, spec)
    frames: list[np.ndarray] = []
    requested: list[float] = []
    actual: list[float] = []
    episodes: list[int] = []
    object_positions: list[float] = []
    frame_bearings: list[float] = []
    decision_index = 0
    for episode in range(spec.episodes):
        center = STRUCTURED_CENTERS_DEG[episode % len(STRUCTURED_CENTERS_DEG)]
        env = BenchHeadEnv(
            ref3_bench_config(
                264_000_000 + seed * 100 + episode,
                bearing_deg=center,
                context=episode % 2,
            )
        )
        try:
            previous_object = (
                0.0
                if decision_index == 0
                else float(plan["object_position_m"][decision_index - 1])
            )
            for _ in range(spec.decisions_per_episode):
                bearing = center + float(plan["bearing_offset_deg"][decision_index])
                configure_external_object(env, bearing_deg=bearing)
                target = float(plan["targets_deg"][decision_index])
                end_object = float(plan["object_position_m"][decision_index])
                env.set_external_object_displacement(previous_object)
                for subframe in range(5):
                    fraction = (subframe + 1) / 5.0
                    env.set_external_object_displacement(
                        previous_object + fraction * (end_object - previous_object)
                    )
                    observation = None
                    for _ in range(5):
                        observation = env.step(target)
                    frames.append(env.render_camera(spec.image_size, spec.image_size))
                    requested.append(target)
                    actual.append(float(observation.as5600_deg))
                    episodes.append(episode)
                    object_positions.append(env.external_object_displacement())
                    frame_bearings.append(float(plan["bearing_offset_deg"][decision_index]))
                previous_object = end_object
                decision_index += 1
        finally:
            env.close()
    data = {
        "frames": np.stack(frames).astype(np.uint8),
        "requested_deg": np.asarray(requested, dtype=np.float32),
        "as5600_deg": np.asarray(actual, dtype=np.float32),
        "episode": np.asarray(episodes, dtype=np.int16),
        "decision_action_delta_deg": plan["action_delta_deg"].astype(np.float32),
        "decision_object_delta_m": plan["object_delta_m"].astype(np.float32),
        "object_displacement_m": np.asarray(object_positions, dtype=np.float32),
        "episode_object_mobile": plan["mobile_episodes"].astype(bool),
        "bearing_offset_deg": np.asarray(frame_bearings, dtype=np.float32),
    }
    ref2._validate_corpus(data, spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **data)
    return {"path": str(path), "sha256": _sha256_file(path), "images": spec.images}


def _image_x(
    *,
    center_deg: float,
    bearing_offset_deg: float,
    object_position_m: float,
    head_angle_deg: float,
) -> float:
    object_bearing = (
        center_deg
        + bearing_offset_deg
        + math.degrees(math.atan(object_position_m / REF3_DISTANCE_M))
    )
    relative = math.radians(object_bearing - head_angle_deg)
    focal = 32.0 / math.tan(math.radians(REF3_HALF_FOV_DEG))
    return 31.5 + focal * math.tan(relative)


def generate_bank(
    seed: int,
    kind: str,
    path: Path,
    spec: Ref3Spec,
) -> ref2.Ref2Bank:
    if kind not in BANKS:
        raise ValueError(f"unknown REF3 bank: {kind}")
    if path.exists():
        bank = ref2.Ref2Bank.load(path)
        ref2._validate_bank(bank, kind, spec)
        with np.load(path) as stored:
            required = {
                "object_start_m",
                "object_end_m",
                "bearing_offset_deg",
                "pair_digest",
                "motor_digest",
                "piece_seed",
                "object_seed",
                "motor_seed",
                "bearing_seed",
                "render_seed",
                "counterfactual_effect",
                "head_photometric_change",
                "effect_ratio",
                "object_image_x",
                "counterfactual_render_seconds",
            }
            if not required.issubset(stored.files):
                raise RuntimeError(f"REF3 {kind} bank lacks audit fields")
        return bank

    motion = ref2.build_matched_motion_plans(seed, spec)[kind]
    object_start, object_end = _feasible_object_plan(seed, kind, motion)
    bearing_offsets = _bearing_plan(seed, kind, len(object_start))
    core: dict[str, list[Any]] = {
        name: []
        for name in (
            "frames_start",
            "frames_end",
            "current_angle_deg",
            "command_targets_deg",
            "horizon",
            "planned_signed_amplitude_deg",
            "angle_bins",
            "contexts",
            "head_delta_deg",
            "object_delta_m",
            "labels",
        )
    }
    audit: dict[str, list[Any]] = {
        name: []
        for name in (
            "object_start_m",
            "object_end_m",
            "bearing_offset_deg",
            "piece_seed",
            "object_seed",
            "motor_seed",
            "bearing_seed",
            "render_seed",
            "counterfactual_effect",
            "head_photometric_change",
            "effect_ratio",
            "object_image_x",
            "counterfactual_digest",
        )
    }
    counterfactual_render_seconds = 0.0
    for angle_bin, center in enumerate(STRUCTURED_CENTERS_DEG):
        bin_indices = np.flatnonzero(motion["angle_bin"] == angle_bin)
        for context in (0, 1):
            chosen = bin_indices[context::2]
            room_seed = (
                266_000_000
                + seed * 10_000
                + BANKS.index(kind) * 1_000
                + angle_bin * 10
                + context
            )
            env = BenchHeadEnv(ref3_bench_config(room_seed, center, context))
            try:
                for index in chosen:
                    bearing = center + float(bearing_offsets[index])
                    configure_external_object(env, bearing_deg=bearing)
                    start_angle = float(motion["current_angle_deg"][index])
                    targets = motion["command_targets_deg"][index]
                    span = int(motion["horizon"][index])
                    env.set_external_object_displacement(float(object_start[index]))
                    start_observation = set_pretransition_head_pose(env, start_angle)
                    start_frame = env.render_camera(spec.image_size, spec.image_size)
                    for step in range(span):
                        fraction = (step + 1) / span
                        env.set_external_object_displacement(
                            float(
                                object_start[index]
                                + fraction * (object_end[index] - object_start[index])
                            )
                        )
                        for _ in range(5):
                            end_observation = env.step(float(targets[step]))
                    end_frame = env.render_camera(spec.image_size, spec.image_size)
                    env.set_external_object_displacement(float(object_start[index]))
                    counterfactual_started = time.perf_counter()
                    counterfactual = env.render_camera(spec.image_size, spec.image_size)
                    counterfactual_render_seconds += (
                        time.perf_counter() - counterfactual_started
                    )
                    env.set_external_object_displacement(float(object_end[index]))

                    object_effect = float(
                        np.mean(
                            np.abs(
                                end_frame.astype(np.float64)
                                - counterfactual.astype(np.float64)
                            )
                        )
                        / 255.0
                    )
                    head_effect = float(
                        np.mean(
                            np.abs(
                                counterfactual.astype(np.float64)
                                - start_frame.astype(np.float64)
                            )
                        )
                        / 255.0
                    )
                    ratio = object_effect / max(head_effect, 1e-12)

                    core["frames_start"].append(start_frame)
                    core["frames_end"].append(end_frame)
                    core["current_angle_deg"].append(float(start_observation.as5600_deg))
                    core["command_targets_deg"].append(targets.astype(np.float32))
                    core["horizon"].append(span)
                    core["planned_signed_amplitude_deg"].append(
                        float(motion["signed_amplitude_deg"][index])
                    )
                    core["angle_bins"].append(angle_bin)
                    core["contexts"].append(context)
                    core["head_delta_deg"].append(
                        float(end_observation.as5600_deg - start_observation.as5600_deg)
                    )
                    core["object_delta_m"].append(
                        float(object_end[index] - object_start[index])
                    )
                    core["labels"].append(kind)
                    audit["object_start_m"].append(float(object_start[index]))
                    audit["object_end_m"].append(float(object_end[index]))
                    audit["bearing_offset_deg"].append(float(bearing_offsets[index]))
                    audit["piece_seed"].append(room_seed)
                    audit["object_seed"].append(
                        255_000_000 + seed * 10 + BANKS.index(kind)
                    )
                    audit["motor_seed"].append(_motion_seed(seed, kind))
                    audit["bearing_seed"].append(
                        256_000_000 + seed * 10 + BANKS.index(kind)
                    )
                    audit["render_seed"].append(room_seed)
                    audit["counterfactual_effect"].append(object_effect)
                    audit["head_photometric_change"].append(head_effect)
                    audit["effect_ratio"].append(ratio)
                    audit["object_image_x"].append(
                        _image_x(
                            center_deg=center,
                            bearing_offset_deg=float(bearing_offsets[index]),
                            object_position_m=float(object_end[index]),
                            head_angle_deg=float(end_observation.as5600_deg),
                        )
                    )
                    audit["counterfactual_digest"].append(
                        _sha256_bytes(counterfactual.tobytes())
                    )
            finally:
                env.close()

    current = np.asarray(core["current_angle_deg"], dtype=np.float32)
    commands = np.stack(core["command_targets_deg"]).astype(np.float32)
    horizons = np.asarray(core["horizon"], dtype=np.int8)
    motor = ref2.build_motor_input(current, commands, horizons)
    frames_start = np.stack(core["frames_start"]).astype(np.uint8)
    frames_end = np.stack(core["frames_end"]).astype(np.uint8)
    pair_digest = np.asarray(
        [
            _sha256_bytes(left.tobytes() + right.tobytes())
            for left, right in zip(frames_start, frames_end)
        ],
        dtype="U64",
    )
    motor_digest = np.asarray(
        [_sha256_bytes(value.tobytes()) for value in motor],
        dtype="U64",
    )
    payload = {
        "frames_start": frames_start,
        "frames_end": frames_end,
        "current_angle_deg": current,
        "command_targets_deg": commands,
        "motor_input": motor,
        "horizon": horizons,
        "planned_signed_amplitude_deg": np.asarray(
            core["planned_signed_amplitude_deg"],
            dtype=np.float32,
        ),
        "angle_bins": np.asarray(core["angle_bins"], dtype=np.int8),
        "contexts": np.asarray(core["contexts"], dtype=np.int8),
        "head_delta_deg": np.asarray(core["head_delta_deg"], dtype=np.float32),
        "object_delta_m": np.asarray(core["object_delta_m"], dtype=np.float32),
        "labels": np.asarray(core["labels"], dtype="U32"),
        "object_start_m": np.asarray(audit["object_start_m"], dtype=np.float32),
        "object_end_m": np.asarray(audit["object_end_m"], dtype=np.float32),
        "bearing_offset_deg": np.asarray(audit["bearing_offset_deg"], dtype=np.float32),
        "piece_seed": np.asarray(audit["piece_seed"], dtype=np.int64),
        "object_seed": np.asarray(audit["object_seed"], dtype=np.int64),
        "motor_seed": np.asarray(audit["motor_seed"], dtype=np.int64),
        "bearing_seed": np.asarray(audit["bearing_seed"], dtype=np.int64),
        "render_seed": np.asarray(audit["render_seed"], dtype=np.int64),
        "pair_digest": pair_digest,
        "motor_digest": motor_digest,
        "counterfactual_effect": np.asarray(
            audit["counterfactual_effect"],
            dtype=np.float32,
        ),
        "head_photometric_change": np.asarray(
            audit["head_photometric_change"],
            dtype=np.float32,
        ),
        "effect_ratio": np.asarray(audit["effect_ratio"], dtype=np.float32),
        "object_image_x": np.asarray(audit["object_image_x"], dtype=np.float32),
        "counterfactual_digest": np.asarray(
            audit["counterfactual_digest"],
            dtype="U64",
        ),
        "counterfactual_render_seconds": np.asarray(
            [counterfactual_render_seconds],
            dtype=np.float64,
        ),
    }
    bank = ref2.Ref2Bank(
        **{name: payload[name] for name in ref2.Ref2Bank.__annotations__}
    )
    ref2._validate_bank(bank, kind, spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **payload)
    return bank


def load_bank_audit(path: Path) -> dict[str, np.ndarray]:
    names = (
        "object_start_m",
        "object_end_m",
        "bearing_offset_deg",
        "piece_seed",
        "object_seed",
        "motor_seed",
        "bearing_seed",
        "render_seed",
        "pair_digest",
        "motor_digest",
        "counterfactual_effect",
        "head_photometric_change",
        "effect_ratio",
        "object_image_x",
        "counterfactual_digest",
        "counterfactual_render_seconds",
    )
    with np.load(path) as stored:
        return {name: np.array(stored[name]) for name in names}


def _visibility_summary(path: Path, kind: str) -> dict[str, Any]:
    bank = ref2.Ref2Bank.load(path)
    audit = load_bank_audit(path)
    effects = audit["counterfactual_effect"].astype(np.float64)
    by_bin = []
    for angle_bin in range(6):
        selected = bank.angle_bins == angle_bin
        values = effects[selected]
        by_bin.append(
            {
                "bin": angle_bin,
                "minimum": float(np.min(values)),
                "median": float(np.median(values)),
                "maximum": float(np.max(values)),
                "mean": float(np.mean(values)),
            }
        )
    relevant = kind in {"external_only", "mixed"}
    passed = True
    if relevant:
        passed = bool(
            np.all(effects >= REF3_VISIBILITY_MINIMUM)
            and all(
                item["mean"] >= REF3_VISIBILITY_BIN_MEAN_MINIMUM
                for item in by_bin
            )
        )
    return {
        "relevant": relevant,
        "minimum": float(np.min(effects)),
        "median": float(np.median(effects)),
        "maximum": float(np.max(effects)),
        "by_bin": by_bin,
        "passed": passed,
    }


def data_integrity_checks(
    seed: int,
    root: Path,
    spec: Ref3Spec,
) -> dict[str, Any]:
    envelope = field_envelope()
    if not envelope["passed"]:
        raise AssertionError("REF3 structural field envelope failed")

    corpus = ref2.load_corpus(ref2.corpus_path(root, seed))
    corpus_frame_hashes = {
        _sha256_bytes(frame.tobytes())
        for frame in corpus["frames"]
    }
    corpus_pair_hashes: set[str] = set()
    pairs_by_horizon = ref2.build_pairs_multi(corpus["episode"], spec.max_horizon)
    for horizon, indices in pairs_by_horizon.items():
        for index in indices:
            corpus_pair_hashes.add(
                _sha256_bytes(
                    corpus["frames"][index].tobytes()
                    + corpus["frames"][index + horizon].tobytes()
                )
            )

    banks = {
        kind: ref2.Ref2Bank.load(ref2.bank_path(root, seed, kind))
        for kind in BANKS
    }
    audits = {
        kind: load_bank_audit(ref2.bank_path(root, seed, kind))
        for kind in BANKS
    }
    planned = ref2.build_matched_motion_plans(seed, spec)
    for angle_bin in range(6):
        signatures = [
            ref2.matched_motion_signature(planned[kind], angle_bin)
            for kind in MOBILE_MATCHED_BANKS
        ]
        if signatures[1:] != signatures[:-1]:
            raise AssertionError("REF3 mobile schedule multiset mismatch")

    audit_only_fields = {
        "object_start_m",
        "object_end_m",
        "bearing_offset_deg",
        "piece_seed",
        "object_seed",
        "motor_seed",
        "bearing_seed",
        "render_seed",
        "counterfactual_effect",
        "head_photometric_change",
        "effect_ratio",
        "object_image_x",
        "counterfactual_digest",
    }
    if audit_only_fields & set(ref2.Ref2Bank.__annotations__):
        raise AssertionError("REF3 counterfactual audit leaked into learner bank")

    seen_pair: dict[str, str] = {}
    seen_pair_motor: dict[tuple[str, str], tuple[Any, ...]] = {}
    seen_frames: dict[str, tuple[str, int, str]] = {}
    interbank_frame_collisions: list[dict[str, Any]] = []
    diversity: dict[str, Any] = {}
    rng_sets: dict[str, dict[str, set[int]]] = {
        field: {} for field in (
            "piece_seed",
            "object_seed",
            "motor_seed",
            "bearing_seed",
            "render_seed",
        )
    }

    for kind in BANKS:
        bank = banks[kind]
        audit = audits[kind]
        recomputed_motor = ref2.build_motor_input(
            bank.current_angle_deg,
            bank.command_targets_deg,
            bank.horizon,
        )
        if not np.array_equal(recomputed_motor, bank.motor_input):
            raise AssertionError(f"REF3 future-free motor reconstruction failed for {kind}")

        start_hashes = [_sha256_bytes(frame.tobytes()) for frame in bank.frames_start]
        end_hashes = [_sha256_bytes(frame.tobytes()) for frame in bank.frames_end]
        if corpus_frame_hashes & (set(start_hashes) | set(end_hashes)):
            raise AssertionError(f"REF3 corpus-bank frame collision involving {kind}")

        recomputed_pairs = np.asarray(
            [
                _sha256_bytes(left.tobytes() + right.tobytes())
                for left, right in zip(bank.frames_start, bank.frames_end)
            ],
            dtype="U64",
        )
        if not np.array_equal(recomputed_pairs, audit["pair_digest"]):
            raise AssertionError(f"REF3 pair digest mismatch in {kind}")
        if len(set(recomputed_pairs.tolist())) != len(recomputed_pairs):
            raise AssertionError(f"REF3 duplicated pair inside {kind}")
        if corpus_pair_hashes & set(recomputed_pairs.tolist()):
            raise AssertionError(f"REF3 corpus-bank pair collision involving {kind}")

        recomputed_motor_hashes = np.asarray(
            [_sha256_bytes(value.tobytes()) for value in bank.motor_input],
            dtype="U64",
        )
        if not np.array_equal(recomputed_motor_hashes, audit["motor_digest"]):
            raise AssertionError(f"REF3 motor digest mismatch in {kind}")

        for index, (pair_digest, motor_digest) in enumerate(
            zip(recomputed_pairs.tolist(), recomputed_motor_hashes.tolist())
        ):
            if pair_digest in seen_pair:
                raise AssertionError(
                    f"REF3 inter-bank pair collision: {seen_pair[pair_digest]} / {kind}"
                )
            seen_pair[pair_digest] = kind
            provenance = (
                kind,
                seed,
                int(bank.angle_bins[index]),
                int(bank.contexts[index]),
                index,
                int(audit["piece_seed"][index]),
                int(audit["object_seed"][index]),
                int(audit["motor_seed"][index]),
                int(audit["bearing_seed"][index]),
                int(audit["render_seed"][index]),
            )
            key = (pair_digest, motor_digest)
            previous = seen_pair_motor.get(key)
            if previous is not None and previous != provenance:
                raise AssertionError("REF3 pair+motor collision has distinct provenance")
            seen_pair_motor[key] = provenance

        for side, hashes in (("start", start_hashes), ("end", end_hashes)):
            for index, frame_digest in enumerate(hashes):
                previous = seen_frames.get(frame_digest)
                if previous is not None and previous[0] != kind:
                    interbank_frame_collisions.append(
                        {
                            "sha256": frame_digest,
                            "left": {
                                "bank": previous[0],
                                "index": previous[1],
                                "side": previous[2],
                            },
                            "right": {"bank": kind, "index": index, "side": side},
                        }
                    )
                else:
                    seen_frames[frame_digest] = (kind, index, side)

        visibility = _visibility_summary(ref2.bank_path(root, seed, kind), kind)
        if not visibility["passed"]:
            raise AssertionError(f"REF3 visibility failed in {kind}")
        if np.any(np.abs(audit["bearing_offset_deg"]) > REF3_BEARING_OFFSET_MAX_DEG):
            raise AssertionError(f"REF3 bearing offset escaped its support in {kind}")
        for field in rng_sets:
            values = set(int(value) for value in audit[field])
            for other_kind, other_values in rng_sets[field].items():
                if values & other_values:
                    raise AssertionError(
                        f"REF3 {field} overlaps between {other_kind} and {kind}"
                    )
            rng_sets[field][kind] = values

        diversity[kind] = {
            "distinct_start_frames": len(set(start_hashes)),
            "distinct_end_frames": len(set(end_hashes)),
            "distinct_pairs": len(set(recomputed_pairs.tolist())),
            "visibility": visibility,
        }

    mixed_correlation = ref2._correlation(
        banks["mixed"].head_delta_deg,
        banks["mixed"].object_delta_m,
    )
    if abs(mixed_correlation) > 0.05:
        raise AssertionError(f"REF3 mixed independence failed: {mixed_correlation}")
    if np.any(banks["external_only"].head_delta_deg != 0):
        raise AssertionError("REF3 external-only head is not constant")

    return {
        "field_envelope": envelope,
        "matched_mobile_schedules": True,
        "future_free_motor_inputs": True,
        "counterfactual_fields_invisible": True,
        "corpus_frame_disjoint": True,
        "corpus_pair_disjoint": True,
        "interbank_pair_disjoint": True,
        "pair_motor_provenance_unique": True,
        "interbank_frame_collisions": interbank_frame_collisions,
        "rng_spaces_disjoint_between_banks": True,
        "mixed_correlation": mixed_correlation,
        "external_head_constant": True,
        "diversity": diversity,
    }


def prepare_seed(seed: int, root: Path, spec: Ref3Spec) -> dict[str, Any]:
    started = time.perf_counter()
    corpus = generate_corpus(seed, ref2.corpus_path(root, seed), spec)
    counterfactual_seconds = 0.0
    banks: dict[str, Any] = {}
    for kind in BANKS:
        bank_started = time.perf_counter()
        bank = generate_bank(seed, kind, ref2.bank_path(root, seed, kind), spec)
        bank_seconds = time.perf_counter() - bank_started
        path = ref2.bank_path(root, seed, kind)
        audit = load_bank_audit(path)
        counterfactual_seconds += float(audit["counterfactual_render_seconds"][0])
        banks[kind] = {
            "path": str(path),
            "sha256": _sha256_file(path),
            "pairs": len(bank),
            "generation_seconds": bank_seconds,
            "counterfactual_render_seconds": float(
                audit["counterfactual_render_seconds"][0]
            ),
            "visibility": _visibility_summary(path, kind),
        }
    if not all(item["visibility"]["passed"] for item in banks.values()):
        raise AssertionError("REF3 per-pair visibility guard failed")
    payload = {
        "seed": seed,
        "spec_digest": spec.digest(),
        "field_envelope": field_envelope(),
        "corpus": corpus,
        "banks": banks,
        "counterfactual_instrumented_bank_seconds": counterfactual_seconds,
        "elapsed_seconds": time.perf_counter() - started,
    }
    ref2._write_json(root / "manifests" / f"seed_{seed}.json", payload)
    return payload


# Frozen learner/scoring implementation re-exported without modification.
build_matched_motion_plans = ref2.build_matched_motion_plans
build_motor_input = ref2.build_motor_input
encoder_digest = ref2.encoder_digest
evaluation_path = ref2.evaluation_path
make_learner = ref2.make_learner
matched_motion_signature = ref2.matched_motion_signature
parameter_counts = ref2.parameter_counts
run_path = ref2.run_path
state_digest = ref2.state_digest
train_condition = ref2.train_condition
evaluate_seed = ref2.evaluate_seed


def analyze_evaluations(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the inherited analysis with only the declared seed parameters changed."""

    original_reserved = ref2.RESERVED_SEEDS
    original_analysis_seed = ref2.ANALYSIS_SEED
    try:
        ref2.RESERVED_SEEDS = RESERVED_SEEDS
        ref2.ANALYSIS_SEED = ANALYSIS_SEED
        analysis = ref2.analyze_evaluations(evaluations)
    finally:
        ref2.RESERVED_SEEDS = original_reserved
        ref2.ANALYSIS_SEED = original_analysis_seed

    sanity = analysis["sanity_external"]["transport_jepa"]
    sanity["minimum"] = REF3_SANITY_EXTERNAL_MINIMUM
    sanity["passed"] = bool(
        sanity["finite"]
        and sanity["mean"] >= REF3_SANITY_EXTERNAL_MINIMUM
    )
    analysis["guards"]["sanity_external_absolute"] = sanity["passed"]
    analysis["decision"]["eligible_for_contradictory_review"] = bool(
        analysis["h1_passed"]
        and analysis["h3_passed"]
        and analysis["h4_passed"]
        and analysis["h5_passed"]
        and all(analysis["guards"].values())
    )
    return analysis
