from __future__ import annotations

import json

from mcp_sonar.checks.builtin import check_contains_text, check_expect_error
from mcp_sonar.core.types import ToolOutcome


def test_contains_text() -> None:
    outcome = ToolOutcome("t", {}, False, "hello world", 5)
    assert check_contains_text(outcome, text="world")[0]


def test_expect_error_on_flag() -> None:
    outcome = ToolOutcome("t", {}, True, "bad", 3)
    assert check_expect_error(outcome)[0]
