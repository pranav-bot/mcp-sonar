from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp_sonar.integrations.agentic_eval_flow.aggregate import report_to_dict
from mcp_sonar.integrations.agentic_eval_flow.runner import (
    MCPCheckerNotFoundError,
    format_eval_result,
    run_eval_for_target,
)
from mcp_sonar.target import ConnectedTarget


@dataclass(frozen=True)
class EvalFlowResult:
    gate_passed: bool
    overall_score: float
    summary: str
    report_text: str
    metadata: dict[str, Any]


def evaluate_target(
    target: ConnectedTarget,
    *,
    eval_pack: Path | None,
    mcpchecker_bin: str | None,
    threshold: float = 0.7,
) -> EvalFlowResult:
    try:
        report = run_eval_for_target(
            target,
            eval_pack=eval_pack,
            mcpchecker_bin=mcpchecker_bin,
            threshold=threshold,
        )
    except MCPCheckerNotFoundError:
        raise
    except (ValueError, FileNotFoundError, RuntimeError, OSError) as exc:
        message = str(exc)
        return EvalFlowResult(
            gate_passed=False,
            overall_score=0.0,
            summary=f"agentic-mcp: ERROR — {message[:120]}",
            report_text=message,
            metadata={"error": message},
        )

    summary, text = format_eval_result(report)
    return EvalFlowResult(
        gate_passed=report.gate_passed,
        overall_score=report.overall_score,
        summary=summary,
        report_text=text,
        metadata={
            "engine": "mcpchecker",
            "threshold": threshold,
            "recommendation": report.recommendation,
            "report": report_to_dict(report),
        },
    )
