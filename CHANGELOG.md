# Changelog

## 1.2.0 - 2026-11-07

- **Updates panel** (#5): **Check for updates** on the Dokploy page shows this extension, Dokploy and Harness. The
  extension updates itself only when it is clean (no local change, fast-forward, its GitHub checks passed, supported
  by your Harness), only to the commit you confirmed, then refreshes the sessions' skill. Dokploy updates itself to
  its latest release after you type `dokploy` (measured: the sites stay up, Dokploy's page is away about two minutes;
  a second click is refused while it restarts). Harness links to its own Settings -> Updates. git runs in its own
  process group with a time budget, so a stuck network never hangs Harness. `dokploy.py updates` lets sessions read
  it, never run it.

## 1.1.0 - 2026-11-07

- **The skill stays up to date** (#4): `dokploy.py install-skill` and an **Install the skill for sessions** button copy
  it to the workspace; the page and `dokploy.py status` say when that copy is missing or older than the extension.
- **Clearer setup** (#4): where Dokploy v0.30 makes the API key (shown only once), and the real Harness setting to
  leave off (**Expose to Harness sessions**).
- **Roll back, stop and start** (#3): on the page and with `dokploy.py rollback|stop|start APP --yes`. A rollback goes
  back to the successful deployment before the one running now (a failed deploy leaves the previous one running), only
  for applications with rollbacks turned on in Dokploy and never during a deployment; it says which one before asking,
  and the page refuses if that changed before you confirmed. Stopping asks to type the service name. Protected
  services refuse them.
- **Containers, not just the last deployment** (#2): the page's first column is now "Last deployment", and a new
  "Containers" column shows what really runs (running / expected: running, partly down, down, stopped, or unknown when
  Dokploy cannot tell); `dokploy.py health APP` does the same for sessions, one service at a time and at most 4
  requests at once from the page. A one-shot container that exited cleanly does not count as down. `list --json` adds
  `last_deployment`; `status` is deprecated and stays for 1.x scripts.
- **Faster single-service commands**: deploy, logs, health and the page's actions read one service instead of the
  whole inventory.
- CI checks `page.js` as an ES module (`node --check` on a `.js` file let a syntax error through).
- **Protected services** (#1): mark a service read-only on the page; the page and `dokploy.py` refuse to deploy,
  rebuild it or add a domain to it, and only the page can lift it (kept across disconnect / reconnect; an unreadable
  settings file refuses every write instead of opening them).
- **Safer confirmation** (#1): the page shows what a deploy will do (a few seconds of downtime for a compose stack or
  an app that is not start-first, nothing rebuilt without a git source) and asks to type the service name when the
  site can go down; `dokploy.py` puts the same warnings in its question.

## 1.0.0 - 2026-11-07

- Dokploy page: connect with the key from Settings -> Keys, see projects, apps, compose stacks, databases and domains,
  read the last deployment log, deploy or rebuild after a confirmation.
- `dokploy.py` and the `dokploy` skill for Claude sessions: list, environments, deployments, logs, deploy, redeploy,
  domains and app creation, every write after the user agreed (`--yes`).
- The key is only sent to the Dokploy address it was checked against, redirects are not followed, and the values
  passed on to Dokploy are validated.
