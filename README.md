# mcp-sonar

Open-source toolkit to **benchmark**, **compare**, and **interact** with [Model Context Protocol](https://modelcontextprotocol.io/) servers.

- **One server:** run a suite and collect latency + payload stats  
- **Two servers:** same suite, side-by-side comparison  
- **Ad hoc:** list/describe/call tools, inspect server info, list resources/prompts (CLI, no LLM)  
- **Agent:** send a prompt to an LLM wired to an MCP server; see each tool call and the final answer (`sonar agent run`)  
- **Extensible:** drop YAML suites under `config/suites/`, or add Python suites in `src/mcp_sonar/suite/`

Transports: **stdio** (subprocess) and **streamable HTTP** (with optional bearer token). Every CLI command and benchmark report shows which transport and endpoint you are using (stdio vs streamable HTTP are always labeled explicitly).

## Install

```bash
cd ~/dev/mcp-sonar
uv sync --group dev
cp config/targets.example.yaml config/targets.yaml
```

**Try public servers without writing your own:** copy [config/targets.online.example.yaml](config/targets.online.example.yaml) and follow [config/examples/online-mcp-context.md](config/examples/online-mcp-context.md) (npm stdio servers + optional remote HTTP).

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

**Built-in:** `mcp-context` — context window / token usage for tools, prompts, and resources (static estimate + optional LLM review).

```bash
uv sync --extra context-tokens   # optional: tiktoken for accurate static counts
sonar run --config config/targets.yaml --target local-http --suite mcp-context --context-mode static
sonar run ... --suite mcp-context --context-mode both --context-budget 32000 --context-min-llm-score 70
```

**Built-in:** `mcp-load` — parallel connection stress test (N sessions invoke the same tool each iteration).

```bash
sonar run --config config/targets.yaml --target local-http --suite mcp-load \
  --load-concurrency 20 --load-tool echo --load-args '{"message":"load"}' \
  --iterations 5 --warmup 1
```

**YAML:** `tool-accuracy` — deterministic tool output checks (`config/suites/tool-accuracy.yaml`; echo, list, add).

```bash
sonar run --config config/targets.yaml --target everything-stdio --suite tool-accuracy
```

**Built-in:** `mcp-lens` — [MCP Lens](https://github.com/devninja-in/mcp-lens) static and/or LLM evaluation of your server’s tool catalog (no tool invocations). Install the optional dependency and choose what to run:

```bash
uv sync --extra mcp-lens
sonar run --config config/targets.yaml --target local-http --suite mcp-lens --lens-mode static
sonar run --config config/targets.yaml --target local-http --suite mcp-lens --lens-mode llm
sonar run --config config/targets.yaml --target local-http --suite mcp-lens --lens-mode both
```

`--lens-mode` defaults to `both` for `mcp-lens`. The full Lens text report prints after the summary table; use `--verbose` on other suites to show last tool responses, or `--out` for markdown/json with a `detail` field.

**Built-in:** `agentic-mcp` — [Agentic Eval Flow](https://github.com/RHEcosystemAppEng/agentic_eval_flow) MCPChecker tasks (agent + LLM judge) against a **streamable HTTP** target. Requires the [`mcpchecker`](https://github.com/mcpchecker/mcpchecker) CLI and API keys for models in your eval pack’s `eval.yaml`.

```bash
# Default task pack: config/eval-flow/default (override with --eval-pack)
sonar run --config config/targets.yaml --target local-http --suite agentic-mcp
sonar run ... --suite agentic-mcp --eval-pack ./my-mcp-eval --eval-threshold 0.7
```

### LLM providers (`llm.json`)

Copy `config/llm.example.json` to `config/llm.json` (or `llm.json` in the project root) and set `default` to a named config. API keys and gateway URLs use `*_env` fields (never commit secrets).

| `provider` | SDK extra |
|------------|-----------|
| `anthropic` | `uv sync --extra llm-anthropic` |
| `openai` | `uv sync --extra llm-openai` |
| `vertexai` (Gemini) | `uv sync --extra llm-vertex` |
| `anthropic-vertex` | `uv sync --extra llm-anthropic-vertex` |
| `maas` | httpx only; OpenAI-compatible MaaS (`MAAS_BASE_URL`, `MAAS_API_KEY`). Set **`rate_limit_per_minute`** to match your portal tier (client-side throttle): sandbox **10** req/min per model, personal **20**, enterprise per assigned tier. Omit to skip client-side throttling. |
| `models-corps` | Alias for `maas` (legacy config name). |

```bash
sonar llm list --config config/llm.json
sonar llm models --config config/llm.json --name maas-sandbox   # VPN + key
export MCP_SONAR_LLM_CONFIG=config/llm.json   # optional override
```

**YAML:** any `config/suites/*.yaml` is loaded automatically when you pass `--config config/targets.yaml`.

Example (`config/suites/everything-smoke.yaml`) targets the official [server-everything](https://www.npmjs.com/package/@modelcontextprotocol/server-everything) reference server.

```bash
uv run sonar list-suites --config config/targets.yaml
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
sonar list-targets --config config/targets.yaml
sonar list-suites --config config/targets.yaml

# LLM agent (tool loop + step trace; requires llm.json)
sonar agent run --config config/targets.yaml --target everything-stdio \
  --prompt "Call echo with message hello and tell me what came back" --format json

# Interact (no LLM — direct MCP tool calls)
sonar tools list --config config/targets.yaml --target everything-stdio
sonar tools describe --config config/targets.yaml --target everything-stdio --tool echo
sonar tools info --config config/targets.yaml --target everything-stdio

# One-off JSON call
sonar tools benchmark --config config/targets.yaml --target everything-stdio \
  --tool echo --args '{"message":"ping"}' --warmup 2 --iterations 20

sonar tools call --config config/targets.yaml --target everything-stdio \
  --tool echo --args '{"message":"hello"}'

# Typed input form (YAML): generate, edit, invoke
sonar tools template --config config/targets.yaml --target local-http \
  --tool explore_schema -o explore_schema.input.yaml
# edit explore_schema.input.yaml, then:
sonar tools invoke --config config/targets.yaml --args-file explore_schema.input.yaml

# Bulk calls from a file
sonar tools batch-template --tool explore_schema --target local-http -o calls.batch.yaml
sonar tools batch --config config/targets.yaml --file calls.batch.yaml

# Shorthand: list-tools, template, invoke, call, batch, …

# Benchmark one server
sonar run --config config/targets.yaml \
  --target everything-stdio --suite everything-smoke \
  --warmup 2 --iterations 10 --out results --format both

# Compare two servers (use a suite that defines both bindings, or same binding on both targets)
sonar compare --config config/targets.yaml \
  --left everything-stdio --right everything-http --suite mcp-smoke
```

Reports: terminal table plus optional `results.json` / `results.md`.

## Credits

Optional evaluation suites integrate third-party projects. See **[CREDITS.md](CREDITS.md)** for attribution:

- **[MCP Lens](https://github.com/devninja-in/mcp-lens)** — `mcp-lens` suite (`devninja-in`).
- **[Agentic Eval Flow](https://github.com/RHEcosystemAppEng/agentic_eval_flow)** — `agentic-mcp` suite ([RHEcosystemAppEng](https://github.com/RHEcosystemAppEng)), via the [mcpchecker](https://github.com/mcpchecker/mcpchecker) CLI.

## Compare different server shapes

Give each target a different `binding` and define matching `calls` keys in your suite YAML (see `config/suites/compare-echo.yaml`).

## Add a Python suite

1. Implement `Suite` in `src/mcp_sonar/suite/<name>/`.
2. Register in `suite/registry.py` via `_load_builtin_suites()` (or load from your own package).

## Tests

```bash
uv run pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
