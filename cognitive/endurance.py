"""Bounded endurance campaign for the persistent developmental supervisor."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from cognitive.kernel import CognitiveKernel
from cognitive.models import SafetyContext
from cognitive.supervisor import (
    DevelopmentCycleRequest,
    PersistentDevelopmentSupervisor,
)
from j0.recorder import directory_size


FAULT_PATTERN = (
    "direct",
    "after_selected",
    "after_executed",
    "after_assessment",
    "unsafe_then_resume",
)


@dataclass(frozen=True)
class EnduranceConfig:
    campaign_id: str = "life008-endurance-v1"
    session_id: str = "life008-endurance-session-v1"
    competence_name: str = "bounded_servo_tracking"
    cycle_count: int = 64
    seed_start: int = 17801
    clock_base_ns: int = 1_000_000_000
    max_database_bytes: int = 4 * 1024 * 1024
    max_j0_bytes: int = 4 * 1024 * 1024
    max_mean_combined_bytes_per_cycle: int = 128 * 1024

    def __post_init__(self) -> None:
        if not self.campaign_id or not self.session_id or not self.competence_name:
            raise ValueError("endurance campaign identities are required")
        if self.cycle_count < 5:
            raise ValueError("endurance campaign requires at least five cycles")
        if not 0 <= self.seed_start <= 0xFFFFFFFF:
            raise ValueError("seed_start is outside uint32")
        if self.seed_start + self.cycle_count - 1 > 0xFFFFFFFF:
            raise ValueError("endurance seed range exceeds uint32")
        if self.clock_base_ns < 0:
            raise ValueError("clock_base_ns must be non-negative")
        if min(
            self.max_database_bytes,
            self.max_j0_bytes,
            self.max_mean_combined_bytes_per_cycle,
        ) <= 0:
            raise ValueError("endurance size limits must be positive")


@dataclass(frozen=True)
class EnduranceReport:
    campaign: Mapping[str, Any]
    counts: Mapping[str, Any]
    invocation: Mapping[str, Any]
    storage: Mapping[str, Any]
    integrity: Mapping[str, Any]
    gates: Mapping[str, bool]
    logical_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _database_family_size(path: Path) -> int:
    return sum(
        candidate.stat().st_size
        for candidate in (
            path,
            Path(str(path) + "-wal"),
            Path(str(path) + "-shm"),
        )
        if candidate.exists()
    )


def _database_family_contains(path: Path, needle: bytes) -> bool:
    return any(
        needle in candidate.read_bytes()
        for candidate in (
            path,
            Path(str(path) + "-wal"),
            Path(str(path) + "-shm"),
        )
        if candidate.exists()
    )


def _cycle_request(config: EnduranceConfig, index: int) -> DevelopmentCycleRequest:
    label = f"{config.campaign_id}-{index:04d}"
    return DevelopmentCycleRequest(
        cycle_id=f"cycle-{label}",
        execution_id=f"execution-{label}",
        j0_session_id=f"j0-{label}",
        seed=config.seed_start + index,
    )


def _reopen(
    kernel: CognitiveKernel,
    database_path: Path,
    catalog,
) -> CognitiveKernel:
    kernel.close()
    restored = CognitiveKernel(database_path, catalog=catalog)
    if restored.session_id is None:
        raise RuntimeError("endurance restart lost its active cognitive session")
    return restored


def run_endurance_campaign(
    database_path: str | Path,
    data_root: str | Path,
    *,
    catalog,
    supervisor: PersistentDevelopmentSupervisor,
    safety: SafetyContext,
    config: EnduranceConfig | None = None,
    report_path: str | Path | None = None,
) -> EnduranceReport:
    """Run or resume a deterministic multi-cycle endurance qualification."""

    campaign = config or EnduranceConfig()
    database = Path(database_path)
    j0_root = Path(data_root)
    requests = [_cycle_request(campaign, index) for index in range(campaign.cycle_count)]
    restart_count = 0
    unsafe_block_count = 0
    skipped_complete = 0
    kernel = CognitiveKernel(database, catalog=catalog)
    try:
        missing = [
            request
            for request in requests
            if (
                kernel.memory.development_cycle(request.cycle_id) is None
                or kernel.memory.development_cycle(request.cycle_id)["status"] != "complete"
            )
        ]
        if missing:
            if kernel.session_id is None:
                existing = kernel.memory.session(campaign.session_id)
                if existing is not None:
                    raise RuntimeError("endurance session ended before all cycles completed")
                kernel.start_session(
                    campaign.session_id,
                    started_at_ns=campaign.clock_base_ns,
                    metadata={
                        "purpose": "life-008-endurance",
                        "campaign_id": campaign.campaign_id,
                    },
                )
            elif kernel.session_id != campaign.session_id:
                raise RuntimeError("another cognitive session is active")

        for index, request in enumerate(requests):
            existing = kernel.memory.development_cycle(request.cycle_id)
            if existing is not None and existing["status"] == "complete":
                skipped_complete += 1
                continue
            now_ns = campaign.clock_base_ns + (index + 1) * 1_000_000_000
            pattern = FAULT_PATTERN[index % len(FAULT_PATTERN)]
            if pattern == "direct":
                supervisor.advance(kernel, request, now_ns=now_ns, safety=safety)
            elif pattern == "after_selected":
                supervisor.advance(
                    kernel,
                    request,
                    now_ns=now_ns,
                    safety=safety,
                    stop_after="selected",
                )
                kernel = _reopen(kernel, database, catalog)
                restart_count += 1
                supervisor.advance(kernel, request, now_ns=now_ns, safety=safety)
            elif pattern == "after_executed":
                supervisor.advance(
                    kernel,
                    request,
                    now_ns=now_ns,
                    safety=safety,
                    stop_after="executed",
                )
                kernel = _reopen(kernel, database, catalog)
                restart_count += 1
                supervisor.advance(kernel, request, now_ns=now_ns, safety=safety)
            elif pattern == "after_assessment":
                supervisor.advance(
                    kernel,
                    request,
                    now_ns=now_ns,
                    safety=safety,
                    stop_after="assessment_applied",
                )
                kernel = _reopen(kernel, database, catalog)
                restart_count += 1
                supervisor.advance(kernel, request, now_ns=now_ns, safety=safety)
            else:
                supervisor.advance(
                    kernel,
                    request,
                    now_ns=now_ns,
                    safety=safety,
                    stop_after="selected",
                )
                unsafe = SafetyContext(
                    emergency_stop=True,
                    hardware_healthy=safety.hardware_healthy,
                    model_update_in_progress=safety.model_update_in_progress,
                    quota_state=safety.quota_state,
                    allowed_primitives=safety.allowed_primitives,
                )
                try:
                    supervisor.advance(kernel, request, now_ns=now_ns, safety=unsafe)
                except RuntimeError as error:
                    if "emergency_stop" not in str(error):
                        raise
                    unsafe_block_count += 1
                else:
                    raise AssertionError("unsafe endurance execution was not blocked")
                if kernel.memory.development_cycle(request.cycle_id)["status"] != "selected":
                    raise AssertionError("unsafe attempt changed the selected cycle")
                kernel = _reopen(kernel, database, catalog)
                restart_count += 1
                supervisor.advance(kernel, request, now_ns=now_ns, safety=safety)

        if kernel.session_id is not None:
            kernel.end_session(
                ended_at_ns=campaign.clock_base_ns
                + (campaign.cycle_count + 1) * 1_000_000_000
            )

        cycle_ids = [request.cycle_id for request in requests]
        proposal_ids: list[str] = []
        statuses: list[str] = []
        assessment_statuses: list[str] = []
        for cycle_id in cycle_ids:
            row = kernel.memory.development_cycle(cycle_id)
            if row is None:
                statuses.append("missing")
                continue
            statuses.append(str(row["status"]))
            proposal_ids.append(str(row["proposal_id"]))
            result = json.loads(row["result_json"])
            assessment_statuses.append(str(result.get("assessment_status", "missing")))

        execution_ids = [request.execution_id for request in requests]
        completed_executions = sum(
            kernel.memory.experiment_execution(execution_id) is not None
            and kernel.memory.experiment_execution(execution_id)["status"] == "complete"
            for execution_id in execution_ids
        )
        j0_complete = 0
        j0_event_counts: list[int] = []
        for request in requests:
            manifest_path = (
                j0_root / "sessions" / request.j0_session_id / "manifest.json"
            )
            if not manifest_path.is_file():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("status") == "complete":
                j0_complete += 1
            j0_event_counts.append(int(manifest.get("event_count", -1)))

        competence_history = [
            row["to_status"]
            for row in kernel.memory.competence_history(campaign.competence_name)
        ]
        assessment_count = len(
            kernel.memory.competence_assessments(campaign.competence_name)
        )
        proposal_unique = len(set(proposal_ids))
        execution_unique = len(set(execution_ids))
        integrity_check = kernel.memory.integrity_check()
        active_cycles = kernel.memory.connection.execute(
            """
            SELECT COUNT(*) FROM development_cycles
            WHERE status IN ('selected', 'executed')
            """
        ).fetchone()[0]
        running_executions = kernel.memory.connection.execute(
            "SELECT COUNT(*) FROM experiment_executions WHERE status = 'running'"
        ).fetchone()[0]
        database_bytes = _database_family_size(database)
        j0_bytes = directory_size(j0_root)
        combined_mean = (database_bytes + j0_bytes) / campaign.cycle_count
        raw_needles_absent = not any(
            _database_family_contains(database, needle)
            for needle in (
                b"requested_deg",
                b"as5600_deg",
                b"targets_deg",
                b"servo_target",
            )
        )

        counts = {
            "cycles": len(statuses),
            "complete_cycles": statuses.count("complete"),
            "proposals": len(proposal_ids),
            "unique_proposals": proposal_unique,
            "complete_executions": completed_executions,
            "unique_execution_ids": execution_unique,
            "complete_j0_sessions": j0_complete,
            "assessments": assessment_count,
            "insufficient_history_cycles": assessment_statuses.count(
                "insufficient_history"
            ),
            "applied_assessment_cycles": assessment_statuses.count("applied"),
            "active_cycles": int(active_cycles),
            "running_executions": int(running_executions),
        }
        storage = {
            "database_family_bytes": database_bytes,
            "j0_bytes": j0_bytes,
            "combined_mean_bytes_per_cycle": combined_mean,
        }
        planned_faults = {
            name: sum(
                index % len(FAULT_PATTERN) == pattern_index
                for index in range(campaign.cycle_count)
            )
            for pattern_index, name in enumerate(FAULT_PATTERN)
        }
        integrity = {
            "sqlite_integrity_check": integrity_check,
            "competence_history": competence_history,
            "all_j0_event_counts_12": j0_event_counts == [12] * campaign.cycle_count,
            "raw_payload_fields_absent_from_sqlite": raw_needles_absent,
            "planned_fault_counts": planned_faults,
        }
        gates = {
            "all_cycles_complete": counts["complete_cycles"] == campaign.cycle_count,
            "one_proposal_per_cycle": counts["proposals"] == proposal_unique
            == campaign.cycle_count,
            "one_execution_per_cycle": completed_executions == execution_unique
            == campaign.cycle_count,
            "j0_sessions_complete": j0_complete == campaign.cycle_count
            and integrity["all_j0_event_counts_12"],
            "assessment_count": assessment_count == campaign.cycle_count - 1,
            "single_initial_competence_promotion": competence_history
            == ["learning", "candidate", "validated"],
            "sqlite_integrity": integrity_check == "ok",
            "no_active_residue": active_cycles == 0 and running_executions == 0,
            "raw_payload_absent": raw_needles_absent,
            "database_size": database_bytes < campaign.max_database_bytes,
            "j0_size": j0_bytes < campaign.max_j0_bytes,
            "mean_growth": combined_mean
            < campaign.max_mean_combined_bytes_per_cycle,
            "fault_matrix_covered": all(value > 0 for value in planned_faults.values()),
        }
        logical_payload = {
            "campaign": asdict(campaign),
            "counts": counts,
            "integrity": integrity,
            "non_storage_gates": {
                key: value
                for key, value in gates.items()
                if key not in {"database_size", "j0_size", "mean_growth"}
            },
        }
        logical_digest = hashlib.sha256(
            json.dumps(
                logical_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        report = EnduranceReport(
            campaign=asdict(campaign),
            counts=counts,
            invocation={
                "restart_count": restart_count,
                "unsafe_block_count": unsafe_block_count,
                "skipped_complete_cycles": skipped_complete,
            },
            storage=storage,
            integrity=integrity,
            gates=gates,
            logical_digest=logical_digest,
        )
        if report_path is not None:
            target = Path(report_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(
                    report.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        failed = [name for name, passed in gates.items() if not passed]
        if failed:
            raise AssertionError("LIFE-008 endurance gates failed: " + ", ".join(failed))
        return report
    finally:
        try:
            kernel.close()
        except Exception:
            pass
