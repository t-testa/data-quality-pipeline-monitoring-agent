# Verification record

Executed locally on 2026-10-11. Earlier failures were corrected, not counted as passes.

| Area | Actual evidence |
|---|---|
| Windows automated tests | Baseline 53 passed / 91.70% statements reproduced; expanded 72 passed / 92.36% statements / 80.45% branches / 89.65% combined; Python 3.12.10 |
| Linux automated tests | 72 passed; 89.65% combined coverage on Python 3.12.15 in the final Debian 13 test image |
| Dependency integrity | Hash-locked runtime/development installs succeeded; `pip check` clean |
| Vulnerabilities | Runtime, development and toolchain lock audits clean; OS image advisories separately recorded in acceptance report; no blanket security-clear claim |
| Quality engine | All ten kinds tested; pass/failure/error behavior, schema changes, threshold checks |
| Pipeline | Eight scenarios executed; rollback, bounded retries, update/delete replay, persisted state and interrupted-run lock tested |
| API | Missing/wrong auth, paid-role denial, request size, rate limit, input bounds and evidence matching tested |
| MCP | All nine tool registrations tested; real stdio initialize/list/call verified against running API; invalid run input rejected |
| AI | Provider adapter mocked; structured contract, refusal, unsupported refs/categories, prompt injection and daily budget tested; no live paid API call made |
| NorthstarBI | Ten generated read-only checks executed against local SQL Server; results described in discovery.md |
| Docker | Linux image built with ODBC 18; non-root service healthy; all eight demos and authenticated/unauthenticated HTTP smoke checks passed |
| Browser | Authenticated synthetic overview, pipeline/table filters, quality evidence and deterministic duplicate investigation inspected in browser; screenshot in local artifacts |
| Infrastructure | VM and budget Bicep templates compiled locally; no deployment, what-if, Azure routing or capacity validation performed |
| CI | actionlint 1.7.12 passes locally; Windows/Linux and Docker jobs configured with immutable actions and image audit; GitHub-hosted execution blocked on private repository publishing |

Tests cover deterministic contracts rather than subjective LLM quality. A provider response is only accepted when selected IDs exist in the retrieved scope and guidance corresponds to selected non-passing evidence. There is no claim that a model discovered a true root cause. One upstream Starlette/AnyIO deprecation warning remains; it did not fail tests.

Final review added 19 cases, including all recorded failure categories without a key, hostile source fields, invalid model scope, suppression resistance, concurrent budget reservations, future schema rejection, readiness failure, chunked/slow requests and non-ASCII credentials. The no-key provider callable is asserted unreachable. The model adapter is mocked; prompt-injection resistance is verified at the deterministic boundary, not by claiming a live model resisted every attack.

The fresh Docker acceptance harness uses its own random credentials, source-free environment, project and empty named volume. It compares the complete run/result payloads for 16 runs across restart and recreation, then compares restored SQLite contents and integrity. Final image scan: 187 package/advisory occurrences, zero critical and zero scanner-listed fixes; 44 high occurrences across eight distinct advisories remain a production-security gate. See [acceptance](acceptance.md). This extends the earlier Python-only security checks.

Cross-platform verification caught inherited Docker `DQ_DATA_DIR` affecting a CLI test; all tests now explicitly clear deployment environment variables. Grounding review also added a regression test ensuring query execution errors describe an unknown data condition, not an asserted quality violation. The SQLite online backup completed and passed an integrity check. Container recreation preserved all 16 initial demo runs and the runtime UID was verified as 10001.

Reproduce with README commands. JUnit and audit JSON are under ignored `artifacts/`; the summary is versioned while detailed local results remain private. Temporary test databases are isolated. `scripts/smoke_mcp.py` requires the API with demo data running. `Dockerfile.test` supports running the full suite in a disposable Linux container without giving tests access to host databases.

## Outstanding acceptance boundaries

- A dedicated read-only Northstar principal is not provisioned; a dedicated least-privilege identity is required by the routine CLI. One-time SELECT-only discovery is separately verified.
- OpenAI request/response behavior is adapter-tested, not account/model-live verified. Keyless behavior is verified.
- Optional `sql/demo.sql` fixture is prepared for an isolated `DQDemo` database; it was not executed. The automatic incident loader uses SQLite; SQL Server source checks were verified separately against NorthstarBI.
- Cloud deployment remains a proposal until private networking, credentials, budget and explicit spending approval are supplied.
- GitHub CLI is absent, the workspace has no remote, and the connected GitHub tool surface has no repository-creation operation. Local commits are prepared; the exact private publishing command is in README.
