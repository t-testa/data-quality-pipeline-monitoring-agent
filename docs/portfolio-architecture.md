# Northwatch — private local portfolio architecture

```mermaid
flowchart LR
  subgraph Host[Existing personal computer]
    Browser[Browser on localhost]
    Client[Approved local MCP client]
    MCP[Python MCP server: stdio / nine read-only tools]
    subgraph Docker[Docker Compose / one worker]
      API[FastAPI / bearer authorization]
      Evidence[Bounded evidence service]
      Checks[Ten deterministic quality contracts]
      Loader[Synthetic incremental loader]
    end
    Volume[(Named local volume: monitoring history / synthetic data / checkpoints)]
    Backup[(Private full-volume archive and checksum)]
    Browser -->|127.0.0.1:8765| API
    Client -->|stdio| MCP
    MCP -->|Authenticated loopback HTTP| API
    API --> Evidence
    Evidence -->|Read persisted facts| Volume
    Loader --> Checks
    Loader -->|Transactional checkpoint| Volume
    Checks -->|Persist checks and execution| Volume
    Volume -->|Writers stopped / no-network helper| Backup
    Backup -->|Integrity check / new empty volume| Restore[(Isolated restore drill)]
  end
  Tailnet[Optional approved personal devices] -. Not configured .-> Serve[Tailscale Serve proposal]
  Serve -. Host loopback proxy / approval required .-> API
  Source[Optional SELECT-only SQL source adapter] -. Preserved but disabled in portfolio profile .-> Checks
```

The local profile has no cloud host and no model-provider connection. The optional
AI implementation remains available in source but its key/model are empty in this
profile. Source connectivity likewise remains implemented but disabled for synthetic
demonstrations. Tailscale is a proposal only; its eventual reverse proxy would target
the host's loopback HTTP service, not add a public Docker listener. Azure is postponed.

Authoritative facts come from persisted run/check records. Hypotheses are labeled
unconfirmed; absent values remain unavailable. Authentication stays in the API;
MCP has no SQL/shell/action tool. The host administrator remains privileged. Local
storage is durable across container replacement, not high availability or an off-host
backup. No tenant isolation, production SLA or external exposure is claimed.
