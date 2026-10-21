from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_ENV_SUFFIX = "_env"


def resolve_llm_config_path(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None
    env_path = os.environ.get("MCP_SONAR_LLM_CONFIG", "").strip()
    if env_path:
        path = Path(env_path).expanduser()
        return path if path.is_file() else None
    for candidate in (Path.cwd() / "llm.json", Path.cwd() / "config" / "llm.json"):
        if candidate.is_file():
            return candidate
    return None


def _resolve_config_values(cfg: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for key, value in cfg.items():
        if key.endswith(_ENV_SUFFIX) and isinstance(value, str):
            base_key = key[: -len(_ENV_SUFFIX)]
            env_val = os.environ.get(value, "").strip()
            resolved[base_key] = env_val or None
        else:
            resolved[key] = value
    return resolved


def load_llm_file(path: Path | None = None) -> dict[str, Any] | None:
    config_path = path or resolve_llm_config_path()
    if config_path is None:
        return None
    with config_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    configs = data.get("configs", {})
    if not isinstance(configs, dict):
        raise ValueError("llm.json: 'configs' must be an object")
    resolved_configs: dict[str, dict[str, Any]] = {}
    for name, cfg in configs.items():
        if not isinstance(cfg, dict):
            raise ValueError(f"llm.json: config '{name}' must be an object")
        resolved_configs[name] = _resolve_config_values(cfg)
    return {
        "path": str(config_path.resolve()),
        "default": data.get("default"),
        "configs": resolved_configs,
    }


def get_default_config_name(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    default = data.get("default")
    return str(default) if default else None


def summarize_configs(data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not data:
        return []
    rows: list[dict[str, Any]] = []
    for name, cfg in sorted(data.get("configs", {}).items()):
        provider = str(cfg.get("provider", ""))
        has_creds = bool(
            cfg.get("api_key")
            or cfg.get("project")
            or (provider == "models-corps" and cfg.get("base_url") and cfg.get("api_key"))
        )
        rows.append(
            {
                "name": name,
                "provider": provider,
                "model": cfg.get("model", ""),
                "has_credentials": has_creds,
                "rate_limit_per_minute": cfg.get("rate_limit_per_minute"),
            }
        )
    return rows
