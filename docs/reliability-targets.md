# Local acceptance targets — defined before the hardening load/fault tests

Azure is now postponed. The operational objectives below are retained as future
production targets, not a current cloud plan. See [local validation](local-readiness.md)
for the prepared zero-subscription-cost portfolio setup and tested full-volume recovery.

Scope: one API worker, one local SQLite WAL database, 512 MiB container memory,
one CPU, synthetic data only, fresh isolated Docker volume. This is not an Azure
benchmark or a high-availability commitment.

| Exercise | Acceptance target |
|---|---|
| Dashboard reads | 60 authenticated requests, concurrency 6; no errors; p95 <500 ms |
| MCP reads | 24 real stdio tool calls, concurrency 4; no errors; p95 <2,000 ms |
| Restart / SIGKILL | Ready within 30 seconds; exact completed run/check contents survive |
| Recovery from local backup | Integrity check succeeds; exact logical contents; restore verification <60 seconds |
| Interrupted pipeline | Uncommitted target/checkpoint changes roll back; stale run blocks replay until explicit operator recovery |
| SQLite contention | Readers see committed data during a writer; a blocked writer fails within the configured 5-second busy timeout |
| Storage errors | Failed finish is atomic; no false success; low-space readiness returns 503 |
| Incremental replay | First load 100 rows, unchanged replay 0; updates/tombstones exactly once |
| Growth sample | Record bytes/run for 1,000 synthetic runs with 10 checks each; retain all records |

Proposed operational objectives, **not yet achieved in Azure**: backup RPO <=24 h,
operator-assisted RTO <=60 min, encrypted off-host daily backups retained 30 days,
capacity warning at 20% free and critical at 10% or 1 GiB free. The application
readiness floor defaults to 64 MiB; it is an emergency guard, not the capacity alert.
No retention deletion is authorized or scheduled. Estimate retention capacity from
the measured sample and expected run frequency before adopting a purge policy.
