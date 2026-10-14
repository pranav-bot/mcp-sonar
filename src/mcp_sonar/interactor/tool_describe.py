from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import mcp_types as types
from rich.console import Console
from rich.table import Table

from mcp_sonar.interactor.format import _tool_input_schema, _tool_output_schema

_console = Console()


def _format_default(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _type_label(schema: dict[str, Any]) -> str:
    if "enum" in schema:
        return "enum: " + " | ".join(str(v) for v in schema["enum"])
    if schema.get("type") == "array":
        items = schema.get("items") or {}
        inner = _type_label(items) if isinstance(items, dict) else "any"
        return f"array[{inner}]"
    if "anyOf" in schema:
        parts: list[str] = []
        nullable = False
        for variant in schema["anyOf"]:
            if not isinstance(variant, dict):
                continue
            if variant.get("type") == "null":
                nullable = True
                continue
            parts.append(_type_label(variant))
        label = " | ".join(parts) if parts else "any"
        if nullable:
            label = f"{label} | null" if label else "null"
        return label
    if "properties" in schema:
        return "object"
    return str(schema.get("type", "any"))


def _primary_object_schema(schema: dict[str, Any]) -> dict[str, Any] | None:
    if schema.get("type") == "object" or "properties" in schema:
        return schema
    for variant in schema.get("anyOf", []):
        if isinstance(variant, dict) and (
            variant.get("type") == "object" or "properties" in variant
        ):
            return variant
    return None


def _iter_parameter_rows(
    schema: dict[str, Any],
    *,
    prefix: str = "",
) -> Iterator[tuple[str, str, str, str, str]]:
    properties = schema.get("properties") or {}
    if not isinstance(properties, dict):
        return
    required = set(schema.get("required") or [])
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        full_name = f"{prefix}{name}" if prefix else name
        type_label = _type_label(prop)
        req = "yes" if name in required else ""
        default = ""
        if "default" in prop:
            default = _format_default(prop["default"])
        description = (prop.get("description") or "").strip()
        yield full_name, type_label, req, default, description

        nested = _primary_object_schema(prop)
        if nested and nested.get("properties"):
            nested_schema = {
                "properties": nested["properties"],
                "required": nested.get("required") or [],
            }
            for row in _iter_parameter_rows(nested_schema, prefix=f"{full_name}."):
                yield row


def print_tool_description(tool: types.Tool) -> None:
    """Human-readable tool name, description, and flattened parameters."""
    _console.print(f"[bold cyan]{tool.name}[/bold cyan]\n")

    description = (tool.description or "").strip()
    if description:
        _console.print("[bold]Description[/bold]")
        _console.print(description)
        _console.print()

    input_schema = _tool_input_schema(tool)
    if input_schema:
        rows = list(_iter_parameter_rows(input_schema))
        if rows:
            _console.print("[bold]Parameters[/bold]")
            table = Table(show_header=True, header_style="bold", expand=True)
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="dim")
            table.add_column("Req.", justify="center", width=4)
            table.add_column("Default", style="dim")
            table.add_column("Description", overflow="fold", max_width=72)
            for name, type_label, req, default, desc in rows:
                table.add_row(name, type_label, req, default, desc.replace("\n", " "))
            _console.print(table)
            _console.print()

    output_schema = _tool_output_schema(tool)
    if output_schema:
        out_type = _type_label(output_schema)
        extra = ""
        if output_schema.get("additionalProperties"):
            extra = " (additional properties allowed)"
        _console.print(f"[bold]Returns[/bold]  {out_type}{extra}")
