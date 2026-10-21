from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mcp_sonar.llm.config import load_llm_file, resolve_llm_config_path, summarize_configs
from mcp_sonar.llm.registry import get_adapter_for_config


def run_llm_list(config_path: Path | None, fmt: str) -> None:
    data = load_llm_file(config_path)
    path = config_path or resolve_llm_config_path()
    if data is None:
        raise click.ClickException(
            "No llm.json found. Set MCP_SONAR_LLM_CONFIG, use ./llm.json, "
            "or copy config/llm.example.json to config/llm.json."
        )
    default = data.get("default")
    rows = summarize_configs(data)

    if fmt == "json":
        click.echo(
            json.dumps(
                {"path": data.get("path"), "default": default, "configs": rows},
                indent=2,
            )
        )
        return

    console = Console()
    console.print(f"LLM config: [bold]{data.get('path')}[/bold]  default=[cyan]{default}[/cyan]")
    table = Table(title="LLM providers")
    table.add_column("Name")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Credentials")
    table.add_column("Rate limit")
    for row in rows:
        rate = row.get("rate_limit_per_minute")
        rate_cell = f"{rate}/min" if rate else "-"
        table.add_row(
            row["name"],
            row["provider"],
            str(row.get("model") or ""),
            "yes" if row.get("has_credentials") else "no",
            rate_cell,
        )
    console.print(table)


def run_llm_models(config_path: Path | None, config_name: str | None) -> None:
    """Call MaaS GET /models for a named llm.json entry (maas or models-corps)."""

    data = load_llm_file(config_path)
    if data is None:
        raise click.ClickException(
            "No llm.json found. Set MCP_SONAR_LLM_CONFIG, use ./llm.json, "
            "or copy config/llm.example.json to config/llm.json."
        )
    name = config_name or data.get("default")
    if not name:
        raise click.ClickException("No config name: pass --name or set default in llm.json")
    try:
        adapter = get_adapter_for_config(str(name))
    except ValueError as err:
        raise click.ClickException(str(err)) from err
    list_fn = getattr(adapter, "list_model_ids", None)
    if not callable(list_fn):
        raise click.ClickException(
            f"Config '{name}' does not use MaaS (no list_model_ids). "
            "Use a maas or models-corps provider entry."
        )
    import asyncio

    try:
        ids = asyncio.run(list_fn())
    except RuntimeError as err:
        raise click.ClickException(str(err)) from err
    click.echo(json.dumps({"config": name, "models": ids}, indent=2))
