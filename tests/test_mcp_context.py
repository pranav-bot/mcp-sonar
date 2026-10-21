from __future__ import annotations

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
