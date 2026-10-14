"""Flat `sonar` subcommands for MCP interaction (no LLM)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from mcp_sonar.cli_help import (
    ARGS_JSON_HELP,
    with_config_option,
    with_list_format_option,
    with_target_option,
    with_tools_format_option,
)
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
    @with_target_option()
    @with_config_option()
    @with_tools_format_option()
    def list_tools_cmd(target: str, config_path: Path | None, fmt: str) -> None:
        """\b
        Shorthand for `sonar tools list`.

        List MCP tools for --target; same --format options (table, names, json).
        """

        try:
            require_targets_path(config_path)
        except FileNotFoundError as exc:
            _targets_error(exc)

        async def _run() -> None:
            await run_tools_list(target, config_path, fmt)  # type: ignore[arg-type]

        asyncio.run(_run())

    @cli.command("describe-tool")
    @with_target_option()
    @click.argument(
        "tool_name",
        metavar="TOOL",
        type=str,
        required=True,
    )
    @with_config_option()
    def describe_tool_cmd(target: str, tool_name: str, config_path: Path | None) -> None:
        """\b
        Shorthand for `sonar tools describe --tool TOOL`.

        Prints JSON schema for a single tool.
        """

        async def _run() -> None:
            await run_tools_describe(target, tool_name, config_path)

        asyncio.run(_run())

    @cli.command("info")
    @with_target_option()
    @with_config_option()
    def info_cmd(target: str, config_path: Path | None) -> None:
        """\b
        Shorthand for `sonar tools info`.

        Server name, version, capabilities, and target transport details.
        """

        async def _run() -> None:
            await run_tools_info(target, config_path)

        asyncio.run(_run())

    @cli.command("call")
    @with_target_option()
    @click.argument(
        "tool_name",
        metavar="TOOL",
        type=str,
        required=True,
    )
    @click.option("--args", "args_json", default="{}", help=ARGS_JSON_HELP)
    @with_config_option()
    def call_cmd(target: str, tool_name: str, args_json: str, config_path: Path | None) -> None:
        """\b
        Shorthand for `sonar tools call --tool TOOL`.

        Example:
          sonar call echo --target my-server --args '{"message":"hello"}'
        """

        async def _run() -> None:
            await run_tools_call(target, tool_name, args_json, config_path)

        asyncio.run(_run())

    @cli.command("list-resources")
    @with_target_option()
    @with_config_option()
    @with_list_format_option()
    def list_resources_cmd(target: str, config_path: Path | None, fmt: str) -> None:
        """Shorthand for `sonar tools resources list`."""

        async def _run() -> None:
            await run_resources_list(target, config_path, fmt)  # type: ignore[arg-type]

        asyncio.run(_run())

    @cli.command("list-prompts")
    @with_target_option()
    @with_config_option()
    @with_list_format_option()
    def list_prompts_cmd(target: str, config_path: Path | None, fmt: str) -> None:
        """Shorthand for `sonar tools prompts list`."""

        async def _run() -> None:
            await run_prompts_list(target, config_path, fmt)  # type: ignore[arg-type]

        asyncio.run(_run())
