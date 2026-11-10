---
name: dokploy
description: Deploy, redeploy, read deployment logs, add domains or create apps in Dokploy through the Dokploy extension of Harness Maxxing. Use when the user asks to deploy or ship an app, see why a Dokploy deployment failed, put an app on a domain, or list what runs in Dokploy.
---

# Dokploy

The Dokploy extension (`/root/maxxing/extensions/dokploy/`) talks to Dokploy for you. Its key stays in Settings ->
Keys (`DOKPLOY_API_KEY`): **never look for it, never `maxxing keys get` it, never print it**. Every command reads it
by itself.

```bash
D=/root/maxxing/extensions/dokploy/dokploy.py
python3 $D status                       # connected? (if not: the user opens the Dokploy page in Harness)
python3 $D link-skill                   # when status says this skill is missing or a copy
python3 $D updates [--json]            # what can be updated (read-only)
python3 $D alerts --dry-run            # problems the alerts job would post (read-only)
python3 $D list [--json]                # projects, apps, compose stacks, databases, their state and domains
python3 $D environments [--json]        # environment ids, for app create
python3 $D deployments APP [--json]     # newest first
python3 $D health APP [--json]          # containers really running: check this, not the list, for "is it up?"
python3 $D logs APP [--deployment ID] [--lines N]
python3 $D container-logs APP [--container ID] [--lines N] [--since 1h] [--search TEXT]
python3 $D domain list APP
python3 $D deploy APP --yes             # or redeploy (rebuild)
python3 $D stop|start APP --yes         # its containers, nothing rebuilt
python3 $D rollback APP --yes           # back before the deployment running now (applications)
python3 $D domain add APP HOST [--port N] [--path P] [--service S] [--no-https] --yes
python3 $D app create --environment ID --name N --repo URL [--branch B] [--build nixpacks|dockerfile|...] --yes
```

## Rules

- **Ask before every write.** `deploy`, `redeploy`, `stop`, `start`, `rollback`, `domain add` and `app create` change
  a live service: say what will happen (which app, which project, which domain) and wait for the user's yes before
  adding `--yes`. A command without `--yes` stops with exit code 3 and changes nothing.
- **Protected services** (`[protected]` in `list`, `"protected": true` in `--json`) are read-only: deploy, redeploy,
  stop, start, rollback and domain add are refused (`protected`). Never look for a way around it: only the user lifts
  it, on the Dokploy page in Harness.
- **Say the risks before asking.** A deploy without `--yes` prints them (`tell the user: ...`): a compose stack or an
  app that is not start-first is down for a few seconds; a service with no git source rebuilds nothing.
- **`list` shows the last deployment, not whether the site is up**: `done` can hide a container that died since. To
  answer "is it up?", run `health APP`: `ok`, `partial` (some containers down), `down`, `stopped` (0 replicas wanted,
  or every container exited cleanly) or `unknown` (Dokploy cannot match its containers: check in Dokploy), with
  running / expected containers. It always exits 0: read the first word. For a compose it also lists the hosts its
  own Traefik labels route (`routed`): live, but not Dokploy domains, so never `domain add` them (that would make a
  second router for the same host).
- **Updates are the user's.** `updates` only reads: never update the extension, Dokploy, Traefik or Harness yourself; tell
  the user to use **Updates** on the Dokploy page (Harness: Settings -> Updates).
- If `status` says this skill is missing or a copy, tell the user: the **Link the skill for sessions** button of
  the Dokploy page (or `link-skill`, if they agree) links it once, so it follows every update.
- APP is the id, the name or the app name from `list`; a name used in two projects needs the id.
- A compose stack's domain needs `--service` (a service of its compose file). Repository URLs: `https://`, `ssh://` or
  `git@host:path`. A domain also needs its DNS pointing to the server, then a redeploy.
- **Deployment logs can contain environment values**: quote only the lines that explain an error, never secrets.
- Logs are read on this server only; for a Dokploy on another server, send the user to Dokploy's own page.
- **A deployment broke the site?** Offer `rollback` first (it says which deployment it goes back to). Dokploy keeps no
  record of a rollback: a second one targets the same deployment, it does not go further back. Errors:
  `rollback_off` (rollbacks are off for that app in Dokploy: they need a registry), `deploy_in_progress` (wait),
  `no_rollback`, `not_supported` (compose stacks: redeploy instead).
- Errors: `not_connected` or `key_changed` -> the user opens the Dokploy page in Harness and checks the key; `refused`
  -> the key was revoked in Dokploy; `unreachable` -> Dokploy is down or the address is wrong.
