# Changelog

## 1.0.0 - 2026-11-07

- Dokploy page: connect with the key from Settings -> Keys, see projects, apps, compose stacks, databases and
  domains, read the last deployment log, deploy or rebuild after a confirmation.
- `dokploy.py` and the `dokploy` skill for Claude sessions: list, environments, deployments, logs, deploy,
  redeploy, domains and app creation, every write after the user agreed (`--yes`).
- The key is only sent to the Dokploy address it was checked against, redirects are not followed, and the values
  passed on to Dokploy are validated.
