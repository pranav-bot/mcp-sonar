from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class TimingStats:
    min_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float
    samples: int


@dataclass
class ToolOutcome:
    tool_name: str
    arguments: dict[str, Any]
    is_error: bool
    text: str
    payload_bytes: int
    structured: Any | None = None
    error_message: str | None = None


@dataclass
class ScenarioRunResult:
    scenario_id: str
    target_name: str
    binding: str
    transport_kind: str
    transport_endpoint: str
    transport_label: str
    functional_pass: bool
    functional_message: str
    timing: TimingStats
    success_rate: float
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class SingleTargetReport:
    suite_id: str
    target_name: str
    target_label: str
    binding: str
    transport_kind: str
    transport_endpoint: str
    warmup: int
    iterations: int
    scenarios: list[ScenarioRunResult] = field(default_factory=list)


@dataclass
class CompareScenarioRow:
    scenario_id: str
    left: ScenarioRunResult | None
    right: ScenarioRunResult | None


@dataclass
class CompareReport:
    suite_id: str
    left_target: str
    left_label: str
    left_transport_kind: str
    left_transport_endpoint: str
    right_target: str
    right_label: str
    right_transport_kind: str
    right_transport_endpoint: str
    warmup: int
    iterations: int
    rows: list[CompareScenarioRow] = field(default_factory=list)


ReportFormat = Literal["json", "md", "both"]
