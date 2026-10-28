from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import mcp_sonar.interactor.agent_cmds as agent_cmds
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.interactor.agent import AgentRunResult, run_agent
from mcp_sonar.interactor.agent_cmds import run_agent_batch_cmd


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


def _finished(prompt: str) -> AgentRunResult:
    return AgentRunResult(
        prompt=prompt,
        steps=[],
        final_answer="ok",
        llm_config="test",
        stopped_reason="complete",
    )


def _patch_batch(monkeypatch: pytest.MonkeyPatch, opened: list[str], run):
    class _Conn:
        def __init__(self, target: str) -> None:
            self.target = target

        async def __aenter__(self):
            opened.append(self.target)
            return (self.target, object())

        async def __aexit__(self, *args: object) -> bool:
            return False

    monkeypatch.setattr(agent_cmds, "bootstrap_local_workspace", lambda _config: None)
    monkeypatch.setattr(agent_cmds, "resolve_llm_config_path", lambda: None)
    monkeypatch.setattr(agent_cmds, "get_adapter_for_config", lambda _name: object())
    monkeypatch.setattr(agent_cmds, "print_connected_target", lambda _connected: None)
    monkeypatch.setattr(agent_cmds, "open_target", lambda target, _config: _Conn(target))
    monkeypatch.setattr(agent_cmds, "run_agent", run)


@pytest.mark.asyncio
async def test_agent_batch_opens_target_per_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text('target: t\nprompts:\n  - "alpha"\n  - "beta"\n', encoding="utf-8")
    opened: list[str] = []
    seen: list[str] = []

    async def fake_run(target, adapter, prompt, *, llm_config_name, max_steps):
        seen.append(prompt)
        return _finished(prompt)

    _patch_batch(monkeypatch, opened, fake_run)
    results = await run_agent_batch_cmd(path, None, None, llm_config="test", max_steps=2, fmt="json")
    assert opened == ["t", "t"]
    assert seen == ["alpha", "beta"]
    assert [item.prompt for item in results] == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_agent_batch_prints_finished_prompts_when_a_later_one_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text('target: t\nprompts:\n  - "alpha"\n  - "beta"\n', encoding="utf-8")
    printed: list[str] = []

    async def fake_run(target, adapter, prompt, *, llm_config_name, max_steps):
        if prompt == "beta":
            raise RuntimeError("session died")
        return _finished(prompt)

    _patch_batch(monkeypatch, [], fake_run)
    monkeypatch.setattr(agent_cmds.console, "print_json", lambda json=None, **_kwargs: printed.append(json or ""))
    with pytest.raises(RuntimeError, match="session died"):
        await run_agent_batch_cmd(path, None, None, llm_config="test", max_steps=2, fmt="json")
    assert printed and "alpha" in printed[0]
    assert "beta" not in printed[0]


@pytest.mark.asyncio
async def test_plain_unknown_field_is_sent_again() -> None:
    calls: list[str] = []

    class _Target:
        async def list_tool_definitions(self) -> list[_FakeTool]:
            return [_FakeTool("echo")]

        async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolOutcome:
            calls.append(name)
            return ToolOutcome(name, arguments or {}, True, "Unknown format for this field", 5)

    class _Adapter:
        def __init__(self) -> None:
            self.left = 2

        async def select_tool(self, tools: list[dict], user_prompt: str) -> dict:
            if self.left:
                self.left -= 1
                return {"tool_name": "echo", "arguments": {"message": "x"}}
            return {"tool_name": "", "arguments": {}}

        async def generate_answer(self, tool_result: Any, user_prompt: str) -> str:
            return "ok"

    await run_agent(_Target(), _Adapter(), "again", llm_config_name="test", max_steps=4)
    assert calls == ["echo", "echo"]
