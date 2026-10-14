from __future__ import annotations

from mcp_sonar.checks.builtin import check_list_tools_nonempty, check_not_error
from mcp_sonar.suite.base import ScenarioStep, Suite

DEFAULT_BINDING = "default"


class McpSmokeSuite(Suite):
    """Protocol-level checks that apply to most MCP servers."""

    @property
    def id(self) -> str:
        return "mcp-smoke"

    @property
    def description(self) -> str:
        return "Minimal MCP protocol smoke test (tools/list)."

    def steps(self) -> list[ScenarioStep]:
        return [
            ScenarioStep(
                id="list_tools",
                description="MCP tools/list returns at least one tool",
                bindings={
                    DEFAULT_BINDING: lambda: ("__list_tools__", {}),
                },
                check=check_list_tools_nonempty,
            ),
        ]


def register() -> None:
    from mcp_sonar.suite.registry import register_suite  # noqa: PLC0415

    register_suite(McpSmokeSuite())
