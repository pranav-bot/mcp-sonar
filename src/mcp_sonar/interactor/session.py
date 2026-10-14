from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import click

from mcp_sonar.config import load_targets, require_targets_path, resolve_target
from mcp_sonar.target import ConnectedTarget, connect_target


@asynccontextmanager
async def open_target(
    target: str,
    config_path: Path | None,
) -> AsyncIterator[tuple[str, ConnectedTarget]]:
    config_file = require_targets_path(config_path)
    targets = load_targets(config_file)
    target_name, target_cfg = resolve_target(targets, target)
    async with connect_target(target_name, target_cfg) as connected:
        yield target_name, connected


def parse_tool_args(args_json: str) -> dict:
    try:
        arguments = json.loads(args_json)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid --args JSON: {exc}") from exc
    if not isinstance(arguments, dict):
        raise click.ClickException("--args must be a JSON object")
    return arguments
