from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

import json

import click
from rich.console import Console
from rich.table import Table

from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.interactor.tool_benchmark import ToolBenchmarkResult, benchmark_tool_call
from mcp_sonar.display import print_connected_target
from mcp_sonar.interactor.args_file import load_batch_file, resolve_invoke
from mcp_sonar.interactor.format import (
    print_prompts_table,
    print_resources_table,
    print_server_info,
    print_tools_table,
    tool_definition_to_dict,
    tools_as_json,
)
from mcp_sonar.interactor.session import open_target, parse_tool_args
from mcp_sonar.interactor.tool_describe import print_tool_description
from mcp_sonar.interactor.tool_template import render_batch_example, render_invoke_template
from mcp_sonar.target import ConnectedTarget

ToolsListFormat = Literal["table", "names", "json"]
DescribeFormat = Literal["rich", "json"]


def _table_title(connected: ConnectedTarget, what: str) -> str:
    return f"MCP {what} — {connected.name} ({connected.transport.kind_label})"


async def _with_connected(
    target: str,
    config_path: Path | None,
    action: Callable[[ConnectedTarget], Awaitable[None]],
    *,
    announce: bool = True,
) -> None:
    async with open_target(target, config_path) as (_name, connected):
        if announce:
            print_connected_target(connected)
        await action(connected)


def _resolve_call_params(
    *,
    tool_cli: str | None,
    target_cli: str | None,
    args_json: str | None,
    args_file: Path | None,
) -> tuple[str, str, dict]:
    try:
        return resolve_invoke(
            tool_cli=tool_cli,
            target_cli=target_cli,
            args_json=args_json,
            args_file=args_file,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


async def run_tools_list(
    target: str,
    config_path: Path | None,
    fmt: ToolsListFormat,
) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        tools = await connected.list_tool_definitions()
        if fmt == "names":
            for tool in tools:
                click.echo(tool.name)
            return
        if fmt == "json":
            click.echo(tools_as_json(tools))
            return
        print_tools_table(tools, title=_table_title(connected, "tools"))

    await _with_connected(target, config_path, _action)


async def run_tools_describe(
    target: str,
    tool_name: str,
    config_path: Path | None,
    fmt: DescribeFormat = "rich",
) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        tools = await connected.list_tool_definitions()
        match = next((t for t in tools if t.name == tool_name), None)
        if match is None:
            known = ", ".join(t.name for t in tools) or "(none)"
            raise click.ClickException(f"Unknown tool '{tool_name}'. Available: {known}")
        if fmt == "json":
            click.echo(json.dumps(tool_definition_to_dict(match), indent=2))
            return
        print_tool_description(match)

    await _with_connected(target, config_path, _action)


async def run_tools_info(target: str, config_path: Path | None) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        if connected.init_result is None:
            raise click.ClickException("Server did not return initialize metadata.")
        print_server_info(connected)

    await _with_connected(target, config_path, _action)


async def run_tools_template(
    target: str,
    tool_name: str,
    config_path: Path | None,
    out_path: Path | None,
) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        tools = await connected.list_tool_definitions()
        match = next((t for t in tools if t.name == tool_name), None)
        if match is None:
            known = ", ".join(t.name for t in tools) or "(none)"
            raise click.ClickException(f"Unknown tool '{tool_name}'. Available: {known}")
        text = render_invoke_template(match, target=target)
        if out_path is not None:
            out_path.write_text(text, encoding="utf-8")
            click.echo(f"Wrote {out_path}", err=True)
        else:
            click.echo(text)

    await _with_connected(target, config_path, _action, announce=False)


def print_tool_benchmark_report(result: ToolBenchmarkResult, *, fmt: Literal["rich", "json"]) -> None:
    if fmt == "json":
        click.echo(
            json.dumps(
                {
                    "tool": result.tool_name,
                    "arguments": result.arguments,
                    "success_rate": result.success_rate,
                    "last_error": result.last_error,
                    "timing_ms": {
                        "min": result.timing.min_ms,
                        "p50": result.timing.p50_ms,
                        "p95": result.timing.p95_ms,
                        "max": result.timing.max_ms,
                        "samples": result.timing.samples,
                    },
                },
                indent=2,
            )
        )
        return

    console = Console()
    table = Table(title=f"Tool latency — {result.tool_name}")
    table.add_column("Metric")
    table.add_column("ms")
    table.add_row("min", f"{result.timing.min_ms:.1f}")
    table.add_row("p50", f"{result.timing.p50_ms:.1f}")
    table.add_row("p95", f"{result.timing.p95_ms:.1f}")
    table.add_row("max", f"{result.timing.max_ms:.1f}")
    table.add_row("samples", str(result.timing.samples))
    table.add_row("success rate", f"{result.success_rate * 100:.0f}%")
    if result.last_error and result.success_rate < 1.0:
        table.add_row("last error", result.last_error[:80])
    console.print(table)


async def run_tools_benchmark(
    target_cli: str | None,
    tool_cli: str | None,
    config_path: Path | None,
    *,
    args_json: str | None = None,
    args_file: Path | None = None,
    warmup: int,
    iterations: int,
    fmt: Literal["rich", "json"],
) -> ToolBenchmarkResult:
    tool_name, target_name, arguments = _resolve_call_params(
        tool_cli=tool_cli,
        target_cli=target_cli,
        args_json=args_json,
        args_file=args_file,
    )

    result_holder: list[ToolBenchmarkResult] = []

    async def _run(connected: ConnectedTarget) -> None:
        result_holder.append(
            await benchmark_tool_call(
                connected,
                tool_name,
                arguments,
                warmup=warmup,
                iterations=iterations,
            )
        )

    await _with_connected(target_name, config_path, _run)
    result = result_holder[0]
    print_tool_benchmark_report(result, fmt=fmt)
    return result


async def run_tools_call(
    target_cli: str | None,
    tool_cli: str | None,
    config_path: Path | None,
    *,
    args_json: str | None = None,
    args_file: Path | None = None,
) -> None:
    tool_name, target_name, arguments = _resolve_call_params(
        tool_cli=tool_cli,
        target_cli=target_cli,
        args_json=args_json,
        args_file=args_file,
    )

    async def _action(connected: ConnectedTarget) -> None:
        outcome = await connected.call_tool(tool_name, arguments)
        emit_tool_outcome(outcome)

    await _with_connected(target_name, config_path, _action)


async def run_tools_batch(
    batch_file: Path,
    config_path: Path | None,
    target_cli: str | None,
    *,
    continue_on_error: bool = False,
) -> None:
    try:
        batch = load_batch_file(batch_file)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    default_target = target_cli or batch.target
    if not default_target and any(c.target is None for c in batch.calls):
        raise click.ClickException(
            "Set --target or a top-level 'target' in the batch file "
            "(or per call under calls[].target)."
        )

    failures = 0
    total = len(batch.calls)
    for index, call in enumerate(batch.calls, start=1):
        target_name = call.target or default_target
        if not target_name:
            raise click.ClickException(f"calls[{index - 1}]: missing target")

        click.echo(f"\n--- call {index}/{total}: {call.tool} @ {target_name} ---", err=True)

        async with open_target(target_name, config_path) as (_name, connected):
            print_connected_target(connected)
            outcome = await connected.call_tool(call.tool, call.arguments)

        if not print_tool_outcome(outcome):
            failures += 1
            if not continue_on_error:
                raise SystemExit(1)

    if failures:
        raise SystemExit(1)


def print_tool_outcome(outcome: ToolOutcome) -> bool:
    """Print tool text; return False if the tool reported an error."""
    click.echo(outcome.text)
    return not outcome.is_error


def emit_tool_outcome(outcome: ToolOutcome) -> None:
    if not print_tool_outcome(outcome):
        raise SystemExit(1)


async def run_resources_list(
    target: str,
    config_path: Path | None,
    fmt: ToolsListFormat,
) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        try:
            resources = await connected.list_resources()
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(f"list_resources failed: {exc}") from exc
        if fmt == "names":
            for resource in resources:
                click.echo(resource.uri)
            return
        if fmt == "json":
            payload = [
                {"uri": r.uri, "name": r.name, "description": r.description} for r in resources
            ]
            click.echo(json.dumps(payload, indent=2))
            return
        print_resources_table(resources, title=_table_title(connected, "resources"))

    await _with_connected(target, config_path, _action)


async def run_prompts_list(
    target: str,
    config_path: Path | None,
    fmt: ToolsListFormat,
) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        try:
            prompts = await connected.list_prompts()
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(f"list_prompts failed: {exc}") from exc
        if fmt == "names":
            for prompt in prompts:
                click.echo(prompt.name)
            return
        if fmt == "json":
            payload = [{"name": p.name, "description": p.description} for p in prompts]
            click.echo(json.dumps(payload, indent=2))
            return
        print_prompts_table(prompts, title=_table_title(connected, "prompts"))

    await _with_connected(target, config_path, _action)


def write_batch_example(tool_name: str, target: str | None, out_path: Path | None) -> None:
    text = render_batch_example(tool_name, target=target)
    if out_path is not None:
        out_path.write_text(text, encoding="utf-8")
        click.echo(f"Wrote {out_path}", err=True)
    else:
        click.echo(text)
