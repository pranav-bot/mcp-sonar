from __future__ import annotations

import json
from typing import Any

from mcp_sonar.core.types import ToolOutcome


def check_not_error(outcome: ToolOutcome, **_kwargs: Any) -> tuple[bool, str]:
    if outcome.is_error:
        return False, outcome.text[:200]
    return True, "ok"


def check_expect_error(outcome: ToolOutcome, **_kwargs: Any) -> tuple[bool, str]:
    if outcome.is_error:
        return True, "error as expected"
    return False, "expected failure but call succeeded"


def check_list_tools_nonempty(outcome: ToolOutcome, **_kwargs: Any) -> tuple[bool, str]:
    if outcome.is_error:
        return False, outcome.text[:200]
    lines = [line.strip() for line in outcome.text.splitlines() if line.strip()]
    if lines:
        return True, f"{len(lines)} tools"
    return False, "empty tool list"


def check_contains_text(outcome: ToolOutcome, *, text: str, **_kwargs: Any) -> tuple[bool, str]:
    if outcome.is_error:
        return False, outcome.text[:200] or "tool error"
    if text.lower() in outcome.text.lower():
        return True, f"found '{text}'"
    return False, f"'{text}' not in response"


def _check_structured_gate(outcome: ToolOutcome) -> tuple[bool, str]:
    if outcome.is_error:
        return False, outcome.error_message or outcome.text[:200]
    structured = outcome.structured if isinstance(outcome.structured, dict) else None
    if structured and "summary" in structured:
        return bool(structured.get("gate_passed")), str(structured["summary"])
    if structured and "gate_passed" in structured:
        score = structured.get("overall_score", 0)
        passed = bool(structured["gate_passed"])
        return passed, f"score {score:.1f} gate {'pass' if passed else 'FAIL'}"
    return check_not_error(outcome)


def check_lens_gate(outcome: ToolOutcome, **_kwargs: Any) -> tuple[bool, str]:
    return _check_structured_gate(outcome)


def check_eval_flow_gate(outcome: ToolOutcome, **_kwargs: Any) -> tuple[bool, str]:
    return _check_structured_gate(outcome)


def check_load_gate(outcome: ToolOutcome, **_kwargs: Any) -> tuple[bool, str]:
    return _check_structured_gate(outcome)


def check_context_gate(outcome: ToolOutcome, **_kwargs: Any) -> tuple[bool, str]:
    return _check_structured_gate(outcome)


def check_json_path_exists(outcome: ToolOutcome, *, path: str, **_kwargs: Any) -> tuple[bool, str]:
    data = _parse_json(outcome.text)
    if data is None and isinstance(outcome.structured, (dict, list)):
        data = outcome.structured
    if data is None:
        return False, "response is not JSON"
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False, f"path missing: {path}"
    return True, f"path ok: {path}"


def _parse_json(text: str) -> Any | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


CHECKS: dict[str, Any] = {
    "not_error": check_not_error,
    "expect_error": check_expect_error,
    "list_tools_nonempty": check_list_tools_nonempty,
    "contains_text": check_contains_text,
    "json_path_exists": check_json_path_exists,
}


def get_check(name: str) -> Any:
    if name not in CHECKS:
        known = ", ".join(sorted(CHECKS))
        raise KeyError(f"Unknown check '{name}'. Known: {known}")
    return CHECKS[name]
