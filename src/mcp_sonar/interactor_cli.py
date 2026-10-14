"""Flat `sonar` subcommands for MCP interaction (no LLM)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from mcp_sonar.cli_help import (
    ARGS_FILE_HELP,
    ARGS_JSON_HELP,
    BATCH_FILE_HELP,
    with_config_option,
    with_describe_format_option,
    with_list_format_option,
    with_target_option,
    with_tools_format_option,
)
from mcp_sonar.config import require_targets_path
from mcp_sonar.interactor.tools_cmds import (
    run_prompts_list,
    run_resources_list,
    run_tools_batch,
    run_tools_call,
    run_tools_describe,
    run_tools_info,
    run_tools_list,
    run_tools_template,
    write_batch_example,
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
    @with_describe_format_option()
    def describe_tool_cmd(
        target: str,
        tool_name: str,
        config_path: Path | None,
        fmt: str,
    ) -> None:
        """\b
        Shorthand for `sonar tools describe --tool TOOL`.

        Readable parameter table by default; use --format json for raw schema.
        """

        async def _run() -> None:
            await run_tools_describe(target, tool_name, config_path, fmt)  # type: ignore[arg-type]

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

    @cli.command("invoke")
    @click.option(
        "--args-file",
        required=True,
        type=click.Path(path_type=Path, exists=True, dir_okay=False),
        help=ARGS_FILE_HELP,
    )
    @with_target_option(required=False)
    @click.option("--tool", "tool_name", default=None)
    @click.option("--args", "args_json", default=None, help=ARGS_JSON_HELP)
    @with_config_option()
    def invoke_cmd(
        args_file: Path,
        target: str | None,
        tool_name: str | None,
        args_json: str | None,
        config_path: Path | None,
    ) -> None:
        """Shorthand for `sonar tools invoke --args-file PATH`."""

        async def _run() -> None:
            await run_tools_call(
                target,
                tool_name,
                config_path,
                args_json=args_json,
                args_file=args_file,
            )

        asyncio.run(_run())

    @cli.command("call")
    @with_target_option(required=False)
    @click.argument("tool_name", metavar="TOOL", required=False, default=None)
    @click.option("--args", "args_json", default=None, help=ARGS_JSON_HELP)
    @click.option(
        "--args-file",
        type=click.Path(path_type=Path, exists=True, dir_okay=False),
        default=None,
        help=ARGS_FILE_HELP,
    )
    @with_config_option()
    def call_cmd(
        target: str | None,
        tool_name: str | None,
        args_json: str | None,
        args_file: Path | None,
        config_path: Path | None,
    ) -> None:
        """\b
        Shorthand for `sonar tools call`.

        Example:
          sonar call echo --target my-server --args '{"message":"hello"}'
        """

        async def _run() -> None:
            await run_tools_call(
                target,
                tool_name,
                config_path,
                args_json=args_json,
                args_file=args_file,
            )

        asyncio.run(_run())

    @cli.command("template")
    @with_target_option()
    @click.option("--tool", "tool_name", required=True)
    @with_config_option()
    @click.option("-o", "--out", type=click.Path(path_type=Path, dir_okay=False), default=None)
    def template_cmd(
        target: str,
        tool_name: str,
        config_path: Path | None,
        out: Path | None,
    ) -> None:
        """Shorthand for `sonar tools template` (typed YAML input form)."""

        async def _run() -> None:
            await run_tools_template(target, tool_name, config_path, out)

        asyncio.run(_run())

    @cli.command("batch")
    @click.option(
        "--file",
        "batch_file",
        required=True,
        type=click.Path(path_type=Path, exists=True, dir_okay=False),
        help=BATCH_FILE_HELP,
    )
    @with_target_option(required=False)
    @with_config_option()
    @click.option("--continue-on-error", is_flag=True)
    def batch_cmd(
        batch_file: Path,
        target: str | None,
        config_path: Path | None,
        continue_on_error: bool,
    ) -> None:
        """Shorthand for `sonar tools batch --file PATH`."""

        async def _run() -> None:
            await run_tools_batch(
                batch_file,
                config_path,
                target,
                continue_on_error=continue_on_error,
            )

        asyncio.run(_run())

    @cli.command("batch-template")
    @with_target_option(required=False)
    @click.option("--tool", "tool_name", required=True)
    @click.option("-o", "--out", type=click.Path(path_type=Path, dir_okay=False), default=None)
    def batch_template_cmd(tool_name: str, target: str | None, out: Path | None) -> None:
        """Shorthand for `sonar tools batch-template`."""

        write_batch_example(tool_name, target=target, out_path=out)

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
