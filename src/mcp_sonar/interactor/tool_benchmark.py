from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from mcp_sonar.core.stats import timing_stats_ms
from mcp_sonar.core.types import TimingStats
from mcp_sonar.target import ConnectedTarget


@dataclass(frozen=True)
class ToolBenchmarkResult:
    tool_name: str
    arguments: dict[str, Any]
    timing: TimingStats
    success_rate: float
    last_error: str | None = None


async def benchmark_tool_call(
    target: ConnectedTarget,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    warmup: int,
    iterations: int,
) -> ToolBenchmarkResult:
    if iterations < 1:
        raise ValueError("iterations must be at least 1")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")

    durations: list[float] = []
    successes = 0
    last_error: str | None = None
    total_runs = warmup + iterations

    for index in range(total_runs):
        start = time.perf_counter()
        outcome = await target.call_tool(tool_name, arguments)
        elapsed = time.perf_counter() - start
        if index >= warmup:
            durations.append(elapsed)
            if not outcome.is_error:
                successes += 1
            elif outcome.error_message:
                last_error = outcome.error_message
            else:
                last_error = (outcome.text or "tool error")[:500]

    measured = max(iterations, 1)
    return ToolBenchmarkResult(
        tool_name=tool_name,
        arguments=arguments,
        timing=timing_stats_ms(durations),
        success_rate=successes / measured,
        last_error=last_error,
    )
