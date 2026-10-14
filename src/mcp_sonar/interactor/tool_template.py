from __future__ import annotations

from typing import Any

import mcp_types as types
import yaml

from mcp_sonar.interactor.format import _tool_input_schema
from mcp_sonar.interactor.tool_describe import _iter_parameter_rows, _primary_object_schema


def _default_for_property(prop: dict[str, Any]) -> Any:
    if "default" in prop:
        return prop["default"]
    if "anyOf" in prop:
        if any(isinstance(v, dict) and v.get("type") == "null" for v in prop["anyOf"]):
            return None
    prop_type = prop.get("type")
    if prop_type == "object" or "properties" in prop:
        nested = _primary_object_schema(prop)
        if nested and nested.get("properties"):
            return _defaults_from_properties(
                nested["properties"],
                set(nested.get("required") or []),
            )
        return {}
    if prop_type == "array":
        return []
    if prop_type == "boolean":
        return False
    if prop_type in ("integer", "number"):
        return 0
    if prop_type == "string":
        return ""
    return None


def _defaults_from_properties(
    properties: dict[str, Any],
    _required: set[str],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, prop in properties.items():
        if isinstance(prop, dict):
            out[name] = _default_for_property(prop)
    return out


def defaults_from_input_schema(schema: dict[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {}
    properties = schema.get("properties") or {}
    if not isinstance(properties, dict):
        return {}
    required = set(schema.get("required") or [])
    return _defaults_from_properties(properties, required)


def render_invoke_template(
    tool: types.Tool,
    *,
    target: str | None = None,
) -> str:
    """YAML form: field types in comments, editable arguments block."""
    schema = _tool_input_schema(tool)
    arguments = defaults_from_input_schema(schema)

    lines = [
        "# mcp-sonar tool input form (edit arguments, then run without an LLM):",
        f"#   sonar tools invoke --args-file <this-file> --config config/targets.yaml",
        f"# or: sonar tools call --args-file <this-file> --target <name>",
        "#",
        f"# Tool: {tool.name}",
    ]
    description = (tool.description or "").strip()
    if description:
        first = description.split("\n", 1)[0]
        lines.append(f"# {first[:200]}")
    lines.append("#")
    lines.append("# Fields (type | required | default):")
    if schema:
        for name, type_label, req, default, desc in _iter_parameter_rows(schema):
            req_mark = "required" if req else "optional"
            default_part = f", default={default}" if default else ""
            hint = f" — {desc[:80]}" if desc else ""
            lines.append(f"#   {name}: {type_label} ({req_mark}{default_part}){hint}")
    lines.append("")

    body: dict[str, Any] = {"tool": tool.name, "arguments": arguments}
    if target:
        body["target"] = target
    lines.append(
        yaml.safe_dump(body, sort_keys=False, default_flow_style=False).rstrip()
    )
    return "\n".join(lines) + "\n"


def render_batch_example(tool_name: str, *, target: str | None = None) -> str:
    doc: dict[str, Any] = {
        "calls": [
            {"tool": tool_name, "arguments": {}},
            {"tool": tool_name, "arguments": {}},
        ]
    }
    if target:
        doc["target"] = target
    header = (
        "# mcp-sonar batch tool calls — list many argument objects under calls:\n"
        "#   sonar tools batch --file <this-file> --config config/targets.yaml\n\n"
    )
    return header + yaml.safe_dump(doc, sort_keys=False, default_flow_style=False)
