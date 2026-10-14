from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mcp_sonar.llm.config import load_llm_file, resolve_llm_config_path, summarize_configs


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
