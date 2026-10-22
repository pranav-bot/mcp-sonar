from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_dotenv_file(path: Path, *, override: bool = False) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip().strip('"').strip("'")
        if not override and key in os.environ:
            continue
        os.environ[key] = value


def load_local_dotenv(*, override: bool = False) -> None:
    """Load gitignored ``local/.env`` into the process environment."""
    _load_dotenv_file(Path.cwd() / "local" / ".env", override=override)


def _jwt_expired(token: str, leeway_sec: int = 120) -> bool:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        exp = data.get("exp")
        if not isinstance(exp, (int, float)):
            return True
        return float(exp) <= time.time() + leeway_sec
    except (IndexError, json.JSONDecodeError, ValueError):
        return True


def _local_has_oauth_credentials(env_path: Path) -> bool:
    if not env_path.is_file():
        return False
    keys: set[str] = set()
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.partition("=")[0].strip().lower().replace("-", "_")
        keys.add(key)
    id_ok = bool(keys & {"client_id", "oauth_client_id", "mcp_oauth_client_id"})
    secret_ok = bool(keys & {"client_secret", "oauth_client_secret", "mcp_oauth_client_secret"})
    return id_ok and secret_ok


def ensure_local_bearer_token() -> None:
    """Refresh ``MCP_SONAR_BEARER_TOKEN`` via gitignored ``local/fetch_token.py`` when needed."""
    root = Path.cwd()
    env_path = root / "local" / ".env"
    script = root / "local" / "fetch_token.py"
    if not script.is_file() or not _local_has_oauth_credentials(env_path):
        return

    load_local_dotenv()
    token = os.environ.get("MCP_SONAR_BEARER_TOKEN", "").strip()
    if token and not _jwt_expired(token):
        return

    try:
        subprocess.run(
            [sys.executable, str(script), "--write-sonar"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.warning("local/fetch_token.py failed: %s", (exc.stderr or exc.stdout or "").strip())
        return
    load_local_dotenv(override=True)


def bootstrap_local_workspace(targets_config: Path | None = None) -> None:
    """Load gitignored ``local/.env`` and default LLM config for ``local/targets.yaml``."""
    load_local_dotenv()
    ensure_local_bearer_token()
    root = Path.cwd()

    if targets_config is not None:
        try:
            resolved = targets_config.expanduser().resolve()
        except OSError:
            resolved = targets_config.expanduser()
        if resolved.name == "targets.yaml" and resolved.parent.name == "local":
            llm_path = root / "local" / "llm.json"
            if llm_path.is_file():
                os.environ.setdefault("MCP_SONAR_LLM_CONFIG", str(llm_path))
