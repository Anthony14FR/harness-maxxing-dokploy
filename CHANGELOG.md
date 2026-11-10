# Changelog

## 1.6.0 - 2026-11-10

- **Alerts in Harness notifications (and Telegram)**: Overview → **Alerts** → **Turn alerts on**. Every 5 minutes a
  Harness cron job checks Dokploy and posts each new problem once, then its end: a failed deployment or backup, a
  service down, a disk at 90 % or memory at 95 %, a failed Traefik update, Dokploy not answering. In the language of
  Harness; Telegram follows the rule of the **Dokploy** source. It only reads Dokploy. `dokploy.py alerts --dry-run`
  shows what would be posted.

## 1.5.0 - 2026-11-10

- **Update Traefik from Harness**: when Dokploy recommends a newer Traefik, **Updates** (and the Server tab) offer
  **Update Traefik**. You type `traefik` to confirm; Dokploy pulls the image and recreates Traefik with its environment
  and ports, so your sites can be unreachable for a few seconds. The page follows it until Traefik runs the new version,
  or shows Dokploy's error (a failed update keeps the previous Traefik). It only runs the version you confirmed, never
  while another update runs or while Traefik is stopped. A failed last update appears in **Overview → Needs your
  attention**; `dokploy.py updates` shows Traefik too (sessions still never update anything).

## 1.4.2 - 2026-11-10

- **Readable update notes**: the notes of a new version are shown formatted (version headings, bullets, bold, code)
  instead of raw Markdown. You see it from the update after this one: the notes are drawn by the version you have.

## 1.4.1 - 2026-11-10

- **Statuses start with a capital**: Done / Réussi, Running 2/2 / En marche 2/2, Failed / En échec, Healthy / Sain...
- **A finer phone layout** (checked at 320, 375 and 430 px): on a narrow screen the tabs other than the open one show
  only their icon (their name stays for screen readers), so all six fit; counters stay two per row; Server and Overview
  cards no longer overflow; service cards share their width between Deploy, Last log and More; deployments start
  with their service; links get a 44 px touch area; the updates strip fits on one line ("Check"); shorter search hints.
  The French "Vue d'ensemble" tab is now "Aperçu".

## 1.4.0 - 2026-11-10

- **A full Dokploy dashboard**: updates on top, then Overview (what needs attention, counters, CPU / memory / disk,
  recent deployments), Services, Domains (HTTPS, certificates, hosts routed by Traefik labels), Databases (containers,
  backups and their last run), Deployments (apps, stacks and backups, failed or in progress, with log) and Server
  (resources, Dokploy's database and Traefik with its version, public IP, Docker disk usage, remote servers). Each part
  that an older Dokploy lacks says so instead of failing; only plain listed fields leave the server, never the secrets
  Dokploy nests in its answers.
- **In the sidebar by itself**: the page pins itself once when Harness loads it; unpin it and it stays unpinned.
- **Works on a phone**: tables become cards, touch-sized buttons, the tab bar scrolls; keyboard tabs, labels for
  screen readers, light and dark, English or French as Harness is set. Actions other than Deploy and Logs sit in a
  **More** menu.
- Databases now show their name with Dokploy v0.31 (its project list gives them only an id), in the page and in
  `dokploy.py list`.

## 1.3.1 - 2026-11-09

- **Domains of a compose that routes itself**: a compose whose own Traefik labels route its hosts (instead of
  domains declared in Dokploy) showed `-` in the Domains column although its site was up. The page now adds those
  hosts once the containers are read (hover: "Routed by this compose's own Traefik labels"), and `dokploy.py health`
  lists them as `routed`. Only the routing labels of the compose's running containers are read; nothing is changed in
  Dokploy. The skill tells sessions never to `domain add` them (a second router for the same host).

## 1.3.0 - 2026-11-09

- **The skill is linked, not copied**: `ln -s` (the new Harness community rule), the page's **Link the skill for
  sessions** button or `dokploy.py link-skill`; a link follows every `git pull`. Nothing breaks from 1.x: the old copy
  keeps working and an extension update never replaces it; the button or `link-skill` moves it aside, makes the link
  and puts the copy back if anything fails; a folder holding the user's own files, or a link to another folder, is
  left as it is; a dead link is repaired; `install-skill` still works (it links). README: **Settings -> Pages ->
  Rescan** (Extensions -> Reload on older Harness).

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
