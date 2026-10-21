from __future__ import annotations

import os
from pathlib import Path


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


def load_local_dotenv() -> None:
    """Load gitignored ``local/.env`` into the process environment (no override)."""
    _load_dotenv_file(Path.cwd() / "local" / ".env")


def bootstrap_local_workspace(targets_config: Path | None = None) -> None:
    """Load gitignored ``local/.env`` and default LLM config for ``local/targets.yaml``."""
    load_local_dotenv()
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
