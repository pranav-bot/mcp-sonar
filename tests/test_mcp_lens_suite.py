from __future__ import annotations

import pytest

from mcp_sonar.checks.builtin import check_lens_gate
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.suite.mcp_lens_context import reset_lens_mode, set_lens_mode
from mcp_sonar.suite.registry import get_suite


def test_mcp_lens_suite_step_ids_by_mode() -> None:
    suite = get_suite("mcp-lens")
    token = set_lens_mode("static")
    try:
        assert [s.id for s in suite.steps()] == ["lens_static"]
    finally:
        reset_lens_mode(token)

    token = set_lens_mode("llm")
    try:
        assert [s.id for s in suite.steps()] == ["lens_llm"]
    finally:
        reset_lens_mode(token)

    token = set_lens_mode("both")
    try:
        assert [s.id for s in suite.steps()] == ["lens_static", "lens_llm"]
    finally:
        reset_lens_mode(token)


def test_check_lens_gate_uses_structured_summary() -> None:
    outcome = ToolOutcome(
        "__mcp_lens_static__",
        {"mode": "static"},
        False,
        "report body",
        12,
        structured={"gate_passed": True, "overall_score": 88.0, "summary": "mcp-lens (static): PASS"},
    )
    ok, msg = check_lens_gate(outcome)
    assert ok
    assert "PASS" in msg


def test_apply_lens_mode_rejects_non_lens_suite() -> None:
    import click

    from mcp_sonar.cli import _apply_lens_mode

    with pytest.raises(click.ClickException) as exc:
        _apply_lens_mode("mcp-smoke", "static")
    assert "mcp-lens" in str(exc.value)
