from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from mcp_sonar.integrations.agentic_eval_flow.aggregate import (
    MCPCheckerReport,
    aggregate_mcpchecker_output,
    render_report_text,
)
from mcp_sonar.integrations.agentic_eval_flow.pack import materialize_eval_workspace, resolve_eval_pack
from mcp_sonar.target import ConnectedTarget


class MCPCheckerNotFoundError(RuntimeError):
    """Raised when the mcpchecker CLI is not on PATH."""


def find_mcpchecker(binary: str | None = None) -> str:
    name = binary or "mcpchecker"
    path = shutil.which(name)
    if not path:
        raise MCPCheckerNotFoundError(
            "mcpchecker CLI not found. Install from https://github.com/mcpchecker/mcpchecker "
            "or set --mcpchecker-bin."
        )
    return path


def _extract_json_blob(raw: str) -> dict:
    match = re.search(r"\{[\s\S]*\}\s*$", raw)
    if not match:
        raise ValueError("mcpchecker output did not contain a JSON object")
    return json.loads(match.group(0))


def run_mcpchecker_cli(
    *,
    workspace: Path,
    mcpchecker_bin: str,
    env: dict[str, str],
    timeout_sec: int = 600,
) -> Path:
    eval_yaml = workspace / "eval.yaml"
    mcp_config = workspace / "mcp-config.yaml"
    if not eval_yaml.is_file():
        raise FileNotFoundError(f"eval.yaml missing in {workspace}")
    if not mcp_config.is_file():
        raise FileNotFoundError(f"mcp-config.yaml missing in {workspace}")

    output_path = workspace / "mcpchecker-out.json"
    cmd = [
        mcpchecker_bin,
        "check",
        str(eval_yaml),
        "--mcp-config-file",
        str(mcp_config),
        "-o",
        "json",
    ]
    completed = subprocess.run(
        cmd,
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    combined = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    if not combined.strip():
        raise RuntimeError(f"mcpchecker produced no output (exit {completed.returncode})")
    try:
        payload = _extract_json_blob(combined)
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            f"mcpchecker exit {completed.returncode}; failed to parse JSON: {exc}\n"
            f"--- output ---\n{combined[:2000]}"
        ) from exc
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def run_eval_for_target(
    target: ConnectedTarget,
    *,
    eval_pack: Path | None,
    mcpchecker_bin: str | None,
    threshold: float,
) -> MCPCheckerReport:
    pack = resolve_eval_pack(eval_pack)
    binary = find_mcpchecker(mcpchecker_bin)
    workspace, env = materialize_eval_workspace(target, pack)
    try:
        output_path = run_mcpchecker_cli(workspace=workspace, mcpchecker_bin=binary, env=env)
        return aggregate_mcpchecker_output(
            output_path,
            submission_name=target.name,
            threshold=threshold,
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def format_eval_result(report: MCPCheckerReport) -> tuple[str, str]:
    summary = (
        f"agentic-mcp: {report.passed_tasks}/{report.total_tasks} tasks, "
        f"score {report.overall_score:.1%}, gate {'PASS' if report.gate_passed else 'FAIL'}"
    )
    return summary, render_report_text(report)
