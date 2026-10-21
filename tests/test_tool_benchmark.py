from __future__ import annotations

from typing import Any

import pytest

from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.interactor.tool_benchmark import benchmark_tool_call


class _FakeTarget:
    def __init__(self) -> None:
        self.calls = 0

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolOutcome:
        self.calls += 1
        return ToolOutcome(name, arguments or {}, False, "ok", 2)


@pytest.mark.asyncio
async def test_benchmark_tool_call_counts_samples() -> None:
    target = _FakeTarget()
    result = await benchmark_tool_call(target, "echo", {"message": "x"}, warmup=1, iterations=3)
    assert target.calls == 4
    assert result.timing.samples == 3
    assert result.success_rate == 1.0
    assert result.timing.p50_ms >= 0


@pytest.mark.asyncio
async def test_benchmark_tool_call_tracks_failures() -> None:
    class _FailTarget:
        async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolOutcome:
            return ToolOutcome(name, {}, True, "fail", 0, error_message="boom")

    result = await benchmark_tool_call(_FailTarget(), "t", {}, warmup=0, iterations=2)
    assert result.success_rate == 0.0
    assert result.last_error == "boom"
