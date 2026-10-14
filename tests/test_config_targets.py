from __future__ import annotations

import pytest

from mcp_sonar.config import (
    StdioTransportConfig,
    StreamableHttpTransportConfig,
    TargetConfig,
    TargetsFile,
    UnknownTargetError,
    resolve_target,
)


def test_unknown_target_lists_options() -> None:
    targets = TargetsFile(
        targets={
            "local-http": TargetConfig(
                label="HTTP dev",
                transport=StreamableHttpTransportConfig(url="http://127.0.0.1:8011/mcp"),
            ),
            "everything-stdio": TargetConfig(
                transport=StdioTransportConfig(command="npx", args=["-y", "pkg"]),
            ),
        }
    )
    with pytest.raises(UnknownTargetError) as err:
        resolve_target(targets, "my-server")
    message = err.value.format_message()
    assert "Unknown target 'my-server'" in message
    assert "local-http" in message
    assert "everything-stdio" in message
    assert "streamable HTTP" in message
    assert "stdio" in message
    assert "list-targets" in message
