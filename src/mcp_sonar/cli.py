from __future__ import annotations

import asyncio
from pathlib import Path

import click

from mcp_sonar.cli_help import (
    ARGS_FILE_HELP,
    ARGS_JSON_HELP,
    BATCH_FILE_HELP,
    ITERATIONS_HELP,
    MAIN_EPILOG,
    OUT_HELP,
    REPORT_FORMAT_HELP,
    SKIP_FUNCTIONAL_HELP,
    SUITE_HELP,
    TOOLS_GROUP_HELP,
    WARMUP_HELP,
    with_config_option,
    with_describe_format_option,
    with_list_format_option,
    with_target_option,
    with_tools_format_option,
)
from mcp_sonar.config import (
    TargetConfig,
    TargetsFile,
    UnknownTargetError,
    default_targets_path,
    load_targets,
    require_targets_path,
    resolve_target,
)
from mcp_sonar.core.report import emit_report, print_compare_report, print_single_report
from mcp_sonar.core.runner import compare_targets, run_suite_on_target
from mcp_sonar.core.types import ReportFormat
from mcp_sonar.display import print_targets_table
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
from mcp_sonar.suite.registry import ensure_suites_loaded, get_suite, list_suites
from mcp_sonar.target import connect_target


def _resolve_config(path: Path | None) -> Path:
    try:
        return require_targets_path(path)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc


def _config_dir(config_file: Path) -> Path:
    return config_file.parent


def _resolve_target_checked(targets: TargetsFile, name: str) -> tuple[str, TargetConfig]:
    try:
        return resolve_target(targets, name)
    except UnknownTargetError as exc:
        raise click.ClickException(exc.format_message()) from exc


@click.group(
    context_settings={"max_content_width": 96, "help_option_names": ["-h", "--help"]},
    epilog=MAIN_EPILOG,
)
def main() -> None:
    """\b
    mcp-sonar — benchmark and interact with Model Context Protocol (MCP) servers.

    Use named targets in targets.yaml. Each target connects via stdio
    (local subprocess) or streamable HTTP (remote URL). Reports and interact
    commands always show which transport is in use.

    \b
    Command groups:
      list-*     Discover configured targets and benchmark suites
      tools      Full interact subcommands (list, describe, call, …)
      run        Benchmark one target with a suite
      compare    Benchmark two targets side by side

    Shorthand commands (same as `sonar tools …`):
      list-tools, describe-tool, invoke, call, template, batch, info, …
    """


@main.command("list-suites")
@with_config_option()
def list_suites_cmd(config_path: Path | None) -> None:
    """\b
    List benchmark suites available to `sonar run` and `sonar compare`.

    Loads built-in suites plus any YAML files in config/suites/ when
    --config points at a targets.yaml inside your project config/ directory.
    """

    config_file = _resolve_config(config_path) if config_path else default_targets_path()
    if config_file.is_file():
        ensure_suites_loaded(_config_dir(config_file))
    else:
        ensure_suites_loaded(None)
    for suite in list_suites():
        bindings = ", ".join(sorted(suite.supported_bindings()))
        click.echo(f"{suite.id}\t{suite.description}\tbindings: {bindings}")


@main.command("list-targets")
@with_config_option()
def list_targets_cmd(config_path: Path | None) -> None:
    """\b
    List MCP endpoints defined in targets.yaml.

    Shows transport kind (stdio vs streamable HTTP), connection endpoint,
    human label, and suite binding name for each target.
    """

    config_file = _resolve_config(config_path)
    targets = load_targets(config_file)
    print_targets_table(targets)


@main.group("tools", help=TOOLS_GROUP_HELP)
def tools_group() -> None:
    """Discover and call tools on a single MCP target."""


@tools_group.command("list")
@with_target_option()
@with_config_option()
@with_tools_format_option()
def tools_list_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """\b
    List tools the MCP server exposes (tools/list).

    Announces the target and transport on stderr. Use --format names or json
    when piping output to other tools.
    """

    async def _run() -> None:
        await run_tools_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@tools_group.command("describe")
@with_target_option()
@click.option(
    "--tool",
    "tool_name",
    required=True,
    help="Tool name exactly as returned by `sonar tools list --format names`.",
)
@with_config_option()
@with_describe_format_option()
def tools_describe_cmd(target: str, tool_name: str, config_path: Path | None, fmt: str) -> None:
    """\b
    Show a tool's description and parameters in a readable layout.

    Default output is a Rich table of arguments (types, defaults, descriptions).
    Use --format json for the raw MCP tool definition and JSON Schema.
    """

    async def _run() -> None:
        await run_tools_describe(target, tool_name, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@tools_group.command("info")
@with_target_option()
@with_config_option()
def tools_info_cmd(target: str, config_path: Path | None) -> None:
    """\b
    Show MCP server metadata from the initialize handshake.

    Includes server name/version, capabilities, instructions (if any), and
    the resolved target transport (stdio or streamable HTTP).
    """

    async def _run() -> None:
        await run_tools_info(target, config_path)

    asyncio.run(_run())


@tools_group.command("call")
@with_target_option(required=False)
@click.option(
    "--tool",
    "tool_name",
    required=False,
    help="Tool name (required unless set in --args-file).",
)
@click.option("--args", "args_json", default=None, help=ARGS_JSON_HELP)
@click.option(
    "--args-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help=ARGS_FILE_HELP,
)
@with_config_option()
def tools_call_cmd(
    target: str | None,
    tool_name: str | None,
    args_json: str | None,
    args_file: Path | None,
    config_path: Path | None,
) -> None:
    """\b
    Call one MCP tool and print the result (no LLM).

    Pass JSON with --args, or edit a form file from `sonar tools template` and
    pass --args-file. CLI --target and --tool override values in the file.
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


@tools_group.command("invoke")
@click.option(
    "--args-file",
    required=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help=ARGS_FILE_HELP,
)
@click.option("--tool", "tool_name", default=None, help="Override tool name from the file.")
@with_target_option(required=False)
@click.option("--args", "args_json", default=None, help=ARGS_JSON_HELP)
@with_config_option()
def tools_invoke_cmd(
    args_file: Path,
    tool_name: str | None,
    target: str | None,
    args_json: str | None,
    config_path: Path | None,
) -> None:
    """\b
    Run one tool call from an args file (primary no-LLM workflow).

    Create the file with `sonar tools template`, edit arguments, then invoke.
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


@tools_group.command("template")
@with_target_option()
@click.option("--tool", "tool_name", required=True, help="Tool to build an input form for.")
@with_config_option()
@click.option(
    "-o",
    "--out",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Write the form to this path (default: print to stdout).",
)
def tools_template_cmd(
    target: str,
    tool_name: str,
    config_path: Path | None,
    out: Path | None,
) -> None:
    """\b
    Write a YAML input form: argument keys, types in comments, and defaults.

    Edit the form, then `sonar tools invoke --args-file <path>`.
    """

    async def _run() -> None:
        await run_tools_template(target, tool_name, config_path, out)

    asyncio.run(_run())


@tools_group.command("batch")
@click.option(
    "--file",
    "batch_file",
    required=True,
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help=BATCH_FILE_HELP,
)
@with_target_option(required=False)
@with_config_option()
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Run remaining calls after a tool error (still exits 1 at the end if any failed).",
)
def tools_batch_cmd(
    batch_file: Path,
    target: str | None,
    config_path: Path | None,
    continue_on_error: bool,
) -> None:
    """\b
    Run many tool calls from one batch file (no LLM).

    Each entry under calls: must include tool and arguments; target is optional
    if set at the top level or with --target.
    """

    async def _run() -> None:
        await run_tools_batch(
            batch_file,
            config_path,
            target,
            continue_on_error=continue_on_error,
        )

    asyncio.run(_run())


@tools_group.command("batch-template")
@with_target_option(required=False)
@click.option("--tool", "tool_name", required=True)
@click.option(
    "-o",
    "--out",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Write the starter batch file (default: stdout).",
)
def tools_batch_template_cmd(tool_name: str, target: str | None, out: Path | None) -> None:
    """Write a starter YAML file for `sonar tools batch --file`."""

    write_batch_example(tool_name, target=target, out_path=out)


@tools_group.group(
    "resources",
    help="Resources exposed by the server (MCP resources/list), if supported.",
)
def tools_resources_group() -> None:
    """List MCP resources for a target."""


@tools_resources_group.command("list")
@with_target_option()
@with_config_option()
@with_list_format_option()
def tools_resources_list_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List resource URIs and metadata (fails clearly if the server has no resources)."""

    async def _run() -> None:
        await run_resources_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@tools_group.group(
    "prompts",
    help="Prompt templates exposed by the server (MCP prompts/list), if supported.",
)
def tools_prompts_group() -> None:
    """List MCP prompts for a target."""


@tools_prompts_group.command("list")
@with_target_option()
@with_config_option()
@with_list_format_option()
def tools_prompts_list_cmd(target: str, config_path: Path | None, fmt: str) -> None:
    """List prompt names and descriptions (fails clearly if the server has no prompts)."""

    async def _run() -> None:
        await run_prompts_list(target, config_path, fmt)  # type: ignore[arg-type]

    asyncio.run(_run())


@main.command("run")
@with_target_option()
@click.option("--suite", "suite_id", required=True, help=SUITE_HELP)
@with_config_option()
@click.option("--warmup", default=2, show_default=True, help=WARMUP_HELP)
@click.option("--iterations", default=10, show_default=True, help=ITERATIONS_HELP)
@click.option("--out", "out_path", type=click.Path(path_type=Path), default=None, help=OUT_HELP)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "md", "both"]),
    default="both",
    show_default=True,
    help=REPORT_FORMAT_HELP,
)
@click.option("--skip-functional", is_flag=True, help=SKIP_FUNCTIONAL_HELP)
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
    """\b
    Run a benchmark suite against one MCP target.

    For each scenario: warmup iterations, then timed iterations with optional
    functional checks (latency p50/p95/min/max in the terminal report).
    Exits 1 if any scenario fails its functional check.
    """

    async def _run() -> None:
        config_file = _resolve_config(config_path)
        ensure_suites_loaded(_config_dir(config_file))
        targets = load_targets(config_file)
        target_name, target_cfg = _resolve_target_checked(targets, target)
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
@click.option(
    "--left",
    required=True,
    help="Left target name (see list-targets); shown first in reports.",
)
@click.option(
    "--right",
    required=True,
    help="Right target name; compared against --left using the same suite.",
)
@click.option("--suite", "suite_id", required=True, help=SUITE_HELP)
@with_config_option()
@click.option("--warmup", default=2, show_default=True, help=WARMUP_HELP)
@click.option("--iterations", default=10, show_default=True, help=ITERATIONS_HELP)
@click.option("--out", "out_path", type=click.Path(path_type=Path), default=None, help=OUT_HELP)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "md", "both"]),
    default="both",
    show_default=True,
    help=REPORT_FORMAT_HELP,
)
@click.option("--skip-functional", is_flag=True, help=SKIP_FUNCTIONAL_HELP)
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
    """\b
    Run the same suite on two targets and compare results.

    Useful for stdio vs HTTP, local vs remote, or before/after upgrades.
    Warns when left and right use different transports. Exits 1 on functional
    failure on either side.
    """

    async def _run() -> None:
        config_file = _resolve_config(config_path)
        ensure_suites_loaded(_config_dir(config_file))
        targets = load_targets(config_file)
        left_name, left_cfg = _resolve_target_checked(targets, left)
        right_name, right_cfg = _resolve_target_checked(targets, right)
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
