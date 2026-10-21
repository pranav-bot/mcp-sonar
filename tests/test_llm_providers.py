from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_sonar.llm.adapters.models_corps import (
    coerce_tls_verify,
    models_corps_family_path,
    models_corps_predict_url,
)
from mcp_sonar.llm.config import load_llm_file
from mcp_sonar.llm.rate_limit import MinuteRateLimiter
from mcp_sonar.llm.registry import MODELS_CORPS_DEFAULT_RATE_LIMIT, build_adapter


def test_models_corps_family_path() -> None:
    assert models_corps_family_path("claude-3-5-haiku-20241022") == "haiku"
    assert models_corps_family_path("claude-opus-4-20250514") == "opus"
    assert models_corps_family_path("claude-sonnet-4-20250514") == "sonnet"


def test_coerce_tls_verify() -> None:
    assert coerce_tls_verify(False) is False
    assert coerce_tls_verify("false") is False
    assert coerce_tls_verify("true") is True
    assert coerce_tls_verify(None) is True


def test_models_corps_predict_url() -> None:
    url = models_corps_predict_url("https://gateway.example", "claude-sonnet-4-20250514")
    assert url == "https://gateway.example/sonnet/models/claude-sonnet-4-20250514:rawPredict"


@pytest.mark.asyncio
async def test_minute_rate_limiter_waits_for_slot() -> None:
    import time

    limiter = MinuteRateLimiter(1, window_seconds=0.05)
    await limiter.acquire()
    start = time.monotonic()
    await limiter.acquire()
    assert time.monotonic() - start >= 0.04


def test_load_llm_file_resolves_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_KEY", "secret")
    path = tmp_path / "llm.json"
    path.write_text(
        json.dumps(
            {
                "default": "corp",
                "configs": {
                    "corp": {
                        "provider": "models-corps",
                        "model": "claude-sonnet-4-20250514",
                        "api_key_env": "TEST_LLM_KEY",
                        "base_url": "https://gateway.example",
                        "rate_limit_per_minute": 6,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    data = load_llm_file(path)
    assert data is not None
    cfg = data["configs"]["corp"]
    assert cfg["api_key"] == "secret"
    assert cfg["rate_limit_per_minute"] == 6


def test_build_adapter_models_corps_wraps_rate_limit() -> None:
    adapter = build_adapter(
        {
            "provider": "models-corps",
            "model": "claude-sonnet-4-20250514",
            "api_key": "k",
            "base_url": "https://gateway.example",
        }
    )
    from mcp_sonar.llm.adapters.rate_limited import RateLimitedAdapter

    assert isinstance(adapter, RateLimitedAdapter)


def test_build_adapter_models_corps_default_rate_limit() -> None:
    assert MODELS_CORPS_DEFAULT_RATE_LIMIT == 6


def test_build_adapter_requires_base_url() -> None:
    with pytest.raises(ValueError, match="base_url"):
        build_adapter(
            {
                "provider": "models-corps",
                "model": "m",
                "api_key": "k",
            }
        )
