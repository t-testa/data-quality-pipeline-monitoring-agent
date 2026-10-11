# Optional personal private access — evaluated, not enabled

Keep Northwatch on localhost. No external access, account signup, installation,
device enrollment, invitation, firewall rule or Tailscale configuration occurred.
Existing container vulnerabilities remain unaccepted.

A later approved demo could use Tailscale Serve to proxy host loopback to approved
tailnet devices over HTTPS, retaining Northwatch's bearer token. MCP can remain
local stdio; a reviewed remote client could use the HTTPS API and read token.
No MCP HTTP listener, public port forwarding or Docker socket is needed.

The current [Personal plan](https://tailscale.com/pricing) is $0 for non-commercial
personal use, with up to six users and unlimited user devices. Tagged-resource
limits/add-ons and business trials have separate terms. Personal portfolio use may
fit; employer/client work must not be assumed eligible. Recheck before enrollment,
avoid paid upgrades/business trials, and do not add billing under this proposal.

[Serve](https://tailscale.com/docs/features/tailscale-serve) is tailnet-only and
requires HTTPS configuration. Review access rules explicitly: restrict approved
users/devices to the demo host and HTTPS service, test denial from an unapproved
device, and revoke guest access afterward. Northwatch does not use Serve identity
headers for login or per-user authorization; retain its bearer-token boundary.
Viewers receive only the read token, never the diagnostic token.

[Funnel](https://tailscale.com/docs/features/tailscale-funnel) exposes a service to
the public internet and is excluded. Do not enable Funnel, router forwarding,
subnet routing or an exit node. Future review must confirm Funnel is disabled
for the host. The application's loopback binding stays unchanged.

After explicit approval, the proposed foreground command would be
`tailscale serve 8765`; Ctrl+C ends that foreground session. This is documentation
only, not executed. Validate TLS, bearer authentication, allowed/denied devices,
revocation, host sleep/reboot behavior and absence of public reachability first.
The host must be awake with Docker running. Tailscale provides optional connectivity,
not hosting or high availability. Keep tokens out of URLs and screenshots.

**Unverified:** account eligibility/enrollment, ACLs/grants, certificates, remote
reachability, Windows firewall behavior, remote MCP and device revocation. None
is claimed as implemented.
