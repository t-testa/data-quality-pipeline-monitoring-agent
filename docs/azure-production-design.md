# Azure production design and complete planning estimate

Review date: 2026-10-11. **Design only; deployment BLOCKED.** No Azure resource,
paid model call, public application endpoint or infrastructure change was made.
The private GitHub repository is not an application network boundary.

## Recommended topology and release conditions

For the current low-volume single-operator workload, retain one VM, one API
worker, one local SQLite WAL database and a single application replica. B2als_v2
(2 vCPU/4 GiB) is a starting estimate, not a verified Azure capacity result;
burstable CPU credits and sustained load must be measured before acceptance.
Use a separate 32 GiB managed data disk mounted at /srv/northwatch for monitoring
storage, rather than relying on an OS-disk Docker volume. The revised Bicep
template includes a detached-on-delete data disk and system-assigned identity;
formatting/mounting it, scoped role assignments and backup automation are still
operator deployment work, not completed cloud configuration.

The previous B1ms proposal is superseded: Microsoft now lists the
[Bv1 family as End of Life](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bv1-series)
and recommends current sizes for new deployments. The
[Basv2 replacement](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/basv2-series)
is x64 and retains compatibility with the tested image. Regional capacity,
quota, Trusted Launch/image compatibility and actual CPU credit behavior still
require preflight validation; none is implied by a retail price entry.

Application access: approved private VPN route -> private VM SSH public-key
authentication -> localhost SSH tunnel -> application bearer authentication.
Do not attach a public IP to the VM or open port 8765 on its NSG. A new VPN/NAT
gateway has public infrastructure addresses; that does not make the application
public. If “no public infrastructure addresses anywhere” is required, reuse an
approved private corporate route/ExpressRoute and obtain its actual allocation.
The existing subnet, operator CIDR, source route, DNS and outbound policy are
unverified. Reject broad/public operator CIDRs. Permit egress only to required
package/image, monitoring, storage and optional model endpoints through an
approved firewall/proxy policy; NAT alone does not restrict destinations.

MCP remains local stdio on the trusted operator machine, using its API connection
through the tunnel. No remote MCP listener is proposed. Read tokens authorize all
workspace evidence; they are not per-user or per-pipeline access controls. For
multiple users, individual Entra identities, revocation, role/scope authorization
and attributable auditing are acceptance blockers. They are not implemented by
the VM template or this hardening patch. Single-operator shared-token operation
requires an explicit scope decision; it is not equivalent to enterprise SSO.

Secrets: give the VM a managed identity with only Key Vault secret-read and
backup-container Blob Data Contributor scope. Retrieve required secrets into an
operator-owned mode-600 runtime file (Windows equivalents require ACLs), outside
images, Git and deployment output. Use private endpoints/DNS for Key Vault and
Blob, disable their public network access, and rotate/restart through a reviewed
procedure. This provisioning/rotation automation is not deployed or verified.
An ACL-protected local secret file is a lower-cost single-operator alternative,
but retains manual rotation and host-administrator trust.

Source: a separately provisioned SELECT-only SQL identity, validated server TLS
certificate and approved private network route. Both source scripts now reject
TLS bypass and elevated/write-capable monitored-object access. Those application
checks do not prove the real account's grants: DBA verification of all effective
grants, roles, procedures and impersonation is still required. No live source
identity or remote source path was exercised in this review.

Recovery: daily consistent SQLite backup to private encrypted Blob; keep 30 daily
copies, prohibit overwrite of an existing local backup, verify integrity, and
restore into a separate stopped instance monthly. Retain two approved image
digests and versioned configuration. Target RPO <=24 h and operator-assisted
RTO <=60 min. Local tests prove snapshot integrity, not off-host Azure recovery.
Backup retention must be distinguished from monitoring-history retention; no
history purge has been scheduled or approved. Alert before disk exhaustion.

Observability: collect bounded JSON request events (generated ID, route template,
status, duration), container health/readiness, disk capacity, backup freshness,
failed/interrupted pipeline counts and unexpected process restarts. Do not ingest
raw query strings, headers, bodies or source/provider errors. Configure a missing
heartbeat/backup log alert and capacity/error metric alerts to an owned action
group. Structured local logging works; delivery and on-call ownership remain
unverified. The 64 MiB readiness guard is not a substitute for early capacity alerts.

Deployment automation design: CI produces immutable tested image + full scan;
release requires approved residual risks and spending. An approved runner with
private connectivity transfers that image, checks disk and backup integrity,
stops writers, starts the approved digest, waits for readiness and runs read-only
smoke tests. On failure restore the previous digest and a schema-compatible backup.
No cloud credentials are placed in Git; use scoped workload identity if GitHub
deployment is later enabled. The existing CI is validation-only; this private
deployment/rollback job remains NOT TESTED and must not be presented as operational.

## Monthly cost model

USD retail, Canada Central, 730-hour month, Linux PAYG. Rates freshly read from
the [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
on 2026-10-11; exact meter records are retained locally in
`artifacts/hardening-azure-prices.json`. No free allowance, negotiated discount or
free GitHub minutes is assumed in the total. Usage estimates are not hard caps.

| Component | Explicit assumption | Monthly USD |
|---|---|---:|
| VM compute | B2als_v2 $0.0418/h x 730 | 30.51 |
| OS disk | E4 Standard SSD LRS 32 GiB | 2.64 |
| Monitoring data disk | Second E4 32 GiB | 2.64 |
| SSD operations | $0.002/10K; allowance for 5M operations | 1.00 |
| Backup Blob capacity | Hot LRS 5 GB x $0.02 | 0.10 |
| Backup operations | 1,000 writes + small reads/list allowance; rounded up | 0.02 |
| Blob + Key Vault private endpoints | 2 x $0.01/h x 730 | 14.60 |
| Private Link processing | 10 GB x $0.01 | 0.10 |
| Private DNS | 2 zones x $0.50 + 100K queries at $0.40/M | 1.04 |
| Key Vault operations | Budget 10K standard operations x $0.03/10K | 0.03 |
| Central logs | 1 GB at $2.76; no free ingestion grant assumed | 2.76 |
| Alerts + email | Two 5-minute system-log alerts at $1.50 plus two metric alerts at $0.10; low-volume email rounds to <$0.01 | 3.20 |
| Internet egress | 10 GB x $0.087, conservatively treating free tier as already used | 0.87 |
| VPN gateway | VpnGw1AZ $0.21/h x 730 | 153.30 |
| VPN public infrastructure IP | One standard IPv4 $0.005/h x 730; single active gateway | 3.65 |
| P2S connection allowance | One billable connection $0.01/h x 730; conservatively before SKU inclusions | 7.30 |
| NAT gateway | Standard $0.045/h x 730 | 32.85 |
| NAT public infrastructure IP | One standard IPv4 $0.005/h x 730 | 3.65 |
| NAT processing | 10 GB x $0.045 | 0.45 |
| Optional AI | Disabled | 0.00 |
| Registry | No ACR: transfer reviewed image archive through private SSH | 0.00 |
| **Dedicated-network total** | Rounded planning estimate | **260.71** |

If a verified existing VPN, its public IP/connection entitlement and NAT gateway/IP
are reused, incremental service cost is **$59.96/month plus the organization's
allocated cost for that shared infrastructure**. Do not call the shared assets
economically free. At only 40 VM hours/month, subtract $28.84 of compute: about
$231.87 dedicated or $31.12 incremental-plus-allocation. Gateways, private
endpoints, disks and retained storage still bill when the VM is deallocated.
Allow ~$290/month before tax for the dedicated scenario (about 10% contingency).

This includes a single-region managed disk and small Blob backup, not a second
warm VM, zone failover, geo-replicated backup, Azure Backup VM protection, Bastion,
Defender paid plans, a managed database or paid Entra licensing. None is selected
implicitly. A site-to-site source link can add a metered connection ($0.015/h,
$10.95/month) and on-premises appliance/ISP costs. Those are not needed for the
synthetic-only estimate; real NorthstarBI deployment is blocked until that route
and its quote are approved. Larger data, longer log retention, more alerts, data
disk mounts/shared-disk features, redundancy and cross-region traffic change the
quote. Tax, FX and operator labor are additional; workload/billing-account details
must be confirmed before approval. Private-repository CI usage is an existing
GitHub account cost, with incremental cost dependent on its remaining allowance.

Optional AI planning example: `gpt-4.1-mini-2025-04-14`, currently $0.40/M input and
$1.60/M output tokens ([official model pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini)).
For 12 synthetic live evaluation calls, budget conservatively 20,000 input tokens
(bounded input plus instruction/schema allowance) and 600 output tokens each:
12 x (20,000 x 0.40/M + 600 x 1.60/M) = **$0.10752**. Request approval for a
**US$0.20 maximum evaluation budget**, no retries, no tools and no real source rows.
No model is enabled or live-tested yet. At 20 maximum-sized calls/day for 30 days,
the same estimate is ~$5.38/month, separately billed from Azure. Model/provider
account availability and actual token usage remain unverified. The application's
request/byte/output limits are not a cross-provider dollar spending cap.

## Alternatives and lifecycle

| Option | Fit and trade-off | Decision |
|---|---|---|
| Existing private local host | No new Azure recurring cost; existing hardware, power, backups and operator effort still apply | Lowest incremental cost while deployment blockers remain |
| Single private VM | Matches tested single-host SQLite; predictable cost; manual recovery and no HA | Proposed small-workload topology, approval pending |
| Container Apps with Azure Files | Elastic compute, but shared/network filesystem WAL is unsuitable; replicas risk invalid storage assumptions | Do not move this SQLite volume onto SMB/NFS |
| Container Apps/App Service + PostgreSQL | Supports concurrent replicas and managed database recovery; adds schema/migration, transaction, connection-pool, deployment, private network and always-on DB costs | Present separate migration and regional SKU quote if HA/multi-host is required; no migration performed |
| AKS | Adds orchestration, node and control/operations costs without a demonstrated need | Not justified for this workload |

SQLite WAL requires same-host participants ([SQLite WAL documentation](https://sqlite.org/wal.html)).
Container Apps persistence/billing are separate from scale-to-zero compute
([storage](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts),
[billing](https://learn.microsoft.com/en-us/azure/container-apps/billing)). The local
load result supports a bounded single-operator deployment; it does not demonstrate
HA, unlimited history, multi-worker budgets or distributed writers.

Budget alerts at 50/80/100% must cover both dedicated and allocated network costs;
Azure alerts are not enforced spending caps. External OpenAI usage needs its own
account controls. Configure and verify deallocation on the approved schedule;
guest OS shutdown alone is not enough ([VM billing states](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing)).
Rollback retains the previous image/config and tested compatible backup. Cleanup
requires an approved inventory of only project-owned VM, disks, snapshots,
endpoints, gateways/IPs, DNS, logs, storage and identity grants; preserve required
evidence and never delete shared network resources. Neither shutdown automation,
cloud rollback nor resource cleanup was executed.
