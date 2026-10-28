from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

from mcp_sonar.integrations.context_usage.catalog import CatalogSnapshot, fetch_catalog
from mcp_sonar.integrations.context_usage.llm_eval import analyze_llm_context, render_llm_report
from mcp_sonar.integrations.context_usage.static_eval import analyze_static_context, render_static_report
from mcp_sonar.target import ConnectedTarget

ContextMode = Literal["static", "llm", "both"]


@dataclass(frozen=True)
class ContextEvalResult:
    mode: ContextMode
    gate_passed: bool
    overall_score: float
    summary: str
    report_text: str
    metadata: dict[str, Any]


async def _run_llm(catalog: CatalogSnapshot, min_llm_score: float, token_budget: int) -> tuple[bool, float, str, str, dict]:
    from mcp_sonar.llm.registry import get_adapter_for_config, get_default_llm_name  # noqa: PLC0415

    default_name = get_default_llm_name()
    if not default_name:
        raise RuntimeError(
            "LLM context review requires llm.json with a default provider (see config/llm.example.json)"
        )
    adapter = get_adapter_for_config(default_name)
    metrics = await analyze_llm_context(
        catalog,
        adapter,
        min_score=min_llm_score,
        token_budget=token_budget,
    )
    report = render_llm_report(metrics)
    meta = {
        "context_score": metrics.context_score,
        "llm_estimated_tokens": metrics.estimated_tokens,
        "min_llm_score": min_llm_score,
    }
    return metrics.gate_passed, metrics.context_score, metrics.summary, report, meta


async def evaluate_context_async(
    catalog: CatalogSnapshot,
    *,
    mode: ContextMode,
    token_budget: int,
    min_llm_score: float,
) -> ContextEvalResult:
    sections: list[str] = []
    metadata: dict[str, Any] = {"context_mode": mode, "token_budget": token_budget}
    gates: list[bool] = []
    scores: list[float] = []

    if mode in ("static", "both"):
        static = analyze_static_context(catalog, token_budget=token_budget)
        static_text = render_static_report(static)
        sections.append(static_text)
        gates.append(static.gate_passed)
        if token_budget > 0:
            scores.append(min(100.0, 100.0 * token_budget / max(static.total_tokens, 1)))
        else:
            scores.append(100.0)
        metadata["static"] = {
            "total_tokens": static.total_tokens,
            "tools_tokens": static.tools_tokens,
            "token_method": static.tools_token_method,
            "gate_passed": static.gate_passed,
        }

    if mode in ("llm", "both"):
        try:
            passed, score, summary, llm_text, llm_meta = await _run_llm(
                catalog, min_llm_score, token_budget
            )
            sections.append(llm_text)
            gates.append(passed)
            scores.append(score)
            metadata.update(llm_meta)
            metadata["llm_gate_passed"] = passed
        except (RuntimeError, ValueError) as exc:
            if mode == "llm":
                raise
            metadata["llm_error"] = str(exc)
            sections.append(f"LLM context review skipped: {exc}")

    if mode == "llm" and "llm_gate_passed" not in metadata and "llm_error" in metadata:
        raise RuntimeError(metadata["llm_error"])

    gate_passed = all(gates) if gates else False
    overall = sum(scores) / len(scores) if scores else 0.0
    report_text = "\n\n".join(sections)
    summary = (
        f"mcp-context ({mode}): ~{metadata.get('static', {}).get('total_tokens', '?')} tokens (static), "
        f"score {overall:.1f}/100, gate {'PASS' if gate_passed else 'FAIL'}"
    )
    if mode == "llm" and "context_score" in metadata:
        summary = (
            f"mcp-context (llm): efficiency {metadata['context_score']:.1f}/100, "
            f"gate {'PASS' if gate_passed else 'FAIL'}"
        )

    return ContextEvalResult(
        mode=mode,
        gate_passed=gate_passed,
        overall_score=overall,
        summary=summary,
        report_text=report_text,
        metadata=metadata,
    )


def evaluate_context(
    catalog: CatalogSnapshot,
    *,
    mode: ContextMode,
    token_budget: int,
    min_llm_score: float,
) -> ContextEvalResult:
    """Sync entry point (not from an active asyncio loop)."""
    return asyncio.run(
        evaluate_context_async(
            catalog,
            mode=mode,
            token_budget=token_budget,
            min_llm_score=min_llm_score,
        )
    )


async def evaluate_target_context(
    target: ConnectedTarget,
    *,
    mode: ContextMode,
    token_budget: int,
    min_llm_score: float,
) -> ContextEvalResult:
    catalog = await fetch_catalog(target)
    return await evaluate_context_async(
        catalog,
        mode=mode,
        token_budget=token_budget,
        min_llm_score=min_llm_score,
    )


def _result_from_static(catalog: CatalogSnapshot, token_budget: int) -> ContextEvalResult:
    static = analyze_static_context(catalog, token_budget=token_budget)
    text = render_static_report(static)
    score = (
        min(100.0, 100.0 * token_budget / max(static.total_tokens, 1))
        if token_budget > 0
        else 100.0
    )
    summary = (
        f"mcp-context (static): ~{static.total_tokens} tokens "
        f"({static.tools_token_method}), gate {'PASS' if static.gate_passed else 'FAIL'}"
    )
    return ContextEvalResult(
        mode="static",
        gate_passed=static.gate_passed,
        overall_score=score,
        summary=summary,
        report_text=text,
        metadata={
            "static": {
                "total_tokens": static.total_tokens,
                "tools_tokens": static.tools_tokens,
                "gate_passed": static.gate_passed,
            }
        },
    )


async def evaluate_static_step(
    target: ConnectedTarget,
    *,
    token_budget: int,
) -> ContextEvalResult:
    catalog = await fetch_catalog(target)
    return _result_from_static(catalog, token_budget)


async def evaluate_llm_step(
    target: ConnectedTarget,
    *,
    token_budget: int,
    min_llm_score: float,
) -> ContextEvalResult:
    catalog = await fetch_catalog(target)
    passed, score, summary, report, meta = await _run_llm(catalog, min_llm_score, token_budget)
    return ContextEvalResult(
        mode="llm",
        gate_passed=passed,
        overall_score=score,
        summary=f"mcp-context (llm): {summary}",
        report_text=report,
        metadata=meta,
    )
