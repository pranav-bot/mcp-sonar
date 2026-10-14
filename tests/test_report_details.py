from __future__ import annotations

from mcp_sonar.core.runner import _scenario_detail
from mcp_sonar.core.stats import timing_stats_ms
from mcp_sonar.core.types import ScenarioRunResult, SingleTargetReport, ToolOutcome


def test_scenario_detail_lens_always_captured() -> None:
    outcome = ToolOutcome(
        "__mcp_lens_static__",
        {},
        False,
        "full lens report\nline two",
        20,
    )
    assert _scenario_detail(outcome, include_all_responses=False) == "full lens report\nline two"


def test_scenario_detail_other_tools_only_with_verbose() -> None:
    outcome = ToolOutcome("echo", {}, False, "hello", 5)
    assert _scenario_detail(outcome, include_all_responses=False) is None
    assert _scenario_detail(outcome, include_all_responses=True) == "hello"


def test_single_report_has_detail_field() -> None:
    report = SingleTargetReport(
        suite_id="mcp-lens",
        target_name="t",
        target_label="T",
        binding="default",
        transport_kind="stdio",
        transport_endpoint="cmd",
        warmup=0,
        iterations=1,
        scenarios=[
            ScenarioRunResult(
                scenario_id="lens_static",
                target_name="t",
                binding="default",
                transport_kind="stdio",
                transport_endpoint="cmd",
                transport_label="stdio",
                functional_pass=True,
                functional_message="ok",
                timing=timing_stats_ms([0.1]),
                success_rate=1.0,
                detail="report body",
            )
        ],
    )
    assert report.scenarios[0].detail == "report body"
