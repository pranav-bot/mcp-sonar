"""Flat CLI for MCP interaction (no LLM), similar to generic mcp-interactor tools."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from mcp_benchmarker.config import require_targets_path
from mcp_benchmarker.interactor.tools_cmds import (
    run_prompts_list,
    run_resources_list,
    run_tools_call,
    run_tools_describe,
    run_tools_info,
    run_tools_list,
)


def _targets_error(exc: FileNotFoundError) -> None:
    raise click.ClickException(str(exc)) from exc


@click.group()
def main() -> None:
    """Interact with MCP servers: list tools, call tools, inspect server metadata."""


@main.command("list-tools")
@click.option("--target", required=True, help="Target name from targets.yaml")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "names", "json"]),
    default="table",
    show_default=True,
)
def list_tools_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List tools exposed by an MCP server."""
    try:
        require_targets_path(config_path)
    except FileNotFoundError as exc:
        _targets_error(exc)

    async def _run() -> None:
        await run_tools_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@main.command("describe-tool")
@click.option("--target", required=True)
@click.argument("tool_name")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def describe_tool_cmd(target: str, tool_name: str, config_path: Path | None) -> None:
    """Print one tool's name, description, and input JSON Schema."""

    async def _run() -> None:
        await run_tools_describe(target, tool_name, config_path)

    asyncio.run(_run())


@main.command("info")
@click.option("--target", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def info_cmd(target: str, config_path: Path | None) -> None:
    """Show MCP server info from the initialize handshake."""

    async def _run() -> None:
        await run_tools_info(target, config_path)

    asyncio.run(_run())


@main.command()
@click.option("--target", required=True)
@click.argument("tool_name")
@click.option("--args", "args_json", default="{}", help="JSON object of tool arguments")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def call(target: str, tool_name: str, args_json: str, config_path: Path | None) -> None:
    """Call an MCP tool and print the result."""

    async def _run() -> None:
        await run_tools_call(target, tool_name, args_json, config_path)

    asyncio.run(_run())


@main.command("list-resources")
@click.option("--target", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "names", "json"]),
    default="table",
    show_default=True,
)
def list_resources_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List MCP resources (if the server supports them)."""

    async def _run() -> None:
        await run_resources_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@main.command("list-prompts")
@click.option("--target", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "names", "json"]),
    default="table",
    show_default=True,
)
def list_prompts_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List MCP prompts (if the server supports them)."""

    async def _run() -> None:
        await run_prompts_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


if __name__ == "__main__":
    main()
