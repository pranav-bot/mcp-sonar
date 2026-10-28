from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class InvokeSpec:
    """Single tool call loaded from an args file (YAML or JSON)."""

    tool: str | None
    target: str | None
    arguments: dict[str, Any]


@dataclass(frozen=True)
class BatchCall:
    tool: str
    target: str | None
    arguments: dict[str, Any]


@dataclass(frozen=True)
class BatchSpec:
    target: str | None
    calls: list[BatchCall]


@dataclass(frozen=True)
class PromptBatch:
    target: str | None
    prompts: list[str]


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        import json

        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a mapping")
    return data


def load_invoke_file(path: Path) -> InvokeSpec:
    data = _load_mapping(path)
    tool = data.get("tool")
    if tool is not None and not isinstance(tool, str):
        raise ValueError(f"{path}: 'tool' must be a string")
    target = data.get("target")
    if target is not None and not isinstance(target, str):
        raise ValueError(f"{path}: 'target' must be a string")
    arguments = data.get("arguments", {})
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ValueError(f"{path}: 'arguments' must be a mapping")
    return InvokeSpec(tool=tool, target=target, arguments=arguments)


def load_batch_file(path: Path) -> BatchSpec:
    data = _load_mapping(path)
    default_target = data.get("target")
    if default_target is not None and not isinstance(default_target, str):
        raise ValueError(f"{path}: 'target' must be a string")
    raw_calls = data.get("calls")
    if not isinstance(raw_calls, list) or not raw_calls:
        raise ValueError(f"{path}: 'calls' must be a non-empty list")
    calls: list[BatchCall] = []
    for index, item in enumerate(raw_calls):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: calls[{index}] must be a mapping")
        tool = item.get("tool")
        if not isinstance(tool, str) or not tool:
            raise ValueError(f"{path}: calls[{index}].tool is required")
        row_target = item.get("target")
        if row_target is not None and not isinstance(row_target, str):
            raise ValueError(f"{path}: calls[{index}].target must be a string")
        arguments = item.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ValueError(f"{path}: calls[{index}].arguments must be a mapping")
        calls.append(BatchCall(tool=tool, target=row_target, arguments=arguments))
    return BatchSpec(target=default_target, calls=calls)


def load_prompt_batch(path: Path) -> PromptBatch:
    data = _load_mapping(path)
    target = data.get("target")
    if target is not None and not isinstance(target, str):
        raise ValueError(f"{path}: 'target' must be a string")
    raw_prompts = data.get("prompts")
    if not isinstance(raw_prompts, list) or not raw_prompts:
        raise ValueError(f"{path}: 'prompts' must be a non-empty list")
    prompts: list[str] = []
    for index, item in enumerate(raw_prompts):
        if not isinstance(item, str):
            raise ValueError(
                f"{path}: prompts[{index}] must be a quoted string "
                f"(YAML turned it into {type(item).__name__})"
            )
        if not item.strip():
            raise ValueError(f"{path}: prompts[{index}] must be a non-empty string")
        prompts.append(item)
    return PromptBatch(target=target, prompts=prompts)


def resolve_invoke(
    *,
    tool_cli: str | None,
    target_cli: str | None,
    args_json: str | None,
    args_file: Path | None,
) -> tuple[str, str, dict[str, Any]]:
    """Merge CLI flags with an optional args file into (tool, target, arguments)."""
    from mcp_sonar.interactor.session import parse_tool_args  # noqa: PLC0415

    arguments: dict[str, Any] = {}
    tool: str | None = tool_cli
    target: str | None = target_cli

    if args_file is not None:
        spec = load_invoke_file(args_file)
        tool = tool_cli or spec.tool
        target = target_cli or spec.target
        arguments = dict(spec.arguments)

    if args_json is not None:
        arguments = {**arguments, **parse_tool_args(args_json)}
    elif not arguments and args_file is None:
        arguments = {}

    if not tool:
        raise ValueError("Tool name required: pass --tool or set 'tool' in the args file")
    if not target:
        raise ValueError("Target required: pass --target or set 'target' in the args file")
    return tool, target, arguments
