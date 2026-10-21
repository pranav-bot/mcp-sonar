from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAAS_PROVIDER = "maas"
# Sandbox tier default (per model, per minute). Override in llm.json.
MAAS_DEFAULT_RATE_LIMIT = 10


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


def maas_chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def maas_models_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/models"


def mcp_tools_to_openai(tools: list[dict]) -> list[dict[str, Any]]:
    openai_tools: list[dict[str, Any]] = []
    for tool in tools:
        schema = tool.get("inputSchema")
        if not isinstance(schema, dict):
            schema = {"type": "object", "properties": {}}
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description") or "",
                    "parameters": schema,
                },
            }
        )
    return openai_tools


def _parse_tool_call(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return {"tool_name": "", "arguments": {}}
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    if not isinstance(message, dict):
        return {"tool_name": "", "arguments": {}}
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or not tool_calls:
        return {"tool_name": "", "arguments": {}}
    first = tool_calls[0] if isinstance(tool_calls[0], dict) else {}
    function = first.get("function") if isinstance(first.get("function"), dict) else {}
    name = str(function.get("name") or "").strip()
    raw_args = function.get("arguments", "{}")
    if isinstance(raw_args, dict):
        arguments = raw_args
    else:
        try:
            arguments = json.loads(str(raw_args) or "{}")
        except json.JSONDecodeError:
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    return {"tool_name": name, "arguments": arguments}


def _parse_assistant_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else {}
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return str(content) if content is not None else ""


class MaasAdapter:
    """Models.corp MaaS — OpenAI-compatible ``/v1/chat/completions`` (Bearer auth).

    Configure ``base_url`` (e.g. ``https://…/oai/v1``) and API key via ``llm.json``
    ``*_env`` fields. List models with :meth:`list_model_ids`.
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
            raise ValueError("maas provider requires api_key (use api_key_env in llm.json)")
        if not base_url:
            raise ValueError("maas provider requires base_url (use base_url_env in llm.json)")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._verify = coerce_tls_verify(verify)
        logger.debug("MaasAdapter model=%s base_url=%s", model, self.base_url)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, url: str, *, json_body: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout, verify=self._verify) as client:
            response = await client.request(method, url, headers=self._headers(), json=json_body)
        if response.status_code == 429:
            raise RuntimeError(
                "MaaS rate limit exceeded (HTTP 429). Sandbox tier is typically 10 requests/minute "
                "per model — back off and retry."
            )
        if response.status_code >= 400:
            raise RuntimeError(f"MaaS HTTP {response.status_code}: {response.text[:500]}")
        return response.json()

    async def list_model_ids(self) -> list[str]:
        payload = await self._request("GET", maas_models_url(self.base_url))
        data = payload.get("data")
        if not isinstance(data, list):
            return []
        ids: list[str] = []
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
        return sorted(ids)

    async def _chat(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", maas_chat_completions_url(self.base_url), json_body=body)

    async def select_tool(self, tools: list[dict], user_prompt: str) -> dict:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 2048,
        }
        if tools:
            body["tools"] = mcp_tools_to_openai(tools)
            body["tool_choice"] = "auto"
        payload = await self._chat(body)
        return _parse_tool_call(payload)

    async def generate_answer(self, tool_result: Any, user_prompt: str) -> str:
        content = user_prompt
        if tool_result is not None:
            content = f"Based on the tool result: {tool_result}\n\n{user_prompt}"
        body = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": content}],
        }
        payload = await self._chat(body)
        text = _parse_assistant_text(payload)
        if text:
            return text
        return json.dumps(payload)[:2000]
