from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mcp_sonar.config import (
    StdioTransportConfig,
    StreamableHttpTransportConfig,
    TargetConfig,
)

TransportKind = Literal["stdio", "streamable_http"]

# User-facing labels (always use these in CLI and reports).
KIND_LABEL: dict[TransportKind, str] = {
    "stdio": "stdio",
    "streamable_http": "streamable HTTP",
}


@dataclass(frozen=True)
class TransportInfo:
    """How we reach an MCP server for a configured target."""

    kind: TransportKind
    endpoint: str

    @property
    def kind_label(self) -> str:
        return KIND_LABEL[self.kind]

    def summary(self) -> str:
        """Single line: transport kind plus connection detail."""
        return f"{self.kind_label} — {self.endpoint}"

    def tag(self) -> str:
        """Bracketed kind for compact headers."""
        return f"[{self.kind_label}]"


def transport_info(config: TargetConfig) -> TransportInfo:
    transport = config.transport
    if isinstance(transport, StdioTransportConfig):
        parts = [transport.command, *transport.args]
        endpoint = " ".join(parts)
        if transport.cwd:
            endpoint = f"{endpoint}  (cwd={transport.cwd})"
        return TransportInfo(kind="stdio", endpoint=endpoint)
    if isinstance(transport, StreamableHttpTransportConfig):
        return TransportInfo(kind="streamable_http", endpoint=transport.url)
    raise TypeError(f"Unsupported transport config: {type(transport)!r}")


def stdio_command_line(transport: StdioTransportConfig) -> str:
    return " ".join([transport.command, *transport.args])
