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


def require_targets_path(path: Path | None) -> Path:
    """Return an existing targets.yaml path or raise FileNotFoundError."""
    config = path or default_targets_path()
    if not config.is_file():
        example = config.parent / "targets.example.yaml"
        raise FileNotFoundError(
            f"Targets file not found: {config}\nCopy {example} to {config} and configure your MCP servers."
        )
    return config


class UnknownTargetError(LookupError):
    """Raised when --target does not match any entry in targets.yaml."""

    def __init__(self, name: str, config: TargetsFile) -> None:
        self.name = name
        self.config = config
        super().__init__(name)

    def format_message(self) -> str:
        from mcp_sonar.transport import transport_info  # noqa: PLC0415

        lines = [
            f"Unknown target '{self.name}'.",
            "",
            "Available targets (use one of these with --target):",
        ]
        if not self.config.targets:
            lines.append("  (none — add entries under `targets:` in targets.yaml)")
        else:
            for target_name, cfg in sorted(self.config.targets.items()):
                info = transport_info(cfg)
                label = cfg.label or target_name
                lines.append(
                    f"  {target_name}  —  {info.kind_label}  —  {label}"
                )
                lines.append(f"      {info.endpoint}")
        lines.append("")
        lines.append("Inspect targets: sonar list-targets --config <path-to-targets.yaml>")
        return "\n".join(lines)


def resolve_target(config: TargetsFile, name: str) -> tuple[str, TargetConfig]:
    if name not in config.targets:
        raise UnknownTargetError(name, config)
    return name, config.targets[name]
