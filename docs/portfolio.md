# Portfolio narrative and demo checklist

## Sanitized public description

Built a private data reliability monitor combining deterministic SQL quality contracts, incremental ingestion, persistent execution history and an evidence-grounded diagnostic interface. Demonstrations reproduce duplicate keys, broken relationships, missing values, volume declines, stale data, failed loads and schema drift. A read-only MCP interface lets approved AI clients retrieve bounded evidence. Optional model output is validated against stored IDs and curated investigation categories, separating observations from unconfirmed causes.

Business value: make broken reporting inputs visible before analysts spend hours explaining inconsistent dashboards; give engineers a clear first investigation step and traceable evidence. No unmeasured ROI or production SLA is claimed.

## Synthetic demonstration (5 minutes)

1. Run all eight isolated demos; open the dashboard and authenticate without recording the token.
2. Show the overview and explain that pass rate uses each pipeline's latest run, while execution counts use all history.
3. Select demo-success: all ten contracts pass; replay processes zero new rows.
4. Select demo-duplicates: one excess customer key; inspect its evidence ID and threshold.
5. Select demo-row_decline: 80% drop, baseline 100, target 20, deletion records processed transactionally.
6. Select demo-pipeline_failure: failed status and two retries; explain rollback/checkpoint behavior.
7. Select demo-schema_change: added column evidence.
8. Investigate a selected run. Show deterministic facts, unconfirmed hypotheses, missing evidence, and AI-unavailable state when no key is set.
9. Use an approved MCP client to call get_incident_details for that run; compare IDs with the dashboard.
10. Show tests, architecture and deployment tradeoffs. Do not imply external pipeline monitoring or cloud deployment.

## Screenshot checklist

- Use container demo data only, not live Northstar discovery history.
- Capture overview, duplicate details, volume trend, schema change, retry history and structured investigation.
- Exclude tokens, `.env`, terminal credentials, internal hostnames, real customer data and personal account information.
- Ensure narrow-screen layout is readable and tables can scroll.
- Review each image before public sharing. Keep the source repository private.

## Interview talking points

- Why deterministic checks determine metrics and model output cannot change a fact.
- How idempotent upserts, tombstones and an atomic watermark prevent partial-load replay problems.
- Why a crash between target commit and metadata finalization is a recoverable boundary rather than a claimed distributed transaction.
- How baseline poisoning is reduced by excluding failed runs, and where legitimate business shifts need threshold review.
- Why aggregate reconciliation cannot prove row-level equality and business dates are not ingestion freshness signals.
- How a stdio proxy narrows MCP exposure and keeps authorization centralized.
- Why SQLite is appropriate locally and why multi-replica Container Apps needs a different metadata backend.
- How model-reference validation, no raw logs, and curated guidance constrain prompt injection and hallucination.
- Remaining growth: per-user Entra access, external scheduler adapters, alert delivery, retention, server metadata storage and historical intent parsing.
