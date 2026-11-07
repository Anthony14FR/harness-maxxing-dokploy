# Changelog

## Unreleased

- **Containers, not just the last deployment** (#2): the page's first column is now "Last deployment", and a new
  "Containers" column shows what really runs (running / expected: running, partly down, down, stopped, or
  unknown when Dokploy cannot tell); `dokploy.py health APP`
  does the same for sessions, one service at a time and at most 4 requests at once from the page. A one-shot
  container that exited cleanly does not count as down. `list --json` adds `last_deployment`; `status` is
  deprecated and stays for 1.x scripts.
- **Faster single-service commands**: deploy, logs, health and the page's actions read one service instead of the
  whole inventory.
- CI checks `page.js` as an ES module (`node --check` on a `.js` file let a syntax error through).
- **Protected services** (#1): mark a service read-only on the page; the page and `dokploy.py` refuse to deploy,
  rebuild it or add a domain to it, and only the page can lift it (kept across disconnect / reconnect; an
  unreadable settings file refuses every write instead of opening them).
- **Safer confirmation** (#1): the page shows what a deploy will do (a few seconds of downtime for a compose stack or
  an app that is not start-first, nothing rebuilt without a git source) and asks to type the service name when the
  site can go down; `dokploy.py` puts the same warnings in its question.

## 1.0.0 - 2026-11-07

- Dokploy page: connect with the key from Settings -> Keys, see projects, apps, compose stacks, databases and
  domains, read the last deployment log, deploy or rebuild after a confirmation.
- `dokploy.py` and the `dokploy` skill for Claude sessions: list, environments, deployments, logs, deploy,
  redeploy, domains and app creation, every write after the user agreed (`--yes`).
- The key is only sent to the Dokploy address it was checked against, redirects are not followed, and the values
  passed on to Dokploy are validated.
