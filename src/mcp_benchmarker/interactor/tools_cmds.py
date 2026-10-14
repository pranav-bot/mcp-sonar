from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal

import click

from mcp_benchmarker.core.types import ToolOutcome
from mcp_benchmarker.display import print_connected_target
from mcp_benchmarker.interactor.format import (
    print_prompts_table,
    print_resources_table,
    print_server_info,
    print_tools_table,
    tool_definition_to_dict,
    tools_as_json,
)
from mcp_benchmarker.interactor.session import open_target, parse_tool_args
from mcp_benchmarker.target import ConnectedTarget

ToolsListFormat = Literal["table", "names", "json"]


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
) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        tools = await connected.list_tool_definitions()
        match = next((t for t in tools if t.name == tool_name), None)
        if match is None:
            known = ", ".join(t.name for t in tools) or "(none)"
            raise click.ClickException(f"Unknown tool '{tool_name}'. Available: {known}")
        click.echo(json.dumps(tool_definition_to_dict(match), indent=2))

    await _with_connected(target, config_path, _action)


async def run_tools_info(target: str, config_path: Path | None) -> None:
    async def _action(connected: ConnectedTarget) -> None:
        if connected.init_result is None:
            raise click.ClickException("Server did not return initialize metadata.")
        print_server_info(connected)

    await _with_connected(target, config_path, _action)


async def run_tools_call(
    target: str,
    tool_name: str,
    args_json: str,
    config_path: Path | None,
) -> None:
    arguments = parse_tool_args(args_json)

    async def _action(connected: ConnectedTarget) -> None:
        outcome = await connected.call_tool(tool_name, arguments)
        emit_tool_outcome(outcome)

    await _with_connected(target, config_path, _action)


def emit_tool_outcome(outcome: ToolOutcome) -> None:
    click.echo(outcome.text)
    if outcome.is_error:
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
