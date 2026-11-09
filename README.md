# Dokploy for Harness Maxxing

A community [page extension](https://github.com/makushingu/harness-maxxing/blob/main/docs/user/13-page-extensions.md)
for [Harness Maxxing](https://github.com/makushingu/harness-maxxing) that connects it to
[Dokploy](https://dokploy.com):

- **A Dokploy page** in Harness: your projects, applications, compose stacks, databases and domains with their last
  deployment, the containers really running and the last deployment log, and **Deploy**, **Rebuild**, **Roll back**,
  **Stop** and **Start** buttons that ask you first (type the service name when the site can be down for a few
  seconds).
- **Protected services**: mark a production service read-only on the page; the page and `dokploy.py` then refuse to
  deploy, rebuild it or add a domain to it, and only the page can lift it.
- **A skill for Claude sessions**: Claude lists what runs, reads why a deployment failed, deploys, adds a domain or
  creates an app from a git repository, and asks you before every change.

It changes nothing in Harness itself and works however Harness is reached (its own Caddy, Tailscale, local, or
behind Dokploy's Traefik with `maxxing proxy`).

> **Community extension, not reviewed by the Harness Maxxing maintainers.** Like every extension, `api.py` runs
> inside the Harness server with its rights (root on a standard install). Read the code before installing it.

## Requirements

- Harness Maxxing with page extensions (extension contract `"api": 1`).
- A Dokploy you can reach from the Harness server (tested with Dokploy v0.30.10) and an API key. In Dokploy v0.30:
  **Settings -> Profile** (`/dashboard/settings/profile`), block **API/CLI Keys**, **Generate New Key**. The key is
  shown only once: copy it right away.

## Install

1. On the Harness server, as root:

   ```bash
   git clone https://github.com/Anthony14FR/harness-maxxing-dokploy.git /root/maxxing/extensions/dokploy
   ```

   (`/root/maxxing` is the default workspace: use yours if you changed it. The folder must be named `dokploy`.)
2. **Settings -> Pages -> Rescan** (**Settings -> Extensions -> Reload** on older Harness versions), then open
   **Dokploy** (pin it to keep it in the sidebar).
3. **Settings -> Keys -> Add a key**: name `DOKPLOY_API_KEY`, your Dokploy API key as the value, and leave
   **Expose to Harness sessions** off (the default): the extension reads the key without it.
4. On the Dokploy page, check the address (default `http://127.0.0.1:3000`, Dokploy on the same server) and click
   **Check and connect**.
5. For Claude sessions, link the skill once (Claude Code does not read skills from extension folders; a link, not a
   copy, so every `git pull` keeps it current):

   ```bash
   ln -s /root/maxxing/extensions/dokploy/skill/dokploy /root/maxxing/.claude/skills/dokploy
   ```

   The **Link the skill for sessions** button of the Dokploy page, or `dokploy.py link-skill`, does the same.

   **Coming from 1.x?** Nothing breaks: the copy 1.x made keeps working. The page and `dokploy.py status` then offer
   to replace it with the link; that replaces it only when it holds nothing but this extension's own files, otherwise
   it says which files to move first. `dokploy.py install-skill` from the 1.x instructions still works (it links).

## Update

On the Dokploy page, **Updates -> Check for updates** shows, for each part, what is installed and what is new:

- **This extension**: **Update** is offered only when it is clean: no file of the extension changed here, the new
  version follows the installed one (fast-forward), its tests passed on GitHub, and it runs with your Harness. It then
  pulls the new version, refreshes the sessions' skill, and the page reloads. Otherwise it says why.
- **Dokploy**: its version and the latest one; **Update** asks you to type `dokploy`, then Dokploy updates itself to
  its latest release (it takes no version: a release published in between would be the one installed). A second
  click within five minutes is refused while Dokploy restarts. Measured on a test server
  (v0.30.10 -> v0.31.0): the sites stay up (Traefik and the apps are not restarted), Dokploy's own page and API are
  away for about two minutes.
- **Harness Maxxing** updates itself, with its own checks and rollback, in **Settings -> Updates** (linked there).

The extension updates only to the exact commit you confirmed, from what the check fetched. Its automatic update needs
a public GitHub repository whose checks passed (this one): a private or non-GitHub copy is shown with the reason and
is updated by hand. If git says the folder is owned by another user, run the commands below as that user, or
`git config --global --add safe.directory /root/maxxing/extensions/dokploy`.
Harness reloads an extension by itself when its files change, so no restart is needed. By hand, the same as the
extension's button:

```bash
git -C /root/maxxing/extensions/dokploy pull --ff-only
```

## What it sends, and where

- **Only to the Dokploy address you checked on the page**: Dokploy API calls (`GET|POST <address>/api/<procedure>`)
  with your key in the `x-api-key` header. Reads: `project.all`, `application.one`, `compose.one`, `deployment.all`,
  `deployment.allByCompose`, `docker.getContainersByAppNameMatch`, `docker.getStackContainersByAppName`. Writes, each
  only after you agree: `application.deploy` / `redeploy` / `stop` / `start`, `compose.deploy` / `redeploy` / `stop` /
  `start`, `rollback.rollback`, `domain.create`, `application.create`, `application.saveGitProvider`,
  `application.saveBuildType`.
- **For updates, only when you click Check or Update**: `settings.getDokployVersion`, `settings.getUpdateData` and,
  after you confirm, `settings.updateServer` to Dokploy; `git fetch` / `git merge --ff-only` of this folder from the
  repository it was cloned from; GitHub's public API (`GET /repos/<owner>/<repo>/commits/<sha>/check-runs`, no token)
  to see that the new version passed its tests. Updating runs new code of this extension as root, the same trust as
  the first `git clone`.
- Nothing else, to nobody else: no telemetry, no other host. Redirects are not followed, so the key is never sent to
  another address.
- Plain `http://` is accepted only for this machine, a private network or a Tailscale address; anything else needs
  `https://`.

## How the key is kept

- The key lives only in **Settings -> Keys** (`DOKPLOY_API_KEY`). The page's `api.py` reads it with `ctx.secret()`;
  the session script reads it with `maxxing keys get` inside its own process, for each call. It is never written in
  this folder, never printed, and never put in the environment of sessions.
- The extension's state folder (`/var/lib/claude-maxxing/extensions/dokploy/settings.json`, root only) keeps the
  Dokploy address, a fingerprint of the key it was checked with (never the key) and the protected services. A key
  changed in Keys is not used until you check it again on the page.
- The script warns when `DOKPLOY_API_KEY` is exposed to sessions.
- Claude sessions run as root on a standard install: these rules keep the key out of their environment, prompts and
  output, they are not a wall against a session that sets out to read the vault.

## For Claude sessions

The skill teaches Claude these commands (`skill/dokploy/SKILL.md`):

```bash
D=/root/maxxing/extensions/dokploy/dokploy.py
python3 $D status
python3 $D link-skill
python3 $D updates [--json]
python3 $D list [--json]
python3 $D environments [--json]
python3 $D deployments APP [--json]
python3 $D health APP [--json]
python3 $D logs APP [--deployment ID] [--lines N]
python3 $D domain list APP
python3 $D deploy|redeploy APP --yes
python3 $D stop|start|rollback APP --yes
python3 $D domain add APP HOST [--port N] [--path P] [--service S] [--no-https] --yes
python3 $D app create --environment ID --name N --repo URL [--branch B] [--build T] --yes
```

A protected service refuses deploy, redeploy, stop, start, rollback and domain add, even with `--yes`, and the script has no command to lift
the protection. Like `--yes`, it guards the page and the commands Claude is told to use; it is not a lock against a
root session set on going around it.
Every write needs `--yes`, which the skill tells Claude to add only after you agreed; without it the command stops
(exit code 3) and changes nothing. That is how Claude is told to work, not a lock: review what it proposes. Values
passed on to Dokploy (git URL, branch, names, host, port, path) are validated first. Deployment logs are read from
Dokploy's log folder on this server only, and can contain values a build printed: keep secrets out of build output.

## Remove it

```bash
rm -rf /root/maxxing/extensions/dokploy /var/lib/claude-maxxing/extensions/dokploy
rm -rf /root/maxxing/.claude/skills/dokploy   # the link (or the copy 1.x made)
```

Then **Settings -> Pages -> Rescan** (or **Extensions -> Reload**), delete `DOKPLOY_API_KEY` in **Settings -> Keys**, and revoke the key in
Dokploy. Your Dokploy, its apps and their domains are left as they are.

## Development

Standard library only (Python 3.11+). Tests run against a local fake Dokploy and a fake `maxxing` command:

```bash
uv run --with pytest pytest
uv run --with ruff ruff check . && uv run --with ruff ruff format --check .
node --check page.js
```

## License

[MIT](LICENSE). Harness Maxxing and Dokploy are the projects of their own authors; this extension is not
affiliated with either.
