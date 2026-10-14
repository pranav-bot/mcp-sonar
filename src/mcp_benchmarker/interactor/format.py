from __future__ import annotations

import json
from typing import Any

import mcp_types as types
from rich.console import Console
from rich.table import Table

console = Console()


def _truncate(text: str, max_len: int = 100) -> str:
    one_line = text.replace("\n", " ")
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 3] + "..."


def _tool_input_schema(tool: types.Tool) -> dict[str, Any] | None:
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)
    return schema


def _tool_output_schema(tool: types.Tool) -> dict[str, Any] | None:
    schema = getattr(tool, "output_schema", None)
    if schema is None:
        schema = getattr(tool, "outputSchema", None)
    return schema


def tool_definition_to_dict(tool: types.Tool) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description,
    }
    input_schema = _tool_input_schema(tool)
    if input_schema is not None:
        data["inputSchema"] = input_schema
    output_schema = _tool_output_schema(tool)
    if output_schema is not None:
        data["outputSchema"] = output_schema
    return data


def tools_as_json(tools: list[types.Tool]) -> str:
    return json.dumps([tool_definition_to_dict(t) for t in tools], indent=2)


def print_tools_table(tools: list[types.Tool], *, title: str = "MCP tools") -> None:
    table = Table(title=title)
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for tool in tools:
        description = _truncate(tool.description or "")
        table.add_row(tool.name, description)
    console.print(table)


def print_resources_table(resources: list[types.Resource], *, title: str = "MCP resources") -> None:
    table = Table(title=title)
    table.add_column("URI", style="cyan")
    table.add_column("Name")
    table.add_column("Description")
    for resource in resources:
        table.add_row(
            resource.uri,
            resource.name or "",
            _truncate(resource.description or ""),
        )
    console.print(table)


def print_prompts_table(prompts: list[types.Prompt], *, title: str = "MCP prompts") -> None:
    table = Table(title=title)
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for prompt in prompts:
        table.add_row(prompt.name, _truncate(prompt.description or ""))
    console.print(table)


def server_info_dict(init: types.InitializeResult) -> dict[str, Any]:
    info: dict[str, Any] = {}
    server = getattr(init, "server_info", None) or getattr(init, "serverInfo", None)
    if server is not None:
        info["serverInfo"] = {
            "name": server.name,
            "version": server.version,
        }
    if init.instructions:
        info["instructions"] = init.instructions
    if init.capabilities is not None:
        info["capabilities"] = init.capabilities.model_dump(mode="json", exclude_none=True)
    return info


def print_server_info(connected: object) -> None:
    from mcp_benchmarker.target import ConnectedTarget  # noqa: PLC0415

    if not isinstance(connected, ConnectedTarget):
        raise TypeError("expected ConnectedTarget")
    init = connected.init_result
    if init is None:
        raise ValueError("missing initialize result")
    payload = server_info_dict(init)
    payload["target"] = {
        "name": connected.name,
        "label": connected.label,
        "transport": connected.transport.kind,
        "transportLabel": connected.transport.kind_label,
        "endpoint": connected.transport.endpoint,
    }
    console.print_json(data=payload)
