from __future__ import annotations

from mcp_sonar.checks.builtin import check_eval_flow_gate
from mcp_sonar.suite.base import ScenarioStep, Suite
from mcp_sonar.suite.agentic_eval_context import get_eval_pack, get_eval_threshold, get_mcpchecker_bin

DEFAULT_BINDING = "default"

AGENTIC_MCPCHECKER_TOOL = "__agentic_mcpchecker__"


class AgenticEvalFlowSuite(Suite):
    """MCPChecker task evaluation via [agentic_eval_flow](https://github.com/RHEcosystemAppEng/agentic_eval_flow).

    Requires the ``mcpchecker`` CLI on PATH, a streamable HTTP target, and an eval pack
    (default ``config/eval-flow/default``). LLM API keys must be in the environment
    for agent/judge models declared in ``eval.yaml``.
    """

    @property
    def id(self) -> str:
        return "agentic-mcp"

    @property
    def description(self) -> str:
        return (
            "Agentic Eval Flow MCPChecker tasks against your MCP server "
            "(use --eval-pack, --mcpchecker-bin; HTTP targets only)."
        )

    def steps(self) -> list[ScenarioStep]:
        _ = (get_eval_pack(), get_mcpchecker_bin(), get_eval_threshold())
        return [
            ScenarioStep(
                id="mcpchecker",
                description="MCPChecker agent tasks with LLM judge (70% pass threshold)",
                bindings={
                    DEFAULT_BINDING: lambda: (AGENTIC_MCPCHECKER_TOOL, {"engine": "mcpchecker"}),
                },
                check=check_eval_flow_gate,
            )
        ]


def register() -> None:
    from mcp_sonar.suite.registry import register_suite  # noqa: PLC0415

    register_suite(AgenticEvalFlowSuite())
