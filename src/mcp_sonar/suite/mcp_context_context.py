from __future__ import annotations

import contextvars

from mcp_sonar.integrations.context_usage.evaluate import ContextMode

_context_mode: contextvars.ContextVar[ContextMode] = contextvars.ContextVar("context_mode", default="both")
_token_budget: contextvars.ContextVar[int] = contextvars.ContextVar("token_budget", default=0)
_min_llm_score: contextvars.ContextVar[float] = contextvars.ContextVar("min_llm_score", default=70.0)


class ContextSettingsToken:
    def __init__(
        self,
        mode: contextvars.Token[ContextMode],
        budget: contextvars.Token[int],
        min_score: contextvars.Token[float],
    ) -> None:
        self.mode = mode
        self.budget = budget
        self.min_score = min_score


def set_context_settings(
    *,
    mode: ContextMode,
    token_budget: int,
    min_llm_score: float,
) -> ContextSettingsToken:
    return ContextSettingsToken(
        _context_mode.set(mode),
        _token_budget.set(max(0, token_budget)),
        _min_llm_score.set(min_llm_score),
    )


def get_context_mode() -> ContextMode:
    return _context_mode.get()


def get_token_budget() -> int:
    return _token_budget.get()


def get_min_llm_score() -> float:
    return _min_llm_score.get()


def reset_context_settings(token: ContextSettingsToken) -> None:
    _context_mode.reset(token.mode)
    _token_budget.reset(token.budget)
    _min_llm_score.reset(token.min_score)
