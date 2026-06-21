"""NTP-style clock offset estimates for Arduino synchronization replies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Iterable


@dataclass(frozen=True)
class SyncEstimate:
    token: int
    round_trip_ns: int
    device_to_host_offset_ns: int
    host_send_ns: int
    host_receive_ns: int
    device_receive_us: int
    device_send_us: int


def estimate_sync(
    *,
    token: int,
    host_send_ns: int,
    host_receive_ns: int,
    device_receive_us: int,
    device_send_us: int,
) -> SyncEstimate:
    device_receive_ns = device_receive_us * 1000
    device_send_ns = device_send_us * 1000
    device_processing_ns = max(0, device_send_ns - device_receive_ns)
    round_trip_ns = max(0, host_receive_ns - host_send_ns - device_processing_ns)
    offset_ns = round(((host_send_ns - device_receive_ns) + (host_receive_ns - device_send_ns)) / 2)
    return SyncEstimate(
        token=token,
        round_trip_ns=round_trip_ns,
        device_to_host_offset_ns=offset_ns,
        host_send_ns=host_send_ns,
        host_receive_ns=host_receive_ns,
        device_receive_us=device_receive_us,
        device_send_us=device_send_us,
    )


def summarize_sync(estimates: Iterable[SyncEstimate]) -> dict:
    values = list(estimates)
    if not values:
        return {"count": 0, "median_offset_ns": None, "jitter_ns": None, "median_round_trip_ns": None}
    offsets = [item.device_to_host_offset_ns for item in values]
    center = median(offsets)
    deviations = [abs(value - center) for value in offsets]
    return {
        "count": len(values),
        "median_offset_ns": int(center),
        "jitter_ns": int(max(deviations, default=0)),
        "median_round_trip_ns": int(median(item.round_trip_ns for item in values)),
        "samples": [asdict(item) for item in values],
    }
