from __future__ import annotations

from pathlib import Path

import pytest

from mcp_sonar.interactor.args_file import (
    load_batch_file,
    load_invoke_file,
    load_prompt_batch,
    resolve_invoke,
)
from mcp_sonar.interactor.tool_template import defaults_from_input_schema, render_invoke_template
import mcp_types as types


def test_load_invoke_file(tmp_path: Path) -> None:
    path = tmp_path / "call.yaml"
    path.write_text(
        "tool: echo\n"
        "target: my-tgt\n"
        "arguments:\n"
        "  message: hi\n",
        encoding="utf-8",
    )
    spec = load_invoke_file(path)
    assert spec.tool == "echo"
    assert spec.target == "my-tgt"
    assert spec.arguments == {"message": "hi"}


def test_resolve_invoke_cli_overrides_file(tmp_path: Path) -> None:
    path = tmp_path / "call.yaml"
    path.write_text("tool: echo\narguments:\n  message: from-file\n", encoding="utf-8")
    tool, target, args = resolve_invoke(
        tool_cli="other",
        target_cli="cli-target",
        args_json='{"extra": 1}',
        args_file=path,
    )
    assert tool == "other"
    assert target == "cli-target"
    assert args == {"message": "from-file", "extra": 1}


def test_load_batch_file(tmp_path: Path) -> None:
    path = tmp_path / "batch.yaml"
    path.write_text(
        "target: local-http\n"
        "calls:\n"
        "  - tool: a\n"
        "    arguments: {}\n"
        "  - tool: b\n"
        "    target: other\n"
        "    arguments:\n"
        "      x: 1\n",
        encoding="utf-8",
    )
    batch = load_batch_file(path)
    assert batch.target == "local-http"
    assert len(batch.calls) == 2
    assert batch.calls[1].target == "other"
    assert batch.calls[1].arguments == {"x": 1}


def test_load_prompt_batch(tmp_path: Path) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text(
        "target: everything-stdio\n"
        "prompts:\n"
        "  - Say hello\n"
        "  - Say goodbye\n",
        encoding="utf-8",
    )
    batch = load_prompt_batch(path)
    assert batch.target == "everything-stdio"
    assert batch.prompts == ["Say hello", "Say goodbye"]


def test_load_prompt_batch_rejects_empty_list(tmp_path: Path) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text("prompts: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty list"):
        load_prompt_batch(path)


def test_load_prompt_batch_rejects_non_string(tmp_path: Path) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text(
        "prompts:\n  - Which open incidents mention the payments API: this week?\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="quoted string"):
        load_prompt_batch(path)


def test_load_prompt_batch_keeps_quoted_sentence(tmp_path: Path) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text(
        'prompts:\n  - "Which open incidents mention the payments API: this week?"\n',
        encoding="utf-8",
    )
    batch = load_prompt_batch(path)
    assert batch.prompts == ["Which open incidents mention the payments API: this week?"]


def test_load_prompt_batch_rejects_blank_string(tmp_path: Path) -> None:
    path = tmp_path / "prompts.yaml"
    path.write_text('prompts:\n  - ""\n', encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty string"):
        load_prompt_batch(path)


def test_render_invoke_template_includes_arguments() -> None:
    tool = types.Tool(
        name="echo",
        description="Echo back",
        input_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "default": "hello"},
            },
        },
    )
    text = render_invoke_template(tool, target="t1")
    assert "tool: echo" in text
    assert "target: t1" in text
    assert "message:" in text
    assert "#   message: string" in text


def test_defaults_from_schema_nullable() -> None:
    schema = {
        "type": "object",
        "properties": {
            "scope": {"anyOf": [{"type": "object"}, {"type": "null"}], "default": None},
            "limit": {"type": "integer", "default": 40},
        },
    }
    args = defaults_from_input_schema(schema)
    assert args["scope"] is None
    assert args["limit"] == 40


def test_resolve_invoke_requires_tool() -> None:
    with pytest.raises(ValueError, match="Tool name required"):
        resolve_invoke(tool_cli=None, target_cli="t", args_json=None, args_file=None)
