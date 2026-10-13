from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mcp_benchmarker.checks import get_check
from mcp_benchmarker.suite.base import ScenarioStep, Suite


def _call_factory(tool: str, arguments: dict[str, Any]) -> Any:
    frozen_args = dict(arguments)

    def factory() -> tuple[str, dict[str, Any]]:
        return tool, frozen_args

    return factory


def _build_check(spec: Any) -> Any:
    if spec is None:
        return get_check("not_error")
    if isinstance(spec, str):
        return get_check(spec)
    if isinstance(spec, dict):
        name = spec.get("name")
        if not isinstance(name, str):
            raise ValueError("check.name must be a string")
        fn = get_check(name)
        args = spec.get("args") or {}

        def wrapped(outcome: Any) -> tuple[bool, str]:
            return fn(outcome, **args)

        return wrapped
    raise ValueError(f"Invalid check spec: {spec!r}")


class YamlSuite(Suite):
    def __init__(self, suite_id: str, description: str, steps_list: list[ScenarioStep]) -> None:
        self._id = suite_id
        self._description = description
        self._steps = steps_list

    @property
    def id(self) -> str:
        return self._id

    @property
    def description(self) -> str:
        return self._description

    def steps(self) -> list[ScenarioStep]:
        return self._steps


def suite_from_yaml(path: Path) -> YamlSuite:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid suite file: {path}")

    suite_id = raw.get("id")
    if not isinstance(suite_id, str) or not suite_id:
        raise ValueError(f"Suite file {path} must have a non-empty 'id'")

    description = raw.get("description")
    if not isinstance(description, str):
        description = f"Suite loaded from {path.name}"

    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError(f"Suite {suite_id} must have a 'scenarios' list")

    steps: list[ScenarioStep] = []
    for index, item in enumerate(scenarios):
        if not isinstance(item, dict):
            raise ValueError(f"Scenario {index} in {path} must be a mapping")
        step_id = item.get("id")
        if not isinstance(step_id, str) or not step_id:
            raise ValueError(f"Scenario {index} missing 'id'")
        step_desc = item.get("description")
        if not isinstance(step_desc, str):
            step_desc = step_id

        calls = item.get("calls")
        if not isinstance(calls, dict):
            raise ValueError(f"Scenario {step_id} must have 'calls' mapping (binding -> tool)")

        bindings: dict[str, Any] = {}
        for binding_name, call in calls.items():
            if not isinstance(call, dict):
                raise ValueError(f"Scenario {step_id} call for {binding_name} must be a mapping")
            tool = call.get("tool")
            if not isinstance(tool, str):
                raise ValueError(f"Scenario {step_id} missing tool for binding {binding_name}")
            arguments = call.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError(f"Scenario {step_id} arguments must be a mapping")
            bindings[str(binding_name)] = _call_factory(tool, arguments)

        skip_for = item.get("skip_for_bindings") or []
        if not isinstance(skip_for, list):
            raise ValueError(f"Scenario {step_id} skip_for_bindings must be a list")

        steps.append(
            ScenarioStep(
                id=step_id,
                description=step_desc,
                bindings=bindings,
                check=_build_check(item.get("check")),
                skip_for_bindings=frozenset(str(s) for s in skip_for),
            )
        )

    return YamlSuite(suite_id, description, steps)
