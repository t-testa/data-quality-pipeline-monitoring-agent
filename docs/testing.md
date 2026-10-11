# Verification record

Executed locally on 2026-10-11. Earlier failures were corrected, not counted as passes.

| Area | Actual evidence |
|---|---|
| Windows automated tests | 53 passed; 91.70% statement coverage; Python 3.12.10 |
| Linux automated tests | Full suite run in Docker on Python 3.12.15; results verified separately from Windows |
| Dependency integrity | Hash-locked runtime/development installs succeeded; `pip check` clean |
| Vulnerabilities | Installed and runtime-lock audits report no known vulnerabilities at audit time |
| Quality engine | All ten kinds tested; pass/failure/error behavior, schema changes, threshold checks |
| Pipeline | Eight scenarios executed; rollback, bounded retries, update/delete replay, persisted state and interrupted-run lock tested |
| API | Missing/wrong auth, paid-role denial, request size, rate limit, input bounds and evidence matching tested |
| MCP | All nine tool registrations tested; real stdio initialize/list/call verified against running API; invalid run input rejected |
| AI | Provider adapter mocked; structured contract, refusal, unsupported refs/categories, prompt injection and daily budget tested; no live paid API call made |
| NorthstarBI | Ten generated read-only checks executed against local SQL Server; results described in discovery.md |
| Docker | Linux image built with ODBC 18; non-root service healthy; all eight demos and authenticated/unauthenticated HTTP smoke checks passed |
| Browser | Authenticated synthetic overview, pipeline/table filters, quality evidence and deterministic duplicate investigation inspected in browser; screenshot in local artifacts |
| Infrastructure | VM and budget Bicep templates compiled locally; no deployment, what-if, Azure routing or capacity validation performed |
| CI | Windows/Linux and Docker jobs configured; GitHub-hosted execution pending private repository publishing |

Tests cover deterministic contracts rather than subjective LLM quality. A provider response is only accepted when selected IDs exist in the retrieved scope and guidance corresponds to selected non-passing evidence. There is no claim that a model discovered a true root cause. One upstream Starlette/AnyIO deprecation warning remains; it did not fail tests.

Cross-platform verification caught inherited Docker `DQ_DATA_DIR` affecting a CLI test; all tests now explicitly clear deployment environment variables. Grounding review also added a regression test ensuring query execution errors describe an unknown data condition, not an asserted quality violation. The SQLite online backup completed and passed an integrity check. Container recreation preserved all 16 initial demo runs and the runtime UID was verified as 10001.

Reproduce with README commands. JUnit and audit JSON are under ignored `artifacts/`; the summary is versioned while detailed local results remain private. Temporary test databases are isolated. `scripts/smoke_mcp.py` requires the API with demo data running. `Dockerfile.test` supports running the full suite in a disposable Linux container without giving tests access to host databases.

## Outstanding acceptance boundaries

- A dedicated read-only Northstar principal is not provisioned; a dedicated least-privilege identity is required by the routine CLI. One-time SELECT-only discovery is separately verified.
- OpenAI request/response behavior is adapter-tested, not account/model-live verified. Keyless behavior is verified.
- Optional `sql/demo.sql` fixture is prepared for an isolated `DQDemo` database; it was not executed. The automatic incident loader uses SQLite; SQL Server source checks were verified separately against NorthstarBI.
- Cloud deployment remains a proposal until private networking, credentials, budget and explicit spending approval are supplied.
- GitHub CLI is absent, the workspace has no remote, and the connected GitHub tool surface has no repository-creation operation. Local commits are prepared; the exact private publishing command is in README.
