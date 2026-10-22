from __future__ import annotations

import os
from pathlib import Path

from mcp_sonar.local_bootstrap import _jwt_expired, bootstrap_local_workspace


def test_bootstrap_local_targets_sets_llm_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    local = tmp_path / "local"
    local.mkdir()
    (local / ".env").write_text("MODELS_CORPS_VERIFY_SSL=false\n", encoding="utf-8")
    (local / "llm.json").write_text("{}", encoding="utf-8")
    targets = local / "targets.yaml"
    targets.write_text("targets: {}\n", encoding="utf-8")
    monkeypatch.delenv("MCP_SONAR_LLM_CONFIG", raising=False)
    bootstrap_local_workspace(targets)
    assert os.environ.get("MCP_SONAR_LLM_CONFIG") == str(local / "llm.json")
    assert os.environ.get("MODELS_CORPS_VERIFY_SSL") == "false"


def test_jwt_expired_future_token() -> None:
    import base64
    import json

    payload = base64.urlsafe_b64encode(json.dumps({"exp": 9_999_999_999}).encode()).decode().rstrip("=")
    token = f"hdr.{payload}.sig"
    assert _jwt_expired(token) is False


def test_jwt_expired_past_token() -> None:
    assert _jwt_expired("a.b.c") is True
