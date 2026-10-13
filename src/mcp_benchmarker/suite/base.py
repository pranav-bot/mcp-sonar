from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from mcp_benchmarker.core.types import ToolOutcome

FunctionalCheck = Callable[[ToolOutcome], tuple[bool, str]]
BindingFactory = Callable[[], tuple[str, dict[str, Any]]]


@dataclass(frozen=True)
class ScenarioStep:
    id: str
    description: str
    bindings: dict[str, BindingFactory]
    check: FunctionalCheck
    skip_for_bindings: frozenset[str] = frozenset()


@dataclass
class Suite(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def steps(self) -> list[ScenarioStep]:
        raise NotImplementedError

    def supported_bindings(self) -> set[str]:
        bindings: set[str] = set()
        for step in self.steps():
            bindings.update(step.bindings)
        return bindings


@dataclass
class ResolvedStep:
    step: ScenarioStep
    tool_name: str
    arguments: dict[str, Any]
    skipped: bool = False
    skip_reason: str | None = None


def resolve_step(step: ScenarioStep, binding: str) -> ResolvedStep:
    if binding in step.skip_for_bindings:
        return ResolvedStep(
            step=step,
            tool_name="",
            arguments={},
            skipped=True,
            skip_reason=f"not applicable for binding {binding}",
        )
    if binding not in step.bindings:
        return ResolvedStep(
            step=step,
            tool_name="",
            arguments={},
            skipped=True,
            skip_reason=f"no binding '{binding}' in scenario",
        )
    tool_name, arguments = step.bindings[binding]()
    return ResolvedStep(step=step, tool_name=tool_name, arguments=arguments)
