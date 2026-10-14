# Credits and third-party evaluation frameworks

mcp-sonar bundles optional **suites** that call external open-source evaluation projects. We thank their authors and document how they are used here.

## [MCP Lens](https://github.com/devninja-in/mcp-lens)

- **Authors / maintainers:** [devninja-in](https://github.com/devninja-in) (MCP Lens project).
- **Used in sonar:** built-in suite `mcp-lens` (`sonar run --suite mcp-lens`).
- **Integration:** optional Python dependency (`uv sync --extra mcp-lens`, git source in `pyproject.toml`). Static and LLM evaluation logic runs inside the upstream `mcp-lens` package; sonar lists tools from your MCP target and invokes that API via `src/mcp_sonar/integrations/mcp_lens/`.
- **License:** follow the license in the [mcp-lens repository](https://github.com/devninja-in/mcp-lens).

## [Agentic Eval Flow](https://github.com/RHEcosystemAppEng/agentic_eval_flow)

- **Authors / maintainers:** [RHEcosystemAppEng](https://github.com/RHEcosystemAppEng) (Agentic Eval Flow / abevalflow).
- **Used in sonar:** built-in suite `agentic-mcp` (`sonar run --suite agentic-mcp`).
- **Integration:**
  - Task pack layout (`eval.yaml`, `tasks/`) matches Agentic Eval Flow MCPChecker submissions; default pack under `config/eval-flow/default/`.
  - Report aggregation in `src/mcp_sonar/integrations/agentic_eval_flow/aggregate.py` is adapted from `scripts/aggregate_mcpchecker.py` in the Agentic Eval Flow repository (Apache-2.0).
  - Execution uses the separate **[mcpchecker](https://github.com/mcpchecker/mcpchecker)** CLI (`mcpchecker check …`), as in the upstream Tekton pipeline — sonar does not ship the Go binary.
- **License:** [Apache-2.0](https://github.com/RHEcosystemAppEng/agentic_eval_flow/blob/main/LICENSE) for Agentic Eval Flow; refer to mcpchecker for its license.

## [mcpchecker](https://github.com/mcpchecker/mcpchecker)

- **Used with:** `agentic-mcp` suite only (runtime dependency on your machine, not a Python package of mcp-sonar).
- **Role:** runs agent + LLM-judge tasks against MCP servers; JSON output is aggregated into sonar reports using the Agentic Eval Flow report shape above.
