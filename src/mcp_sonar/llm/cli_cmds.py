from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

import httpx

from mcp_sonar.local_bootstrap import load_local_dotenv
from mcp_sonar.llm.config import load_llm_file, resolve_llm_config_path, summarize_configs
from mcp_sonar.llm.registry import get_adapter_for_config


def run_llm_list(config_path: Path | None, fmt: str) -> None:
    load_local_dotenv()
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


def _ssl_connect_hint() -> str:
    return (
        "TLS verify failed. Set MAAS_VERIFY_SSL=false in local/.env, "
        "or point verify_ssl_env at your CA bundle."
    )


def run_llm_models(config_path: Path | None, config_name: str | None) -> None:
    """Call GET /models for a named maas entry in llm.json."""

    load_local_dotenv()
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
        adapter = get_adapter_for_config(str(name), llm_path=config_path)
    except ValueError as err:
        raise click.ClickException(str(err)) from err
    list_fn = getattr(adapter, "list_model_ids", None)
    if not callable(list_fn):
        raise click.ClickException(
            f"Config '{name}' does not use MaaS (no list_model_ids). "
            "Use a maas provider entry."
        )
    import asyncio

    try:
        ids = asyncio.run(list_fn())
    except httpx.ConnectError as err:
        msg = str(err)
        if "CERTIFICATE_VERIFY_FAILED" in msg or "certificate verify" in msg.lower():
            raise click.ClickException(f"{msg}\n\n{_ssl_connect_hint()}") from err
        raise click.ClickException(msg) from err
    except RuntimeError as err:
        raise click.ClickException(str(err)) from err
    click.echo(json.dumps({"config": name, "models": ids}, indent=2))
