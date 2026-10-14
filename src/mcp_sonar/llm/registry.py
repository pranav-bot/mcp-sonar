from __future__ import annotations

from typing import Any

from mcp_sonar.llm.adapters.models_corps import ModelsCorpsAdapter
from mcp_sonar.llm.adapters.rate_limited import RateLimitedAdapter
from mcp_sonar.llm.config import get_default_config_name, load_llm_file, resolve_llm_config_path
from mcp_sonar.llm.rate_limit import MinuteRateLimiter

MODELS_CORPS_PROVIDER = "models-corps"
MODELS_CORPS_DEFAULT_RATE_LIMIT = 6

_LENS_PROVIDERS = frozenset({"mock", "anthropic", "openai", "vertexai", "anthropic-vertex"})

_INSTALL_HINTS = {
    "openai": "uv sync --extra llm-openai",
    "anthropic": "uv sync --extra llm-anthropic",
    "vertexai": "uv sync --extra llm-vertex",
    "anthropic-vertex": "uv sync --extra llm-anthropic-vertex",
    MODELS_CORPS_PROVIDER: "uses httpx (already installed); set base_url_env and api_key_env",
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


def get_adapter_for_config(config_name: str) -> Any:
    data = load_llm_file()
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
    if provider == MODELS_CORPS_PROVIDER:
        adapter = ModelsCorpsAdapter(
            model=str(cfg.get("model") or "claude-sonnet-4-20250514"),
            api_key=str(cfg.get("api_key") or ""),
            base_url=str(cfg.get("base_url") or ""),
        )
        per_minute = int(cfg.get("rate_limit_per_minute", MODELS_CORPS_DEFAULT_RATE_LIMIT))
        limiter = MinuteRateLimiter(per_minute)
        return RateLimitedAdapter(adapter, limiter)

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
        f"Supported: {', '.join(sorted(_LENS_PROVIDERS | {MODELS_CORPS_PROVIDER}))}"
    )
