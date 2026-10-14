"""Aggregate MCPChecker CLI JSON into Agentic Eval Flow report shape.

Adapted from ``scripts/aggregate_mcpchecker.py`` in
https://github.com/RHEcosystemAppEng/agentic_eval_flow (Apache-2.0).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class TaskResult:
    task_id: str
    task_name: str
    status: Literal["passed", "failed", "error", "skipped"]
    tool_calls: int = 0
    error_message: str | None = None
    agent_response: str | None = None


@dataclass
class MCPCheckerReport:
    submission_name: str
    eval_name: str
    overall_score: float
    passed_tasks: int
    failed_tasks: int
    error_tasks: int
    skipped_tasks: int
    total_tasks: int
    tasks: list[TaskResult] = field(default_factory=list)
    recommendation: str = "fail"
    threshold: float = 0.7

    @property
    def gate_passed(self) -> bool:
        return self.overall_score >= self.threshold


def _task_status(task_data: dict[str, Any]) -> str:
    if "taskPassed" in task_data:
        return "passed" if task_data["taskPassed"] else "failed"
    status_raw = str(task_data.get("status", "unknown")).lower()
    if status_raw in ("passed", "pass", "success"):
        return "passed"
    if status_raw in ("failed", "fail", "failure"):
        return "failed"
    if status_raw in ("skipped", "skip"):
        return "skipped"
    return "error"


def extract_task_results(raw_output: dict[str, Any]) -> list[TaskResult]:
    task_results = raw_output.get("taskResults") or raw_output.get("results") or []
    tasks: list[TaskResult] = []
    for task_data in task_results:
        if not isinstance(task_data, dict):
            continue
        task_id = str(task_data.get("taskId", task_data.get("taskPath", task_data.get("name", "unknown"))))
        task_name = str(task_data.get("taskName", task_data.get("name", task_id)))
        call_history = task_data.get("callHistory") or {}
        if isinstance(call_history, dict):
            tool_calls_data = call_history.get("ToolCalls") or []
        else:
            tool_calls_data = call_history or []
        if not tool_calls_data:
            tool_calls_data = task_data.get("toolCalls") or []
        tasks.append(
            TaskResult(
                task_id=task_id,
                task_name=task_name,
                status=_task_status(task_data),
                tool_calls=len(tool_calls_data) if tool_calls_data else 0,
                error_message=task_data.get("error", task_data.get("errorMessage")),
                agent_response=task_data.get("agentResponse", task_data.get("response", task_data.get("taskOutput"))),
            )
        )
    return tasks


def aggregate_mcpchecker_output(
    output_path: Path,
    *,
    submission_name: str,
    threshold: float = 0.7,
) -> MCPCheckerReport:
    raw = json.loads(output_path.read_text(encoding="utf-8"))
    eval_name = str(raw.get("evalName", raw.get("name", "sonar-eval")))
    tasks = extract_task_results(raw)
    passed = sum(1 for t in tasks if t.status == "passed")
    failed = sum(1 for t in tasks if t.status == "failed")
    errors = sum(1 for t in tasks if t.status == "error")
    skipped = sum(1 for t in tasks if t.status == "skipped")
    total = len(tasks)
    score = passed / total if total else 0.0
    return MCPCheckerReport(
        submission_name=submission_name,
        eval_name=eval_name,
        overall_score=score,
        passed_tasks=passed,
        failed_tasks=failed,
        error_tasks=errors,
        skipped_tasks=skipped,
        total_tasks=total,
        tasks=tasks,
        recommendation="pass" if score >= threshold else "fail",
        threshold=threshold,
    )


def render_report_text(report: MCPCheckerReport) -> str:
    lines = [
        f"Agentic Eval Flow (MCPChecker): {report.passed_tasks}/{report.total_tasks} tasks passed",
        f"Overall score: {report.overall_score:.2%} (threshold {report.threshold:.0%}) — {report.recommendation.upper()}",
        "",
    ]
    for task in report.tasks:
        lines.append(f"- {task.task_name} [{task.task_id}]: {task.status}")
        if task.error_message:
            lines.append(f"    error: {task.error_message[:200]}")
    return "\n".join(lines)


def report_to_dict(report: MCPCheckerReport) -> dict[str, Any]:
    return asdict(report)
