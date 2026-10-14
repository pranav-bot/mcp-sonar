from __future__ import annotations

from mcp_sonar.checks.builtin import check_load_gate
from mcp_sonar.suite.base import ScenarioStep, Suite
from mcp_sonar.suite.load_context import get_load_arguments, get_load_tool

DEFAULT_BINDING = "default"

MCP_LOAD_PARALLEL_TOOL = "__mcp_load_parallel__"


class McpLoadSuite(Suite):
    """Parallel connection load test against one tool (default tools/list).

    Use ``sonar run --suite mcp-load`` with ``--load-concurrency``, ``--load-tool``,
    and ``--load-args``.
    """

    @property
    def id(self) -> str:
        return "mcp-load"

    @property
    def description(self) -> str:
        return (
            "Stress test: N parallel MCP sessions each invoking the same tool. "
            "Configure with --load-concurrency, --load-tool, --load-args."
        )

    def steps(self) -> list[ScenarioStep]:
        tool = get_load_tool()
        args = get_load_arguments()
        return [
            ScenarioStep(
                id="parallel_load",
                description=f"Parallel load ({tool})",
                bindings={
                    DEFAULT_BINDING: lambda t=tool, a=args: (MCP_LOAD_PARALLEL_TOOL, {"tool": t, "arguments": a}),
                },
                check=check_load_gate,
            ),
        ]


def register() -> None:
    from mcp_sonar.suite.registry import register_suite  # noqa: PLC0415

    register_suite(McpLoadSuite())
