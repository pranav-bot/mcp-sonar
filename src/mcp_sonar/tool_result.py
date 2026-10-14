from __future__ import annotations

import json
from typing import Any

import mcp_types as types

from mcp_sonar.core.types import ToolOutcome


def _is_error(result: types.CallToolResult) -> bool:
    # mcp_types uses snake_case; older SDKs exposed camelCase on the model.
    if hasattr(result, "is_error"):
        return bool(result.is_error)
    return bool(getattr(result, "isError", False))


def _structured_content(result: types.CallToolResult) -> Any:
    if hasattr(result, "structured_content"):
        return result.structured_content
    return getattr(result, "structuredContent", None)


def tool_result_text(result: types.CallToolResult) -> str:
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, types.TextContent):
            parts.append(block.text)
        else:
            parts.append(str(block))
    if parts:
        return "\n".join(parts)
    structured = _structured_content(result)
    if structured is not None:
        return json.dumps(structured, indent=2)
    return ""


def outcome_from_call(
    tool_name: str,
    arguments: dict[str, Any],
    result: types.CallToolResult,
) -> ToolOutcome:
    text = tool_result_text(result)
    return ToolOutcome(
        tool_name=tool_name,
        arguments=arguments,
        is_error=_is_error(result),
        text=text,
        payload_bytes=len(text.encode("utf-8")),
        structured=_structured_content(result),
        error_message=text if _is_error(result) else None,
    )


def outcome_from_exception(
    tool_name: str,
    arguments: dict[str, Any],
    exc: BaseException,
) -> ToolOutcome:
    message = str(exc)
    return ToolOutcome(
        tool_name=tool_name,
        arguments=arguments,
        is_error=True,
        text=message,
        payload_bytes=len(message.encode("utf-8")),
        structured=None,
        error_message=message,
    )
