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

VERBOSE_RUN_HELP = (
    "After the summary table, print full last tool response for each scenario. "
    "The mcp-lens suite always prints its text report; use this flag for other suites. "
    "Scenario detail is included in --out markdown/json when captured."
)

LENS_MODE_HELP = (
    "For suite mcp-lens only: run static rules, LLM checks, or both (default: both). "
    "Requires `uv sync --extra mcp-lens`; LLM mode needs MCP Lens llm.json."
)

EVAL_PACK_HELP = (
    "For suite agentic-mcp only: directory with eval.yaml and tasks/ "
    "(default: config/eval-flow/default)."
)

MCPCHECKER_BIN_HELP = "For suite agentic-mcp only: path to mcpchecker CLI (default: mcpchecker on PATH)."

EVAL_THRESHOLD_HELP = (
    "For suite agentic-mcp only: pass threshold for MCPChecker overall score (default: 0.7)."
)

LOAD_CONCURRENCY_HELP = "For suite mcp-load only: parallel MCP sessions per iteration (default: 10)."

LOAD_TOOL_HELP = "For suite mcp-load only: tool to invoke under load (default: __list_tools__)."

LOAD_ARGS_HELP = "For suite mcp-load only: JSON arguments for --load-tool (ignored for __list_tools__)."

LOAD_MIN_SUCCESS_HELP = (
    "For suite mcp-load only: minimum success rate across parallel workers (default: 0.95)."
)

CONTEXT_MODE_HELP = (
    "For suite mcp-context only: static token estimate, LLM efficiency review, or both (default: both)."
)

CONTEXT_BUDGET_HELP = (
    "For suite mcp-context only: max estimated tokens for static gate (0 = informational, always pass)."
)

CONTEXT_MIN_LLM_SCORE_HELP = (
    "For suite mcp-context only: minimum LLM context efficiency score 0-100 (default: 70)."
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

AGENT_GROUP_HELP = """\b
Run an LLM against an MCP target: the model may call tools in a loop until it
answers. Each tool invocation is recorded (name, arguments, result).

Requires llm.json (or MCP_SONAR_LLM_CONFIG). Uses the same adapters as mcp-lens
and mcp-context (Anthropic, OpenAI, Vertex, MaaS / models-corps).

Examples:
  sonar agent run --target my-server --prompt "List CVEs and summarize"
  sonar agent run --target my-server --prompt-file task.txt --format json
"""

AGENT_MAX_STEPS_HELP = "Maximum LLM tool-selection rounds before forcing a final answer (default: 8)."

AGENT_LLM_CONFIG_HELP = "Named entry from llm.json (default: the file's default provider)."

AGENT_PROMPT_FILE_HELP = "Read the user prompt from a text file instead of --prompt."

TOOLS_GROUP_HELP = """\b
Interact with one MCP server (no LLM): list/describe/call tools and optional
resources or prompts. Every command prints the target name, transport
(stdio or streamable HTTP), and endpoint on stderr before output.

Examples:
  sonar tools list --target my-server --config config/targets.yaml
  sonar tools describe --target my-server --tool echo --config config/targets.yaml
  sonar tools call --target my-server --tool echo --args '{"message":"hi"}'
"""
