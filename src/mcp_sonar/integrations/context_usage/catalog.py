from __future__ import annotations

import json
from dataclasses import dataclass, field

from mcp_sonar.integrations.mcp_lens.export import tools_to_lens_dicts
from mcp_sonar.target import ConnectedTarget


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


async def fetch_catalog(target: ConnectedTarget) -> CatalogSnapshot:
    tools = tools_to_lens_dicts(await target.list_tool_definitions())
    prompts: list[dict] = []
    resources: list[dict] = []
    try:
        for prompt in await target.list_prompts():
            prompts.append(
                {
                    "name": prompt.name,
                    "description": prompt.description,
                }
            )
    except Exception:
        pass
    try:
        for resource in await target.list_resources():
            resources.append(
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description,
                }
            )
    except Exception:
        pass
    return CatalogSnapshot(
        server_name=target.name,
        tools=tools,
        prompts=prompts,
        resources=resources,
    )
