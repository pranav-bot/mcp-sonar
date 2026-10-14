from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

LensMode = Literal["static", "llm", "both"]


class LensNotInstalledError(ImportError):
    """Raised when the optional mcp-lens package is not installed."""


def mcp_lens_available() -> bool:
    try:
        import src.app.eval.cli  # noqa: F401, PLC0415
    except ImportError:
        return False
    return True


def _require_lens() -> None:
    if not mcp_lens_available():
        raise LensNotInstalledError(
            "MCP Lens is not installed. Install with:\n"
            "  uv sync --extra mcp-lens\n"
            "See https://github.com/devninja-in/mcp-lens"
        )


@dataclass(frozen=True)
class LensEvalResult:
    mode: LensMode
    gate_passed: bool
    overall_score: float
    summary: str
    report_text: str
    metadata: dict[str, Any]


def _build_static_layers(tools: list[dict]) -> dict:
    from src.app.eval.overlap import detect_overlaps  # noqa: PLC0415
    from src.app.eval.protocol import check_protocol_all  # noqa: PLC0415
    from src.app.eval.quality import check_quality_all  # noqa: PLC0415
    from src.app.eval.security import check_security_all  # noqa: PLC0415

    layers = {
        "protocol": check_protocol_all(tools),
        "quality": check_quality_all(tools),
        "security": check_security_all(tools),
    }
    overlaps = detect_overlaps(tools)
    if overlaps:
        layers["quality"].catalog_checks.extend(overlaps)
    return layers


async def _build_llm_layer(tools: list[dict]) -> tuple[object | None, dict[str, Any]]:
    from src.app.eval.llm_config import (  # noqa: PLC0415
        get_adapter_for_config,
        get_default_llm_name,
        load_llm_configs,
    )
    from src.app.eval.llm_eval import check_llm_all  # noqa: PLC0415

    meta: dict[str, Any] = {}
    default_name = get_default_llm_name()
    configs = load_llm_configs()
    if not configs or not default_name:
        raise RuntimeError(
            "LLM evaluation requires llm.json with a default provider "
            "(see MCP Lens docs: https://github.com/devninja-in/mcp-lens)"
        )
    cfg = configs.get(default_name, {})
    adapter = get_adapter_for_config(default_name)
    llm_layer = await check_llm_all(tools, adapter)
    meta = {
        "llm_provider": cfg.get("provider", default_name),
        "llm_model": cfg.get("model") or "default",
    }
    return llm_layer, meta


def evaluate_tools(
    tools: list[dict],
    *,
    server_name: str,
    mode: LensMode,
) -> LensEvalResult:
    """Run MCP Lens static and/or LLM evaluation on tool definitions."""
    _require_lens()
    from src.app.eval.models import EvalReport  # noqa: PLC0415
    from src.app.eval.report import render_text  # noqa: PLC0415
    from src.app.eval.scoring import apply_scoring  # noqa: PLC0415

    layers: dict = {}
    metadata: dict[str, Any] = {"lens_mode": mode}

    if mode in ("static", "both"):
        layers.update(_build_static_layers(tools))

    if mode in ("llm", "both"):
        try:
            llm_layer, llm_meta = asyncio.run(_build_llm_layer(tools))
            if llm_layer is not None:
                layers["llm"] = llm_layer
            metadata.update(llm_meta)
        except RuntimeError as exc:
            if mode == "llm":
                raise
            metadata["llm_error"] = str(exc)

    if mode == "llm" and "llm" not in layers:
        raise RuntimeError(metadata.get("llm_error", "LLM evaluation did not run"))

    report = EvalReport(
        timestamp=datetime.now(UTC).isoformat(),
        server_name=server_name,
        layers=layers,
        metadata=metadata,
    )
    report = apply_scoring(report)
    text = render_text(report)
    summary = (
        f"mcp-lens ({mode}): score {report.overall_score:.1f}/100, "
        f"gate {'PASS' if report.gate_passed else 'FAIL'}"
    )
    return LensEvalResult(
        mode=mode,
        gate_passed=report.gate_passed,
        overall_score=float(report.overall_score),
        summary=summary,
        report_text=text,
        metadata=metadata,
    )
