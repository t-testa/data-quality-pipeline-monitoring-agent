# Production-readiness and portfolio acceptance — 2026-10-11

**Decision: suitable for a private, single-operator portfolio demonstration after local checks; not approved for production deployment. No Azure resources, paid model calls or GitHub publication were performed.**

| Status | Acceptance item | Evidence / limit |
|---|---|---|
| PASS | Original claim reproduced | 53 tests passed; 91.70% statement coverage before review changes. |
| PASS | Expanded Windows regression suite | 72 passed; 92.36% statements, 80.45% branches, 89.65% combined coverage. One upstream deprecation warning. |
| PASS | Final Linux regression suite | 72 passed on Python 3.12.15; 89.65% combined coverage. |
| PASS | Fresh Docker and persistent history | Isolated no-cache build, empty volume, 16 synthetic runs, exact restart/recreation equality, online backup restoration and UID 10001 verified. |
| PASS | Python dependency security | Runtime, development and toolchain lockfile audits report no known advisories; pip check and hash-verified installation pass. |
| PASS | Source warning investigation | Read-only investigation completed; source-derived findings and records are excluded from Git and retained only in ignored private local artifacts. |
| PASS | AI deterministic safety boundary | Recorded failure scenarios, no-key behavior, invalid/foreign IDs, unsupported output, provider failure, hostile questions/source strings and concurrent budget tested. All facts retained even when model selects a subset. |
| PASS | Local CI validation | actionlint 1.7.12 passes; platform tests, lint, audits and Docker commands executed locally. Actions and scanner pinned; read-only workflow permissions. |
| PASS | Private publishing preparation | Sanitized README/portfolio, publishing checklist, ignored private artifacts, worktree and reachable-history heuristic secret scan. No remote configured. |
| PASS | Azure template review | Both Bicep templates compile. Private NIC, SSH-key access, loopback app binding and persistent disk design reviewed; this is not deployment validation. |
| FAIL | Unconditional production security acceptance | OS image advisories remain; package audit success alone cannot establish security. See image review below. |
| FAIL | Complete Azure operating-cost quote | Earlier $4–5 / $20–22 monthly figures are application subtotals. Private access, egress, backups and operations are unresolved, not zero. |
| BLOCKED | GitHub-hosted CI verification | Repository is unpublished; no run URL or green hosted run exists. Local checks cannot verify GitHub execution. |
| BLOCKED | Routine real-source operation | Dedicated least-privilege SQL identity and approved remote certificate/network path are not supplied. Source identity approval remains an operator prerequisite. |
| BLOCKED | Azure deployment | User explicitly withheld approval; connectivity, complete cost envelope and production gates remain unresolved. |
| NOT TESTED | Live model/account behavior | No paid API call; model-specific refusal, latency, service availability and live prompt-injection behavior are not verified. |
| NOT TESTED | Production resilience and scale | Disk-full/corruption/power-loss tests, long-duration load, large source volumes, off-host disaster recovery, external scheduler/alerting, Entra access and Azure network paths. |

## What coverage misses

The original percentage counted executed Python statements. It did not measure browser JavaScript, container OS packages, actual hosted CI, cloud policies, live model correctness or business semantics. Current branch coverage is only 80.45%, and CLI/source integration paths remain relatively weak. A line executing does not prove correct behavior under all null/type/timezone/threshold combinations.

SQLite transaction tests are not a proof of cross-system atomicity: a process can die after target commit but before metadata finalization. Source checks are separate SELECTs, so changing source data can create apparent reconciliation differences. Concurrency tests cover one-host locks and AI budgets, not sustained production traffic. No row-level equality, historical price policy or real freshness SLA is inferred from aggregate checks. Python 3.12 is verified; the declared 3.11/3.13 range is not independently tested.

## Locally resolved findings

Filtered evidence now applies table/freshness matching before its output limit. AI can prioritize findings but cannot hide recorded failures. Request bodies have bounded memory and a receive deadline; non-ASCII invalid credentials return 401. Readiness checks metadata access. Future metadata schema versions fail closed. POSIX secret creation requests mode 600. Docker uses a digest-pinned Debian 13 base, removes build-time curl and runtime installers, and retains hash-verified dependencies. CI scans both application and development dependencies, the toolchain and fixable high/critical image advisories.

## Image security review

The initial Debian 12 scan found 350 package/advisory occurrences, including two critical and 66 high. Debian's tracker identifies [CVE-2025-7458](https://security-tracker.debian.org/tracker/CVE-2025-7458) as fixed in Debian 13; it requires attacker-controlled SQL, which the exposed API does not offer. The other initial critical, [CVE-2023-45853](https://security-tracker.debian.org/tracker/CVE-2023-45853), concerns MiniZip code that Debian says is not built into the affected Bookworm zlib binary. The base was upgraded rather than silently suppressing either finding. Pip and its bundled libraries were removed from runtime after dependency installation. Scanner severity is a triage signal, not proof of exploitability; no exploit was attempted.

Final Trivy 0.75.0 scan: **0 critical, 44 high, 64 medium, 78 low, 1 unknown package/advisory occurrences; 0 findings with an available fixed version in the scanner data.** The 44 high occurrences represent eight distinct advisories, often repeated across binaries from the same source package. They concern util-linux, acl, ncurses, systemd and perl components. SQLite is now 3.46.1, ODBC 18 is registered, and runtime pip is absent. The complete unsuppressed scan is in ignored `artifacts/container-vulnerabilities-final.json`; the CI gate deliberately covers the narrower fixable-high/critical subset.

Remaining unfixed OS findings need package-specific applicability review or a hardened replacement image before production approval. Non-root execution, dropped capabilities, a read-only filesystem and no arbitrary command/SQL interface reduce exposure but are not a blanket waiver. No CVE suppression file was added.

## Azure operating acceptance

See the [audited proposal](deployment.md). The VM compute/disk estimate is conditional on existing private access and egress. A new gateway design can dominate the subtotal. Shared network costs and external AI charges can fall outside the proposed resource-group budget, and budget alerts do not cap spending. Private route, egress, SQL access, backup retention/RPO/RTO and operator responsibilities must be decided before a total is approvable. No free Bastion native tunnel is assumed.

Shared bearer roles support the intended trusted operator; there is no individual identity/MFA or per-user audit trail. Persistent disk survives restart but does not provide off-host recovery or high availability. Deallocate to stop compute billing, retain/price disks deliberately, and clean up only reviewed project resources after exporting verified backups. None of those cloud operations was performed.

## Evidence and reproduction

Use README test commands, `python scripts/scan_secrets.py --history` and `python scripts/docker_acceptance.py`. The latter builds without cache into a fresh isolated project/volume, generates separate credentials, validates empty history, records eight synthetic scenarios, compares exact history after restart/recreation, restores a SQLite backup and runs Linux tests. It stops its containers while retaining its isolated volume. Detailed source records and scanner/test JSON stay under ignored `artifacts/`; do not publish them. The local main demonstration volume remains separate.
