# Local Docker operations — Azure postponed

**Decision, 2026-10-11:** keep Northwatch private on the existing computer. Azure
is postponed because its complete recurring cost is too high. No new hosting,
paid AI, remote exposure or deployment is authorized. This prepared configuration
is an operator-reviewed next step, not a replacement of the running app.

The target is **$0 additional hosting/service subscriptions**, using existing
hardware, storage and internet. Electricity, disk capacity and operator time are
not literally zero. Docker Desktop is free for eligible personal use; reassess
before business use ([Docker licensing](https://docs.docker.com/desktop/setup/install/windows-install/)).
No paid registry, domain, VPN, database or cloud backup is required. Existing CI
checks remain unchanged; private Actions usage must stay within the account's
included allowance/spending policy.

## Prepared local configuration

`compose.local.yaml` inherits the existing service, with explicit external-volume
selection, PID limit, stop grace period and health-check timings. It uses a separate
`northwatch-local:candidate` image so a build does not replace the running image
tag. It retains loopback `127.0.0.1:8765`, UID 10001, one worker, read-only root,
dropped capabilities, no-new-privileges, 512 MiB/one CPU, bounded logs and
`restart: unless-stopped`.

The bridge network permits outbound traffic; it is not an egress firewall. Paid
calls are disabled by empty key/model configuration. An `internal` Docker network
was tested but this Docker Desktop engine did not publish its loopback port, so
it is not used. No LAN/public listener or host firewall exception was added.

The portfolio configuration overrides API key, model and source URL to empty
values. The original `.env`, default Compose file, SQL Server adapter and optional
AI code remain intact. This profile is synthetic and cannot invoke paid AI.
Deterministic investigation and all nine MCP tools remain available. Connecting
real sources or enabling AI requires separate review.

The existing history volume is `dataqualityagent_monitoring-data`. Do not assume
a new Compose project selects it. Required `NORTHWATCH_DATA_VOLUME` explicitly
selects an existing volume; `external: true` refuses a missing one and keeps it
outside Compose cleanup. Never run two instances against the same volume. The
candidate has not been activated against the existing history.

## Build and preflight

From the repository root, with the hash-locked development environment installed:

```powershell
docker build --pull -t northwatch-local:candidate .
$env:NORTHWATCH_DATA_VOLUME = 'dataqualityagent_monitoring-data'
docker volume inspect $env:NORTHWATCH_DATA_VOLUME --format '{{.Name}}'
docker compose -f compose.local.yaml config --quiet
.\.venv\Scripts\python.exe -m scripts.local_deployment_acceptance
```

The acceptance harness uses a unique project, synthetic tokens, new volumes and
an ephemeral loopback port. It stops its own containers afterward and retains its
test volumes/backups for inspection. It never starts the operator's Compose project.
Do not print expanded Compose configuration: it can contain secrets. Do not use
`init` to overwrite the existing `.env`.

## Full-volume backup and restore drill

Existing `scripts.backup` supports online **metadata-only** SQLite backup. It reads
the host's configured data directory, not automatically Docker's volume, and omits
synthetic warehouses/checkpoints. `scripts.local_snapshot` supplies a separate
**stopped-volume** procedure and refuses running containers using that volume.
Keep host writers stopped too and prevent another operator starting writers during
the copy. The Docker check is not a distributed lock or protection from a host admin.

Its helper has no network, Docker socket or credentials, runs unprivileged with a
read-only root, and copies the complete volume including SQLite WAL files and
loader checkpoints. It never stops services or deletes volumes itself.

These operational commands require an approved downtime window. This task tested
them only on disposable synthetic volumes:

```powershell
docker compose stop monitor
$snapshot = Join-Path $PWD ('.local/backups/northwatch-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.tar.gz')
.\.venv\Scripts\python.exe -m scripts.local_snapshot backup dataqualityagent_monitoring-data $snapshot
docker compose start monitor

# Restore to a NEW volume, without overwriting the original.
$restoreVolume = 'northwatch-restore-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
.\.venv\Scripts\python.exe -m scripts.local_snapshot restore $restoreVolume $snapshot
```

The archive and checksum sidecar must both be new. An interrupted backup can leave
a partial file; choose a new filename and inspect the failed one. Restore requires
a matching SHA-256, rejects links/path traversal, refuses existing volumes/nonempty
destinations, checks space and runs SQLite integrity checks. Failed restores stay
isolated in the new volume; do not start an app on one. Checksums detect corruption,
not replacement of both files. Restore only your own trusted backups.

Protect `.local/backups` with Windows ACLs (or a directory writable by UID 10001 on
Linux), host disk encryption and an existing encrypted removable copy if available.
The tool does not encrypt archives. Backups contain private evidence and must never
enter Git or screenshots. No automatic retention/deletion job was introduced. A
second copy on the same disk is not hardware-loss recovery. Back up after meaningful
demo changes/before upgrades, and periodically repeat a restore drill.

## Activation and rollback — not executed

After separate approval, take a verified backup, stop the old service, and run
`docker compose -f compose.local.yaml up -d --no-build --wait` with the intended
volume selected. Confirm health, full run/check evidence, deterministic investigation
and MCP before accepting the switch. Retain the old image and volume. Rollback
uses the prior compatible image/configuration and a separate verified restored
volume; never overwrite the only copy. This profile introduces no schema migration.

An intentional `stop` remains stopped under `unless-stopped`. Process failure can
restart automatically; an unhealthy but running process is only marked unhealthy.
No health-triggered auto-healing service was added. Docker must be running; host
sleep, reboot, power loss or disk failure interrupts access. Boot/login recovery
and off-host disaster recovery remain unverified.

## Security and deferred remote/cloud access

The 44 HIGH findings remain unresolved and unaccepted. Local hosting does not
remediate them. See [local validation](local-readiness.md) and the
[advisory register](vulnerability-register.md). No external exposure is authorized.
[Tailscale](tailscale-evaluation.md) is evaluated only; no installation, enrollment,
sharing, Serve/Funnel or firewall change occurred. Use in-person or an existing
screen-sharing demonstration for now.

The [archived Azure proposal](azure-deployment-proposal.md),
[full cost model](azure-production-design.md) and templates remain as engineering
history. They are **postponed, not approved for execution**. No Azure resource was
created by this work.
