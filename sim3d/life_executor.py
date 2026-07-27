"""Bounded MuJoCo-only executor for persisted cognitive proposals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

from cognitive.kernel import CognitiveKernel
from cognitive.models import ExperimentProposal, SafetyContext
from cognitive.observed_signals import ServoTrialSummary
from j0.events import Event
from j0.recorder import QuotaPolicy, SessionRecorder
from sim3d.bench_env import BenchHeadEnv
from sim3d.bench_model import BenchConfig


@dataclass(frozen=True)
class BoundedPrimitivePlan:
    primitive: str
    targets_deg: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.primitive:
            raise ValueError("primitive name is required")
        if not 1 <= len(self.targets_deg) <= 64:
            raise ValueError("a bounded primitive must contain 1 to 64 steps")
        for target in self.targets_deg:
            if not math.isfinite(target) or not 10.0 <= target <= 170.0:
                raise ValueError("primitive targets must be finite and inside [10, 170]")

    def digest(self) -> str:
        payload = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


DEFAULT_LIFE_PLANS = (
    BoundedPrimitivePlan("diagnose_bounded_servo", (40.0,) * 12),
    BoundedPrimitivePlan("scan_bounded_servo", (40.0, 140.0) * 6),
)


@dataclass(frozen=True)
class SimulatedExecutionOutcome:
    proposal_id: str
    execution_id: str
    j0_session_id: str
    session_dir: Path
    plan_digest: str
    summary: ServoTrialSummary


class BoundedMujocoExecutor:
    """Execute only registered bounded primitives in the bench digital twin."""

    def __init__(
        self,
        data_root: str | Path,
        *,
        plans: Iterable[BoundedPrimitivePlan] = DEFAULT_LIFE_PLANS,
        quota: QuotaPolicy | None = None,
    ) -> None:
        self.data_root = Path(data_root)
        self.quota = quota or QuotaPolicy()
        self._plans: dict[str, BoundedPrimitivePlan] = {}
        for plan in plans:
            if plan.primitive in self._plans:
                raise ValueError(f"duplicate bounded primitive: {plan.primitive}")
            self._plans[plan.primitive] = plan
        if not self._plans:
            raise ValueError("at least one bounded primitive is required")

    @staticmethod
    def _guard_safety(proposal: ExperimentProposal, safety: SafetyContext) -> None:
        reasons: list[str] = []
        if safety.emergency_stop:
            reasons.append("emergency_stop")
        if not safety.hardware_healthy:
            reasons.append("simulator_unhealthy")
        if safety.model_update_in_progress:
            reasons.append("model_update_in_progress")
        if safety.quota_state not in {"ok", "warning"}:
            reasons.append(f"quota:{safety.quota_state}")
        if proposal.primitive not in safety.allowed_primitives:
            reasons.append("primitive_not_allowed")
        if reasons:
            raise RuntimeError("simulation execution blocked: " + ", ".join(reasons))

    @staticmethod
    def _verify_persisted_proposal(
        kernel: CognitiveKernel,
        proposal: ExperimentProposal,
    ) -> None:
        if kernel.session_id is None:
            raise RuntimeError("an active cognitive session is required")
        row = kernel.memory.proposal(proposal.proposal_id)
        if row is None:
            raise ValueError("proposal is not persisted")
        expected = (
            proposal.session_id,
            proposal.experiment_id,
            proposal.primitive,
        )
        actual = (row["session_id"], row["experiment_id"], row["primitive"])
        if actual != expected:
            raise ValueError("proposal object does not match its persisted identity")
        if proposal.session_id != kernel.session_id:
            raise ValueError("proposal does not belong to the active cognitive session")
        if row["status"] != "proposed":
            raise ValueError("persisted proposal is no longer proposed")

    def execute(
        self,
        kernel: CognitiveKernel,
        proposal: ExperimentProposal,
        *,
        execution_id: str,
        j0_session_id: str,
        seed: int,
        started_at_ns: int,
        safety: SafetyContext,
    ) -> SimulatedExecutionOutcome:
        """Run a complete registered primitive and return its verified LIFE-003 result."""

        if not execution_id or not j0_session_id:
            raise ValueError("execution_id and j0_session_id are required")
        if started_at_ns < 0:
            raise ValueError("started_at_ns must be non-negative")
        if not 0 <= seed <= 0xFFFFFFFF:
            raise ValueError("seed must be in [0, 2^32-1]")
        self._verify_persisted_proposal(kernel, proposal)
        self._guard_safety(proposal, safety)
        try:
            plan = self._plans[proposal.primitive]
        except KeyError as error:
            raise ValueError(f"unsupported bounded primitive: {proposal.primitive}") from error

        plan_digest = plan.digest()
        recorder: SessionRecorder | None = None
        env: BenchHeadEnv | None = None
        execution_begun = False
        try:
            recorder = SessionRecorder(
                self.data_root,
                session_id=j0_session_id,
                metadata={
                    "purpose": "life-004-bounded-mujoco-execution",
                    "proposal_id": proposal.proposal_id,
                    "execution_id": execution_id,
                    "experiment_id": proposal.experiment_id,
                    "primitive": proposal.primitive,
                    "seed": int(seed),
                    "plan_digest": plan_digest,
                },
                quota=self.quota,
            )
            kernel.begin_experiment_execution(
                proposal.proposal_id,
                execution_id=execution_id,
                session_dir=recorder.session_dir,
                started_at_ns=started_at_ns,
            )
            execution_begun = True

            bench_config = BenchConfig(seed=int(seed))
            if any(
                not bench_config.servo.min_deg
                <= target
                <= bench_config.servo.max_deg
                for target in plan.targets_deg
            ):
                raise ValueError("primitive target is outside the active simulator bounds")
            env = BenchHeadEnv(bench_config)
            env.reset(seed=int(seed))
            last_timestamp_ns = started_at_ns
            for sequence_id, target_deg in enumerate(plan.targets_deg):
                observation = env.step(target_deg)
                if observation.requested_deg != target_deg:
                    raise RuntimeError("simulator altered a bounded primitive target")
                last_timestamp_ns = started_at_ns + int(round(observation.time * 1e9))
                recorder.append(
                    Event(
                        session_id=j0_session_id,
                        event_type="servo_state",
                        source_id="bench-head-sim",
                        sequence_id=sequence_id,
                        source_timestamp_ns=last_timestamp_ns,
                        host_receive_timestamp_ns=last_timestamp_ns,
                        payload={
                            "requested_deg": observation.requested_deg,
                            "as5600_deg": observation.as5600_deg,
                        },
                        quality={
                            "payload_valid": True,
                            "simulation": True,
                            "bounded_primitive": True,
                        },
                        calibration_version="bench-head-v1",
                    )
                )
            recorder.close()
            summary = kernel.complete_observed_execution(
                execution_id,
                completed_at_ns=last_timestamp_ns,
            )
            return SimulatedExecutionOutcome(
                proposal_id=proposal.proposal_id,
                execution_id=execution_id,
                j0_session_id=j0_session_id,
                session_dir=recorder.session_dir,
                plan_digest=plan_digest,
                summary=summary,
            )
        except Exception:
            if recorder is not None:
                recorder.abort("LIFE-004 execution failed")
            if execution_begun:
                execution = kernel.memory.experiment_execution(execution_id)
                if execution is not None and execution["status"] == "running":
                    kernel.abort_experiment_execution(execution_id)
            raise
        finally:
            if env is not None:
                env.close()
