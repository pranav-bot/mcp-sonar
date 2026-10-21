from __future__ import annotations

from typing import Any

import pytest

from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.interactor.agent import run_agent


class _FakeTool:
    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description


class _FakeTarget:
    async def list_tool_definitions(self) -> list[_FakeTool]:
        return [_FakeTool("echo", "echo back")]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolOutcome:
        args = arguments or {}
        return ToolOutcome(
            name,
            args,
            False,
            f"echo:{args.get('message', '')}",
            10,
        )


class _FakeAdapter:
    def __init__(self) -> None:
        self.select_calls = 0

    async def select_tool(self, tools: list[dict], user_prompt: str) -> dict:
        self.select_calls += 1
        if self.select_calls == 1:
            return {"tool_name": "echo", "arguments": {"message": "ping"}}
        return {"tool_name": "", "arguments": {}}

    async def generate_answer(self, tool_result: Any, user_prompt: str) -> str:
        return f"Final after {tool_result}"


@pytest.mark.asyncio
async def test_run_agent_tool_then_final() -> None:
    target = _FakeTarget()
    adapter = _FakeAdapter()
    result = await run_agent(target, adapter, "say hi", llm_config_name="test", max_steps=5)
    assert result.stopped_reason == "complete"
    assert len(result.steps) == 2
    assert result.steps[0].kind == "tool_call"
    assert result.steps[0].tool_name == "echo"
    assert result.steps[1].kind == "final"
    assert "echo:ping" in result.final_answer
    assert result.timing is not None
    assert result.timing.tool_ms >= 0
    assert result.steps[0].tool_invoke_ms is not None
    assert result.steps[1].generate_answer_ms is not None
