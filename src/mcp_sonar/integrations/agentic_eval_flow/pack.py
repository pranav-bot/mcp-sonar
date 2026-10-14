from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import yaml

from mcp_sonar.config import StreamableHttpTransportConfig
from mcp_sonar.target import ConnectedTarget


def default_eval_pack_path() -> Path:
    return Path(__file__).resolve().parents[4] / "config" / "eval-flow" / "default"


def resolve_eval_pack(path: Path | None) -> Path:
    if path is not None:
        pack = path.expanduser().resolve()
        if not pack.is_dir():
            raise FileNotFoundError(f"Eval pack not found: {pack}")
        return pack
    default = default_eval_pack_path()
    if default.is_dir():
        return default
    raise FileNotFoundError(
        "No eval pack directory. Use --eval-pack or add config/eval-flow/default."
    )


def mcp_endpoint_from_target(target: ConnectedTarget) -> tuple[str, str | None]:
    transport = target.config.transport
    if not isinstance(transport, StreamableHttpTransportConfig):
        raise ValueError(
            f"Target '{target.name}' uses {getattr(transport, 'type', transport)}; "
            "agentic-mcp suite requires streamable_http (MCPChecker needs MCP_URL)."
        )
    token: str | None = None
    if target.config.auth and target.config.auth.bearer_env:
        token = os.environ.get(target.config.auth.bearer_env, "").strip() or None
    return transport.url, token


def write_mcp_config(path: Path, *, server_name: str, url: str, bearer_token: str | None) -> None:
    entry: dict = {"name": server_name, "url": url}
    if bearer_token:
        entry["auth"] = {"type": "bearer", "token": bearer_token}
    doc = {"mcpServers": [entry]}
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def materialize_eval_workspace(
    target: ConnectedTarget,
    eval_pack: Path,
) -> tuple[Path, dict[str, str]]:
    """Copy eval pack and inject mcp-config.yaml; return workspace path and subprocess env."""
    url, token = mcp_endpoint_from_target(target)
    workspace = Path(tempfile.mkdtemp(prefix="sonar-mcpchecker-"))
    shutil.copytree(eval_pack, workspace, dirs_exist_ok=True)
    write_mcp_config(workspace / "mcp-config.yaml", server_name=target.name, url=url, bearer_token=token)
    env = os.environ.copy()
    env["MCP_URL"] = url
    if token:
        env["MCP_BEARER_TOKEN"] = token
    return workspace, env
