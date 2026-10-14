from __future__ import annotations

from mcp_sonar.checks.builtin import check_context_gate
from mcp_sonar.suite.base import ScenarioStep, Suite
from mcp_sonar.suite.mcp_context_context import get_context_mode

DEFAULT_BINDING = "default"

CONTEXT_STATIC_TOOL = "__mcp_context_static__"
CONTEXT_LLM_TOOL = "__mcp_context_llm__"


class McpContextSuite(Suite):
    """Estimate MCP catalog context usage (tokens) and optional LLM efficiency review.

    Use ``sonar run --suite mcp-context --context-mode static|llm|both``.
    Install ``tiktoken`` for accurate static counts (`uv sync --extra context-tokens`).
    LLM mode uses ``llm.json`` (same as mcp-lens LLM).
    """

    @property
    def id(self) -> str:
        return "mcp-context"

    @property
    def description(self) -> str:
        return (
            "Context window usage for tools/prompts/resources (static token estimate "
            "and optional LLM review). Use --context-mode and --context-budget."
        )

    def steps(self) -> list[ScenarioStep]:
        mode = get_context_mode()
        steps: list[ScenarioStep] = []
        if mode in ("static", "both"):
            steps.append(
                ScenarioStep(
                    id="context_static",
                    description="Static token estimate for tools, prompts, and resources",
                    bindings={DEFAULT_BINDING: lambda: (CONTEXT_STATIC_TOOL, {"mode": "static"})},
                    check=check_context_gate,
                )
            )
        if mode in ("llm", "both"):
            steps.append(
                ScenarioStep(
                    id="context_llm",
                    description="LLM review of context efficiency (requires llm.json)",
                    bindings={DEFAULT_BINDING: lambda: (CONTEXT_LLM_TOOL, {"mode": "llm"})},
                    check=check_context_gate,
                )
            )
        return steps


def register() -> None:
    from mcp_sonar.suite.registry import register_suite  # noqa: PLC0415

    register_suite(McpContextSuite())
