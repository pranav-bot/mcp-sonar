"""Optional integration with [MCP Lens](https://github.com/devninja-in/mcp-lens)."""

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
