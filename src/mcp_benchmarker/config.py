from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, Field

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return os.environ.get(key, "")

    return _ENV_PATTERN.sub(repl, value)


def _expand_env_tree(data: Any) -> Any:
    if isinstance(data, str):
        return _expand_env(data)
    if isinstance(data, dict):
        return {k: _expand_env_tree(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_expand_env_tree(item) for item in data]
    return data


class StdioTransportConfig(BaseModel):
    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    cwd: str | None = None


class StreamableHttpTransportConfig(BaseModel):
    type: Literal["streamable_http"] = "streamable_http"
    url: str


class AuthConfig(BaseModel):
    bearer_env: str | None = None


TransportConfig = Annotated[
    StdioTransportConfig | StreamableHttpTransportConfig,
    Field(discriminator="type"),
]


class TargetConfig(BaseModel):
    label: str | None = None
    binding: str = "default"
    transport: TransportConfig
    auth: AuthConfig | None = None
    env: dict[str, str] = Field(default_factory=dict)


class TargetsFile(BaseModel):
    targets: dict[str, TargetConfig]


def load_targets(path: Path) -> TargetsFile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid targets file: {path}")
    expanded = _expand_env_tree(raw)
    return TargetsFile.model_validate(expanded)


def default_targets_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "targets.yaml"


def resolve_target(config: TargetsFile, name: str) -> tuple[str, TargetConfig]:
    if name not in config.targets:
        known = ", ".join(sorted(config.targets))
        raise KeyError(f"Unknown target '{name}'. Known: {known}")
    return name, config.targets[name]
