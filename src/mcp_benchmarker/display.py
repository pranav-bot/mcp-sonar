from __future__ import annotations

from rich.console import Console
from rich.table import Table

from mcp_benchmarker.config import TargetConfig, TargetsFile
from mcp_benchmarker.target import ConnectedTarget
from mcp_benchmarker.transport import TransportInfo, transport_info

_stderr_console = Console(stderr=True)
_stdout_console = Console()


def _kind_style(kind: str) -> str:
    if kind == "stdio":
        return "bold cyan"
    return "bold magenta"


def format_target_heading(name: str, label: str, transport: TransportInfo) -> str:
    return (
        f"Target [bold]{name}[/bold]"
        f" ({label})"
        f"  [{_kind_style(transport.kind)}]{transport.kind_label}[/]"
        f"  [dim]{transport.endpoint}[/dim]"
    )


def print_connected_target(connected: ConnectedTarget) -> None:
    """Announce which MCP server is in use (stderr so stdout stays pipe-friendly)."""
    heading = format_target_heading(connected.name, connected.label, connected.transport)
    _stderr_console.print(heading)


def print_targets_table(targets: TargetsFile) -> None:
    table = Table(title="MCP targets")
    table.add_column("Name", style="bold")
    table.add_column("Label")
    table.add_column("Transport")
    table.add_column("Endpoint")
    table.add_column("Binding")
    for name, cfg in sorted(targets.targets.items()):
        info = transport_info(cfg)
        table.add_row(
            name,
            cfg.label or name,
            f"[{_kind_style(info.kind)}]{info.kind_label}[/]",
            info.endpoint,
            cfg.binding,
        )
    _stdout_console.print(table)


def print_benchmark_target_header(
    target_name: str,
    label: str,
    transport: TransportInfo,
    *,
    binding: str,
    suite_id: str,
) -> None:
    _stdout_console.print(
        f"\n[bold]Suite[/bold] {suite_id}  "
        + format_target_heading(target_name, label, transport)
        + f"  [dim]binding={binding}[/dim]"
    )


def print_compare_targets_header(
    suite_id: str,
    left_name: str,
    left_label: str,
    left_transport: TransportInfo,
    right_name: str,
    right_label: str,
    right_transport: TransportInfo,
) -> None:
    _stdout_console.print(f"\n[bold]Suite[/bold] {suite_id}")
    _stdout_console.print(
        "  [bold]Left[/bold]  "
        + format_target_heading(left_name, left_label, left_transport)
    )
    _stdout_console.print(
        "  [bold]Right[/bold] "
        + format_target_heading(right_name, right_label, right_transport)
    )
    if left_transport.kind != right_transport.kind:
        _stdout_console.print(
            "[yellow]Note:[/yellow] comparing different transports "
            f"({left_transport.kind_label} vs {right_transport.kind_label})."
        )


def target_config_label(name: str, config: TargetConfig) -> str:
    return config.label or name
