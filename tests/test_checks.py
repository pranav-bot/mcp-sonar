from __future__ import annotations

import json

from mcp_sonar.checks.builtin import check_contains_text, check_expect_error
from mcp_sonar.core.types import ToolOutcome


def test_contains_text() -> None:
    outcome = ToolOutcome("t", {}, False, "hello world", 5)
    assert check_contains_text(outcome, text="world")[0]


def test_contains_text_fails_when_tool_errors() -> None:
    outcome = ToolOutcome("t", {}, True, "invalid message sonar-accuracy-probe", 20)
    passed, _message = check_contains_text(outcome, text="sonar-accuracy-probe")
    assert not passed


def test_expect_error_on_flag() -> None:
    outcome = ToolOutcome("t", {}, True, "bad", 3)
    assert check_expect_error(outcome)[0]


def test_expect_error_ignores_success_text() -> None:
    outcome = ToolOutcome("t", {}, False, "syntax highlighting is enabled", 20)
    assert not check_expect_error(outcome)[0]


def test_json_path_uses_structured_payload() -> None:
    from mcp_sonar.checks.builtin import check_json_path_exists

    outcome = ToolOutcome("t", {}, False, "ok", 2, structured={"id": 1})
    assert check_json_path_exists(outcome, path="id")[0]
