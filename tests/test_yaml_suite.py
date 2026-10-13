from __future__ import annotations

from pathlib import Path

from mcp_benchmarker.suite.yaml_suite import suite_from_yaml


def test_load_everything_smoke_suite() -> None:
    path = Path(__file__).resolve().parents[1] / "config" / "suites" / "everything-smoke.yaml"
    suite = suite_from_yaml(path)
    assert suite.id == "everything-smoke"
    assert len(suite.steps()) == 2
    assert suite.steps()[1].id == "echo_roundtrip"
