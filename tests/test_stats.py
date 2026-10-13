from __future__ import annotations

from mcp_benchmarker.core.stats import timing_stats_ms


def test_timing_stats_empty() -> None:
    stats = timing_stats_ms([])
    assert stats.samples == 0


def test_timing_stats_ordering() -> None:
    stats = timing_stats_ms([0.01, 0.02, 0.03, 0.04])
    assert stats.min_ms == 10.0
    assert stats.max_ms == 40.0
    assert stats.p50_ms == 25.0
