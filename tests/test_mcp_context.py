from __future__ import annotations

import pytest
from mcp.shared.exceptions import MCPError

from mcp_sonar.checks.builtin import check_context_gate
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.integrations.context_usage.catalog import CatalogSnapshot
from mcp_sonar.integrations.context_usage.static_eval import analyze_static_context, render_static_report
from mcp_sonar.integrations.context_usage.tokens import estimate_tokens
from mcp_sonar.suite.mcp_context_context import reset_context_settings, set_context_settings
from mcp_sonar.suite.registry import get_suite


def test_estimate_tokens_heuristic() -> None:
    count, method = estimate_tokens("abcd" * 10)
    assert method in ("chars/4", "tiktoken:cl100k_base")
    assert count == 10


def test_static_context_budget_gate() -> None:
    catalog = CatalogSnapshot(
        server_name="t",
        tools=[{"name": "echo", "description": "x" * 400, "inputSchema": {"type": "object"}}],
    )
    metrics = analyze_static_context(catalog, token_budget=50)
    assert metrics.total_tokens > 50
    assert not metrics.gate_passed
    assert "Largest tools" in render_static_report(metrics)


def test_mcp_context_suite_modes() -> None:
    suite = get_suite("mcp-context")
    token = set_context_settings(mode="static", token_budget=0, min_llm_score=70.0)
    try:
        assert [s.id for s in suite.steps()] == ["context_static"]
    finally:
        reset_context_settings(token)


@pytest.mark.asyncio
async def test_fetch_catalog_treats_missing_method_as_empty() -> None:
    from mcp_sonar.integrations.context_usage.catalog import fetch_catalog

    class _Target:
        name = "t"

        async def list_tool_definitions(self) -> list:
            return []

        async def list_prompts(self) -> list:
            raise MCPError(-32601, "Method not found")

        async def list_resources(self) -> list:
            raise MCPError(-32601, "Method not found")

    catalog = await fetch_catalog(_Target())  # type: ignore[arg-type]
    assert catalog.prompts == []
    assert catalog.resources == []


@pytest.mark.asyncio
async def test_fetch_catalog_fails_on_real_list_error() -> None:
    from mcp_sonar.integrations.context_usage.catalog import fetch_catalog

    class _Target:
        name = "t"

        async def list_tool_definitions(self) -> list:
            return []

        async def list_prompts(self) -> list:
            return []

        async def list_resources(self) -> list:
            raise RuntimeError("connection reset")

    with pytest.raises(RuntimeError, match="list_resources failed"):
        await fetch_catalog(_Target())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_context_both_keeps_static_when_llm_reply_is_not_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_sonar.integrations.context_usage.evaluate import evaluate_context_async

    async def _boom(*_args, **_kwargs):
        raise ValueError("LLM response did not contain JSON object")

    monkeypatch.setattr("mcp_sonar.integrations.context_usage.evaluate._run_llm", _boom)
    result = await evaluate_context_async(
        CatalogSnapshot(server_name="t", tools=[{"name": "echo"}]),
        mode="both",
        token_budget=0,
        min_llm_score=70,
    )
    assert "llm_error" in result.metadata
    assert "static" in result.metadata


def test_parse_llm_json_uses_the_last_object() -> None:
    from mcp_sonar.integrations.context_usage.llm_eval import _parse_llm_json

    text = 'example {"context_score": 1} final {"context_score": 90, "summary": "ok"}'
    assert _parse_llm_json(text)["context_score"] == 90


def test_check_context_gate() -> None:
    outcome = ToolOutcome(
        "__mcp_context_static__",
        {},
        False,
        "report",
        6,
        structured={"gate_passed": True, "summary": "ok", "overall_score": 90.0},
    )
    assert check_context_gate(outcome)[0]
