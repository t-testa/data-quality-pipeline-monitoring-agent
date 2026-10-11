# Data Quality & Pipeline Monitoring Agent

**Northwatch** turns database quality contracts and pipeline execution records into inspectable evidence. It includes an incremental demo loader, ten configurable check types, persistent monitoring, a private dashboard, nine read-only MCP tools, and optional tightly grounded OpenAI diagnostics.

Current status: [production hardening and acceptance](docs/production-readiness.md).
Local verification passes; unresolved image advisories and operational prerequisites
block production approval. No paid AI validation or Azure deployment is claimed.

Built as a separate project. Existing source databases and reports are accessed read-only. Source repository is intended to remain private; no cloud deployment or public endpoint is created by setup. Screenshots and demonstrations use synthetic data.

## Quick start — Windows / Python 3.12

From this directory:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-dev.lock
.\.venv\Scripts\python.exe -m dqagent.cli init
.\.venv\Scripts\python.exe -m dqagent.cli demo all
.\.venv\Scripts\python.exe -m dqagent.cli serve
```
If `.env` already exists, skip `init`; it intentionally refuses to overwrite secrets. On Linux/macOS use `python3.12` and `.venv/bin/python`. Python 3.11–3.13 is the declared range; the verified runtime is 3.12.

Open [localhost:8765](http://127.0.0.1:8765). Copy `DQ_API_TOKEN` from your local `.env` into the dashboard's access field. The dashboard stores it only in memory. Use `DQ_DIAGNOSTIC_TOKEN` only when invoking optional AI. Without an API key, deterministic evidence remains fully operational and the interface explicitly marks AI unavailable.

## Docker

With a generated `.env` and Docker Desktop running:
```powershell
docker compose up -d --build --wait
docker compose exec -T monitor python -m dqagent.cli demo all
python scripts/smoke_http.py
```
Container traffic binds only to `127.0.0.1:8765`. The non-root container persists evidence in a named local Docker volume. Container and Python-local histories are separate. Do not run both servers on the same port. `docker compose down` stops the service while retaining evidence. Never remove volumes unless intentionally discarding the demo history.

## Reproducible incidents

```powershell
.\.venv\Scripts\python.exe -m dqagent.cli demo duplicates
```
Choose `success`, `duplicates`, `missing_reference`, `nulls`, `row_decline`, `stale`, `pipeline_failure`, `schema_change`, or `all`. Each pipeline seeds a separate synthetic database, records a baseline, injects one idempotent incident, and records its result. Reruns retain history and do not overwrite existing source systems. The first baseline run warns because volume comparison needs prior evidence. A later healthy run passes all ten checks.

## SQL Server source adapter

Routine source monitoring requires a DBA-provisioned SELECT-only principal; the CLI rejects privileged identities. Configure an encrypted SQLAlchemy `mssql+pyodbc` URL in `DQ_SOURCE_URL` and a reviewed rules file. The included sample contract can be invoked with:
```powershell
.\.venv\Scripts\python.exe -m dqagent.cli check-source --rules dqagent/rules/northstar.json
```
Use ODBC Driver 18, validate server certificates, percent-encode credential characters, and never paste the URL into logs or Git. Adapt the sample schema and business thresholds to your approved source. There is no fabricated ingestion timestamp, external pipeline integration or production incident injector.

## Verification

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pytest -q --cov=dqagent --cov-fail-under=80
.\.venv\Scripts\pip-audit.exe -r requirements.lock --disable-pip --no-deps
```
Windows restricted execution environments may block the asyncio loopback socket used by TestClient; execute tests in a normal authorized terminal. The [current acceptance report](docs/production-readiness.md) separates actual checks from unverified deployment assumptions. The CI workflow runs Windows/Linux tests, lint, dependency audits and container checks; the preceding published revision has a verified hosted run, while the hardening changes are locally validated until explicitly published. Hash-pinned runtime/development lockfiles are checked in. CI exports the full image inventory as well as preserving its fixable-HIGH/CRITICAL gate; an unresolved finding is not a production approval.

## Documentation

- [Architecture, data flow and pipeline semantics](docs/architecture.md)
- [Quality rule catalog](docs/rules.md)
- [API and MCP client configuration](docs/api-mcp.md)
- [Security boundaries](docs/security.md)
- [Private Azure proposal, costs and rollback](docs/deployment.md)
- [Current Azure production design and complete costs](docs/azure-production-design.md)
- [Individual vulnerability dispositions](docs/vulnerability-register.md)
- [Portfolio story and demo checklist](docs/portfolio.md)

## Operations and limitations

Single host, one API worker, no automatic scheduler or remediation. A crashed run remains running until an operator confirms the process stopped and runs `python -m dqagent.cli recover RUN_ID --operator-confirmed-stopped`. Use `python -m scripts.backup PRIVATE_DESTINATION.sqlite` for a consistent local metadata backup; restore only while writers are stopped and verify integrity. Backups contain private monitoring evidence.

The AI selects evidence and curated hypotheses; it does not author unverified root causes. Free-form historical questions do not select dates automatically—choose a run explicitly. Source checks are separate reads, so reconciliation needs a stable source window. SQLite is not a multi-host cloud store. No Entra login, external scheduler connector, automated alert delivery, model-live verification or Azure deployment is claimed.

## Private GitHub publishing

The existing repository is `t-testa/data-quality-pipeline-monitoring-agent` and was
verified private when published. Reverify its visibility before any future push
or sharing; do not recreate it. Only manually reviewed synthetic screenshots and
the sanitized portfolio description should be public. Follow the
[publishing checklist](docs/publishing.md). Private Git hosting does not make a
deployed application private.
