from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_VERTEX_VERSION = "vertex-2023-10-16"


def models_corps_family_path(model_id: str) -> str:
    """Map model id to Vertex path segment (sonnet / haiku / opus)."""
    mid = model_id.lower()
    if "haiku" in mid:
        return "haiku"
    if "opus" in mid:
        return "opus"
    return "sonnet"


def models_corps_predict_url(base_url: str, model_id: str, *, stream: bool = False) -> str:
    base = base_url.rstrip("/")
    family = models_corps_family_path(model_id)
    suffix = "streamRawPredict" if stream else "rawPredict"
    return f"{base}/{family}/models/{model_id}:{suffix}"


def _build_tools_for_api(tools: list[dict]) -> list[dict]:
    result: list[dict] = []
    for tool in tools:
        entry: dict[str, Any] = {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
        }
        if "inputSchema" in tool:
            entry["input_schema"] = tool["inputSchema"]
        result.append(entry)
    return result


def _parse_tool_use(payload: dict[str, Any]) -> dict[str, Any]:
    for block in payload.get("content", []):
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            return {
                "tool_name": block.get("name", ""),
                "arguments": block.get("input") or {},
            }
    return {"tool_name": "", "arguments": {}}


def coerce_tls_verify(value: Any) -> bool | str:
    """httpx ``verify``: False, True, or path to a CA bundle."""
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("", "true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
        if Path(value).expanduser().is_file():
            return str(Path(value).expanduser())
    return True


def _parse_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in payload.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


class ModelsCorpsAdapter:
    """Anthropic-on-Vertex style gateway (Bearer auth, rawPredict URLs).

    Inspired by internal models-corps clients; ``base_url`` and API key come from
    config / environment — no hostnames are hardcoded in this module.
    """

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str,
        timeout: float = 120.0,
        verify: bool | str = True,
    ) -> None:
        if not api_key:
            raise ValueError("models-corps provider requires api_key (use api_key_env in llm.json)")
        if not base_url:
            raise ValueError("models-corps provider requires base_url (use base_url_env in llm.json)")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify = coerce_tls_verify(verify)
        logger.debug("ModelsCorpsAdapter model=%s base_url=%s", model, self.base_url)

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        model_id = self.model
        url = models_corps_predict_url(self.base_url, model_id, stream=False)
        request_body = dict(body)
        request_body["anthropic_version"] = ANTHROPIC_VERTEX_VERSION
        request_body.pop("model", None)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self._timeout, verify=self._verify) as client:
            response = await client.post(url, headers=headers, json=request_body)
        if response.status_code == 429:
            raise RuntimeError(
                "models-corps rate limit exceeded (sandbox basic tier is 6 requests/minute)"
            )
        if response.status_code >= 400:
            raise RuntimeError(f"models-corps HTTP {response.status_code}: {response.text[:500]}")
        return response.json()

    async def select_tool(self, tools: list[dict], user_prompt: str) -> dict:
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "tools": _build_tools_for_api(tools),
            "messages": [{"role": "user", "content": user_prompt}],
        }
        payload = await self._post(body)
        return _parse_tool_use(payload)

    async def generate_answer(self, tool_result: Any, user_prompt: str) -> str:
        content = user_prompt
        if tool_result is not None:
            content = f"Based on the tool result: {tool_result}\n\n{user_prompt}"
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": content}],
        }
        payload = await self._post(body)
        text = _parse_text(payload)
        if text:
            return text
        return json.dumps(payload)[:2000]
