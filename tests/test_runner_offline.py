from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from mcp_sonar.core.runner import run_scenario_on_target
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.suite.registry import get_suite
from mcp_sonar.transport import TransportInfo


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


@pytest.mark.asyncio
async def test_list_tools_error_is_a_failed_sample() -> None:
    suite = get_suite("mcp-smoke")

    class _Down(_FakeTarget):
        async def list_tools(self) -> list[str]:
            raise RuntimeError("connection reset")

    target = _Down.build({})
    result = await run_scenario_on_target(
        target,
        suite,
        "list_tools",
        warmup=0,
        iterations=1,
        skip_functional=False,
    )
    assert not result.functional_pass
    assert "connection reset" in (result.functional_message or "")


@pytest.mark.asyncio
async def test_one_shot_suite_ignores_repeat_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_sonar.core import runner as runner_module
    from mcp_sonar.core.runner import run_suite_on_target

    calls = 0

    async def _once(_target: object) -> ToolOutcome:
        nonlocal calls
        calls += 1
        return ToolOutcome("__agentic_mcpchecker__", {}, False, "ok", 2, structured={"gate_passed": True, "summary": "ok"})

    monkeypatch.setattr(runner_module, "_invoke_agentic_eval", _once)
    suite = get_suite("agentic-mcp")
    target = _FakeTarget.build({})
    report = await run_suite_on_target(target, suite, warmup=2, iterations=10, skip_functional=False)
    assert calls == 1
    assert report.iterations == 1
    assert report.warmup == 0
    assert report.scenarios[0].timing.samples == 1


@pytest.mark.asyncio
async def test_iterations_must_be_positive() -> None:
    suite = get_suite("mcp-smoke")
    target = _FakeTarget.build({})
    with pytest.raises(ValueError, match="iterations must be at least 1"):
        await run_scenario_on_target(
            target,
            suite,
            "list_tools",
            warmup=0,
            iterations=0,
            skip_functional=False,
        )
