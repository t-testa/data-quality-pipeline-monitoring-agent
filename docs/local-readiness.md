# Local portfolio preparation and validation — 2026-10-11

**Decision:** retain a private, locally hosted Docker application with no additional
hosting subscription. Azure is officially postponed for cost. This is a tested
portfolio environment, not production release approval or a security risk waiver.
No Azure resource, paid API call, external exposure or new paid service was created.

## Preservation and prepared artifacts

The existing dashboard was not stopped, replaced or reconfigured. Before/after
read-only monitoring snapshots contained **17 runs and 160 check records**, with
identical logical SQLite SHA-256:
`5f8a09039fb07e3c764170a6bc4e18f212ade4d6d2efa3b3566fc7801dfedb99`.
These are local monitoring counts, not source business statistics. Its existing
image and `dataqualityagent_monitoring-data` volume remain unchanged. No source
system was queried or modified.

Prepared separately:

- `compose.local.yaml`: inherits current hardening, explicitly selects an existing
  external volume, retains loopback access and restart policy, bounds PIDs and
  disables AI/source connections for synthetic portfolio operation.
- `scripts.local_snapshot.py`: full stopped-volume backup; checksums, safe archive
  member handling, restore to a new volume and SQLite integrity verification.
  No automatic stopping, overwriting, volume deletion or retention purge.
- `scripts.local_deployment_acceptance.py`: disposable Compose/restart/MCP/full
  recovery drill against new synthetic volumes; no operator credentials or history.
- Test-image repair: include the previously missing targeted evaluator plus new
  snapshot tests. Application runtime code and the existing CI workflow are unchanged.
- [Local operating guide](deployment.md), [sanitized case study](portfolio.md),
  [architecture diagram](portfolio-architecture.md), [Tailscale assessment](tailscale-evaluation.md).

The candidate was built without cache using the unchanged supported pinned base,
with current stable package upgrades. Runtime image:
`sha256:a6a750a62fe20352d2f327b1958ef04f2fa9a5aaee8a1fc0b75600e4edad53fd`.
It has **not** been rolled out over the existing dashboard. Any activation requires
separate approval and a verified backup/downtime plan.

## Automated verification

| Check | Status | Scope |
|---|---|---|
| Full Windows suite | PASS | 209 tests, 78.35 s, Python 3.12.10 |
| Full Linux suite | PASS | 209 tests, 14.97 s, Python 3.12.15; disposable network-disabled container |
| Application coverage | PASS | 92.94% combined statement/branch; diagnostics 100%; not a claim of 100% coverage of backup scripts |
| New snapshot regressions | PASS | 10 cases: full history/checkpoints, replay, active-volume refusal, existing destination refusal, corruption, traversal, links and duplicate archive names |
| Prepared Compose configuration | PASS isolated | Fresh start/health on loopback; blank AI/source settings; inherited non-root/resource/security controls; explicit external volume |
| Automatic process restart | PASS isolated | Recovered in 6.97 s with an increased Docker restart count; complete recorded run/check evidence unchanged |
| Full-volume backup and restore | PASS isolated | Active-volume refusal; new-volume restore; three SQLite databases pass integrity; fresh service returns the same four recorded fixture runs/checks; incremental replay processes zero new records |
| MCP continuity | PASS isolated | Actual stdio initialization, nine tools discovered, authenticated incident evidence retrieved |
| ODBC compatibility | PASS locally | Microsoft ODBC Driver 18, package 18.7.1.1-1; registration, shared-library load and `ldd` resolution; no live SQL login attempted |
| Hosted CI baseline | PASS for e95a822 only | [Run 38164558506](https://github.com/t-testa/data-quality-pipeline-monitoring-agent/actions/runs/38164558506): 199 tests on each OS, secret/dependency audits, container/restart checks; new local work not covered by that run |
| Current production vulnerability gate | FAIL | 44 HIGH occurrences, eight unique HIGHs, no listed stable fix; none suppressed or accepted |
| Actual production workloads | NOT TESTED | No production source identity, volume/concurrency guarantee, SLA or live operating environment |

One existing upstream Starlette/AnyIO deprecation warning remains. Coverage does
not prove permissions, source consistency, live workload capacity or failure
recovery under every host/filesystem condition.

The Compose trial exposed platform-specific test conditions: Docker Desktop did
not publish ports on an internal-only network, so the prepared profile uses a
normal bridge with loopback-only publication; this is not an egress firewall.
The restart drill uses Uvicorn's handled SIGTERM to trigger process exit without
Docker's manual-stop flag and refreshes the ephemeral test port during bounded
readiness polling. Exact evidence equality is still required after recovery.
The actual configured application port remains fixed at 8765.

## Vulnerability investigation

Fresh Trivy data downloaded at 18:50:47Z; database updated at 13:06:05Z. The rebuilt
candidate retains **44 HIGH, 66 MEDIUM, 82 LOW, 1 UNKNOWN, zero CRITICAL** occurrences
across 78 unique advisories. Python package findings remain zero. The unsuppressed
HIGH/CRITICAL scan exited 1; the CI fixable-only gate was not altered or substituted
for production acceptance.

All eight [HIGH tracker entries](vulnerability-register.md) still list Debian
trixie as vulnerable. Testing/unstable fixes are not supported stable replacements.
The ACL fix changes ABI and is queued for a point release; Perl notes pending
regression resolution. A fresh stable rebuild did not remediate the findings.
Removing ODBC or installing mixed-distribution libraries was not performed.

Candidate inspection reconfirmed UID 10001, no setid files under `/usr`, loadable
ODBC with no unresolved shared libraries, no systemd-homed executable and no
Archive::Tar module in the installed Perl tree. `infocmp` remains present. These
are bounded applicability/mitigation facts, not CVE fixes or acceptance. The host
kernel, Docker Desktop and administrator access are separate trust boundaries.

Next step is a supported stable update or a fully qualified alternative runtime.
Rebuild, rescan, rerun unit/ODBC/MCP/recovery checks and review an approved upgrade
when that changes. No security suppression, paid service or recurring automation
was introduced.

## What remains unverified

- Existing service activation of the new candidate/profile, host reboot/login,
  Docker Desktop startup and suspension behavior. Process restart alone is not
  host recovery; an unhealthy live process is not automatically restarted.
- Independent encrypted backup media/off-host recovery, automated retention,
  alert delivery, real recovery-point/time objectives and prolonged soak/load.
- Real source least-privilege grants, TLS trust, query semantics and stable-window
  reconciliation; the adapter is preserved, not exercised against private data.
- Per-user identity/MFA/revocation, multi-tenant authorization, distributed storage,
  multi-host operation and actual production workload acceptance.
- Tailscale plan eligibility, enrollment, access rules, remote HTTPS/MCP and
  revocation. It remains disabled; public Funnel is excluded.
- Any Azure deployment, recurring hosting bill or production release. Azure design
  artifacts are retained only as postponed engineering history.

Local evidence under ignored `artifacts/`: `local-preparation-tests.xml`,
`local-preparation-coverage.json`, `local-linux-tests.log`,
`local-deployment-acceptance.json`, `local-runtime-probe.json`,
`local-candidate-vulnerabilities.json`, `local-candidate-release-gate.json`.
Private backups and synthetic scratch volumes remain local and are not published.
