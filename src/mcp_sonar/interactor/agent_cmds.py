from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mcp_sonar.display import print_connected_target
from mcp_sonar.interactor.agent import AgentRunResult, run_agent
from mcp_sonar.interactor.session import open_target
from mcp_sonar.local_bootstrap import bootstrap_local_workspace
from mcp_sonar.llm.config import resolve_llm_config_path
from mcp_sonar.llm.registry import get_adapter_for_config, get_default_llm_name

console = Console()

AgentFormat = Literal["rich", "json"]


def _resolve_llm_config_name(explicit: str | None) -> str:
    name = explicit or get_default_llm_name()
    if not name:
        raise RuntimeError(
            "No LLM configured. Set MCP_SONAR_LLM_CONFIG, add config/llm.json, "
            "or pass --llm-config."
        )
    return name


def print_agent_report(result: AgentRunResult, *, fmt: AgentFormat) -> None:
    if fmt == "json":
        console.print_json(json.dumps(result.to_dict(), indent=2))
        return

    table = Table(title="Agent steps")
    table.add_column("#", style="dim")
    table.add_column("Kind")
    table.add_column("Tool")
    table.add_column("Timing (ms)")
    table.add_column("Detail")
    for step in result.steps:
        detail = step.note or step.llm_text or ""
        if step.kind == "tool_call":
            detail = (step.tool_result_text or "")[:200]
            if step.tool_is_error:
                detail = f"[error] {detail}"
        timing_parts: list[str] = []
        if step.select_tool_ms is not None:
            timing_parts.append(f"llm pick {step.select_tool_ms:.0f}")
        if step.tool_invoke_ms is not None:
            timing_parts.append(f"tool {step.tool_invoke_ms:.0f}")
        if step.generate_answer_ms is not None:
            timing_parts.append(f"llm answer {step.generate_answer_ms:.0f}")
        table.add_row(
            str(step.index),
            step.kind,
            step.tool_name or "—",
            ", ".join(timing_parts) or "—",
            detail.replace("\n", " ")[:120],
        )
    console.print(table)
    if result.timing is not None:
        t = result.timing
        console.print(
            f"[dim]Totals: wall {t.wall_ms:.0f} ms · LLM {t.llm_ms:.0f} ms · "
            f"MCP tools {t.tool_ms:.0f} ms[/dim]"
        )
    console.print(
        Panel(
            result.final_answer or "(empty)",
            title=f"Final answer ({result.stopped_reason})",
            border_style="green",
        )
    )


async def run_agent_cmd(
    target: str,
    config_path: Path | None,
    prompt: str,
    *,
    llm_config: str | None,
    max_steps: int,
    fmt: AgentFormat,
) -> AgentRunResult:
    bootstrap_local_workspace(config_path)
    llm_path = resolve_llm_config_path()
    if llm_path is not None:
        console.print(f"[dim]LLM config: {llm_path}[/dim]")
    config_name = _resolve_llm_config_name(llm_config)
    adapter = get_adapter_for_config(config_name)

    async with open_target(target, config_path) as (_name, connected):
        print_connected_target(connected)
        result = await run_agent(
            connected,
            adapter,
            prompt,
            llm_config_name=config_name,
            max_steps=max_steps,
        )
    print_agent_report(result, fmt=fmt)
    return result
