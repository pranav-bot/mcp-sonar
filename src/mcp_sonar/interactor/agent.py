from __future__ import annotations

import json
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


@dataclass
class AgentRunResult:
    prompt: str
    steps: list[AgentStep]
    final_answer: str
    llm_config: str
    stopped_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
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
                }
                for s in self.steps
            ],
        }


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

    tools = [tool_definition_to_dict(t) for t in await target.list_tool_definitions()]
    steps: list[AgentStep] = []
    stopped_reason = "max_steps"

    for i in range(1, max_steps + 1):
        turn_prompt = _build_turn_prompt(prompt, steps)
        try:
            pick = await adapter.select_tool(tools, turn_prompt)
        except Exception as exc:  # noqa: BLE001
            steps.append(
                AgentStep(
                    index=i,
                    kind="error",
                    note=f"LLM select_tool failed: {exc}",
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
            try:
                answer = await adapter.generate_answer(prior, turn_prompt)
            except Exception as exc:  # noqa: BLE001
                steps.append(
                    AgentStep(index=i, kind="error", note=f"LLM generate_answer failed: {exc}")
                )
                stopped_reason = "llm_error"
                final = ""
            else:
                steps.append(AgentStep(index=i, kind="final", llm_text=answer))
                stopped_reason = "complete"
                final = answer
            return AgentRunResult(
                prompt=prompt,
                steps=steps,
                final_answer=final,
                llm_config=llm_config_name,
                stopped_reason=stopped_reason,
            )

        outcome = await target.call_tool(tool_name, arguments)
        steps.append(
            AgentStep(
                index=i,
                kind="tool_call",
                tool_name=tool_name,
                arguments=arguments,
                tool_result_text=outcome.text,
                tool_is_error=outcome.is_error,
            )
        )

    # Exhausted steps — synthesize final answer from last tool result if any
    last_tool = next((s for s in reversed(steps) if s.kind == "tool_call"), None)
    tail_prompt = _build_turn_prompt(prompt, steps)
    try:
        final = await adapter.generate_answer(
            last_tool.tool_result_text if last_tool else None,
            tail_prompt + "\n\nSummarize the answer for the user (no more tool calls).",
        )
    except Exception as exc:  # noqa: BLE001
        steps.append(AgentStep(index=len(steps) + 1, kind="error", note=str(exc)))
        final = last_tool.tool_result_text if last_tool else ""
        stopped_reason = "llm_error"
    else:
        steps.append(AgentStep(index=len(steps) + 1, kind="final", llm_text=final))

    return AgentRunResult(
        prompt=prompt,
        steps=steps,
        final_answer=final,
        llm_config=llm_config_name,
        stopped_reason=stopped_reason,
    )
