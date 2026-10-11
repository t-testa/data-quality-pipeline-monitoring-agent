# Northwatch production hardening and acceptance — 2026-10-11

**Current operating decision: Azure postponed; private local Docker portfolio.**
See [local preparation and validation](local-readiness.md). The earlier cloud costs
and acceptance criteria below remain historical evidence, not a deployment request.
Published `e95a822` subsequently passed [all hosted jobs](https://github.com/t-testa/data-quality-pipeline-monitoring-agent/actions/runs/38164558506),
including 199 tests on each OS; its full scan retained the 44 HIGH findings. New local
preparation is validated separately and does not accept those findings.

**Decision: BLOCKED for production release.** Safe local hardening is implemented
and verified. Functional tests passing does not resolve operating-system advisories,
prove live model quality, provision a least-privilege SQL identity or establish cloud
recovery. No unresolved risk has been accepted on the owner's behalf.

The existing dashboard was not replaced or fault-injected. Its **17 runs and all
associated check contents are unchanged**, verified by identical pre/post SHA-256:
`c33510d9a284a23209067868cdbf3f7f3f71ef5081560a137e96a8b8f6369487`.
All additional execution/incident fixtures, writes, kills and full-disk probes used
temporary directories or separate synthetic Docker storage. NorthstarBI was not
modified or queried. Initial hardening was offline; a subsequent explicitly approved
12-call synthetic live AI evaluation and separate three-call targeted retest are
recorded below. No Azure deployment occurred.

## Implemented changes and commits

| Commit | Problem and verified correction |
|---|---|
| `be45578` | Enforce SQL certificate validation and reject opaque/duplicate/compound overrides; apply the same least-privilege gate to source verification; pin AI destination, disable proxy/redirect rerouting, redact credential patterns and bound projected AI input to 16 KiB; suppress SDK payload logging; add safe structured request events and low-space readiness; reject credential-bearing MCP URLs; make backup creation exclusive and private; explicitly close demo SQLite connections; fix missing ODBC shared-library dependency; remove setid helper privileges; add regression/evaluation/load/recovery coverage and full CI vulnerability inventory. |
| `5bf6527` | Verify a fresh application serves restored backup evidence; add guarded reproducible disk-full exercise that refuses existing/non-tmpfs storage. |
| Report/design commit | This report, complete advisory register, updated current-generation private VM/data-disk/identity proposal and complete cost model. See Git log for its commit ID; a report cannot embed its own commit hash. |

Runtime image tested: `dqaccept9b270dba:acceptance`, image ID
`sha256:c90ab92877190c9b8a64b2fe87bd7100d595303ccce68b9ee4143acb0960e95d`.
The development dashboard still runs its previous image. Local source and candidate
image contain the initial hardening; no production rollout is claimed. Later AI
reference fixes and evaluation harnesses are in local source. Publication of the
validated pending commits is now owner-authorized after the targeted retest and
complete local suite. Hosted verification must match the pushed revision; a prior
run does not validate these changes. No failing application tests were committed.

## Automated verification

| Check | Status | Result |
|---|---|---|
| Original baseline | PASS | 89 tests; 90.26% combined statement/branch coverage reproduced |
| Initial hardening Windows suite | PASS | **137 passed**, Python 3.12.10; 19.08 s |
| Initial hardening Linux suite | PASS | **137 passed**, Python 3.12.15 in fresh Debian 13 test image |
| Post-live-evaluation Windows suite | PASS | **161 passed**, 30.66 s; adds 24 offline evaluator/guardrail tests; 92.34% coverage; current added harness has not been rerun on Linux |
| Post-offline-reference-fix Windows suite | PASS | **188 passed**, 26.91 s; adds 27 deterministic reference/observability regressions; no paid calls; this revision has not been rerun on Linux |
| Post-targeted-live-retest Windows suite | PASS | **199 passed**, 39.99 s; adds 11 offline targeted approval/guardrail regressions; hosted verification follows publication |
| Current coverage | PASS | **92.94% combined**, 888 statements/274 branches; 46 missed statements, 36 missed branches; diagnostics 100% combined |
| Lint, formatting, dependency consistency | PASS | Ruff check/format; pip check; hash-verified fresh image installs |
| Workflow syntax | PASS | actionlint; immutable action/scanner pins and read-only workflow permissions retained |
| Bicep | PASS | VM/budget compile; compiled VM has no public IP, SSH-key authentication, managed identity and detached-on-delete data disk |
| Hosted Actions for publication | Pending at report preparation | Verify the final pushed SHA; results are retained in `artifacts/targeted-github-{runs,jobs}.json`. Local commands are not a hosted run. |
| Python vulnerability audits | PASS | Runtime, development and toolchain locks: no known vulnerabilities in refreshed pip-audit data |
| Secret scans | PASS | Known-secret/heuristic scan plus redacted Gitleaks scans of staged/publishable files and reachable Git history; ignored private runtime material is not published |

One upstream Starlette/AnyIO deprecation warning remains; it does not fail tests.
The previously published revision `e5713e3` passed
[GitHub Actions run 38145800409](https://github.com/t-testa/data-quality-pipeline-monitoring-agent/actions/runs/38145800409).
That run does not validate the new local commits. Repository privacy was reverified.
Coverage does not prove source permission enforcement, real SQL dialect behavior,
model accuracy, every injection resistance case, large-scale performance, host-kernel
security, identity lifecycle or disaster recovery. Those are separately classified.

## Vulnerabilities and residual risk

Fresh Trivy database downloaded from its public feed: updated
2026-10-11T13:06:05Z, downloaded 15:05:25Z. The exact tested runtime has **0 CRITICAL,
44 HIGH, 66 MEDIUM, 82 LOW and 1 UNKNOWN package/advisory occurrences**, across
**78 unique advisories**. All are OS packages; Python-package scan has zero findings.
The eight unique HIGHs and every lower-severity advisory have individual package,
version, dependency-family, exploit-condition and disposition entries in the
[complete vulnerability register](vulnerability-register.md).

The eight HIGHs are CVE-2026-76642, CVE-2026-78408, CVE-2026-78409,
CVE-2026-78410 (util-linux), CVE-2026-54369 (ACL), CVE-2025-69720 (ncurses),
CVE-2026-16742 (systemd) and CVE-2026-9538 (Perl). No stable distribution fix is
listed. The supported base digest is already current; a no-cache apt upgrade was
included. Older Debian is also affected; unstable package mixing and an unqualified
native-driver/image migration were rejected. No feature was removed to reduce counts.

The ODBC runtime repair adds six lower-severity occurrences in the already-present
Kerberos advisory family; it adds no unique advisory. Actual `ctypes.CDLL` loading
and `ldd` now resolve the driver dependencies. Systemd-homed and Archive::Tar's
module are absent; the source-package scanner findings remain visible. Non-root,
read-only root, no capabilities/no-new-privileges and removed setid bits reduce
privileged exploit conditions. They are **mitigations, not fixes or accepted risks**.

The **strict unsuppressed HIGH/CRITICAL release gate FAILS (exit 1)**. The existing
CI fixable-HIGH/CRITICAL gate was not weakened, and CI now also retains the full
inventory including unfixed findings. A green fixable-only job cannot approve this
release. Remediation or explicit owner/security acceptance remains required.

## Authentication, source and MCP assessment

PASS for the implemented single-workspace boundary: distinct >=32-character read
and diagnostic bearer secrets, constant-time comparison, authorization on all
evidence/tools/schema routes, diagnostic-only paid invocation, no credential
browser persistence, textContent rendering, CSP, no permissive CORS, bounded
inputs, sanitized errors and 120 authenticated requests/minute/role. Tokens stay
in browser memory until logout/reload. There is no server-side browser session.

FAIL for broader organizational production identity: no individual login, MFA,
per-pipeline authorization, token expiry, per-user audit attribution or independent
revocation. Rate limiting is process-local and applies after successful auth; one
worker and private network exposure remain required. Shared-token rotation requires
restart. OS/Docker administrators can read runtime secrets and metadata. Redaction
is defense in depth, not general PII detection or protection against a compromised host.

PASS for MCP's nine fixed read-only tools: real stdio discovery/calls, denied auth,
unknown tool/SQL rejection, 1–100 result bounds, 256 KiB byte limit, pipeline/run
matching, HTTPS for remote API addresses, no redirects/proxy inheritance and no
direct database/shell/action surface. The MCP proxy does not launch an HTTP listener.
Full tool results are untrusted data for any external LLM client; Northwatch's own
model receives a separate restricted projection. An arbitrary third-party client
is not certified by these tests.

BLOCKED for live SQL least-privilege validation: no `DQ_SOURCE_URL` is configured.
The code tests reject elevated identities, every prohibited monitored-object write
permission, unresolved access and TLS overrides. They do not establish real account
grants, certificate trust, source consistency or SQL Server runtime semantics. A DBA
must supply a reviewed SELECT-only identity; no source write was attempted to test it.

## AI evaluation

The application chooses the run and loads persisted evidence deterministically.
All checks remain in the response; only the run summary and non-passing numeric/
status/ID projections enter optional AI. Raw logs, row text, names and arbitrary
details are excluded. Input <=16 KiB, question <=1,000 characters, output <=600
tokens, zero SDK retries, network timeout 20 s and atomic 20-attempt/day budget.
The SDK timeout is not an absolute slow-stream wall-clock bound. Requests/bytes
are not a guaranteed dollar cap; free-form questions are not a general DLP-safe field.

The model can select evidence IDs and fixed guidance categories only. Existence,
scope and category relevance are revalidated; facts cannot be authored, hidden or
changed by model output. Explanations remain explicitly unconfirmed. Refusals,
provider errors and invalid selections retain deterministic evidence.

**Offline evaluation: PASS, 18/18 bounded cases**, defined in
`tests/fixtures/ai_evaluation.json`: duplicate, foreign-key, row decline, schema
drift, loader failure, healthy, no run, no checks, invented ID, wrong category,
extra SQL field, question injection, persisted-field injection, timeout, provider
error, refusal, invalid contract and missing key. Separate regression tests cover
thresholds, null values, model-context overflow, credential redaction, cross-run
references and concurrent daily-budget enforcement. Provider adapter tests verify
the pinned destination, no retries, timeout, no storage and structured schema.

**Live AI evaluation: FAIL overall, 11 PASS / 1 FAIL**, after owner approval for
12 attempts and US$0.20. Requested/returned model: `gpt-4.1-mini-2025-04-14`;
endpoint `POST https://api.openai.com/v1/responses`. Preflight confirmed the local
key and a US$0.10752 upper estimate. All 12 attempts are consumed, with no retries.
Reported usage was 4,956 input and 485 output tokens, estimated **US$0.0027584**
at full uncached rates. All responses were HTTP 200; no provider errors/timeouts.
Only synthetic monitoring evidence was sent.

The healthy case failed reference grounding and safely retained deterministic facts.
An empty reference list is plausible but unconfirmed: the rejected raw list was
not retained. Subsequent offline investigation reproduced the exact request hash
and confirmed a schema/runtime mismatch: the schema allowed an empty ID list while
the validator rejected it. The schema and prompt now require a nonempty exact
reference, and failures expose bounded sanitized reasons/reference profiles.
Grounding has not been relaxed. The original healthy response's exact rejected
references remain unknown.
Missing validation/baseline and injection cases passed; all facts
remained unchanged and causal explanations unconfirmed. The
[per-case evaluation report](live-ai-evaluation.md) records checks, actual usage,
costs, evidence limitations and the offline fix. The running dashboard and its
global AI configuration remain unchanged. Further paid calls
require new approval even though the dollar budget was not consumed.

**Separately approved targeted live retest: PASS, 3/3**, on the same exact model
snapshot: healthy, missing validation and duplicate customer. The preflight upper
estimate was US$0.00888 against US$0.01; actual reported usage was 1,311 input plus
118 output tokens, estimated **US$0.0007132**. All three returned HTTP 200/completed
with accepted exact references and no rejection reasons. Healthy facts contained
no invented failure; absent validation remained explicit; duplicates retained
measurement 1, tolerance 0 and unconfirmed causality. Both the original 12-attempt
approval and new three-attempt approval are exhausted. See the
[targeted results and accepted evidence identifiers](targeted-ai-evaluation.md).
This bounded retest resolves the observed healthy-case acceptance failure for the
tested configuration without claiming general model reliability or production release.

**Autonomous AI MCP selection: NOT TESTED / not implemented**: no MCP tools or
tool-selection loop are passed to the model. Python invocation does not prove it.

The new reproducible evaluation harness defaults to a mock transport and uses a
durable 12-attempt ledger for its explicitly requested live mode. Test-image input
includes this harness for its new offline regressions. The evaluation itself did not
modify runtime code; the subsequent offline reference fix changes the local diagnostic
adapter, schema, prompt and safe rejection reporting. Source, working-file and history secret scans remain
part of final local validation; results/data artifacts and credentials stay ignored.

## Reliability, recovery and storage

Targets were defined in [reliability-targets.md](reliability-targets.md) before the
experiments. The runtime used one worker, one CPU and 512 MiB; no Azure hardware
performance is implied.

| Exercise | Status | Observed result |
|---|---|---|
| Concurrent HTTP reads | PASS | 60 requests / concurrency 6; p95 **47 ms**, max 62 ms, zero errors; target <500 ms |
| Concurrent real MCP reads | PASS | 24 calls / concurrency 4; p95 **1,250 ms**, zero errors; target <2,000 ms |
| Fresh container | PASS | Empty isolated history, eight scenarios/16 isolated records, authenticated/keyless evidence |
| SIGKILL and restart | PASS | Ready and exact completed evidence in **11.22 s**; target <30 s |
| Graceful restart/recreation | PASS | Exact persisted run/check payload equality |
| Incremental replay/concurrency | PASS | First 100 rows, subsequent zero; updates/tombstones once; parallel loaders commit a single increment |
| Interrupted pipeline | PASS | Actual killed subprocess rolls back uncommitted checkpoint/target changes; running marker blocks replay until explicit CLI recovery |
| SQLite locks | PASS | WAL reader sees committed data while writer holds lock; competing writer fails within tested 5 s busy-timeout bound |
| SQLite capacity/storage errors | PASS | Real SQLITE_FULL via page ceiling; finish transaction rolls back, no partial check set or false success |
| Actual full filesystem | PASS | New 2 MiB tmpfs exhausted; SQLite returned SQLITE_IOERR_SHMSIZE; no false success, explicit recovery and integrity check passed |
| Readiness/liveness | PASS | Storage failure/low free space => readiness 503, liveness stays 200; no private error text |
| Backup/restore | PASS | 1,000 runs/10,000 checks, exact logical SHA-256 and integrity; fresh app serves restored evidence; **0.203 s** backup+restore verification vs <60 s target |
| Storage growth | PASS | 7,139,328 bytes / 1,000 ten-check runs (~6.81 MiB; ~7.14 KB/run); all retained |
| Automated retention | FAIL | No approved purge/archive policy or scheduled retention job; no existing records deleted |
| Observability | PASS locally | Generated request IDs/status/duration and safe route templates; credential/raw-input exclusion tested |
| Off-host DR, alert delivery, Azure VM/kernel failure | NOT TESTED | No production environment provisioned; local fixtures do not prove these |

At this synthetic record size, hourly runs for one pipeline imply ~62.5 MB/year;
minute-frequency runs ~3.75 GB/year, excluding source fixtures, WAL headroom, logs,
indexes changing with scale and backup copies. These are estimates, not capacity
guarantees. Retention and alert thresholds must be chosen before production.
SQLite remains appropriate only for the measured single-host scope. PostgreSQL
would support multi-host writers/replicas and managed recovery but requires schema,
transaction/pooling, migration, private networking and cost work. No database was replaced.

## Azure architecture, costs and operational acceptance

The [complete design](azure-production-design.md) covers private access, SSH and
application authorization, local stdio MCP, managed identity/secrets, data disk,
private Blob backup, logs/alerts, egress, cost controls, deployment/rollback and
cleanup. Bv1's newly documented End-of-Life status invalidates the old B1ms choice;
the template now proposes B2als_v2 with a data disk and identity. It compiles, but
mounting, scoped role assignments, secret bootstrap, backups, private deployment
automation, alert routes and cloud rollback are **not operationally validated**.

Fresh Canada Central USD retail estimate: **$260.71/month dedicated private network**,
or **$59.96/month incremental plus allocated existing VPN/NAT infrastructure costs**.
Includes compute, two disks, transactions, private endpoints/DNS, private backups,
Key Vault, logs/alerts, egress and gateway/IP processing assumptions. AI is $0 while
disabled; the optional bounded-use example is ~$5.38/month. Tax, FX, labor and
unselected HA/managed DB/extra source connectivity are explicitly scoped in the model.
An application-only VM subtotal is not a complete operating quote.

## Requirement disposition

PASS means the stated scoped local evidence exists, not blanket production approval.
BLOCKED means external credentials, approval or an owner decision is required.

| Requested requirement | Status | Scope / remaining dependency |
|---|---|---|
| Phase 1.1 repository/status audit | PASS | Tracked source, scripts, config, templates, workflow, tests and docs reviewed; initial tree clean |
| 1.2 current dependency/container scans | PASS | Fresh public vulnerability database and lock audits |
| 1.3–1.4 unique advisories/classification/paths | PASS | 78-row register; eight HIGH dispositions; runtime applicability limits explicit |
| 1.5 supported security upgrades | PASS | Current base verified, fresh apt upgrade; no listed stable fix or Python advisory; missing ODBC dependency repaired |
| 1.6 alternatives/removal/compensating controls | PASS | Older stable/unstable/minimal image/ODBC trade-offs reviewed; privilege bits removed without suppressing findings |
| 1.7 residual-risk acceptance | BLOCKED | No formal owner acceptance; strict release gate fails |
| 1.8 auth/session/token/log/error audit | PASS | Implemented controls tested; enterprise identity gaps remain FAIL |
| 1.9 MCP boundaries | PASS | Registration, real concurrency, auth, scope, byte/row bounds tested |
| 1.10 real SQL least privilege | BLOCKED | No configured source identity; code/mock checks pass |
| 1.11 untrusted data / AI action boundary | PASS scoped | Curated output/reference checks; approved synthetic live injection controls passed; no autonomous action tools |
| 1.12 working tree/history secrets | PASS | Publishable files and full reachable history scanned; private ignored runtime secrets not copied to Git |
| Phase 2 evidence architecture / expected dataset | PASS | Explicit projection and 18 reproducible offline cases |
| 2 duplicate/reference/row/schema/pipeline/missing evidence | PASS scoped | Offline and approved synthetic live expectations preserved; no real business evidence sent |
| 2 hallucination/injection/contract/fallback | PASS offline | Invalid IDs/categories/extra fields/refusal/errors rejected |
| 2 token/spend limits/redaction | PASS bounded controls | Byte/output/request caps and redaction tested; no exact dollar cap/general DLP or absolute slow-stream deadline |
| 2 original live AI | Historical FAIL | Original 12-attempt evaluation remains 11 PASS / 1 healthy reference-selection FAIL; safe fallback; no retries |
| 2 targeted healthy fix and controls | PASS scoped | Separately approved three-attempt retest: 3 PASS; exact references, unavailable validation, duplicate measurement/tolerance; no retries |
| 2 autonomous MCP selection | NOT TESTED | Unsupported, not represented as working |
| Phase 3.1–3.2 HTTP/MCP concurrency | PASS | Measured targets above; no sustained multi-hour soak claim |
| 3.3–3.5 incremental/idempotency/checkpoints/SQLite | PASS | Atomicity, replay, parallel load and busy timeout |
| 3.6–3.7 termination/interruption | PASS | Isolated SIGKILL and killed writer; operator recovery |
| 3.8 disk-full/storage errors | PASS | Both SQLite page ceiling and actual disposable tmpfs exhaustion |
| 3.9 backup/restore | PASS local | Exact snapshot and fresh restored app; cloud recovery NOT TESTED |
| 3.10 growth/retention | FAIL production retention | Growth measured/preservation passed; policy and scheduler absent |
| 3.11 health/readiness | PASS | Readability and free-space guard, sanitized failure |
| 3.12 logging/observability | PASS local | Structured events; delivery/on-call operationally NOT TESTED |
| Phase 4 architecture/alternatives/full costs | PASS design | Current official sources and fresh retail meters; prerequisites documented |
| 4 actual private routing, identities, secrets, backups, monitoring | BLOCKED | Requires approved Azure environment and owner configuration |
| 4 deployment/rollback/shutdown/cleanup execution | NOT TESTED | Design only; no resources provisioned |
| Phase 5 focused fixes/regressions/reproducibility | PASS | Two implementation/validation commits, cross-platform tests and harnesses |
| 5 preserve source/history/functionality | PASS | No NorthstarBI data changes; original 17-run hash unchanged; ODBC functionality repaired |
| 5 publish new commits / hosted Actions | Pending at report preparation | Owner authorized publication after the 199-test local pass; verify final SHA and hosted job outcomes independently of production acceptance |

Remaining acceptance decisions: (1) resolve or formally accept each image residual;
(2) select single-operator versus enterprise identity scope; (3) supply DBA-approved
source grants/TLS/route; (4) define ongoing AI evaluation/monitoring beyond the passing bounded retest;
(5) approve region, complete cost envelope and private connectivity;
(6) implement and test off-host backup/restore, retention, patching, alert delivery
and cloud deployment/rollback. No automatic approval, risk waiver or paid action
is inferred from completing the local work.

## Reproduction and local evidence

From the repository root with the development environment installed:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=dqagent --cov-branch --cov-fail-under=80
.\.venv\Scripts\python.exe -m pytest -q tests/test_ai_evaluation.py
.\.venv\Scripts\python.exe scripts/docker_acceptance.py
.\.venv\Scripts\python.exe -m scripts.storage_acceptance
.\.venv\Scripts\python.exe scripts/scan_secrets.py --history
.\.local\gitleaks\gitleaks.exe git . --log-opts=--all --redact
.\.local\trivy\trivy.exe image --scanners vuln --severity HIGH,CRITICAL --exit-code 1 dqaccept9b270dba:acceptance
```

The last command is intentionally expected to FAIL until the findings are resolved;
do not add ignore flags to turn it green. `docker_acceptance.py` uses a unique new
project/volume and stops its own containers; it never invokes the existing Compose
project. It retains its synthetic volume and candidate images for inspection.
The full-disk harness must be run only in its guarded empty tmpfs:

```powershell
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs '/data:size=2m,uid=10001,gid=10001' --tmpfs '/tmp:size=8m' --mount "type=bind,source=$PWD/scripts/full_disk_acceptance.py,target=/probe.py,readonly" --entrypoint python -e PYTHONPATH=/app dqaccept9b270dba:acceptance /probe.py --isolated-tmpfs
```

Local ignored evidence: `hardening-tests.xml`, `hardening-coverage.json`,
`hardening-offline-eval.xml`, `hardening-docker-results.json`,
`hardening-docker-detail.log`, `hardening-storage.json`, `hardening-full-disk.json`,
`hardening-image-after.json`, `hardening-release-gate.json`,
`hardening-advisory-dispositions.json`, `hardening-*-audit.json`,
`hardening-gitleaks-*.json`, `hardening-history-before.json`,
`hardening-history-after.json`, `hardening-azure-prices.json` and
`hardening-github-status.json`, all under `artifacts/`. Artifacts/private databases
and credentials are not committed. The live dashboard remains available at its
existing localhost address for the next owner-controlled demonstration.
