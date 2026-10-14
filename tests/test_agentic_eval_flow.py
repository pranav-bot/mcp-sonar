from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from mcp_sonar.checks.builtin import check_eval_flow_gate
from mcp_sonar.config import StdioTransportConfig, TargetConfig
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.integrations.agentic_eval_flow.aggregate import aggregate_mcpchecker_output
from mcp_sonar.integrations.agentic_eval_flow.pack import mcp_endpoint_from_target
from mcp_sonar.suite.registry import get_suite
from mcp_sonar.transport import TransportInfo


def test_agentic_mcp_suite_registered() -> None:
    suite = get_suite("agentic-mcp")
    assert [s.id for s in suite.steps()] == ["mcpchecker"]


def test_aggregate_mcpchecker_output_scores_tasks(tmp_path: Path) -> None:
    raw = {
        "results": [
            {"taskName": "a", "taskPassed": True},
            {"taskName": "b", "taskPassed": False},
        ]
    }
    path = tmp_path / "out.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    report = aggregate_mcpchecker_output(path, submission_name="t", threshold=0.7)
    assert report.total_tasks == 2
    assert report.passed_tasks == 1
    assert report.overall_score == 0.5
    assert not report.gate_passed


def test_check_eval_flow_gate() -> None:
    outcome = ToolOutcome(
        "__agentic_mcpchecker__",
        {},
        False,
        "body",
        4,
        structured={"gate_passed": True, "overall_score": 0.85, "summary": "ok"},
    )
    assert check_eval_flow_gate(outcome)[0]


@dataclass
class _FakeTarget:
    name: str
    config: TargetConfig
    transport: TransportInfo


def test_mcp_endpoint_requires_streamable_http() -> None:
    target = _FakeTarget(
        "t",
        TargetConfig(transport=StdioTransportConfig(command="c", args=[])),
        TransportInfo("stdio", "c"),
    )
    with pytest.raises(ValueError, match="streamable_http"):
        mcp_endpoint_from_target(target)  # type: ignore[arg-type]
