# Agent guide — mcp-sonar

This repository is an **open-source** toolkit for benchmarking **and** interacting with [Model Context Protocol](https://modelcontextprotocol.io/) servers. Treat every change as something a stranger on the internet will read, run, and contribute to.

## Open source — no vendor-specific content

- Do **not** add Red Hat–specific (or any single-employer) URLs, product names, SSO realms, internal hostnames, or auth flows tied to one organization.
- Use **generic** examples: `@modelcontextprotocol/server-everything`, `localhost`, env vars like `MCP_SONAR_BEARER_TOKEN`, and public MCP documentation.
- README, config examples (`config/targets.example.yaml`, `config/suites/*.yaml`), CLI help text, and comments must stay portable. If you need a real endpoint for local dev, keep it in **gitignored** `config/targets.yaml`, not in committed files.
- Auth in this project is intentionally simple: bearer tokens via environment variables (`auth.bearer_env` in targets). Do not embed proprietary OAuth client IDs, issuer URLs, or token-fetch CLIs here; users bring their own tokens.

## What this project does

| Area | Purpose |
|------|---------|
| **Benchmarking** | Suites (`run`, `compare`), latency stats, functional checks |
| **Interaction** | List/describe/call tools (and related MCP surfaces) without an LLM — CLI only |

Shared connection logic lives in `src/mcp_sonar/target.py` (`connect_target`, `ConnectedTarget`). Transport kind and endpoints are defined in `transport.py`; user-visible headings and tables use `display.py`. Benchmark runners and the interactor CLI must reuse these modules — do not duplicate MCP session wiring or transport formatting.

## Layout

```
src/mcp_sonar/
  cli.py              # Click entry: sonar
  interactor_cli.py   # Flat `sonar` subcommands (registered from cli.py)
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
2. Expose via `sonar tools …` and mirror important commands on `sonar` for a flat UX.
3. Document in `README.md` with generic targets only.
4. Add tests that do not require a running MCP server unless marked `live`.

File-based calls live in `interactor/args_file.py` and `interactor/tool_template.py`. Prefer YAML input files over long `--args` JSON on the shell. Human-readable tool output belongs in `interactor/tool_describe.py` (`--format rich` default, `json` for scripts).

## Adding benchmark suites

- YAML under `config/suites/` or Python suite in `src/mcp_sonar/suite/` registered in `suite/registry.py`.
- Bindings must align with `binding` on targets in `targets.yaml`.

### Credits (`CREDITS.md`)

Keep **CREDITS.md** updated when adding or changing integrations with external eval frameworks (MCP Lens, Agentic Eval Flow, mcpchecker). README links to it; do not remove upstream attribution.

### Optional MCP Lens suite (`mcp-lens`)

[MCP Lens](https://github.com/devninja-in/mcp-lens) by **devninja-in** is an **optional** dependency (`uv sync --extra mcp-lens`), not required for core installs.

- Integration code: `src/mcp_sonar/integrations/mcp_lens/` (export tool defs, call Lens eval APIs).
- Suite: `src/mcp_sonar/suite/mcp_lens.py`; mode is set via CLI `--lens-mode static|llm|both` using `suite/mcp_lens_context.py` (context var read when `steps()` runs).
- Runner pseudo-tools `__mcp_lens_static__` / `__mcp_lens_llm__` in `core/runner.py` list tools from the target and run Lens without invoking MCP tools.
- Functional check: `check_lens_gate` in `checks/builtin.py`.
- Do not vendor MCP Lens; keep it as a git-sourced optional extra in `pyproject.toml`.

### Agentic Eval Flow suite (`agentic-mcp`)

- **[RHEcosystemAppEng/agentic_eval_flow](https://github.com/RHEcosystemAppEng/agentic_eval_flow)** (Apache-2.0): MCPChecker submission layout and report model; aggregation adapted in `integrations/agentic_eval_flow/aggregate.py` from upstream `scripts/aggregate_mcpchecker.py`.
- Uses the **[mcpchecker](https://github.com/mcpchecker/mcpchecker)** CLI at runtime (not vendored in this repo).
- Default eval pack: `config/eval-flow/default`. Users can point `--eval-pack` at a submission-style directory (`eval.yaml`, `tasks/`).
- **HTTP targets only** — MCPChecker needs `MCP_URL`; sonar generates `mcp-config.yaml` from `streamable_http` + `auth.bearer_env`.
- Do not commit proprietary gateway URLs; keep real eval packs gitignored if needed.

### LLM providers (`src/mcp_sonar/llm/`)

- Config: `config/llm.example.json` → user’s gitignored `config/llm.json` or `MCP_SONAR_LLM_CONFIG`.
- `registry.build_adapter()` delegates `anthropic`, `openai`, `vertexai`, `anthropic-vertex` to MCP Lens adapters; `models-corps` is implemented in-tree (Vertex `rawPredict` + Bearer) with **client-side** `MinuteRateLimiter` (default 6/min, sandbox tier).
- Do not commit real gateway hostnames or API keys; use `base_url_env` / `api_key_env` in examples only.

## Before you finish

```bash
uv run pytest -v
uv run sonar --help
```

Do not commit secrets, `.env`, or personal `config/targets.yaml` with real tokens.
