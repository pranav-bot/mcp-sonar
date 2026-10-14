from __future__ import annotations

from mcp_sonar.checks.builtin import check_load_gate
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.suite.load_context import reset_load_settings, set_load_settings
from mcp_sonar.suite.registry import get_suite
from mcp_sonar.suite.yaml_suite import suite_from_yaml
from pathlib import Path


def test_mcp_load_suite_registered() -> None:
    suite = get_suite("mcp-load")
    token = set_load_settings(concurrency=5, tool="echo", arguments={"message": "x"}, min_success_rate=0.9)
    try:
        steps = suite.steps()
        assert steps[0].id == "parallel_load"
    finally:
        reset_load_settings(token)


def test_check_load_gate() -> None:
    outcome = ToolOutcome(
        "__mcp_load_parallel__",
        {},
        False,
        "detail",
        6,
        structured={"gate_passed": True, "success_rate": 1.0, "summary": "load ok"},
    )
    assert check_load_gate(outcome)[0]


def test_tool_accuracy_suite_yaml() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "suites" / "tool-accuracy.yaml"
    suite = suite_from_yaml(path)
    assert suite.id == "tool-accuracy"
    assert len(suite.steps()) >= 3
    assert suite.steps()[0].id == "list_tools"
