"""Flat `sonar` subcommands for MCP interaction (no LLM)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from mcp_sonar.config import require_targets_path
from mcp_sonar.interactor.tools_cmds import (
    run_prompts_list,
    run_resources_list,
    run_tools_call,
    run_tools_describe,
    run_tools_info,
    run_tools_list,
)


def _targets_error(exc: FileNotFoundError) -> None:
    raise click.ClickException(str(exc)) from exc


def register_flat_commands(cli: click.Group) -> None:
    """Attach shorthand interact commands to the root `sonar` group."""

    @cli.command("list-tools")
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
        """List tools exposed by an MCP server (shorthand for `sonar tools list`)."""
        try:
            require_targets_path(config_path)
        except FileNotFoundError as exc:
            _targets_error(exc)

        async def _run() -> None:
            await run_tools_list(target, config_path, fmt)  # type: ignore[arg-type]

        asyncio.run(_run())

    @cli.command("describe-tool")
    @click.option("--target", required=True)
    @click.argument("tool_name")
    @click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
    def describe_tool_cmd(target: str, tool_name: str, config_path: Path | None) -> None:
        """Print one tool's schema (shorthand for `sonar tools describe`)."""

        async def _run() -> None:
            await run_tools_describe(target, tool_name, config_path)

        asyncio.run(_run())

    @cli.command("info")
    @click.option("--target", required=True)
    @click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
    def info_cmd(target: str, config_path: Path | None) -> None:
        """Show MCP server initialize metadata (shorthand for `sonar tools info`)."""

        async def _run() -> None:
            await run_tools_info(target, config_path)

        asyncio.run(_run())

    @cli.command("call")
    @click.option("--target", required=True)
    @click.argument("tool_name")
    @click.option("--args", "args_json", default="{}", help="JSON object of tool arguments")
    @click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
    def call_cmd(target: str, tool_name: str, args_json: str, config_path: Path | None) -> None:
        """Call an MCP tool (shorthand for `sonar tools call`)."""

        async def _run() -> None:
            await run_tools_call(target, tool_name, args_json, config_path)

        asyncio.run(_run())

    @cli.command("list-resources")
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
        """List MCP resources (shorthand for `sonar tools resources list`)."""

        async def _run() -> None:
            await run_resources_list(target, config_path, fmt)  # type: ignore[arg-type]

        asyncio.run(_run())

    @cli.command("list-prompts")
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
        """List MCP prompts (shorthand for `sonar tools prompts list`)."""

        async def _run() -> None:
            await run_prompts_list(target, config_path, fmt)  # type: ignore[arg-type]

        asyncio.run(_run())
