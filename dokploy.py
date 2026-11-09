#!/usr/bin/env python3
"""Deploy through Dokploy from a Claude session; the key is read from Harness Keys for each call, never printed.

    dokploy.py status                                         also says when the sessions' skill is missing or a copy
    dokploy.py updates [--json]                               what can be updated (changes nothing: the user updates)
    dokploy.py install-skill (or link-skill)                  link <workspace>/.claude/skills/dokploy to skill/dokploy
    dokploy.py list [--json]                                  projects, apps, compose stacks, databases, domains
    dokploy.py environments [--json]                          where `app create` can put an app
    dokploy.py deploy|redeploy APP --yes [--title T]          APP = id, name or app name
    dokploy.py deployments APP [--json]
    dokploy.py stop|start APP --yes                           stop or start its containers (nothing rebuilt)
    dokploy.py rollback APP --yes                             back before the deployment running now (apps)
    dokploy.py health APP [--json]                            containers really running (not the last deployment)
    dokploy.py logs APP [--deployment ID] [--lines N]
    dokploy.py domain list APP
    dokploy.py domain add APP HOST [--port N] [--path P] [--service S] [--no-https] --yes
    dokploy.py app create --environment ID --name N --repo URL [--branch B] [--build T] [--build-path P] --yes

Exit codes: 0 ok, 1 nothing found, 2 error, 3 a write without --yes (ask the user first). `health` exits 0
whatever the state: read its first word (ok, partial, down, stopped, unknown). `list` shows the last deployment.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _core():
    spec = importlib.util.spec_from_file_location("dokploy_core", HERE / "dokploy_core.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


core = _core()


def state_dir() -> Path:
    """The folder Harness gives this extension: <state>/extensions/<id>."""
    ext_id = json.loads((HERE / "manifest.json").read_text())["id"]
    return Path(os.environ.get("MAXXING_STATE") or "/var/lib/claude-maxxing") / "extensions" / ext_id


def _maxxing(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [os.environ.get("MAXXING_BIN") or "maxxing", *args], capture_output=True, text=True, timeout=30, check=False
    )


def workspace() -> Path:
    """Harness's workspace, from its config.json (the default one when it says nothing)."""
    try:
        cfg = json.loads((state_dir().parent.parent / "config.json").read_text())
    except (OSError, ValueError):
        cfg = {}
    ws = cfg.get("workspace") if isinstance(cfg, dict) else None
    return Path(ws if isinstance(ws, str) and ws else "/root/maxxing")


def secret(name: str) -> str | None:
    """The key from Harness Keys, kept in this process only (never printed, never in the environment)."""
    try:
        r = _maxxing("keys", "get", name)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (r.stdout.strip() or None) if r.returncode == 0 else None


def warn_if_exposed() -> None:
    try:
        rows = json.loads(_maxxing("keys", "list", "--json").stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return
    if any(isinstance(r, dict) and r.get("name") == core.KEY and r.get("expose") for r in rows):
        print(f"warning: {core.KEY} is exposed to sessions: turn that off in Settings -> Keys", file=sys.stderr)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dokploy.py", description="Deploy through Dokploy (Harness Maxxing extension).")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="connected or not, and the address")
    for name in ("install-skill", "link-skill"):  # install-skill kept: 1.x instructions still work
        sub.add_parser(name, help="link the skill into the workspace, where Claude Code reads it")
    sub.add_parser("updates", help="what can be updated (read-only)").add_argument("--json", action="store_true")
    for name, what in (
        ("list", "projects, apps, stacks, databases and their domains"),
        ("environments", "projects and environments, with the ids app create needs"),
    ):
        sub.add_parser(name, help=what).add_argument("--json", action="store_true")
    for name in ("deploy", "redeploy"):
        d = sub.add_parser(name, help=f"{name} an application or compose stack")
        d.add_argument("app")
        d.add_argument("--title")
        d.add_argument("--yes", action="store_true")
    d = sub.add_parser("deployments", help="deployments of an app, newest first")
    d.add_argument("app")
    d.add_argument("--json", action="store_true")
    for name, what in (
        ("stop", "stop its containers"),
        ("start", "start its containers"),
        ("rollback", "go back before the deployment running now (applications)"),
    ):
        x = sub.add_parser(name, help=what)
        x.add_argument("app")
        x.add_argument("--yes", action="store_true")
    hp = sub.add_parser("health", help="containers really running, not the last deployment")
    hp.add_argument("app")
    hp.add_argument("--json", action="store_true")
    lg = sub.add_parser("logs", help="log of the last (or a given) deployment")
    lg.add_argument("app")
    lg.add_argument("--deployment")
    lg.add_argument("--lines", type=int, default=200)
    dom = sub.add_parser("domain", help="domains served by Dokploy's Traefik").add_subparsers(dest="sub", required=True)
    dom.add_parser("list").add_argument("app")
    a = dom.add_parser("add")
    a.add_argument("app")
    a.add_argument("host")
    a.add_argument("--port", type=int, help="port the app listens on inside its container")
    a.add_argument("--path")
    a.add_argument("--service", help="compose stack: the service of the stack to serve")
    a.add_argument("--no-https", action="store_true")
    a.add_argument("--yes", action="store_true")
    app = sub.add_parser("app", help="create an application from a git repository").add_subparsers(
        dest="sub", required=True
    )
    ac = app.add_parser("create")
    ac.add_argument("--environment", required=True, help="environment id (see: environments)")
    ac.add_argument("--name", required=True)
    ac.add_argument("--repo", required=True, help="git URL: https://, ssh:// or git@host:path")
    ac.add_argument("--branch", default="main")
    ac.add_argument("--build", default="nixpacks", choices=core.BUILD_TYPES)
    ac.add_argument("--build-path", default="/")
    ac.add_argument("--yes", action="store_true")
    return p


def _agreed(a: argparse.Namespace, what: str) -> bool:
    if a.yes:
        return True
    print(f"{what}: ask the user, then run it again with --yes", file=sys.stderr)
    return False


RISK_TEXT = {
    "downtime": "its containers are stopped and started again: the site can be down for a few seconds",
    "no_rebuild": "it has no git source: nothing is rebuilt, the same image starts again",
    "unknown": "Dokploy did not give its details: assume the site can go down",
}


def _warned(svc: dict) -> str:
    """The risks of a deploy, appended to the question Claude puts to the user."""
    r = [RISK_TEXT[x] for x in core.risks(svc)]
    return f" (tell the user: {'; '.join(r)})" if r else ""


def _urls(s: dict) -> str:
    return " ".join(
        ("https://" if d["https"] else "http://") + d["host"] + (d["path"] if d["path"] != "/" else "")
        for d in s["domains"]
    )


def run(a: argparse.Namespace) -> int:
    st = state_dir()
    if a.action in ("install-skill", "link-skill"):
        print(f"skill linked at {core.install_skill(workspace())}")
        return 0
    if a.action == "updates":
        res = {"extension": core.ext_check(core.EXT_DIR)}
        try:
            res["dokploy"] = core.dokploy_check(core.client(st, secret))
        except core.DokployError as e:
            res["dokploy"] = {"error": e.code, "message": e.message}
        if a.json:
            print(json.dumps(res, indent=2))
            return 0
        x, d = res["extension"], res["dokploy"]
        blockers = f" ({', '.join(x['blockers'])})" if x["blockers"] else ""
        print(f"extension  {x['current']} -> {x['new'] or '-'}  {x['state']}{blockers}")
        print(
            f"dokploy    {d.get('current') or '-'} -> {d.get('latest') or '-'}  "
            f"{d.get('message') or ('available' if d.get('available') else 'up_to_date')}"
        )
        print("updates are the user's: they run them on the Dokploy page in Harness (which also checks the")
        print("extension contract of this Harness)")
        return 0
    if a.action == "status":
        sk = core.skill_state(workspace())
        if sk == "copied":
            print(
                "note: sessions use a copy of the dokploy skill (it goes stale): dokploy.py link-skill", file=sys.stderr
            )
        elif sk == "missing":
            print("warning: the dokploy skill of sessions is missing: dokploy.py link-skill", file=sys.stderr)
        elif sk in ("custom", "linked"):
            print(f"note: the dokploy skill of sessions is the user's own ({sk}): left as it is", file=sys.stderr)
        elif sk == "broken":
            print("warning: this extension's skill folder is empty: git pull", file=sys.stderr)
        s = core.status(st, secret)
        state = (
            "connected"
            if s["connected"]
            else "key changed: check it again on the Dokploy page"
            if s["key_changed"]
            else "no key in Settings -> Keys"
            if not s["key_present"]
            else "not connected"
        )
        print(f"{state}  {s['url'] or '-'}")
        return 0 if s["connected"] else 1
    c = core.client(st, secret)
    if a.action == "environments":
        envs = core.environments(c.get("project.all"))
        if a.json:
            print(json.dumps(envs, indent=2))
        else:
            for e in envs:
                print(f"{(e['project'] or '')[:28]:<28} {(e['name'] or '')[:20]:<20} {e['id']}")
            if not envs:
                print("No environment: create a project in Dokploy first.")
        return 0
    if a.action == "app":
        if not _agreed(a, f"create {a.name} from {a.repo}"):
            return 3
        app_id = core.app_create(c, a.environment, a.name, a.repo, a.branch, a.build, a.build_path)
        print(f"created {a.name} ({app_id}); deploy it with: dokploy.py deploy {app_id} --yes")
        return 0
    if a.action == "list":
        prot = core.protected(st)
        svcs = [{**s, "protected": s["id"] in prot, "risks": core.risks(s)} for s in core.inventory(c)]
        if a.json:
            print(json.dumps(svcs, indent=2))
        else:
            for s in svcs:
                where = (s["project"] or "") + (f"/{s['environment']}" if s["environment"] else "")
                print(
                    f"{(s['last_deployment'] or '-'):<8} {s['kind']:<11} {where[:28]:<28} {s['name'][:28]:<28} "
                    f"{s['id']:<24} {_urls(s)}{'  [protected]' if s['protected'] else ''}"
                )
            if not svcs:
                print("Nothing in Dokploy yet.")
        return 0
    svc = core.lookup(c, a.app)
    if a.action in ("deploy", "redeploy", "stop", "start", "rollback") or getattr(a, "sub", None) == "add":
        core.guard(st, svc)  # protected: refused before even asking the user
    if a.action in ("deploy", "redeploy"):
        if not _agreed(a, f"{a.action} {svc['project']}/{svc['name']}{_warned(svc)}"):
            return 3
        core.deploy(c, svc, a.title, again=a.action == "redeploy")
        print(f"{a.action} of {svc['name']} started; follow it with: dokploy.py logs {svc['id']}")
        return 0
    if a.action in ("stop", "start"):
        warn = " (tell the user: the site is down until it is started again)" if a.action == "stop" else ""
        if not _agreed(a, f"{a.action} {svc['project']}/{svc['name']}{warn}"):
            return 3
        core.power(c, svc, a.action == "start")
        print(f"{svc['name']}: {a.action} sent; check it with: dokploy.py health {svc['id']}")
        return 0
    if a.action == "rollback":
        target = core.rollback_target(c, svc)
        back = f"{target['title'] or target['id']} ({target['created']})"
        down = f" (tell the user: {RISK_TEXT['downtime']})" if "downtime" in core.risks(svc) else ""
        if not _agreed(a, f"roll {svc['project']}/{svc['name']} back to {back}{down}"):
            return 3
        core.rollback(c, svc, target)
        print(f"rollback of {svc['name']} to {back} started; follow it with: dokploy.py deployments {svc['id']}")
        return 0
    if a.action == "health":
        hl = core.health(c, svc)
        if a.json:
            print(json.dumps(hl, indent=2))
            return 0
        want = f"/{hl['expected']}" if hl["expected"] is not None else f"/{len(hl['containers'])}"
        print(f"{hl['state']}  {hl['running']}{want} running")
        for b in hl["containers"]:
            print(f"  {(b['state'] or '-'):<10} {b['name']}  {b['status'] or ''}")
        return 0
    if a.action == "deployments":
        deps = core.deployments(c, svc)
        if a.json:
            print(json.dumps([{k: v for k, v in d.items() if k != "log_path"} for d in deps], indent=2))
        for d in [] if a.json else deps:
            print(f"{(d['status'] or '-'):<8} {d['created'] or '':<26} {d['id']:<24} {d['title'] or ''}")
        return 0
    if a.action == "logs":
        deps = core.deployments(c, svc)
        dep = next((d for d in deps if d["id"] == a.deployment), None) if a.deployment else (deps[0] if deps else None)
        if not dep:
            print("no such deployment", file=sys.stderr)
            return 1
        print(f"# {dep['status']} {dep['created']} {dep['title'] or ''}")
        print(core.log(dep, a.lines))
        return 0
    if a.sub == "list":
        for d in svc["domains"]:
            print(
                f"{'https' if d['https'] else 'http ':<5} {d['host']}{d['path'] if d['path'] != '/' else ''}"
                f"  -> port {d['port'] or '-'}"
            )
        return 0
    if not _agreed(a, f"add {a.host} to {svc['name']}"):
        return 3
    core.domain_add(c, svc, a.host, a.port, not a.no_https, a.path, a.service)
    print(f"{a.host} -> {svc['name']} added; point its DNS to this server, then redeploy")
    return 0


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    warn_if_exposed()
    try:
        return run(a)
    except core.DokployError as e:
        print(f"error ({e.code}): {e.message}", file=sys.stderr)
        return 1 if e.code == "not_found" else 2


if __name__ == "__main__":
    sys.exit(main())
