from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mcp_sonar.json_text import last_json_object

from mcp_sonar.integrations.context_usage.catalog import CatalogSnapshot
from mcp_sonar.integrations.context_usage.static_eval import analyze_static_context, render_static_report


@dataclass(frozen=True)
class LlmContextMetrics:
    context_score: float
    estimated_tokens: int | None
    summary: str
    gate_passed: bool
    min_score: float
    raw_response: str


def _parse_llm_json(text: str) -> dict[str, Any]:
    try:
        return last_json_object(text)
    except ValueError as exc:
        raise ValueError("LLM response did not contain JSON object") from exc


async def analyze_llm_context(
    catalog: CatalogSnapshot,
    adapter: Any,
    *,
    min_score: float,
    token_budget: int,
) -> LlmContextMetrics:
    static = analyze_static_context(catalog, token_budget=token_budget)
    summary_block = render_static_report(static)
    prompt = (
        "You are evaluating MCP server context usage for LLM agents.\n"
        "A large tool catalog consumes model context window and can hurt agent performance.\n\n"
        f"{summary_block}\n\n"
        "Reply with JSON only:\n"
        '{"context_score": <0-100, higher means more context-efficient design>, '
        '"estimated_tokens": <integer guess for full catalog in a typical tools API payload>, '
        '"summary": "<one sentence>"}\n'
    )
    raw = await adapter.generate_answer(None, prompt)
    data = _parse_llm_json(raw)
    score = float(data.get("context_score", 0))
    est = data.get("estimated_tokens")
    estimated_tokens = int(est) if est is not None else None
    summary = str(data.get("summary", raw[:200]))
    gate_passed = score >= min_score
    return LlmContextMetrics(
        context_score=score,
        estimated_tokens=estimated_tokens,
        summary=summary,
        gate_passed=gate_passed,
        min_score=min_score,
        raw_response=raw,
    )


def render_llm_report(metrics: LlmContextMetrics) -> str:
    lines = [
        "Context usage (LLM review)",
        f"Context efficiency score: {metrics.context_score:.1f}/100 (min {metrics.min_score:.0f}) — "
        f"{'PASS' if metrics.gate_passed else 'FAIL'}",
        f"LLM estimated tokens: {metrics.estimated_tokens if metrics.estimated_tokens is not None else 'n/a'}",
        f"Summary: {metrics.summary}",
    ]
    return "\n".join(lines)
