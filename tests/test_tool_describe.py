from __future__ import annotations

from mcp_sonar.interactor.tool_describe import _iter_parameter_rows, _type_label


def test_type_label_enum_and_nullable() -> None:
    assert _type_label({"type": "string", "enum": ["query", "mutation"]}) == "enum: query | mutation"
    assert _type_label({"anyOf": [{"type": "string"}, {"type": "null"}]}) == "string | null"


def test_iter_parameter_rows_flattens_nested_object() -> None:
    schema = {
        "type": "object",
        "properties": {
            "root": {"type": "string", "default": "query", "enum": ["query"]},
            "scope": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "kind": {"type": "string", "enum": ["type", "root_field"]},
                            "name": {"type": "string"},
                        },
                        "required": ["kind"],
                    },
                    {"type": "null"},
                ],
                "default": None,
            },
        },
    }
    rows = list(_iter_parameter_rows(schema))
    names = [r[0] for r in rows]
    assert "root" in names
    assert "scope" in names
    assert "scope.kind" in names
    assert "scope.name" in names
    kind_row = next(r for r in rows if r[0] == "scope.kind")
    assert kind_row[1] == "enum: type | root_field"
    assert kind_row[2] == "yes"
