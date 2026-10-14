from __future__ import annotations

from typing import Any

from mcp_sonar.llm.rate_limit import MinuteRateLimiter


class RateLimitedAdapter:
    """Wraps a ModelAdapter and enforces a per-minute call cap before each request."""

    def __init__(self, inner: Any, limiter: MinuteRateLimiter) -> None:
        self._inner = inner
        self._limiter = limiter

    async def select_tool(self, tools: list[dict], user_prompt: str) -> dict:
        await self._limiter.acquire()
        return await self._inner.select_tool(tools, user_prompt)

    async def generate_answer(self, tool_result: Any, user_prompt: str) -> str:
        await self._limiter.acquire()
        return await self._inner.generate_answer(tool_result, user_prompt)
