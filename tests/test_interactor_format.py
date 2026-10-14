from __future__ import annotations

import json

import mcp_types as types

from mcp_benchmarker.interactor.format import tool_definition_to_dict, tools_as_json


def test_tool_definition_to_dict_includes_schema() -> None:
    tool = types.Tool(
        name="echo",
        description="Echo a message",
        input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
    )
    data = tool_definition_to_dict(tool)
    assert data["name"] == "echo"
    assert data["description"] == "Echo a message"
    assert data["inputSchema"]["properties"]["message"]["type"] == "string"


def test_tools_as_json_round_trip() -> None:
    tools = [
        types.Tool(name="a", description="first", input_schema={"type": "object"}),
        types.Tool(name="b", description="second", input_schema={}),
    ]
    parsed = json.loads(tools_as_json(tools))
    assert len(parsed) == 2
    assert parsed[0]["name"] == "a"
