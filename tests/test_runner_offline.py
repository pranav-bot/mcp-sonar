from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from mcp_benchmarker.core.runner import run_scenario_on_target
from mcp_benchmarker.core.types import ToolOutcome
from mcp_benchmarker.suite.registry import get_suite
from mcp_benchmarker.transport import TransportInfo


@dataclass
class _FakeTarget:
    name: str
    binding: str
    transport: TransportInfo
    _responses: dict[str, ToolOutcome]

    @property
    def label(self) -> str:
        return self.name

    @classmethod
    def build(cls, responses: dict[str, ToolOutcome]) -> _FakeTarget:
        return cls(
            name="fake",
            binding="default",
            transport=TransportInfo(kind="stdio", endpoint="fake-cmd"),
            _responses=responses,
        )

    async def list_tools(self) -> list[str]:
        return ["echo"]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolOutcome:
        return self._responses.get(
            name,
            ToolOutcome(tool_name=name, arguments=arguments or {}, is_error=True, text="missing", payload_bytes=0),
        )


@pytest.mark.asyncio
async def test_run_mcp_smoke_list_tools() -> None:
    suite = get_suite("mcp-smoke")
    target = _FakeTarget.build(
        {
            "__list_tools__": ToolOutcome(
                tool_name="__list_tools__",
                arguments={},
                is_error=False,
                text="echo\nadd",
                payload_bytes=10,
            )
        }
    )
    result = await run_scenario_on_target(
        target,
        suite,
        "list_tools",
        warmup=0,
        iterations=2,
        skip_functional=False,
    )
    assert result.functional_pass
    assert result.timing.samples == 2
