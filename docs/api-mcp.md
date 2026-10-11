# API and MCP

Base address: `http://127.0.0.1:8765`. Send `Authorization: Bearer <token>` to all `/api/` routes. Missing/invalid credentials return 401; read-only callers requesting AI receive 403; input errors return 422; rate limits return 429. The static shell and `/health` reveal no monitoring evidence.

| Route | Purpose |
|---|---|
| GET /api/overview | All-time run counts and latest-run quality/freshness summary |
| GET /api/pipelines | Pipeline registry, counts and last all-pass execution |
| GET /api/runs?pipeline=...&limit=30&offset=0 | Bounded, paginated execution history |
| GET /api/runs/{id} | Run with up to 100 validation results |
| POST /api/tools/{name} | Approved read-only evidence tools |
| POST /api/diagnose | Structured evidence, unconfirmed explanations and safe steps |
| GET /api/openapi.json | Authenticated OpenAPI contract |

Diagnostic body:
```json
{"pipeline":"demo-duplicates","question":"What should I investigate first?","use_ai":false}
```
Supply `run_id` to choose an exact run. Without it, the latest recorded run is selected. Dates such as “yesterday” are **not** parsed; the response states the scope. Select the intended run in the dashboard. No fabricated historical answer is produced when evidence is absent. Set `DQ_OPENAI_API_KEY` and `DQ_OPENAI_MODEL` to enable the optional provider. No model name or paid API usage is assumed; model must support Responses structured outputs.

## Real MCP stdio server

Install the project dependencies, start the API and configure an approved MCP client:
```json
{
  "mcpServers": {
    "data-quality": {
      "command": "ABSOLUTE_PATH_TO_VENV_PYTHON",
      "args": ["-m", "dqagent.mcp_server"],
      "cwd": "ABSOLUTE_PATH_TO_PROJECT",
      "env": {
        "DQ_MCP_API_URL": "http://127.0.0.1:8765",
        "DQ_MCP_TOKEN": "SUPPLY_READ_TOKEN_THROUGH_CLIENT_SECRET_SETTINGS"
      }
    }
  }
}
```
If the client has no cwd option, install the package with `pip install --no-deps -e .` in that venv. Never commit a completed client config containing its secret.

Tools: `list_pipelines`, `get_pipeline_status`, `get_pipeline_run`, `get_recent_failures`, `list_data_quality_checks`, `get_data_quality_results`, `get_table_quality_summary`, `get_data_freshness`, `get_incident_details`.

Inputs: optional pipeline, run_id, table; limit 1–100. Status needs pipeline; run-specific tools need run_id; table summary also needs table. A supplied pipeline must match the run. Results use `{data, limit, bounded}`. `get_recent_failures` filters a bounded recent-run window, not the complete failure history. `list_data_quality_checks` returns recorded definitions/results for a run; it does not imply an unexecuted configuration has been validated. Tools are approved read-only operations, not arbitrary query execution.

The optional AI integration uses the [OpenAI structured output contract](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses). The additional local evidence validation is the application's grounding boundary; structured output alone does not establish truth.
