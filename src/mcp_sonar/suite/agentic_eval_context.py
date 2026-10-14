from __future__ import annotations

import contextvars
from pathlib import Path

_eval_pack: contextvars.ContextVar[Path | None] = contextvars.ContextVar("eval_pack", default=None)
_mcpchecker_bin: contextvars.ContextVar[str | None] = contextvars.ContextVar("mcpchecker_bin", default=None)
_eval_threshold: contextvars.ContextVar[float] = contextvars.ContextVar("eval_threshold", default=0.7)


class EvalFlowSettingsToken:
    def __init__(
        self,
        pack: contextvars.Token[Path | None],
        bin_token: contextvars.Token[str | None],
        threshold_token: contextvars.Token[float],
    ) -> None:
        self.pack = pack
        self.bin_token = bin_token
        self.threshold_token = threshold_token


def set_eval_flow_settings(
    *,
    eval_pack: Path | None,
    mcpchecker_bin: str | None,
    threshold: float,
) -> EvalFlowSettingsToken:
    return EvalFlowSettingsToken(
        _eval_pack.set(eval_pack),
        _mcpchecker_bin.set(mcpchecker_bin),
        _eval_threshold.set(threshold),
    )


def get_eval_pack() -> Path | None:
    return _eval_pack.get()


def get_mcpchecker_bin() -> str | None:
    return _mcpchecker_bin.get()


def get_eval_threshold() -> float:
    return _eval_threshold.get()


def reset_eval_flow_settings(token: EvalFlowSettingsToken) -> None:
    _eval_pack.reset(token.pack)
    _mcpchecker_bin.reset(token.bin_token)
    _eval_threshold.reset(token.threshold_token)
