# Source integration notes

The project supports read-only SQL Server quality checks through a reviewed schema contract. Source-derived inventory, measurements, security posture and business findings are intentionally excluded from the published documentation and history. Detailed investigation evidence remains in ignored private local artifacts.

Routine monitoring requires a dedicated least-privilege identity, approved table scope, metadata visibility and trusted certificate validation. The one-time discovery helper must not be deployed as a scheduled administrative connection. Source queries do not create logins, grants, tables or views.

Business dates must not be treated as ingestion timestamps. Freshness SLAs, reconciliation definitions and pricing policies require explicit business approval. Demonstrations of failures and freshness use isolated synthetic data.

The checked-in sample rule catalog describes an integration contract; it contains no source records, customer values, measurements or credentials. Adapt it only to an approved source schema. Broader driver/server compatibility requires environment-specific verification.
