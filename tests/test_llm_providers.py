from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_sonar.llm.adapters.maas import (
    coerce_tls_verify,
    maas_chat_completions_url,
    maas_models_url,
    mcp_tools_to_openai,
)
from mcp_sonar.llm.config import load_llm_file
from mcp_sonar.llm.rate_limit import MinuteRateLimiter
from mcp_sonar.llm.registry import (
    MAAS_DEFAULT_RATE_LIMIT,
    MODELS_CORPS_DEFAULT_RATE_LIMIT,
    _resolve_maas_verify,
    build_adapter,
)


def test_maas_urls() -> None:
    base = "https://models.corp.redhat.com/oai/v1"
    assert maas_models_url(base) == "https://models.corp.redhat.com/oai/v1/models"
    assert (
        maas_chat_completions_url(base)
        == "https://models.corp.redhat.com/oai/v1/chat/completions"
    )


def test_mcp_tools_to_openai() -> None:
    tools = [{"name": "ping", "description": "Ping", "inputSchema": {"type": "object"}}]
    out = mcp_tools_to_openai(tools)
    assert out[0]["type"] == "function"
    assert out[0]["function"]["name"] == "ping"


def test_resolve_maas_verify_legacy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAAS_VERIFY_SSL", raising=False)
    monkeypatch.setenv("MODELS_CORPS_VERIFY_SSL", "false")
    assert _resolve_maas_verify({}) is False


def test_coerce_tls_verify() -> None:
    assert coerce_tls_verify(False) is False
    assert coerce_tls_verify("false") is False
    assert coerce_tls_verify("true") is True
    assert coerce_tls_verify(None) is True


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
    monkeypatch.setenv("TEST_MAAS_URL", "https://models.corp.redhat.com/oai/v1")
    path = tmp_path / "llm.json"
    path.write_text(
        json.dumps(
            {
                "default": "corp",
                "configs": {
                    "corp": {
                        "provider": "maas",
                        "model": "Qwen3-14B",
                        "api_key_env": "TEST_LLM_KEY",
                        "base_url_env": "TEST_MAAS_URL",
                        "rate_limit_per_minute": 10,
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
    assert cfg["base_url"] == "https://models.corp.redhat.com/oai/v1"
    assert cfg["rate_limit_per_minute"] == 10


def test_build_adapter_maas_wraps_rate_limit() -> None:
    adapter = build_adapter(
        {
            "provider": "maas",
            "model": "Qwen3-14B",
            "api_key": "k",
            "base_url": "https://models.corp.redhat.com/oai/v1",
        }
    )
    from mcp_sonar.llm.adapters.rate_limited import RateLimitedAdapter

    assert isinstance(adapter, RateLimitedAdapter)


def test_build_adapter_models_corps_alias() -> None:
    adapter = build_adapter(
        {
            "provider": "models-corps",
            "model": "Qwen3-14B",
            "api_key": "k",
            "base_url": "https://models.corp.redhat.com/oai/v1",
        }
    )
    from mcp_sonar.llm.adapters.rate_limited import RateLimitedAdapter

    assert isinstance(adapter, RateLimitedAdapter)


def test_maas_default_rate_limit_sandbox() -> None:
    assert MAAS_DEFAULT_RATE_LIMIT == 10
    assert MODELS_CORPS_DEFAULT_RATE_LIMIT == 10


def test_build_adapter_requires_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAAS_BASE_URL", raising=False)
    monkeypatch.delenv("MODELS_CORPS_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="base_url"):
        build_adapter(
            {
                "provider": "maas",
                "model": "m",
                "api_key": "k",
            }
        )
