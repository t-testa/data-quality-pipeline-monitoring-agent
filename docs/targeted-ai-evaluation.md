# Targeted synthetic live AI retest — 2026-10-11

**3/3 PASS; all three approved attempts consumed.** No retry or additional paid
request was made. This separately approved retest validates the healthy-reference
fix and two controls; it does not replace the original 11/12 historical result or
establish general model reliability. Production release remains blocked.

## Preflight and limits

The local ignored `.env` key was accessible and never displayed, logged or copied
to Git. GitHub's authenticated API confirmed the publication repository
`t-testa/data-quality-pipeline-monitoring-agent` is **private**.

Requested and returned model on all calls: **gpt-4.1-mini-2025-04-14**. All three
requests used the existing production adapter's `POST /v1/responses`, structured
Selection schema, restricted evidence projection and exact-reference grounding.
[Official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
confirms Responses/Structured Outputs support and rates of $0.40/M input tokens
and $1.60/M output tokens. Full uncached input rates are used for estimates.

The separate evaluator enforces a **3,000-byte serialized request bound**, a
**600-output-token maximum**, 20-second SDK timeout, 30-second worker deadline,
zero retries, no redirects, no proxy inheritance, `store=false` and no tools.
All preflight requests were 1,850–2,180 bytes. A conservative **5,000-input-token
allowance** includes 2,000 tokens beyond the byte bound for framing/schema overhead.
The upper local estimate verified before execution was:

`3 × (5,000 × $0.40/M + 600 × $1.60/M) = US$0.00888 < US$0.01`.

This is not a provider-side billing cap or invoice reconciliation. A fixed,
separate durable ledger reserves each unique case before network I/O and checks
remaining budget before each reservation. Failed/ambiguous attempts consume their
full allowance; no retry is authorized. Completed approval cannot launch a fourth
call. Only healthy, no-validation and duplicate cases are allowed.

Fixtures were generated in isolated temporary synthetic storage, with an empty
source URL and synthetic application credentials. The existing monitoring database,
NorthstarBI and dashboard configuration were not used or changed. No Azure action
was taken. The original 12-attempt ledger and historical evaluation artifact remain
unchanged; this approval has its own three-attempt ledger.

## Results

All responses were HTTP 200/completed and passed structured output, exact model,
evidence membership, guidance relevance and unchanged-fact checks. There were no
provider failures or bounded rejection reasons: `ai_failure` was null in all cases.

| Case | Result | Input tokens | Output tokens | Estimated USD |
|---|---|---:|---:|---:|
| Healthy | PASS | 411 | 36 | 0.0002220 |
| Missing validation | PASS | 397 | 31 | 0.0002084 |
| Duplicate customer | PASS | 503 | 51 | 0.0002828 |
| **Total** | **3/3 PASS** | **1,311** | **118** | **0.0007132** |

Healthy accepted reference: `b8f3c1d870a848cda6b6c0bdc1b7a717`, its supplied run
summary. The run has ten passing checks and no warning/failure/error findings;
guidance and causal hypotheses remained empty.

Missing-validation accepted reference: `6d3c1219b6d044bbb17ee627ad1acef9`, its
supplied run summary. The final investigation explicitly states:
“No validation results were recorded for this run; validation execution cannot be
confirmed.” The status remains `not_recorded`; no check results or zero-valued
measurements were invented.

Duplicate accepted references: run `fd0c0a9afcc24967867ddaeb73117c0f` and check
evidence `48634ec4bb194bb7b316be7fd54f3eae`. The persisted `customer_key` failure
reports **measured 1, tolerance 0, affected records 1**. The duplicate guidance
cites that check. Replayed ingestion/missing deduplication remains a hypothesis,
with `confirmed_root_cause=false`; upstream causal evidence remains missing.

The LLM selects identifiers and fixed guidance categories only. Measurements,
missing-evidence statements and hypothesis wording are assembled deterministically
by the application. These results demonstrate the integrated workflow; they do not
claim that the model independently authored or established those facts.

## Reproduction and evidence

Post-evaluation complete local suite: **199 passed**, Windows Python 3.12.10,
39.99 seconds, **92.94% combined statement/branch coverage**; diagnostics remains
100%. This includes 11 new offline tests for the targeted budget, persistence,
concurrent/duplicate reservations, oversized requests, unknown outcomes and
completed-approval refusal. Ruff check/format and dependency consistency passed.
The existing upstream Starlette/AnyIO deprecation warning remains.

Offline preparation (no paid transport) and the full regression suite:

```powershell
.\.venv\Scripts\python.exe -m scripts.targeted_ai_evaluation
.\.venv\Scripts\python.exe -m pytest -q --cov=dqagent --cov-branch --cov-fail-under=80
```

The authorized execution used `python -m scripts.targeted_ai_evaluation --live`.
That approval is now exhausted. Never delete/reset a ledger to repeat a call.

Ignored local evidence: `artifacts/targeted-ai-evaluation.json` retains per-case
checks, accepted references, bounded rejection data, model/version, request hashes,
usage, estimates and synthetic investigation facts. Regression results are in
`artifacts/targeted-ai-tests.xml` and `artifacts/targeted-ai-coverage.json`.
The separate ledger is `.local/approved-targeted-ai-2026-10-11/attempts.sqlite`.
Credentials and raw provider errors/headers are excluded from these artifacts.

## Remaining production blockers

The existing unsuppressed container vulnerability gate remains failed; outstanding
OS advisories are neither suppressed nor accepted. Private source identity/TLS
validation, organizational identity scope, retention, off-host recovery and Azure
networking/operations remain unresolved as detailed in
[production readiness](production-readiness.md). No security gate was weakened.
The running dashboard has not been rebuilt or AI-enabled by this evaluation.
