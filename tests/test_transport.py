from __future__ import annotations

from mcp_benchmarker.config import StdioTransportConfig, StreamableHttpTransportConfig, TargetConfig
from mcp_benchmarker.transport import transport_info


def test_transport_info_stdio() -> None:
    cfg = TargetConfig(
        transport=StdioTransportConfig(command="npx", args=["-y", "pkg"]),
    )
    info = transport_info(cfg)
    assert info.kind == "stdio"
    assert info.kind_label == "stdio"
    assert "npx" in info.endpoint
    assert info.summary().startswith("stdio —")


def test_transport_info_streamable_http() -> None:
    cfg = TargetConfig(
        transport=StreamableHttpTransportConfig(url="http://127.0.0.1:3000/mcp"),
    )
    info = transport_info(cfg)
    assert info.kind == "streamable_http"
    assert info.kind_label == "streamable HTTP"
    assert info.endpoint == "http://127.0.0.1:3000/mcp"
