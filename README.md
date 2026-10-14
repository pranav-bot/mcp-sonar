# mcp-benchmarker

Open-source toolkit to **benchmark**, **compare**, and **interact** with [Model Context Protocol](https://modelcontextprotocol.io/) servers.

- **One server:** run a suite and collect latency + payload stats  
- **Two servers:** same suite, side-by-side comparison  
- **Ad hoc:** list/describe/call tools, inspect server info, list resources/prompts (CLI, no LLM)  
- **Extensible:** drop YAML suites under `config/suites/`, or add Python suites in `src/mcp_benchmarker/suite/`

Transports: **stdio** (subprocess) and **streamable HTTP** (with optional bearer token). Every CLI command and benchmark report shows which transport and endpoint you are using (stdio vs streamable HTTP are always labeled explicitly).

## Install

```bash
cd ~/dev/mcp-benchmarker
uv sync --group dev
cp config/targets.example.yaml config/targets.yaml
```

## Targets (`config/targets.yaml`)

Each target is a named MCP endpoint:

| Field | Meaning |
|-------|---------|
| `binding` | Which scenario branch to run in a suite (default: `default`) |
| `transport` | `stdio` or `streamable_http` |
| `auth.bearer_env` | Env var holding a bearer token (HTTP only) |
| `env` | Extra env vars for stdio subprocesses (`${VAR}` expansion supported) |

## Suites

**Built-in:** `mcp-smoke` — `tools/list` via `__list_tools__`.

**YAML:** any `config/suites/*.yaml` is loaded automatically when you pass `--config config/targets.yaml`.

Example (`config/suites/everything-smoke.yaml`) targets the official [server-everything](https://www.npmjs.com/package/@modelcontextprotocol/server-everything) reference server.

```bash
uv run mcp-bench list-suites --config config/targets.yaml
```

### Writing a YAML suite

```yaml
id: my-suite
description: What this measures
scenarios:
  - id: step_name
    description: Human-readable step
    calls:
      default:                    # binding name
        tool: tool_name           # or __list_tools__
        arguments: {}
    check: not_error              # or { name: contains_text, args: { text: "ok" } }
    skip_for_bindings: []         # optional
```

Checks: `not_error`, `expect_error`, `list_tools_nonempty`, `contains_text`, `json_path_exists`.

## CLI

```bash
# Discover
mcp-bench list-targets --config config/targets.yaml
mcp-bench list-suites --config config/targets.yaml

# Interact (no LLM — direct MCP tool calls)
mcp-bench tools list --config config/targets.yaml --target everything-stdio
mcp-bench tools describe --config config/targets.yaml --target everything-stdio --tool echo
mcp-bench tools info --config config/targets.yaml --target everything-stdio
mcp-bench tools call --config config/targets.yaml --target everything-stdio \
  --tool echo --args '{"message":"hello"}'

# Same interaction via flat CLI (mcp-interact)
mcp-interact list-tools --config config/targets.yaml --target everything-stdio
mcp-interact call echo --config config/targets.yaml --target everything-stdio \
  --args '{"message":"hello"}'

# Benchmark one server
mcp-bench run --config config/targets.yaml \
  --target everything-stdio --suite everything-smoke \
  --warmup 2 --iterations 10 --out results --format both

# Compare two servers (use a suite that defines both bindings, or same binding on both targets)
mcp-bench compare --config config/targets.yaml \
  --left everything-stdio --right everything-http --suite mcp-smoke
```

Reports: terminal table plus optional `results.json` / `results.md`.

## Compare different server shapes

Give each target a different `binding` and define matching `calls` keys in your suite YAML (see `config/suites/compare-echo.yaml`).

## Add a Python suite

1. Implement `Suite` in `src/mcp_benchmarker/suite/<name>/`.
2. Register in `suite/registry.py` via `_load_builtin_suites()` (or load from your own package).

## Tests

```bash
uv run pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
