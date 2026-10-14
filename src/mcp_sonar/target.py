from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
import mcp_types as types
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

from mcp_sonar.config import (
    StdioTransportConfig,
    StreamableHttpTransportConfig,
    TargetConfig,
)
from mcp_sonar.core.types import ToolOutcome
from mcp_sonar.tool_result import outcome_from_call, outcome_from_exception
from mcp_sonar.transport import TransportInfo, transport_info


@dataclass(frozen=True)
class ConnectedTarget:
    name: str
    config: TargetConfig
    session: ClientSession
    transport: TransportInfo
    init_result: types.InitializeResult | None = None

    @property
    def binding(self) -> str:
        return self.config.binding

    @property
    def label(self) -> str:
        return self.config.label or self.name

    @property
    def transport_kind(self) -> str:
        return self.transport.kind

    @property
    def transport_label(self) -> str:
        """Legacy single-line transport description (used in scenario results)."""
        return self.transport.summary()

    async def list_tools(self) -> list[str]:
        result = await self.session.list_tools()
        return [tool.name for tool in result.tools]

    async def list_tool_definitions(self) -> list[types.Tool]:
        result = await self.session.list_tools()
        return list(result.tools)

    async def list_resources(self) -> list[types.Resource]:
        result = await self.session.list_resources()
        return list(result.resources)

    async def list_prompts(self) -> list[types.Prompt]:
        result = await self.session.list_prompts()
        return list(result.prompts)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> ToolOutcome:
        args = arguments or {}
        try:
            result = await self.session.call_tool(name, args)
            return outcome_from_call(name, args, result)
        except Exception as exc:  # noqa: BLE001 — benchmark captures transport errors
            return outcome_from_exception(name, args, exc)


@asynccontextmanager
async def _connected_session(
    name: str,
    config: TargetConfig,
    read_stream: Any,
    write_stream: Any,
) -> AsyncIterator[ConnectedTarget]:
    info = transport_info(config)
    async with ClientSession(read_stream, write_stream) as session:
        init_result = await session.initialize()
        yield ConnectedTarget(
            name=name,
            config=config,
            session=session,
            transport=info,
            init_result=init_result,
        )


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
            async with _connected_session(name, config, read_stream, write_stream) as connected:
                yield connected
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
            ):
                async with _connected_session(name, config, read_stream, write_stream) as connected:
                    yield connected
        return

    raise TypeError(f"Unsupported transport: {type(transport)!r}")
