from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from mcp_sonar.interactor.format import tool_definition_to_dict
from mcp_sonar.target import ConnectedTarget

AgentStepKind = Literal["tool_call", "final", "error"]


@dataclass
class AgentStep:
    index: int
    kind: AgentStepKind
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    tool_result_text: str | None = None
    tool_is_error: bool = False
    llm_text: str | None = None
    note: str | None = None
    select_tool_ms: float | None = None
    tool_invoke_ms: float | None = None
    generate_answer_ms: float | None = None


@dataclass(frozen=True)
class AgentTimingTotals:
    wall_ms: float
    llm_ms: float
    tool_ms: float


@dataclass
class AgentRunResult:
    prompt: str
    steps: list[AgentStep]
    final_answer: str
    llm_config: str
    stopped_reason: str
    timing: AgentTimingTotals | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": self.prompt,
            "llm_config": self.llm_config,
            "stopped_reason": self.stopped_reason,
            "final_answer": self.final_answer,
            "steps": [
                {
                    "index": s.index,
                    "kind": s.kind,
                    "tool_name": s.tool_name,
                    "arguments": s.arguments,
                    "tool_result_text": s.tool_result_text,
                    "tool_is_error": s.tool_is_error,
                    "llm_text": s.llm_text,
                    "note": s.note,
                    "select_tool_ms": s.select_tool_ms,
                    "tool_invoke_ms": s.tool_invoke_ms,
                    "generate_answer_ms": s.generate_answer_ms,
                }
                for s in self.steps
            ],
        }
        if self.timing is not None:
            payload["timing"] = {
                "wall_ms": self.timing.wall_ms,
                "llm_ms": self.timing.llm_ms,
                "tool_ms": self.timing.tool_ms,
            }
        return payload


class McpLlmAdapter(Protocol):
    async def select_tool(self, tools: list[dict], user_prompt: str) -> dict: ...

    async def generate_answer(self, tool_result: Any, user_prompt: str) -> str: ...


def _truncate(text: str, max_len: int = 4000) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "\n… [truncated]"


def _build_turn_prompt(user_prompt: str, steps: list[AgentStep]) -> str:
    lines = [
        user_prompt,
        "",
        "You are connected to an MCP server. Use the provided tools when needed.",
    ]
    if steps:
        lines.append("")
        lines.append("Steps completed in this session:")
        for step in steps:
            if step.kind != "tool_call" or not step.tool_name:
                continue
            args_json = json.dumps(step.arguments, ensure_ascii=False)
            result = _truncate(step.tool_result_text or "")
            err = " [ERROR]" if step.tool_is_error else ""
            lines.append(f"{step.index}. {step.tool_name}({args_json}) ->{err}\n{result}")
    lines.append("")
    lines.append(
        "Call another tool if you need more data, or finish by not selecting a tool "
        "(the system will ask you for a final answer)."
    )
    return "\n".join(lines)


def _agent_timing_totals(steps: list[AgentStep], wall_sec: float) -> AgentTimingTotals:
    llm_ms = 0.0
    tool_ms = 0.0
    for step in steps:
        if step.select_tool_ms is not None:
            llm_ms += step.select_tool_ms
        if step.generate_answer_ms is not None:
            llm_ms += step.generate_answer_ms
        if step.tool_invoke_ms is not None:
            tool_ms += step.tool_invoke_ms
    return AgentTimingTotals(wall_ms=wall_sec * 1000.0, llm_ms=llm_ms, tool_ms=tool_ms)


async def run_agent(
    target: ConnectedTarget,
    adapter: McpLlmAdapter,
    prompt: str,
    *,
    llm_config_name: str,
    max_steps: int = 8,
) -> AgentRunResult:
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")

    run_start = time.perf_counter()
    tools = [tool_definition_to_dict(t) for t in await target.list_tool_definitions()]
    steps: list[AgentStep] = []
    stopped_reason = "max_steps"

    for i in range(1, max_steps + 1):
        turn_prompt = _build_turn_prompt(prompt, steps)
        select_ms: float | None = None
        try:
            t0 = time.perf_counter()
            pick = await adapter.select_tool(tools, turn_prompt)
            select_ms = (time.perf_counter() - t0) * 1000.0
        except Exception as exc:  # noqa: BLE001
            steps.append(
                AgentStep(
                    index=i,
                    kind="error",
                    note=f"LLM select_tool failed: {exc}",
                    select_tool_ms=select_ms,
                )
            )
            stopped_reason = "llm_error"
            break

        tool_name = str(pick.get("tool_name") or "").strip()
        arguments = pick.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}

        if not tool_name:
            last = next((s for s in reversed(steps) if s.kind == "tool_call"), None)
            prior = last.tool_result_text if last else None
            gen_ms: float | None = None
            try:
                t0 = time.perf_counter()
                answer = await adapter.generate_answer(prior, turn_prompt)
                gen_ms = (time.perf_counter() - t0) * 1000.0
            except Exception as exc:  # noqa: BLE001
                steps.append(
                    AgentStep(
                        index=i,
                        kind="error",
                        note=f"LLM generate_answer failed: {exc}",
                        select_tool_ms=select_ms,
                        generate_answer_ms=gen_ms,
                    )
                )
                stopped_reason = "llm_error"
                final = ""
            else:
                steps.append(
                    AgentStep(
                        index=i,
                        kind="final",
                        llm_text=answer,
                        select_tool_ms=select_ms,
                        generate_answer_ms=gen_ms,
                    )
                )
                stopped_reason = "complete"
                final = answer
            wall = time.perf_counter() - run_start
            return AgentRunResult(
                prompt=prompt,
                steps=steps,
                final_answer=final,
                llm_config=llm_config_name,
                stopped_reason=stopped_reason,
                timing=_agent_timing_totals(steps, wall),
            )

        t0 = time.perf_counter()
        outcome = await target.call_tool(tool_name, arguments)
        invoke_ms = (time.perf_counter() - t0) * 1000.0
        steps.append(
            AgentStep(
                index=i,
                kind="tool_call",
                tool_name=tool_name,
                arguments=arguments,
                tool_result_text=outcome.text,
                tool_is_error=outcome.is_error,
                select_tool_ms=select_ms,
                tool_invoke_ms=invoke_ms,
            )
        )

    # Exhausted steps — synthesize final answer from last tool result if any
    last_tool = next((s for s in reversed(steps) if s.kind == "tool_call"), None)
    tail_prompt = _build_turn_prompt(prompt, steps)
    gen_ms: float | None = None
    try:
        t0 = time.perf_counter()
        final = await adapter.generate_answer(
            last_tool.tool_result_text if last_tool else None,
            tail_prompt + "\n\nSummarize the answer for the user (no more tool calls).",
        )
        gen_ms = (time.perf_counter() - t0) * 1000.0
    except Exception as exc:  # noqa: BLE001
        steps.append(
            AgentStep(
                index=len(steps) + 1,
                kind="error",
                note=str(exc),
                generate_answer_ms=gen_ms,
            )
        )
        final = last_tool.tool_result_text if last_tool else ""
        stopped_reason = "llm_error"
    else:
        steps.append(
            AgentStep(
                index=len(steps) + 1,
                kind="final",
                llm_text=final,
                generate_answer_ms=gen_ms,
            )
        )

    wall = time.perf_counter() - run_start
    return AgentRunResult(
        prompt=prompt,
        steps=steps,
        final_answer=final,
        llm_config=llm_config_name,
        stopped_reason=stopped_reason,
        timing=_agent_timing_totals(steps, wall),
    )
