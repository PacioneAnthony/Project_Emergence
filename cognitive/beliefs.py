"""In-memory belief state with deterministic persistence snapshots."""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from cognitive.models import BeliefEstimate


SNAPSHOT_SCHEMA_VERSION = 1


class BeliefUnavailableError(LookupError):
    """Raised when a belief is missing, stale, too uncertain, or too weak."""


class ClockDomainMismatchError(ValueError):
    """Raised when timestamp ordering would cross incomparable clocks."""


class BeliefState:
    def __init__(self) -> None:
        self._beliefs: dict[str, BeliefEstimate] = {}
        self._revision = 0

    @property
    def revision(self) -> int:
        return self._revision

    def __len__(self) -> int:
        return len(self._beliefs)

    def get(self, name: str) -> BeliefEstimate | None:
        return self._beliefs.get(name)

    def update(
        self,
        estimate: BeliefEstimate,
        *,
        allow_clock_change: bool = False,
    ) -> bool:
        """Install a non-older estimate; return False for stale/duplicate input."""

        previous = self._beliefs.get(estimate.name)
        if previous is not None:
            if estimate.clock_domain != previous.clock_domain:
                if not allow_clock_change:
                    raise ClockDomainMismatchError(
                        f"belief {estimate.name!r} changes clock domain from "
                        f"{previous.clock_domain!r} to {estimate.clock_domain!r}"
                    )
            else:
                prior_order = (previous.observed_at_ns, previous.received_at_ns)
                new_order = (estimate.observed_at_ns, estimate.received_at_ns)
                if new_order <= prior_order:
                    return False
        self._beliefs[estimate.name] = estimate
        self._revision += 1
        return True

    def require(
        self,
        name: str,
        *,
        now_ns: int,
        max_age_ns: int,
        max_variance: float,
        min_quality: float = 0.0,
    ) -> BeliefEstimate:
        if now_ns < 0 or max_age_ns < 0 or max_variance < 0:
            raise ValueError("belief constraints must be non-negative")
        estimate = self._beliefs.get(name)
        if estimate is None:
            raise BeliefUnavailableError(f"belief {name!r} is missing")
        if estimate.observed_at_ns > now_ns:
            raise BeliefUnavailableError(f"belief {name!r} is dated in the future")
        if now_ns - estimate.observed_at_ns > max_age_ns:
            raise BeliefUnavailableError(f"belief {name!r} is stale")
        if estimate.variance > max_variance:
            raise BeliefUnavailableError(f"belief {name!r} is too uncertain")
        if estimate.quality < min_quality:
            raise BeliefUnavailableError(f"belief {name!r} quality is too low")
        return estimate

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "revision": self._revision,
            "beliefs": [self._beliefs[name].to_dict() for name in sorted(self._beliefs)],
        }

    def canonical_json(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> "BeliefState":
        version = int(snapshot.get("schema_version", -1))
        if version != SNAPSHOT_SCHEMA_VERSION:
            raise ValueError(f"unsupported belief snapshot schema version: {version}")
        state = cls()
        estimates = [BeliefEstimate.from_dict(item) for item in snapshot.get("beliefs", ())]
        state._beliefs = {estimate.name: estimate for estimate in estimates}
        if len(state._beliefs) != len(estimates):
            raise ValueError("belief snapshot contains duplicate names")
        state._revision = int(snapshot["revision"])
        if state._revision < len(state._beliefs):
            raise ValueError("belief snapshot revision is inconsistent")
        return state


def fuse_independent_gaussians(
    name: str,
    estimates: Iterable[BeliefEstimate],
    *,
    received_at_ns: int,
    source_id: str,
    calibration_version: str = "fused",
    model_version: str = "analytic-v1",
) -> BeliefEstimate:
    """Fuse estimates assuming independent Gaussian observation errors."""

    items = tuple(estimates)
    if not items:
        raise ValueError("at least one estimate is required")
    if len({item.clock_domain for item in items}) != 1:
        raise ClockDomainMismatchError("Gaussian fusion requires one common clock domain")
    if any(item.variance <= 0 for item in items):
        raise ValueError("Gaussian fusion requires strictly positive variances")
    precision = sum(1.0 / item.variance for item in items)
    variance = 1.0 / precision
    mean = variance * sum(item.mean / item.variance for item in items)
    quality = min(item.quality for item in items)
    return BeliefEstimate(
        name=name,
        mean=mean,
        variance=variance,
        observed_at_ns=max(item.observed_at_ns for item in items),
        received_at_ns=received_at_ns,
        source_id=source_id,
        clock_domain=items[0].clock_domain,
        quality=quality,
        calibration_version=calibration_version,
        model_version=model_version,
    )
