from __future__ import annotations

from mcp_sonar.checks.builtin import check_lens_gate
from mcp_sonar.suite.base import ScenarioStep, Suite
from mcp_sonar.suite.mcp_lens_context import get_lens_mode

DEFAULT_BINDING = "default"

LENS_STATIC_TOOL = "__mcp_lens_static__"
LENS_LLM_TOOL = "__mcp_lens_llm__"


class McpLensSuite(Suite):
    """MCP Lens tool evaluation (protocol, quality, security, optional LLM).

    Use ``sonar run --suite mcp-lens --lens-mode static|llm|both``.
    Requires optional dependency: ``uv sync --extra mcp-lens``.
    """

    @property
    def id(self) -> str:
        return "mcp-lens"

    @property
    def description(self) -> str:
        return (
            "MCP Lens evaluation (static rules and optional LLM checks). "
            "Use --lens-mode static, llm, or both."
        )

    def steps(self) -> list[ScenarioStep]:
        mode = get_lens_mode()
        steps: list[ScenarioStep] = []
        if mode in ("static", "both"):
            steps.append(
                ScenarioStep(
                    id="lens_static",
                    description="MCP Lens static layers (protocol, quality, security)",
                    bindings={DEFAULT_BINDING: lambda: (LENS_STATIC_TOOL, {"mode": "static"})},
                    check=check_lens_gate,
                )
            )
        if mode in ("llm", "both"):
            steps.append(
                ScenarioStep(
                    id="lens_llm",
                    description="MCP Lens LLM-assisted evaluation (requires llm.json)",
                    bindings={DEFAULT_BINDING: lambda: (LENS_LLM_TOOL, {"mode": "llm"})},
                    check=check_lens_gate,
                )
            )
        return steps


def register() -> None:
    from mcp_sonar.suite.registry import register_suite  # noqa: PLC0415

    register_suite(McpLensSuite())
