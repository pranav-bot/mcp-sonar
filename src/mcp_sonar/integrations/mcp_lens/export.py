from __future__ import annotations

import mcp_types as types

from mcp_sonar.interactor.format import tool_definition_to_dict


def tools_to_lens_dicts(tools: list[types.Tool]) -> list[dict]:
    """Convert MCP tool definitions to the dict shape MCP Lens expects."""
    return [tool_definition_to_dict(tool) for tool in tools]
