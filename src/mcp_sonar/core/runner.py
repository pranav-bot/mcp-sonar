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
from mcp_sonar.suite.registry import Suite
from mcp_sonar.target import ConnectedTarget


def _transport_fields(target: ConnectedTarget) -> dict[str, str]:
    return {
        "transport_kind": target.transport.kind,
        "transport_endpoint": target.transport.endpoint,
        "transport_label": target.transport.summary(),
    }


async def _invoke_resolved(target: ConnectedTarget, resolved: ResolvedStep) -> Any:
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
    )


async def run_suite_on_target(
    target: ConnectedTarget,
    suite: Suite,
    *,
    warmup: int,
    iterations: int,
    skip_functional: bool,
) -> SingleTargetReport:
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
) -> CompareReport:
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
        )
        right_result = await run_scenario_on_target(
            right,
            suite,
            step.id,
            warmup=warmup,
            iterations=iterations,
            skip_functional=skip_functional,
        )
        report.rows.append(CompareScenarioRow(scenario_id=step.id, left=left_result, right=right_result))
    return report
