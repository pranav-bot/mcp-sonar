from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from mcp.shared.exceptions import MCPError

from mcp_sonar.integrations.mcp_lens.export import tools_to_lens_dicts
from mcp_sonar.target import ConnectedTarget

_METHOD_NOT_FOUND = -32601


def _unsupported_method(exc: BaseException) -> bool:
    if isinstance(exc, MCPError) and exc.code == _METHOD_NOT_FOUND:
        return True
    text = str(exc).lower().replace(" ", "")
    return "methodnotfound" in text


@dataclass
class CatalogSnapshot:
    server_name: str
    tools: list[dict] = field(default_factory=list)
    prompts: list[dict] = field(default_factory=list)
    resources: list[dict] = field(default_factory=list)

    def tools_json_text(self) -> str:
        return json.dumps(self.tools, indent=2, ensure_ascii=False)

    def prompts_text(self) -> str:
        lines: list[str] = []
        for prompt in self.prompts:
            name = prompt.get("name", "")
            desc = prompt.get("description") or ""
            lines.append(f"{name}: {desc}")
        return "\n".join(lines)

    def resources_text(self) -> str:
        lines: list[str] = []
        for resource in self.resources:
            uri = resource.get("uri", "")
            name = resource.get("name") or ""
            desc = resource.get("description") or ""
            lines.append(f"{uri} {name}: {desc}")
        return "\n".join(lines)


async def _optional_catalog(label: str, fetch: Any) -> list[dict]:
    try:
        return await fetch()
    except Exception as exc:  # noqa: BLE001 — method-not-found is empty; anything else fails the suite
        if _unsupported_method(exc):
            return []
        raise RuntimeError(f"{label} failed: {exc}") from exc


async def fetch_catalog(target: ConnectedTarget) -> CatalogSnapshot:
    tools = tools_to_lens_dicts(await target.list_tool_definitions())

    async def _prompts() -> list[dict]:
        return [
            {"name": prompt.name, "description": prompt.description}
            for prompt in await target.list_prompts()
        ]

    async def _resources() -> list[dict]:
        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
            }
            for resource in await target.list_resources()
        ]

    prompts = await _optional_catalog("list_prompts", _prompts)
    resources = await _optional_catalog("list_resources", _resources)
    return CatalogSnapshot(
        server_name=target.name,
        tools=tools,
        prompts=prompts,
        resources=resources,
    )
