"""Shared Click help text and reusable options for the sonar CLI."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import click

F = TypeVar("F", bound=Callable[..., Any])

CONFIG_HELP = (
    "Path to targets.yaml (named MCP endpoints). "
    "Default: config/targets.yaml next to the project root when that file exists."
)

TARGET_HELP = (
    "Target name from targets.yaml (see `sonar list-targets`). "
    "Each target uses either stdio or streamable HTTP; the CLI prints the transport before it runs."
)

FORMAT_TOOLS_HELP = (
    "Output shape: table (human-readable, default), names (one tool per line, for scripts), "
    "json (tool names, descriptions, and input schemas)."
)

FORMAT_LIST_HELP = (
    "Output shape: table (default), names (one item per line), or json."
)

FORMAT_DESCRIBE_HELP = (
    "rich: formatted description and parameter table (default); "
    "json: full tool definition and JSON Schema for scripts."
)

ARGS_JSON_HELP = (
    'Tool arguments as a JSON object. Merged on top of --args-file when both are set.'
)

ARGS_FILE_HELP = (
    "YAML or JSON file with tool, optional target, and an arguments mapping. "
    "Generate a typed form with `sonar tools template`."
)

BATCH_FILE_HELP = (
    "YAML or JSON batch file: optional top-level target, and calls: "
    "[{tool, arguments, target?}, ...]. Use `sonar tools batch-template` for a starter file."
)

WARMUP_HELP = "Iterations executed before timing starts (discarded from latency stats)."

ITERATIONS_HELP = "Timed iterations per scenario; functional checks use the last response."

OUT_HELP = "Write report files; uses .json and/or .md suffixes depending on --format."

REPORT_FORMAT_HELP = "Terminal output always prints; this controls optional files from --out."

SUITE_HELP = "Benchmark suite id (see `sonar list-suites` and config/suites/*.yaml)."

SKIP_FUNCTIONAL_HELP = (
    "Skip pass/fail checks and only measure latency and success rate. "
    "Useful when comparing transports on the same machine."
)

LENS_MODE_HELP = (
    "For suite mcp-lens only: run static rules, LLM checks, or both (default: both). "
    "Requires `uv sync --extra mcp-lens`; LLM mode needs MCP Lens llm.json."
)


def with_config_option(*, required: bool = False) -> Callable[[F], F]:
    def decorator(f: F) -> F:
        return click.option(
            "--config",
            "config_path",
            type=click.Path(path_type=Path, exists=False),
            default=None,
            required=required,
            help=CONFIG_HELP,
        )(f)

    return decorator


def with_target_option(*, required: bool = True) -> Callable[[F], F]:
    def decorator(f: F) -> F:
        return click.option("--target", required=required, help=TARGET_HELP)(f)

    return decorator


def with_tools_format_option() -> Callable[[F], F]:
    def decorator(f: F) -> F:
        return click.option(
            "--format",
            "fmt",
            type=click.Choice(["table", "names", "json"]),
            default="table",
            show_default=True,
            help=FORMAT_TOOLS_HELP,
        )(f)

    return decorator


def with_describe_format_option() -> Callable[[F], F]:
    def decorator(f: F) -> F:
        return click.option(
            "--format",
            "fmt",
            type=click.Choice(["rich", "json"]),
            default="rich",
            show_default=True,
            help=FORMAT_DESCRIBE_HELP,
        )(f)

    return decorator


def with_list_format_option() -> Callable[[F], F]:
    def decorator(f: F) -> F:
        return click.option(
            "--format",
            "fmt",
            type=click.Choice(["table", "names", "json"]),
            default="table",
            show_default=True,
            help=FORMAT_LIST_HELP,
        )(f)

    return decorator


MAIN_EPILOG = """\b
Examples:
  sonar list-targets --config config/targets.yaml
  sonar tools list --config config/targets.yaml --target my-server
  sonar run --config config/targets.yaml --target my-server --suite mcp-smoke

Environment:
  For streamable HTTP targets with auth.bearer_env set, export that variable
  (e.g. MCP_SONAR_BEARER_TOKEN) before running sonar.

More:
  https://github.com/pranav-bot/mcp-sonar
"""

TOOLS_GROUP_HELP = """\b
Interact with one MCP server (no LLM): list/describe/call tools and optional
resources or prompts. Every command prints the target name, transport
(stdio or streamable HTTP), and endpoint on stderr before output.

Examples:
  sonar tools list --target my-server --config config/targets.yaml
  sonar tools describe --target my-server --tool echo --config config/targets.yaml
  sonar tools call --target my-server --tool echo --args '{"message":"hi"}'
"""
