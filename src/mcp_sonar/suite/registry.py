from __future__ import annotations

from pathlib import Path

from mcp_sonar.suite.base import Suite

_SUITES: dict[str, Suite] = {}
_LOADED_DIRS: set[Path] = set()


def register_suite(suite: Suite) -> None:
    if suite.id in _SUITES:
        raise ValueError(f"Suite already registered: {suite.id}")
    _SUITES[suite.id] = suite


def get_suite(suite_id: str) -> Suite:
    if suite_id not in _SUITES:
        known = ", ".join(sorted(_SUITES))
        raise KeyError(f"Unknown suite '{suite_id}'. Known: {known}")
    return _SUITES[suite_id]


def list_suites() -> list[Suite]:
    return sorted(_SUITES.values(), key=lambda s: s.id)


def load_suites_from_directory(directory: Path) -> int:
    """Load ``*.yaml`` / ``*.yml`` suite definitions. Returns count loaded."""
    directory = directory.resolve()
    if directory in _LOADED_DIRS or not directory.is_dir():
        return 0
    count = 0
    from mcp_sonar.suite.yaml_suite import suite_from_yaml  # noqa: PLC0415

    for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        suite = suite_from_yaml(path)
        if suite.id in _SUITES:
            raise ValueError(f"Duplicate suite id '{suite.id}' in {path}")
        register_suite(suite)
        count += 1
    _LOADED_DIRS.add(directory)
    return count


def _load_builtin_suites() -> None:
    from mcp_sonar.suite.mcp_lens import register as register_lens  # noqa: PLC0415
    from mcp_sonar.suite.mcp_smoke import register  # noqa: PLC0415

    register()
    register_lens()


def ensure_suites_loaded(config_dir: Path | None = None) -> None:
    """Load builtins once, then optional ``config/suites`` next to targets."""
    if not _SUITES:
        _load_builtin_suites()
    if config_dir is not None:
        suites_dir = config_dir / "suites"
        load_suites_from_directory(suites_dir)


_load_builtin_suites()
