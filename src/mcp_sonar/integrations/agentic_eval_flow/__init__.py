"""MCPChecker integration for Agentic Eval Flow (https://github.com/RHEcosystemAppEng/agentic_eval_flow).

Report aggregation is adapted from upstream ``scripts/aggregate_mcpchecker.py`` (Apache-2.0).
Runtime evaluation uses the mcpchecker CLI. See CREDITS.md in the mcp-sonar repository root.
"""

from mcp_sonar.integrations.agentic_eval_flow.evaluate import EvalFlowResult, evaluate_target

__all__ = ["EvalFlowResult", "evaluate_target"]
