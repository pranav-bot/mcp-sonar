from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from mcp_benchmarker.core.types import CompareReport, ReportFormat, ScenarioRunResult, SingleTargetReport


def _scenario_row_cells(result: ScenarioRunResult) -> list[str]:
    if result.skipped:
        return ["skip", "-", "-", "-", "-", result.functional_message]
    return [
        "pass" if result.functional_pass else "FAIL",
        f"{result.timing.p50_ms:.1f}",
        f"{result.timing.p95_ms:.1f}",
        f"{result.timing.min_ms:.1f}",
        f"{result.timing.max_ms:.1f}",
        result.functional_message[:60],
    ]


def print_single_report(report: SingleTargetReport) -> None:
    console = Console()
    console.print(
        f"\n[bold]Suite[/bold] {report.suite_id}  [bold]Target[/bold] {report.target_name} "
        f"(binding={report.binding})"
    )
    table = Table(title="Scenario results")
    table.add_column("Scenario")
    table.add_column("Functional")
    table.add_column("p50 ms")
    table.add_column("p95 ms")
    table.add_column("min ms")
    table.add_column("max ms")
    table.add_column("Note")
    for scenario in report.scenarios:
        cells = _scenario_row_cells(scenario)
        table.add_row(scenario.scenario_id, *cells)
    console.print(table)


def print_compare_report(report: CompareReport) -> None:
    console = Console()
    console.print(
        f"\n[bold]Suite[/bold] {report.suite_id}  "
        f"[bold]Left[/bold] {report.left_target}  [bold]Right[/bold] {report.right_target}"
    )
    table = Table(title="Head-to-head (p50 ms)")
    table.add_column("Scenario")
    table.add_column("Left functional")
    table.add_column("Left p50")
    table.add_column("Right functional")
    table.add_column("Right p50")
    table.add_column("Note")
    for row in report.rows:
        left = row.left
        right = row.right
        if left is None or right is None:
            continue
        table.add_row(
            row.scenario_id,
            "skip" if left.skipped else ("pass" if left.functional_pass else "FAIL"),
            "-" if left.skipped else f"{left.timing.p50_ms:.1f}",
            "skip" if right.skipped else ("pass" if right.functional_pass else "FAIL"),
            "-" if right.skipped else f"{right.timing.p50_ms:.1f}",
            left.functional_message[:40],
        )
    console.print(table)


def _dataclass_to_json(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _dataclass_to_json(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_dataclass_to_json(item) for item in obj]
    return obj


def write_json_report(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_dataclass_to_json(payload), indent=2) + "\n", encoding="utf-8")


def write_markdown_single(path: Path, report: SingleTargetReport) -> None:
    lines = [
        f"# MCP benchmark: {report.target_name}",
        "",
        f"- Suite: `{report.suite_id}`",
        f"- Binding: `{report.binding}`",
        f"- Warmup: {report.warmup}, iterations: {report.iterations}",
        "",
        "| Scenario | Functional | p50 ms | p95 ms | Note |",
        "|----------|------------|--------|--------|------|",
    ]
    for scenario in report.scenarios:
        if scenario.skipped:
            lines.append(f"| {scenario.scenario_id} | skip | - | - | {scenario.functional_message} |")
            continue
        status = "pass" if scenario.functional_pass else "**FAIL**"
        lines.append(
            f"| {scenario.scenario_id} | {status} | {scenario.timing.p50_ms:.1f} | "
            f"{scenario.timing.p95_ms:.1f} | {scenario.functional_message} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_markdown_compare(path: Path, report: CompareReport) -> None:
    lines = [
        f"# MCP compare: {report.left_target} vs {report.right_target}",
        "",
        f"- Suite: `{report.suite_id}`",
        f"- Warmup: {report.warmup}, iterations: {report.iterations}",
        "",
        "| Scenario | Left | Left p50 | Right | Right p50 |",
        "|----------|------|----------|-------|-----------|",
    ]
    for row in report.rows:
        left = row.left
        right = row.right
        if left is None or right is None:
            continue
        l_status = "skip" if left.skipped else ("pass" if left.functional_pass else "FAIL")
        r_status = "skip" if right.skipped else ("pass" if right.functional_pass else "FAIL")
        l_p50 = "-" if left.skipped else f"{left.timing.p50_ms:.1f}"
        r_p50 = "-" if right.skipped else f"{right.timing.p50_ms:.1f}"
        lines.append(f"| {row.scenario_id} | {l_status} | {l_p50} | {r_status} | {r_p50} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit_report(
    path: Path | None,
    fmt: ReportFormat,
    payload: SingleTargetReport | CompareReport,
) -> None:
    if path is None:
        return
    stem = path
    if fmt in ("json", "both"):
        json_path = stem if stem.suffix == ".json" else stem.with_suffix(".json")
        write_json_report(json_path, payload)
    if fmt in ("md", "both"):
        md_path = stem if stem.suffix == ".md" else stem.with_suffix(".md")
        if isinstance(payload, SingleTargetReport):
            write_markdown_single(md_path, payload)
        else:
            write_markdown_compare(md_path, payload)
