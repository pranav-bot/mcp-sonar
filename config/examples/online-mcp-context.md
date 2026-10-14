# Example: context usage on public MCP servers

This walkthrough uses **[config/targets.online.example.yaml](../targets.online.example.yaml)**—no custom MCP code required.

## 1. Copy the targets file

```bash
cp config/targets.online.example.yaml config/targets.yaml
```

## 2. List tools (stdio, downloaded from npm)

```bash
uv run sonar tools list --config config/targets.yaml --target everything-stdio
uv run sonar tools list --config config/targets.yaml --target memory-stdio
```

`everything-stdio` pulls [@modelcontextprotocol/server-everything](https://www.npmjs.com/package/@modelcontextprotocol/server-everything).  
`memory-stdio` pulls [@modelcontextprotocol/server-memory](https://www.npmjs.com/package/@modelcontextprotocol/server-memory).

## 3. Static context benchmark (no LLM keys)

```bash
uv run sonar run --config config/targets.yaml \
  --target everything-stdio --suite mcp-context --context-mode static

uv run sonar run --config config/targets.yaml \
  --target memory-stdio --suite mcp-context --context-mode static
```

Optional gate (fail if catalog exceeds ~2k tokens):

```bash
uv run sonar run --config config/targets.yaml \
  --target everything-stdio --suite mcp-context \
  --context-mode static --context-budget 2000
```

## 4. Compare two online stdio servers

Same suite, two npm-backed catalogs:

```bash
uv run sonar compare --config config/targets.yaml \
  --left everything-stdio --right memory-stdio \
  --suite mcp-context --context-mode static
```

## 5. Remote streamable HTTP (optional)

### Tiny Go demo (no token)

```bash
uv run sonar tools list --config config/targets.yaml --target tiny-go-mcp-http
```

Upstream: [tiny-go-mcp-http.fly.dev](https://tiny-go-mcp-http.fly.dev) ([project docs](https://github.com/kioie/tiny-go-mcp-server/blob/main/docs/SMITHERY.md)).

### Smithery or other hosted URL

1. Create or pick a **streamable HTTP** server on [Smithery](https://smithery.ai/) (or copy a `remotes[].url` from the [MCP Registry](https://modelcontextprotocol.io/registry/remote-servers)).
2. Export the MCP endpoint URL and any bearer token your host requires:

```bash
export MCP_REMOTE_URL='https://your-hosted-mcp.example/mcp'
export MCP_SONAR_BEARER_TOKEN='...'   # only if the host uses Authorization: Bearer
uv run sonar run --config config/targets.yaml \
  --target smithery-remote --suite mcp-smoke
```

URLs and `${MCP_REMOTE_URL}` in YAML are expanded from the environment (see `src/mcp_sonar/config.py`).

## 6. LLM context review (optional)

Requires `config/llm.json` (copy from `config/llm.example.json`):

```bash
uv run sonar run --config config/targets.yaml \
  --target everything-stdio --suite mcp-context --context-mode both
```
