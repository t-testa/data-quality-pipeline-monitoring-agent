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

The deterministic `facts` array contains the run summary followed by **all recorded checks**, including passes, warnings, failures and execution errors. Each check retains its run/check/evidence IDs, status, measurement and affected-record count. `expected` includes applicable finite numeric minimum/maximum/tolerance values and the fixed business-rule operator. `details` includes only numeric volume baseline/row count or reconciliation source/comparison totals. These values come from the selected run's stored evidence; diagnostics do not re-query the source or recalculate historical results. Full schema definitions and other check details remain available through the run-detail endpoint and Validation evidence panel.

The run summary reports `validation_status`, `recorded_check_count` and counts by recorded status. `validation_status: "not_recorded"` and a missing-evidence message explicitly identify runs with no check results, including loader failures before validation. No result is not proof that validation ran or passed; historical records do not independently establish whether validation was attempted. JSON `null` remains unavailable, never zero. Status counts describe recorded results, not an expected check inventory.

`possible_explanations` are curated, unconfirmed hypotheses with applicable evidence IDs, generated only from recorded problems or a recorded pipeline error. A missing volume baseline receives its own explanation rather than a claimed volume change. Healthy runs have no problem hypotheses. `missing_evidence` identifies absent validation, unavailable baselines, check execution errors and missing causal context as applicable. The dashboard's existing Confirmed evidence, Possible explanations and Missing evidence sections display these fields without requiring AI.

The optional model sees only the run summary and non-passing check projections, bounded by the existing 100-check/256-KiB evidence-tool limits and 1,000-character question limit. It receives no raw expected/details dictionaries, row text, check names, logs or connection strings. Returned references must belong to that supplied context, and guidance must match the selected problem. Model selection never suppresses deterministic facts. Passing-check IDs remain in the user response but are not eligible model references because they are not sent to the model.

An additional 16 KiB bound applies to serialized question plus projected evidence
before reserving a paid attempt. Oversized contexts skip AI and retain all
deterministic facts. Questions undergo credential-pattern/known-secret redaction;
this does not make arbitrary sensitive prose safe to send. Provider destination,
proxy and redirect restrictions are documented in [security](security.md).
This is evidence selection, not autonomous MCP tool selection; no model tool
definitions or MCP connection are supplied to the provider.

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
