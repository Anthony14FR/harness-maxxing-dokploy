"""HTTP API of the Dokploy page: /api/ext/dokploy/<path>, called by page.js for a signed-in user only."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _core():
    """dokploy_core.py next to this file (Harness imports api.py alone, not as a package)."""
    name = "mx_ext_dokploy_core"
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("dokploy_core.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules[name] = mod
    return mod


core = _core()


def handle(ctx, method, path, query, body):
    state, secret = ctx["state_dir"], ctx["secret"]
    body = body if isinstance(body, dict) else {}
    try:
        if path == "status" and method == "GET":
            return {**core.status(state, secret), "skill": core.skill_state(ctx.get("workspace"))}
        if path == "skill" and method == "POST":  # the user's button: copy the skill for Claude sessions
            if not ctx.get("workspace"):
                return 409, {"error": "skill_failed", "message": "Harness gave no workspace"}
            core.install_skill(ctx["workspace"])
            return {"skill": core.skill_state(ctx["workspace"])}
        if path == "connect" and method == "POST":
            return core.connect(state, secret, str(body.get("url") or ""))
        if path == "disconnect" and method == "POST":
            return {"disconnected": core.disconnect(state)}
        if path == "protect" and method == "POST" and not body.get("on"):  # lifting works offline, and for gone ids
            sid = str(body.get("id") or "")
            return {"id": sid, "protected": sid in core.set_protected(state, sid, False)}
        c = core.client(state, secret)
        if path == "services" and method == "GET":
            prot = core.protected(state)
            svcs = core.inventory(c)
            return {"services": [{**s, "protected": s["id"] in prot, "risks": core.risks(s)} for s in svcs]}
        if path == "protect" and method == "POST":  # the user's own toggle on the page (on: the service must exist)
            svc = core.lookup(c, str(body.get("id") or ""))
            return {
                "id": svc["id"],
                "protected": svc["id"] in core.set_protected(state, svc["id"], bool(body.get("on"))),
            }
        if path == "deploy" and method == "POST":  # the page asked the user before calling it
            svc = core.lookup(c, str(body.get("id") or ""))
            core.guard(state, svc)
            core.deploy(c, svc, "Harness Maxxing", again=bool(body.get("again")))
            return {"started": svc["id"]}
        if path == "rollback" and method == "GET":  # what a rollback would go back to, for the confirmation
            svc = core.lookup(c, str(query.get("id") or ""))
            d = core.rollback_target(c, svc)
            return {"deployment": d["id"], "title": d["title"], "created": d["created"]}
        if path == "action" and method == "POST":  # stop, start or rollback, after the page asked the user
            svc = core.lookup(c, str(body.get("id") or ""))
            act = body.get("action")
            if act not in ("stop", "start", "rollback"):
                return 400, {"error": "bad_action", "message": "action must be stop, start or rollback"}
            core.guard(state, svc)
            if act == "rollback":  # what runs must be what the user confirmed
                core.rollback(c, svc, core.rollback_target(c, svc), str(body.get("deployment") or ""))
            else:
                core.power(c, svc, act == "start")
            return {"done": act, "id": svc["id"]}
        if path == "health" and method == "GET":
            return core.health(c, core.lookup(c, str(query.get("id") or "")))
        if path == "deployments" and method == "GET":
            svc = core.lookup(c, str(query.get("id") or ""))
            return {"deployments": [{k: v for k, v in d.items() if k != "log_path"} for d in core.deployments(c, svc)]}
        if path == "log" and method == "GET":
            svc = core.lookup(c, str(query.get("id") or ""))
            deps = core.deployments(c, svc)
            want = query.get("deployment")
            dep = next((d for d in deps if d["id"] == want), None) if want else (deps[0] if deps else None)
            if not dep:
                return 404, {"error": "not_found", "message": "no such deployment"}
            return {"deployment": dep["id"], "log": core.log(dep, 300)}
    except core.DokployError as e:
        status = {
            "not_connected": 409,
            "no_key": 409,
            "key_changed": 409,
            "protected": 409,
            "bad_settings": 409,
            "rollback_off": 409,
            "no_rollback": 409,
            "not_supported": 409,
            "deploy_in_progress": 409,
            "target_changed": 409,
            "skill_linked": 409,
            "skill_failed": 409,
            "not_found": 404,
        }.get(e.code, 422)
        return status, {"error": e.code, "message": e.message}
    return 404, {"error": "not_found", "message": f"{method} {path}"}
