# Agent guide — mcp-benchmarker

This repository is an **open-source** toolkit for benchmarking **and** interacting with [Model Context Protocol](https://modelcontextprotocol.io/) servers. Treat every change as something a stranger on the internet will read, run, and contribute to.

## Open source — no vendor-specific content

- Do **not** add Red Hat–specific (or any single-employer) URLs, product names, SSO realms, internal hostnames, or auth flows tied to one organization.
- Use **generic** examples: `@modelcontextprotocol/server-everything`, `localhost`, env vars like `MCP_BENCH_BEARER_TOKEN`, and public MCP documentation.
- README, config examples (`config/targets.example.yaml`, `config/suites/*.yaml`), CLI help text, and comments must stay portable. If you need a real endpoint for local dev, keep it in **gitignored** `config/targets.yaml`, not in committed files.
- Auth in this project is intentionally simple: bearer tokens via environment variables (`auth.bearer_env` in targets). Do not embed proprietary OAuth client IDs, issuer URLs, or token-fetch CLIs here; users bring their own tokens.

## What this project does

| Area | Purpose |
|------|---------|
| **Benchmarking** | Suites (`run`, `compare`), latency stats, functional checks |
| **Interaction** | List/describe/call tools (and related MCP surfaces) without an LLM — CLI only |

Shared connection logic lives in `src/mcp_benchmarker/target.py` (`connect_target`, `ConnectedTarget`). Transport kind and endpoints are defined in `transport.py`; user-visible headings and tables use `display.py`. Benchmark runners and the interactor CLI must reuse these modules — do not duplicate MCP session wiring or transport formatting.

## Layout

```
src/mcp_benchmarker/
  cli.py              # Click entry: mcp-bench
  interactor_cli.py   # Flat interactor-style entry: mcp-interact (same backend)
  target.py           # MCP connect + ConnectedTarget
  transport.py        # stdio vs streamable HTTP metadata (single source of truth)
  display.py          # Rich headers/tables showing transport on every command
  interactor/         # Interactor command implementations
  core/               # Runner, stats, reports
  suite/              # Built-in and YAML suites
  checks/             # Functional check functions
config/
  targets.example.yaml
  suites/
tests/
```

## Conventions

- **Python 3.11+**, `uv` for env and lockfile, `pytest` for tests. Prefer offline unit tests with mocks; mark live server tests `@pytest.mark.live`.
- **Click** for CLI; **Rich** for human-readable tables; **JSON** flags for scripting (`--format json`).
- Keep diffs small: extend `ConnectedTarget` and CLI commands rather than new parallel clients.
- Match existing style: `from __future__ import annotations`, explicit types, minimal comments.

## Adding interactor features

When extending MCP interaction (inspired by generic “MCP interactor” CLIs, not SmartQL-specific wrappers):

1. Add session methods on `ConnectedTarget` (or thin helpers in `interactor/`).
2. Expose via `mcp-bench tools …` and mirror important commands on `mcp-interact` for a flat UX.
3. Document in `README.md` with generic targets only.
4. Add tests that do not require a running MCP server unless marked `live`.

## Adding benchmark suites

- YAML under `config/suites/` or Python suite in `src/mcp_benchmarker/suite/` registered in `suite/registry.py`.
- Bindings must align with `binding` on targets in `targets.yaml`.

## Before you finish

```bash
uv run pytest -v
uv run mcp-bench --help
uv run mcp-interact --help
```

Do not commit secrets, `.env`, or personal `config/targets.yaml` with real tokens.
