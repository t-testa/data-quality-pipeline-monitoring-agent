# Private publishing readiness

The local repository is prepared for private publishing. It has no remote and no verified GitHub Actions run. Publishing, visibility confirmation and a green hosted run remain outstanding.

Before publishing, run Ruff, pytest, both lockfile audits and `python scripts/scan_secrets.py --history`. Review `git diff --cached` and `git ls-files`; never force-add ignored files. The heuristic scanner checks the worktree and reachable Git history for common credentials and locally configured secrets, but cannot prove that every possible secret pattern is absent.

`.env`, local databases, test reports, screenshots, scanner downloads and detailed source findings belong in ignored local directories. The README and portfolio narrative omit customer records and account identifiers. The source-specific contract and discovery notes belong only in the private repository; adapt and sanitize them before any future public release. A sanitized current README does not erase earlier Git history.

Use the private publishing commands in README only when publishing is authorized. Confirm repository visibility before sharing. Configure branch protection after the first hosted run, requiring the two platform test jobs and container job. Actions use immutable commit references and read-only repository permissions. No deployment secret is required for CI; generated tokens are ephemeral and AI is disabled.

Inspect the hosted job logs and artifacts after push. Local actionlint validates workflow syntax and local execution validates commands, but neither proves GitHub runner behavior, repository permissions or artifact upload. Record the real run URL only after completion. Do not add a passing CI badge until that evidence exists.

Portfolio materials must use synthetic demos. Present this as a tested single-host prototype with explicit production gates, not a deployed service with an SLA. The acceptance report records the limits.
