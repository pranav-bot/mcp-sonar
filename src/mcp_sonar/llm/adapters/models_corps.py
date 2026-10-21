"""Backward-compatible import path for Models.corp MaaS (OpenAI-compatible API)."""

from mcp_sonar.llm.adapters.maas import (
    MaasAdapter,
    coerce_tls_verify,
    maas_chat_completions_url,
    maas_models_url,
)

# Legacy name used across the codebase and llm.json examples.
ModelsCorpsAdapter = MaasAdapter

__all__ = [
    "MaasAdapter",
    "ModelsCorpsAdapter",
    "coerce_tls_verify",
    "maas_chat_completions_url",
    "maas_models_url",
]
