from __future__ import annotations

import contextvars

from mcp_sonar.integrations.mcp_lens.evaluate import LensMode

_lens_mode: contextvars.ContextVar[LensMode] = contextvars.ContextVar("lens_mode", default="both")


def set_lens_mode(mode: LensMode) -> contextvars.Token[LensMode]:
    return _lens_mode.set(mode)


def get_lens_mode() -> LensMode:
    return _lens_mode.get()


def reset_lens_mode(token: contextvars.Token[LensMode]) -> None:
    _lens_mode.reset(token)
