from __future__ import annotations

import json
from dataclasses import dataclass

from mcp_sonar.integrations.context_usage.catalog import CatalogSnapshot
from mcp_sonar.integrations.context_usage.tokens import estimate_tokens


@dataclass(frozen=True)
class StaticContextMetrics:
    tools_count: int
    tools_chars: int
    tools_tokens: int
    tools_token_method: str
    prompts_count: int
    prompts_tokens: int
    resources_count: int
    resources_tokens: int
    total_tokens: int
    token_budget: int
    gate_passed: bool
    per_tool_tokens: list[tuple[str, int]]


def analyze_static_context(catalog: CatalogSnapshot, *, token_budget: int) -> StaticContextMetrics:
    tools_text = catalog.tools_json_text()
    tools_tokens, tools_method = estimate_tokens(tools_text)

    prompts_text = catalog.prompts_text()
    prompts_tokens, _ = estimate_tokens(prompts_text) if prompts_text else (0, "empty")

    resources_text = catalog.resources_text()
    resources_tokens, _ = estimate_tokens(resources_text) if resources_text else (0, "empty")

    total = tools_tokens + prompts_tokens + resources_tokens

    per_tool: list[tuple[str, int]] = []
    for tool in catalog.tools:
        name = str(tool.get("name", "?"))
        blob = json.dumps(tool, ensure_ascii=False)
        per_tool.append((name, estimate_tokens(blob)[0]))
    per_tool.sort(key=lambda item: item[1], reverse=True)

    if token_budget > 0:
        gate_passed = total <= token_budget
    else:
        gate_passed = True

    return StaticContextMetrics(
        tools_count=len(catalog.tools),
        tools_chars=len(tools_text),
        tools_tokens=tools_tokens,
        tools_token_method=tools_method,
        prompts_count=len(catalog.prompts),
        prompts_tokens=prompts_tokens,
        resources_count=len(catalog.resources),
        resources_tokens=resources_tokens,
        total_tokens=total,
        token_budget=token_budget,
        gate_passed=gate_passed,
        per_tool_tokens=per_tool[:15],
    )


def render_static_report(metrics: StaticContextMetrics) -> str:
    lines = [
        "Context usage (static estimate)",
        f"Tools: {metrics.tools_count} ({metrics.tools_chars} chars, ~{metrics.tools_tokens} tokens via {metrics.tools_token_method})",
        f"Prompts: {metrics.prompts_count} (~{metrics.prompts_tokens} tokens)",
        f"Resources: {metrics.resources_count} (~{metrics.resources_tokens} tokens)",
        f"Total estimated context: ~{metrics.total_tokens} tokens",
    ]
    if metrics.token_budget > 0:
        status = "PASS" if metrics.gate_passed else "FAIL"
        lines.append(f"Budget: {metrics.token_budget} tokens — {status}")
    else:
        lines.append("Budget: not set (informational only)")
    if metrics.per_tool_tokens:
        lines.append("")
        lines.append("Largest tools by estimated tokens:")
        for name, count in metrics.per_tool_tokens[:10]:
            lines.append(f"  - {name}: ~{count}")
    return "\n".join(lines)
