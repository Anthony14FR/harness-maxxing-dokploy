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
python3 $D list [--json]                # projects, apps, compose stacks, databases, their state and domains
python3 $D environments [--json]        # environment ids, for app create
python3 $D deployments APP [--json]     # newest first
python3 $D logs APP [--deployment ID] [--lines N]
python3 $D domain list APP
python3 $D deploy APP --yes             # or redeploy (rebuild)
python3 $D domain add APP HOST [--port N] [--path P] [--service S] [--no-https] --yes
python3 $D app create --environment ID --name N --repo URL [--branch B] [--build nixpacks|dockerfile|...] --yes
```

## Rules

- **Ask before every write.** `deploy`, `redeploy`, `domain add` and `app create` change a live service: say what
  will happen (which app, which project, which domain) and wait for the user's yes before adding `--yes`. A command
  without `--yes` stops with exit code 3 and changes nothing.
- APP is the id, the name or the app name from `list`; a name used in two projects needs the id.
- A compose stack's domain needs `--service` (a service of its compose file). Repository URLs: `https://`,
  `ssh://` or `git@host:path`. A domain also needs its DNS pointing to the server, then a redeploy.
- **Deployment logs can contain environment values**: quote only the lines that explain an error, never secrets.
- Logs are read on this server only; for a Dokploy on another server, send the user to Dokploy's own page.
- Errors: `not_connected` or `key_changed` -> the user opens the Dokploy page in Harness and checks the key;
  `refused` -> the key was revoked in Dokploy; `unreachable` -> Dokploy is down or the address is wrong.
