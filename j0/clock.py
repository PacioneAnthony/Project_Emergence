"""High-resolution host clock shared by all J0 capture sources."""

from __future__ import annotations

import time


def host_time_ns() -> int:
    return time.perf_counter_ns()


def host_clock_metadata() -> dict[str, int | float | str | bool]:
    info = time.get_clock_info("perf_counter")
    return {
        "name": "perf_counter",
        "implementation": info.implementation,
        "monotonic": info.monotonic,
        "adjustable": info.adjustable,
        "resolution_ns": max(1, round(info.resolution * 1_000_000_000)),
    }
