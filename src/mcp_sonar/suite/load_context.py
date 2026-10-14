from __future__ import annotations

import contextvars
import json
from typing import Any

_load_concurrency: contextvars.ContextVar[int] = contextvars.ContextVar("load_concurrency", default=10)
_load_tool: contextvars.ContextVar[str] = contextvars.ContextVar("load_tool", default="__list_tools__")
_load_arguments: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("load_arguments", default={})
_load_min_success_rate: contextvars.ContextVar[float] = contextvars.ContextVar("load_min_success_rate", default=0.95)


class LoadSettingsToken:
    def __init__(
        self,
        concurrency: contextvars.Token[int],
        tool: contextvars.Token[str],
        arguments: contextvars.Token[dict[str, Any]],
        min_rate: contextvars.Token[float],
    ) -> None:
        self.concurrency = concurrency
        self.tool = tool
        self.arguments = arguments
        self.min_rate = min_rate


def set_load_settings(
    *,
    concurrency: int,
    tool: str,
    arguments: dict[str, Any] | None,
    min_success_rate: float,
) -> LoadSettingsToken:
    return LoadSettingsToken(
        _load_concurrency.set(max(1, concurrency)),
        _load_tool.set(tool),
        _load_arguments.set(dict(arguments or {})),
        _load_min_success_rate.set(min_success_rate),
    )


def get_load_concurrency() -> int:
    return _load_concurrency.get()


def get_load_tool() -> str:
    return _load_tool.get()


def get_load_arguments() -> dict[str, Any]:
    return dict(_load_arguments.get())


def get_load_min_success_rate() -> float:
    return _load_min_success_rate.get()


def reset_load_settings(token: LoadSettingsToken) -> None:
    _load_concurrency.reset(token.concurrency)
    _load_tool.reset(token.tool)
    _load_arguments.reset(token.arguments)
    _load_min_success_rate.reset(token.min_rate)


def parse_load_args_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--load-args must be a JSON object")
    return data
