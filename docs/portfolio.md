# Portfolio narrative and demo checklist

**Operating model:** private repository, local Docker, existing hardware and no new
hosting subscription. Azure is postponed for cost. Optional remote access is only
[evaluated](tailscale-evaluation.md), not enabled. Paid AI is disabled for routine
demonstrations. See the [architecture diagram](portfolio-architecture.md) and
[current local validation](local-readiness.md).

## Case study: evidence before explanation

Reporting failures are difficult to investigate when execution status, validation
results and causal guesses are mixed together. Northwatch makes each recorded run
inspectable: what ran, what changed, which contracts passed or failed, what each
check measured, and what evidence is still missing.

I implemented an incremental synthetic loader, ten deterministic quality contracts,
SQLite execution/check history, a FastAPI dashboard and a nine-tool read-only MCP
server. Run/check/evidence identifiers link every investigation back to stored
facts. The optional model can select supplied IDs and approved guidance categories;
it cannot execute SQL, remediate data, invent facts or suppress recorded failures.

One useful engineering finding came from a bounded live evaluation: a healthy run
failed reference validation. Offline reconstruction established a schema/validator
contract mismatch and missing rejection observability, while the exact historical
model references remained unavailable. The fix aligned the schema/prompt and added
bounded diagnostic metadata without weakening grounding. A separately approved
three-case retest passed; neither evaluation grants ongoing paid-call approval.

Reliability work tested persisted history across restart, transactional checkpoints,
disk exhaustion and recovery. Security work distinguished clean Python dependency
audits from unresolved container OS advisories. A green CI job is not presented as
production approval. The documented cloud design was deliberately postponed after
including private access, egress, storage and operational costs in the estimate.
The resulting portfolio emphasizes reproducibility and honest evidence boundaries.

Outcome: a reproducible local demonstration with traceable synthetic incidents,
tested recovery and explicit limitations. No measured business ROI, enterprise
deployment, customer adoption, uptime SLA or production workload capacity is claimed.

## Sanitized public description

Built a private data reliability monitor combining deterministic SQL quality contracts, incremental ingestion, persistent execution history and an evidence-grounded diagnostic interface. Demonstrations reproduce duplicate keys, broken relationships, missing values, volume declines, stale data, failed loads and schema drift. A read-only MCP interface lets approved AI clients retrieve bounded evidence. Optional model output is validated against stored IDs and curated investigation categories, separating observations from unconfirmed causes.

Business value: make broken reporting inputs visible before analysts spend hours explaining inconsistent dashboards; give engineers a clear first investigation step and traceable evidence. No unmeasured ROI or production SLA is claimed.

## Synthetic demonstration (5 minutes)

1. Use existing recorded synthetic runs. Open localhost and authenticate with the read token off-camera; click **Connect**. Do not run `demo all` during a read-only presentation. If a clean demo is later requested, prepare it in a separate volume after approval.
2. Show the overview and explain that pass rate uses each pipeline's latest run, while execution counts use all history.
3. In **Pipeline history → Pipeline**, choose `demo-success`, then click the pipeline name on the desired successful run. Show all ten passing checks in **Validation evidence**. Explain replay from test evidence; do not execute a new run just to demonstrate it.
4. Choose `demo-duplicates`, click its failed run, and find `customer_key` in **Validation evidence**. Expand the shortened identifier in the **Evidence** column. Show measurement 1, affected records 1, tolerance 0, and the full run/check/evidence IDs.
5. Select demo-row_decline: 80% drop, baseline 100, target 20, deletion records processed transactionally.
6. Select demo-pipeline_failure: failed status and two retries; explain rollback/checkpoint behavior.
7. Select demo-schema_change: added column evidence.
8. Under **Explain this run**, leave **Use optional AI evidence selection** unchecked, type “What does the recorded evidence show?”, then click **Investigate selected run**. Show confirmed facts, unconfirmed hypotheses and missing causal evidence. Do not select optional AI or enter a diagnostic token.
9. Use an approved MCP client to call get_incident_details for that run; compare IDs with the dashboard.
10. Show the architecture, passing test evidence, strict vulnerability blocker and local-cost decision. Click **Clear session** afterward. Do not imply external pipeline monitoring or cloud deployment.

The row-decline, pipeline-failure and schema examples are optional if time permits.
The two strongest live walkthroughs are healthy evidence and duplicate evidence.
Use the existing MCP setup from [API and MCP](api-mcp.md); its local smoke command
is `.\.venv\Scripts\python.exe -m scripts.smoke_mcp`. It lists the nine tools and
performs read-only calls. In an approved client, call `get_incident_details` with
`pipeline: demo-duplicates`, the selected run's ID and `limit: 100`; compare the
same check/evidence identifiers. A manual MCP client call does not prove autonomous
LLM tool selection. Disable any paid model features in that client too.

## Screenshot checklist

- Use container demo data only, not real source discovery history.
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

## Acceptance review contribution

The review went beyond coverage: concurrent budgets/locks, hostile questions/source
strings, evidence preservation and complete run/check comparisons across restart
and recovery. See [local readiness](local-readiness.md) and the
[production assessment](production-readiness.md). Share only this sanitized story,
the generic diagram and separately reviewed synthetic screenshots. No publication
of the private repository or screenshots is implied by preparing them.
