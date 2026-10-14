from __future__ import annotations

import asyncio
from pathlib import Path

import click

from mcp_sonar.config import default_targets_path, load_targets, require_targets_path, resolve_target
from mcp_sonar.core.report import emit_report, print_compare_report, print_single_report
from mcp_sonar.core.runner import compare_targets, run_suite_on_target
from mcp_sonar.core.types import ReportFormat
from mcp_sonar.display import print_targets_table
from mcp_sonar.interactor.tools_cmds import (
    run_prompts_list,
    run_resources_list,
    run_tools_call,
    run_tools_describe,
    run_tools_info,
    run_tools_list,
)
from mcp_sonar.suite.registry import ensure_suites_loaded, get_suite, list_suites
from mcp_sonar.target import connect_target


def _resolve_config(path: Path | None) -> Path:
    try:
        return require_targets_path(path)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _config_dir(config_file: Path) -> Path:
    return config_file.parent


@click.group()
def main() -> None:
    """mcp-sonar: benchmark and interact with MCP servers (stdio or streamable HTTP)."""


@main.command("list-suites")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def list_suites_cmd(config_path: Path | None) -> None:
    """List registered benchmark suites."""
    config_file = _resolve_config(config_path) if config_path else default_targets_path()
    if config_file.is_file():
        ensure_suites_loaded(_config_dir(config_file))
    else:
        ensure_suites_loaded(None)
    for suite in list_suites():
        bindings = ", ".join(sorted(suite.supported_bindings()))
        click.echo(f"{suite.id}\t{suite.description}\tbindings: {bindings}")


@main.command("list-targets")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def list_targets_cmd(config_path: Path | None) -> None:
    """List targets defined in targets.yaml."""
    config_file = _resolve_config(config_path)
    targets = load_targets(config_file)
    print_targets_table(targets)


@main.group("tools")
def tools_group() -> None:
    """Discover and call tools on a single target."""


@tools_group.command("list")
@click.option("--target", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "names", "json"]),
    default="table",
    show_default=True,
    help="table: Rich table with descriptions; names: one name per line; json: full schemas",
)
def tools_list_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List tools exposed by an MCP server."""

    async def _run() -> None:
        await run_tools_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@tools_group.command("describe")
@click.option("--target", required=True)
@click.option("--tool", "tool_name", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def tools_describe_cmd(target: str, tool_name: str, config_path: Path | None) -> None:
    """Show one tool's description and input JSON Schema."""

    async def _run() -> None:
        await run_tools_describe(target, tool_name, config_path)

    asyncio.run(_run())


@tools_group.command("info")
@click.option("--target", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def tools_info_cmd(target: str, config_path: Path | None) -> None:
    """Show server metadata from the MCP initialize response."""

    async def _run() -> None:
        await run_tools_info(target, config_path)

    asyncio.run(_run())


@tools_group.command("call")
@click.option("--target", required=True)
@click.option("--tool", "tool_name", required=True)
@click.option("--args", "args_json", default="{}", help="JSON object of tool arguments")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
def tools_call_cmd(target: str, tool_name: str, args_json: str, config_path: Path | None) -> None:
    """Call one MCP tool and print the result."""

    async def _run() -> None:
        await run_tools_call(target, tool_name, args_json, config_path)

    asyncio.run(_run())


@tools_group.group("resources")
def tools_resources_group() -> None:
    """List MCP resources."""


@tools_resources_group.command("list")
@click.option("--target", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "names", "json"]),
    default="table",
    show_default=True,
)
def tools_resources_list_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List resources (when supported by the server)."""

    async def _run() -> None:
        await run_resources_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@tools_group.group("prompts")
def tools_prompts_group() -> None:
    """List MCP prompts."""


@tools_prompts_group.command("list")
@click.option("--target", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["table", "names", "json"]),
    default="table",
    show_default=True,
)
def tools_prompts_list_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List prompts (when supported by the server)."""

    async def _run() -> None:
        await run_prompts_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@main.command("run")
@click.option("--target", required=True, help="Target name from targets.yaml")
@click.option("--suite", "suite_id", required=True, help="Suite id (see list-suites)")
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--warmup", default=2, show_default=True)
@click.option("--iterations", default=10, show_default=True)
@click.option("--out", "out_path", type=click.Path(path_type=Path), default=None)
@click.option("--format", "fmt", type=click.Choice(["json", "md", "both"]), default="both")
@click.option("--skip-functional", is_flag=True, help="Measure latency only")
def run_cmd(
    target: str,
    suite_id: str,
    config_path: Path | None,
    warmup: int,
    iterations: int,
    out_path: Path | None,
    fmt: ReportFormat,
    skip_functional: bool,
) -> None:
    """Benchmark a single MCP target."""

    async def _run() -> None:
        config_file = _resolve_config(config_path)
        ensure_suites_loaded(_config_dir(config_file))
        targets = load_targets(config_file)
        target_name, target_cfg = resolve_target(targets, target)
        suite = get_suite(suite_id)
        if target_cfg.binding not in suite.supported_bindings():
            raise click.ClickException(
                f"Target binding '{target_cfg.binding}' is not used in suite '{suite_id}'. "
                f"Suite bindings: {', '.join(sorted(suite.supported_bindings()))}"
            )
        async with connect_target(target_name, target_cfg) as connected:
            report = await run_suite_on_target(
                connected,
                suite,
                warmup=warmup,
                iterations=iterations,
                skip_functional=skip_functional,
            )
        print_single_report(report)
        emit_report(out_path, fmt, report)
        if any(not s.functional_pass and not s.skipped for s in report.scenarios):
            raise SystemExit(1)

    asyncio.run(_run())


@main.command("compare")
@click.option("--left", required=True, help="Left target name")
@click.option("--right", required=True, help="Right target name")
@click.option("--suite", "suite_id", required=True)
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=None)
@click.option("--warmup", default=2, show_default=True)
@click.option("--iterations", default=10, show_default=True)
@click.option("--out", "out_path", type=click.Path(path_type=Path), default=None)
@click.option("--format", "fmt", type=click.Choice(["json", "md", "both"]), default="both")
@click.option("--skip-functional", is_flag=True)
def compare_cmd(
    left: str,
    right: str,
    suite_id: str,
    config_path: Path | None,
    warmup: int,
    iterations: int,
    out_path: Path | None,
    fmt: ReportFormat,
    skip_functional: bool,
) -> None:
    """Compare two MCP targets using the same suite."""

    async def _run() -> None:
        config_file = _resolve_config(config_path)
        ensure_suites_loaded(_config_dir(config_file))
        targets = load_targets(config_file)
        left_name, left_cfg = resolve_target(targets, left)
        right_name, right_cfg = resolve_target(targets, right)
        suite = get_suite(suite_id)
        for cfg, label in ((left_cfg, left), (right_cfg, right)):
            if cfg.binding not in suite.supported_bindings():
                raise click.ClickException(
                    f"Target '{label}' binding '{cfg.binding}' is not defined in suite '{suite_id}'"
                )
        async with connect_target(left_name, left_cfg) as left_target:
            async with connect_target(right_name, right_cfg) as right_target:
                report = await compare_targets(
                    left_target,
                    right_target,
                    suite,
                    warmup=warmup,
                    iterations=iterations,
                    skip_functional=skip_functional,
                )
        print_compare_report(report)
        emit_report(out_path, fmt, report)
        failed = False
        for row in report.rows:
            for side in (row.left, row.right):
                if side and not side.skipped and not side.functional_pass:
                    failed = True
        if failed:
            raise SystemExit(1)

    asyncio.run(_run())


from mcp_sonar.interactor_cli import register_flat_commands  # noqa: E402

register_flat_commands(main)


if __name__ == "__main__":
    main()
