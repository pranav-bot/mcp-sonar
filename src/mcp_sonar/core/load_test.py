from __future__ import annotations

import asyncio
import time
from typing import Any

from mcp_sonar.config import TargetConfig
from mcp_sonar.core.stats import timing_stats_ms
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.target import ConnectedTarget, connect_target


async def _invoke_on_target(target: ConnectedTarget, tool_name: str, arguments: dict[str, Any]) -> ToolOutcome:
    if tool_name == "__list_tools__":
        names = await target.list_tools()
        text = "\n".join(names)
        return ToolOutcome(
            tool_name="__list_tools__",
            arguments={},
            is_error=False,
            text=text,
            payload_bytes=len(text.encode("utf-8")),
        )
    return await target.call_tool(tool_name, arguments)


async def run_parallel_load(
    target_name: str,
    config: TargetConfig,
    *,
    tool_name: str,
    arguments: dict[str, Any],
    concurrency: int,
    min_success_rate: float,
) -> ToolOutcome:
    """Open ``concurrency`` independent MCP sessions and invoke the same tool on each."""

    async def worker(_index: int) -> tuple[bool, float, str | None]:
        start = time.perf_counter()
        try:
            async with connect_target(target_name, config) as connected:
                outcome = await _invoke_on_target(connected, tool_name, arguments)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            if outcome.is_error:
                return False, elapsed_ms, (outcome.error_message or outcome.text or "tool error")
            return True, elapsed_ms, None
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return False, elapsed_ms if elapsed_ms > 0 else 0.0, str(exc)

    results = await asyncio.gather(*[worker(i) for i in range(concurrency)])
    successes = sum(1 for ok, _, _ in results if ok)
    durations = [ms for _, ms, _ in results]
    first_error = next((msg for ok, _, msg in results if not ok and msg), None)
    stats = timing_stats_ms([d / 1000.0 for d in durations])
    success_rate = successes / concurrency if concurrency else 0.0
    gate_passed = success_rate >= min_success_rate

    summary = (
        f"load: {successes}/{concurrency} ok ({success_rate:.1%}), "
        f"p50 {stats.p50_ms:.0f}ms p95 {stats.p95_ms:.0f}ms, "
        f"min success {min_success_rate:.0%} — {'PASS' if gate_passed else 'FAIL'}"
    )
    if first_error:
        summary += f" — {first_error.splitlines()[0][:200]}"
    detail_lines = [
        summary,
        f"tool={tool_name} concurrency={concurrency}",
        f"wall p50={stats.p50_ms:.1f}ms p95={stats.p95_ms:.1f}ms max={stats.max_ms:.1f}ms",
    ]
    report_text = "\n".join(detail_lines)

    return ToolOutcome(
        tool_name="__mcp_load_parallel__",
        arguments={"tool": tool_name, "concurrency": concurrency, "arguments": arguments},
        is_error=not gate_passed,
        text=report_text,
        payload_bytes=len(report_text.encode()),
        structured={
            "gate_passed": gate_passed,
            "success_rate": success_rate,
            "min_success_rate": min_success_rate,
            "concurrency": concurrency,
            "successes": successes,
            "summary": summary,
            "timing_p50_ms": stats.p50_ms,
            "timing_p95_ms": stats.p95_ms,
        },
        error_message=summary if not gate_passed else None,
    )
