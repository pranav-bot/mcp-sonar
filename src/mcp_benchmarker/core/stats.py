from __future__ import annotations

from mcp_benchmarker.core.types import TimingStats


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def timing_stats_ms(durations_sec: list[float]) -> TimingStats:
    if not durations_sec:
        return TimingStats(0.0, 0.0, 0.0, 0.0, 0)
    ms = [d * 1000.0 for d in durations_sec]
    ms.sort()
    return TimingStats(
        min_ms=ms[0],
        p50_ms=_percentile(ms, 0.5),
        p95_ms=_percentile(ms, 0.95),
        max_ms=ms[-1],
        samples=len(ms),
    )
