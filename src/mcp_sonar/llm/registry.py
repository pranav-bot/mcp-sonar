from __future__ import annotations

import os
from typing import Any

from mcp_sonar.llm.adapters.maas import MAAS_PROVIDER, MAAS_SANDBOX_RATE_LIMIT, MaasAdapter, coerce_tls_verify
from mcp_sonar.llm.adapters.rate_limited import RateLimitedAdapter
from mcp_sonar.llm.config import get_default_config_name, load_llm_file, resolve_llm_config_path
from mcp_sonar.llm.rate_limit import MinuteRateLimiter

MODELS_CORPS_PROVIDER = "models-corps"
# Alias for ``maas``. Sandbox reference limit (10 req/min) — set rate_limit_per_minute per account tier.
MODELS_CORPS_SANDBOX_RATE_LIMIT = MAAS_SANDBOX_RATE_LIMIT

_LENS_PROVIDERS = frozenset({"mock", "anthropic", "openai", "vertexai", "anthropic-vertex"})

_INSTALL_HINTS = {
    "openai": "uv sync --extra llm-openai",
    "anthropic": "uv sync --extra llm-anthropic",
    "vertexai": "uv sync --extra llm-vertex",
    "anthropic-vertex": "uv sync --extra llm-anthropic-vertex",
    MAAS_PROVIDER: "uses httpx; set MAAS_BASE_URL and MAAS_API_KEY (see config/llm.example.json)",
    MODELS_CORPS_PROVIDER: "alias for maas — prefer provider maas and MAAS_* env vars",
}


def load_llm_configs(path: Any = None) -> dict[str, dict] | None:
    from pathlib import Path

    explicit = Path(path) if path is not None else None
    data = load_llm_file(explicit)
    if not data:
        return None
    return data.get("configs")


def get_default_llm_name() -> str | None:
    return get_default_config_name(load_llm_file())


def _resolve_maas_verify(cfg: dict[str, Any]) -> bool | str:
    verify = cfg.get("verify_ssl")
    if verify is not None:
        return coerce_tls_verify(verify)
    ca_bundle = cfg.get("ca_bundle")
    if ca_bundle:
        return coerce_tls_verify(ca_bundle)
    for env_name in ("MAAS_VERIFY_SSL", "MODELS_CORPS_VERIFY_SSL"):
        raw = os.environ.get(env_name, "").strip()
        if raw:
            return coerce_tls_verify(raw)
    return True


def _maas_credentials(cfg: dict[str, Any]) -> tuple[str, str]:
    api_key = str(cfg.get("api_key") or os.environ.get("MAAS_API_KEY") or "")
    base_url = str(cfg.get("base_url") or os.environ.get("MAAS_BASE_URL") or "")
    if not api_key:
        api_key = str(os.environ.get("MODELS_CORPS_API_KEY") or "")
    if not base_url:
        base_url = str(os.environ.get("MODELS_CORPS_BASE_URL") or "")
    return api_key, base_url


def build_maas_adapter(cfg: dict[str, Any]) -> MaasAdapter:
    api_key, base_url = _maas_credentials(cfg)
    adapter = MaasAdapter(
        model=str(cfg.get("model") or "Qwen3-14B"),
        api_key=api_key,
        base_url=base_url,
        verify=_resolve_maas_verify(cfg),
    )
    raw_limit = cfg.get("rate_limit_per_minute")
    if raw_limit is None:
        return adapter
    per_minute = int(raw_limit)
    if per_minute <= 0:
        return adapter
    limiter = MinuteRateLimiter(per_minute)
    return RateLimitedAdapter(adapter, limiter)  # type: ignore[return-value]


def get_adapter_for_config(config_name: str, llm_path: Any = None) -> Any:
    from pathlib import Path

    explicit = Path(llm_path) if llm_path is not None else None
    data = load_llm_file(explicit)
    configs = data.get("configs") if data else None
    if not configs or config_name not in configs:
        known = ", ".join(sorted(configs or []))
        path = resolve_llm_config_path()
        hint = f" (from {path})" if path else " (no llm.json found)"
        raise ValueError(f"Unknown LLM config '{config_name}'{hint}. Known: {known}")
    cfg = configs[config_name]
    return build_adapter(cfg)


def build_adapter(cfg: dict[str, Any]) -> Any:
    provider = str(cfg.get("provider", "")).strip()
    if provider in (MAAS_PROVIDER, MODELS_CORPS_PROVIDER):
        return build_maas_adapter(cfg)

    if provider in _LENS_PROVIDERS:
        try:
            from src.app.eval.model_adapter import get_adapter  # noqa: PLC0415
        except ImportError as err:
            hint = _INSTALL_HINTS.get(provider, "install the provider SDK")
            raise ImportError(
                f"MCP Lens is required for provider '{provider}'. {hint}"
            ) from err
        try:
            return get_adapter(
                name=provider,
                model=cfg.get("model"),
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url"),
                project=cfg.get("project"),
                location=cfg.get("location"),
            )
        except ImportError as err:
            hint = _INSTALL_HINTS.get(provider, "")
            raise ImportError(f"Missing dependency for '{provider}'. {hint}") from err

    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        f"Supported: {', '.join(sorted(_LENS_PROVIDERS | {MAAS_PROVIDER, MODELS_CORPS_PROVIDER}))}"
    )
