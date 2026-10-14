from __future__ import annotations

import time
from typing import Any

from mcp_sonar.core.stats import timing_stats_ms
from mcp_sonar.core.types import (
    CompareReport,
    CompareScenarioRow,
    ScenarioRunResult,
    SingleTargetReport,
)
from mcp_sonar.suite.base import ResolvedStep, resolve_step
from mcp_sonar.suite.mcp_lens import LENS_LLM_TOOL, LENS_STATIC_TOOL
from mcp_sonar.suite.registry import Suite
from mcp_sonar.target import ConnectedTarget

_lens_tool_cache: dict[str, list[dict]] = {}


def _scenario_detail(outcome: Any, *, include_all_responses: bool) -> str | None:
    if outcome is None:
        return None
    text = (getattr(outcome, "text", None) or "").strip()
    if not text:
        return None
    tool_name = getattr(outcome, "tool_name", "")
    if str(tool_name).startswith("__mcp_lens_"):
        return text
    if include_all_responses:
        return text
    return None


def clear_lens_tool_cache() -> None:
    _lens_tool_cache.clear()


async def _lens_tools_for_target(target: ConnectedTarget) -> list[dict]:
    from mcp_sonar.integrations.mcp_lens import tools_to_lens_dicts  # noqa: PLC0415

    if target.name not in _lens_tool_cache:
        definitions = await target.list_tool_definitions()
        _lens_tool_cache[target.name] = tools_to_lens_dicts(definitions)
    return _lens_tool_cache[target.name]


async def _invoke_mcp_lens(target: ConnectedTarget, mode: str) -> Any:
    from mcp_sonar.core.types import ToolOutcome  # noqa: PLC0415
    from mcp_sonar.integrations.mcp_lens.evaluate import LensNotInstalledError, evaluate_tools  # noqa: PLC0415

    try:
        tools = await _lens_tools_for_target(target)
        result = evaluate_tools(tools, server_name=target.name, mode=mode)  # type: ignore[arg-type]
    except (LensNotInstalledError, RuntimeError) as exc:
        message = str(exc)
        return ToolOutcome(
            tool_name=f"__mcp_lens_{mode}__",
            arguments={"mode": mode},
            is_error=True,
            text=message,
            payload_bytes=len(message.encode()),
            error_message=message,
        )

    return ToolOutcome(
        tool_name=f"__mcp_lens_{mode}__",
        arguments={"mode": mode},
        is_error=not result.gate_passed,
        text=result.report_text,
        payload_bytes=len(result.report_text.encode()),
        structured={
            "gate_passed": result.gate_passed,
            "overall_score": result.overall_score,
            "summary": result.summary,
            "lens_mode": result.mode,
        },
        error_message=result.summary if not result.gate_passed else None,
    )


def _transport_fields(target: ConnectedTarget) -> dict[str, str]:
    return {
        "transport_kind": target.transport.kind,
        "transport_endpoint": target.transport.endpoint,
        "transport_label": target.transport.summary(),
    }


async def _invoke_resolved(target: ConnectedTarget, resolved: ResolvedStep) -> Any:
    if resolved.tool_name == LENS_STATIC_TOOL:
        return await _invoke_mcp_lens(target, "static")
    if resolved.tool_name == LENS_LLM_TOOL:
        return await _invoke_mcp_lens(target, "llm")
    if resolved.tool_name == "__list_tools__":
        names = await target.list_tools()
        from mcp_sonar.core.types import ToolOutcome  # noqa: PLC0415

        text = "\n".join(names)
        return ToolOutcome(
            tool_name="__list_tools__",
            arguments={},
            is_error=False,
            text=text,
            payload_bytes=len(text.encode("utf-8")),
        )
    return await target.call_tool(resolved.tool_name, resolved.arguments)


async def run_scenario_on_target(
    target: ConnectedTarget,
    suite: Suite,
    step_id: str,
    *,
    warmup: int,
    iterations: int,
    skip_functional: bool,
    include_all_responses: bool = False,
) -> ScenarioRunResult:
    step = next((s for s in suite.steps() if s.id == step_id), None)
    if step is None:
        raise KeyError(f"Unknown scenario {step_id} in suite {suite.id}")

    resolved = resolve_step(step, target.binding)
    if resolved.skipped:
        return ScenarioRunResult(
            scenario_id=step_id,
            target_name=target.name,
            binding=target.binding,
            **_transport_fields(target),
            functional_pass=True,
            functional_message=resolved.skip_reason or "skipped",
            timing=timing_stats_ms([]),
            success_rate=1.0,
            skipped=True,
            skip_reason=resolved.skip_reason,
        )

    durations: list[float] = []
    successes = 0
    last_outcome = None

    total_runs = warmup + iterations
    for index in range(total_runs):
        start = time.perf_counter()
        outcome = await _invoke_resolved(target, resolved)
        elapsed = time.perf_counter() - start
        if index >= warmup:
            durations.append(elapsed)
            if not outcome.is_error:
                successes += 1
        last_outcome = outcome

    functional_pass = True
    functional_message = "skipped (perf only)"
    if not skip_functional and last_outcome is not None:
        functional_pass, functional_message = step.check(last_outcome)

    measured = max(iterations, 1)
    return ScenarioRunResult(
        scenario_id=step_id,
        target_name=target.name,
        binding=target.binding,
        **_transport_fields(target),
        functional_pass=functional_pass,
        functional_message=functional_message,
        timing=timing_stats_ms(durations),
        success_rate=successes / measured,
        detail=_scenario_detail(last_outcome, include_all_responses=include_all_responses),
    )


async def run_suite_on_target(
    target: ConnectedTarget,
    suite: Suite,
    *,
    warmup: int,
    iterations: int,
    skip_functional: bool,
    include_all_responses: bool = False,
) -> SingleTargetReport:
    if suite.id == "mcp-lens":
        clear_lens_tool_cache()
    report = SingleTargetReport(
        suite_id=suite.id,
        target_name=target.name,
        target_label=target.label,
        binding=target.binding,
        transport_kind=target.transport.kind,
        transport_endpoint=target.transport.endpoint,
        warmup=warmup,
        iterations=iterations,
    )
    for step in suite.steps():
        result = await run_scenario_on_target(
            target,
            suite,
            step.id,
            warmup=warmup,
            iterations=iterations,
            skip_functional=skip_functional,
            include_all_responses=include_all_responses,
        )
        report.scenarios.append(result)
    return report


async def compare_targets(
    left: ConnectedTarget,
    right: ConnectedTarget,
    suite: Suite,
    *,
    warmup: int,
    iterations: int,
    skip_functional: bool,
    include_all_responses: bool = False,
) -> CompareReport:
    if suite.id == "mcp-lens":
        clear_lens_tool_cache()
    report = CompareReport(
        suite_id=suite.id,
        left_target=left.name,
        left_label=left.label,
        left_transport_kind=left.transport.kind,
        left_transport_endpoint=left.transport.endpoint,
        right_target=right.name,
        right_label=right.label,
        right_transport_kind=right.transport.kind,
        right_transport_endpoint=right.transport.endpoint,
        warmup=warmup,
        iterations=iterations,
    )
    for step in suite.steps():
        left_result = await run_scenario_on_target(
            left,
            suite,
            step.id,
            warmup=warmup,
            iterations=iterations,
            skip_functional=skip_functional,
            include_all_responses=include_all_responses,
        )
        right_result = await run_scenario_on_target(
            right,
            suite,
            step.id,
            warmup=warmup,
            iterations=iterations,
            skip_functional=skip_functional,
            include_all_responses=include_all_responses,
        )
        report.rows.append(CompareScenarioRow(scenario_id=step.id, left=left_result, right=right_result))
    return report
