# Private Azure deployment proposal — approval required

**No Azure resources have been created or deployed by this project.** Local operation and container validation come first. Infrastructure templates are a reviewable starting point; a private connectivity route and dedicated SQL identity still require owner configuration.

## Proposed deployment

Use one on-demand Ubuntu VM (`Standard_B1ms`) with a 32 GiB Standard SSD OS disk, private NIC, no public IP, SSH public-key login and a restrictive NSG. Reuse an **existing, verified private operator route** (VPN/private management host). The template requires the existing subnet ID and the operator's private CIDR. It creates neither a VPN nor a Bastion gateway. Outbound package/API access must be supplied by that network; after Azure's outbound-access changes do not assume a private VM has internet connectivity.

Run the tested Docker Compose service bound to the VM's loopback, with its named local volume on the managed disk. Reach it using `ssh -L 8765:127.0.0.1:8765 dqoperator@PRIVATE_IP` over the private route, then browse localhost. An application bearer token is still required. No application port is opened in the NSG. Disable optional AI unless explicitly configured. NorthstarBI remains local; an Azure-to-local private route and read-only credentials would be needed to monitor it. Until then Azure hosts synthetic demos only.

No private network, VPN route, source routing or regional VM capacity has been verified yet. Deployment must not proceed without these checks. If no existing private route is available, stop and quote that access infrastructure separately; never add a public IP as a shortcut.

## Costs and assumptions

USD public retail prices retrieved 2026-10-11 for Canada Central via the [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices). Re-run `python scripts/cost_quote.py` before approval. Tax, currency conversion and negotiated pricing excluded. No free grant assumed.

| Component | Assumption | Estimated monthly USD |
|---|---|---:|
| B1ms Linux compute | $0.023/hour, 40 demo hours | $0.92 |
| B1ms Linux compute alternative | $0.023/hour, 730 hours | $16.79 |
| 32 GiB E4 Standard SSD LRS | $2.64/month retained | $2.64 |
| SSD transactions | $0.002 per 10,000; workload dependent | Allow $0.10–1 |
| Optional AI | Off by default; budget depends on chosen model | $0 default |
| Private access, egress, backups | Reuse existing services; incremental charges unknown | Not included |

Planning subtotal: **about $4–5/month for 40 running hours**, or **$20–22/month always on**, **only when an existing private access/egress route is available**. These are not complete quotes for a new private network. New VPN, Bastion, NAT gateway, backup and logging resources can exceed the application cost and require a revised estimate. Start with a US$25-equivalent resource-group alert budget after confirming billing currency; budget alerts are not hard spending caps. The budget template uses account billing currency, not automatically USD.

[VM pricing](https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/) separates compute from managed disks. Deallocate the VM to stop compute billing; guest shutdown alone is insufficient. Retained disks and snapshots continue to cost money. Delete reviewed project resources when finished to stop those charges.

## Container Apps evaluation

Consumption Container Apps can scale compute to zero, but [billing](https://learn.microsoft.com/en-us/azure/container-apps/billing) and [durable storage](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts) must be evaluated separately. This implementation uses SQLite WAL and local files. SQLite WAL [requires processes on the same host](https://sqlite.org/wal.html); placing it on an SMB share and scaling replicas is not a sound production storage design. Container Apps would require a server database migration, private networking/access and associated idle charges. The VM preserves the verified single-host persistence model at low demo usage cost. Tradeoff: patching and VM lifecycle are operator responsibilities, with no high availability or automatic request-driven scale-to-zero.

## Reviewed deployment steps (not executed)

1. Obtain approval for region, cost envelope, subscription, private subnet/egress, operator CIDR, SSH public key, budget recipient and source scope. Confirm VM SKU availability and current price.
2. Compile templates with `az bicep build --file infrastructure/private-vm.bicep` and `budget.bicep`. Review a resource-group what-if with explicit parameters. Never use an unrelated resource group.
3. After explicit spending approval, create a dedicated resource group, deploy the private VM template and budget template, then confirm no public IP exists and NSG denies application ingress.
4. Connect over the approved private path. Install Docker from its official repository. Copy a reviewed source archive or transfer the locally tested image (`docker save` / `docker load`). This avoids requiring a paid registry.
5. Create a private `.env` owned by the operator with mode 600, unique tokens and no AI key by default. Protect Docker access: Docker group membership is privileged. Secrets are supplied at runtime, not in Bicep or image layers.
6. Run `docker compose up -d --wait`, then `docker compose exec -T monitor python -m dqagent.cli demo all`. Verify unauthenticated 401, authorized evidence, MCP access, restart persistence and private-only routing.
7. Capture synthetic screenshots. Configure a reviewed shutdown schedule/operating procedure. Take and restore-test a backup before upgrades.

## Rollback, shutdown and cleanup

- Retain the prior container image digest and a consistent metadata backup. Stop the service, restore the prior image/config and compatible backup, then restart and run acceptance tests. Current metadata schema is version 1; do not assume future downgrades are compatible.
- Local stop: `docker compose down` preserves the named volume. Do not use `--volumes` unless intentionally discarding evidence.
- Azure stop: `az vm deallocate --resource-group APPROVED_GROUP --name dq-monitor`. Confirm power state is deallocated; retained disk charges remain.
- Before deletion, export required evidence securely and verify its backup. Delete only the dedicated project resource group after explicit approval. The disk's detach policy protects it when deleting only the VM; check for retained orphan disks and snapshots. Resource-group deletion removes all resources in that group.

This proposal is ready for review, not an assertion of cloud production readiness. Entra app authentication, automated secret rotation, high availability, server-database migration and central alerts are not implemented.

## Final acceptance audit

**Deployment decision: BLOCKED. No resources provisioned.** The amounts above are an application subtotal, not total cost of ownership. The public price refresh during final review returned HTTP 429; the earlier same-day saved retail quote remains the basis, and must be refreshed before spending approval.

Total monthly cost = compute hours x regional hourly rate + retained disk + disk transactions + allocated private-access cost + egress/NAT processing + backup storage/operations + optional logging + optional AI + applicable tax/currency conversion. Operator patching, backup checks and incident response are also operating costs, though not Azure meters. Existing network resources are not economically free merely because this project does not create them. At zero VM hours the retained disk and any gateways, snapshots, backup or monitoring services still bill.

For a new private network, a total cannot be responsibly quoted until the route and egress design are selected. Do not approve a $25 budget based on the VM subtotal alone. A resource-group budget does not cover shared network resources in other groups or an external OpenAI bill and cannot stop charges. The application limits AI requests, not dollar expenditure.

Networking review: inbound application access stays on loopback through SSH and a verified private route; no public VM IP is in the template. The operator CIDR is a free-form parameter, so parameter review must reject broad/public ranges. Default outbound NSG rules remain permissive: network policy, DNS, TLS certificate validation and an explicit outbound route still need verification. [Azure default outbound access](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access) cannot be assumed for new private subnets. Free Bastion Developer does not support the native-client tunnel used by this design; Standard/Premium support native clients and only Premium supports private-only Bastion. See the [official SKU matrix](https://learn.microsoft.com/en-us/azure/bastion/bastion-sku-comparison). No Bastion SKU is silently added to this proposal.

Authentication review: SSH public-key access is configured, password login disabled; application authorization consists of two shared bearer roles. It has no per-person identity, MFA, audit attribution or independent user revocation. Tokens are private runtime files/environment and are visible to the Docker/VM administrator. This is suitable only for the intended trusted single-operator demo until stronger access controls are implemented. Remote source monitoring remains blocked on a least-privilege SQL identity and a trusted TLS/private route.

Storage review: the named volume persists on the managed OS disk, but is not a backup or high availability. Local backup/restore tests do not prove Azure disaster recovery. Define RPO/RTO, retention, capacity alerts, off-host encrypted backups and a tested restore procedure before production. SQLite stays single-host. No auto-shutdown schedule, unattended patch rollout, alert routing or secret rotation is deployed. The image scan findings in the acceptance report are an additional security gate.

Shutdown requires Azure deallocation, verified by power state; guest shutdown does not stop allocated compute billing ([billing states](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing)). Cleanup must inventory retained disks, snapshots, private access and logging charges, preserve a verified backup, and delete only explicitly approved dedicated resources. Existing shared subnet/network resources are outside cleanup scope. No shutdown or deletion has been executed against Azure.
