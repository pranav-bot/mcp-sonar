from __future__ import annotations

import os
from pathlib import Path

from mcp_sonar.local_bootstrap import bootstrap_local_workspace


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
