from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

from mcp_benchmarker.config import (
    StdioTransportConfig,
    StreamableHttpTransportConfig,
    TargetConfig,
)
from mcp_benchmarker.tool_result import outcome_from_call, outcome_from_exception
from mcp_benchmarker.core.types import ToolOutcome


@dataclass(frozen=True)
class ConnectedTarget:
    name: str
    config: TargetConfig
    session: ClientSession

    @property
    def binding(self) -> str:
        return self.config.binding

    @property
    def transport_label(self) -> str:
        transport = self.config.transport
        if isinstance(transport, StdioTransportConfig):
            return f"stdio ({transport.command})"
        return f"streamable_http ({transport.url})"

    @property
    def label(self) -> str:
        return self.config.label or self.name

    async def list_tools(self) -> list[str]:
        result = await self.session.list_tools()
        return [tool.name for tool in result.tools]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolOutcome:
        args = arguments or {}
        try:
            result = await self.session.call_tool(name, args)
            return outcome_from_call(name, args, result)
        except Exception as exc:  # noqa: BLE001 — benchmark captures transport errors
            return outcome_from_exception(name, args, exc)


@asynccontextmanager
async def connect_target(name: str, config: TargetConfig) -> AsyncIterator[ConnectedTarget]:
    transport = config.transport
    if isinstance(transport, StdioTransportConfig):
        env = os.environ.copy()
        env.update(config.env)
        params = StdioServerParameters(
            command=transport.command,
            args=transport.args,
            cwd=transport.cwd,
            env=env,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield ConnectedTarget(name=name, config=config, session=session)
        return

    if isinstance(transport, StreamableHttpTransportConfig):
        headers: dict[str, str] = {}
        if config.auth and config.auth.bearer_env:
            token = os.environ.get(config.auth.bearer_env, "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(headers=headers, timeout=120.0) as http_client:
            async with streamable_http_client(transport.url, http_client=http_client) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield ConnectedTarget(name=name, config=config, session=session)
        return

    raise TypeError(f"Unsupported transport: {type(transport)!r}")
