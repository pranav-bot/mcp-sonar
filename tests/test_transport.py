from __future__ import annotations

import click
import httpx
import pytest

from mcp_sonar.config import AuthConfig, StdioTransportConfig, StreamableHttpTransportConfig, TargetConfig
from mcp_sonar.target import _HTTP_TIMEOUT, connect_target
from mcp_sonar.transport import transport_info


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


def test_http_read_timeout_allows_a_slow_tool() -> None:
    assert _HTTP_TIMEOUT.read == 600.0
    assert _HTTP_TIMEOUT.connect == 30.0


@pytest.mark.asyncio
async def test_missing_bearer_env_stops_before_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEFINITELY_UNSET_SONAR_TOKEN", raising=False)
    cfg = TargetConfig(
        transport=StreamableHttpTransportConfig(url="http://127.0.0.1:9/mcp"),
        auth=AuthConfig(bearer_env="DEFINITELY_UNSET_SONAR_TOKEN"),
    )
    with pytest.raises(click.ClickException, match="DEFINITELY_UNSET_SONAR_TOKEN"):
        async with connect_target("t", cfg):
            pass


@pytest.mark.asyncio
async def test_http_client_uses_long_read_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class _Client:
        def __init__(self, **kwargs: object) -> None:
            seen["timeout"] = kwargs.get("timeout")

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_args: object) -> bool:
            return False

    monkeypatch.setenv("SONAR_TEST_BEARER", "token")
    monkeypatch.setattr("mcp_sonar.target.httpx.AsyncClient", _Client)

    class _Stream:
        async def __aenter__(self):
            raise RuntimeError("stop after client init")

        async def __aexit__(self, *_args: object) -> bool:
            return False

    monkeypatch.setattr("mcp_sonar.target.streamable_http_client", lambda *_a, **_k: _Stream())
    cfg = TargetConfig(
        transport=StreamableHttpTransportConfig(url="http://127.0.0.1:9/mcp"),
        auth=AuthConfig(bearer_env="SONAR_TEST_BEARER"),
    )
    with pytest.raises(RuntimeError, match="stop after client init"):
        async with connect_target("t", cfg):
            pass
    timeout = seen["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read == 600.0


@pytest.mark.asyncio
async def test_http_connect_failure_is_one_line(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Client:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_args: object) -> bool:
            return False

    class _Stream:
        async def __aenter__(self):
            raise BaseExceptionGroup(
                "unhandled errors in a TaskGroup",
                [httpx.ConnectError("All connection attempts failed")],
            )

        async def __aexit__(self, *_args: object) -> bool:
            return False

    monkeypatch.setattr("mcp_sonar.target.httpx.AsyncClient", _Client)
    monkeypatch.setattr("mcp_sonar.target.streamable_http_client", lambda *_a, **_k: _Stream())
    cfg = TargetConfig(transport=StreamableHttpTransportConfig(url="http://127.0.0.1:9/mcp"))
    with pytest.raises(click.ClickException, match="All connection attempts failed"):
        async with connect_target("t", cfg):
            pass
