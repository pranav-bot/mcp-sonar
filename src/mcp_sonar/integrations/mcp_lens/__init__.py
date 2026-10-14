"""Optional integration with MCP Lens (https://github.com/devninja-in/mcp-lens).

Evaluation rules and scoring are implemented by the upstream ``mcp-lens`` package;
see CREDITS.md in the mcp-sonar repository root.
"""

from mcp_sonar.integrations.mcp_lens.evaluate import (
    LensMode,
    LensNotInstalledError,
    evaluate_tools,
    mcp_lens_available,
)
from mcp_sonar.integrations.mcp_lens.export import tools_to_lens_dicts

__all__ = [
    "LensMode",
    "LensNotInstalledError",
    "evaluate_tools",
    "mcp_lens_available",
    "tools_to_lens_dicts",
]
