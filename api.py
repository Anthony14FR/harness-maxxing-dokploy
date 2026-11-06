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
            return core.status(state, secret)
        if path == "connect" and method == "POST":
            return core.connect(state, secret, str(body.get("url") or ""))
        if path == "disconnect" and method == "POST":
            return {"disconnected": core.disconnect(state)}
        c = core.client(state, secret)
        if path == "services" and method == "GET":
            return {"services": core.inventory(c)}
        if path == "deploy" and method == "POST":  # the page asked the user before calling it
            svc = core.find(core.inventory(c), str(body.get("id") or ""))
            core.deploy(c, svc, "Harness Maxxing", again=bool(body.get("again")))
            return {"started": svc["id"]}
        if path == "deployments" and method == "GET":
            svc = core.find(core.inventory(c), str(query.get("id") or ""))
            return {"deployments": [{k: v for k, v in d.items() if k != "log_path"} for d in core.deployments(c, svc)]}
        if path == "log" and method == "GET":
            svc = core.find(core.inventory(c), str(query.get("id") or ""))
            deps = core.deployments(c, svc)
            want = query.get("deployment")
            dep = next((d for d in deps if d["id"] == want), None) if want else (deps[0] if deps else None)
            if not dep:
                return 404, {"error": "not_found", "message": "no such deployment"}
            return {"deployment": dep["id"], "log": core.log(dep, 300)}
    except core.DokployError as e:
        status = {"not_connected": 409, "no_key": 409, "key_changed": 409, "not_found": 404}.get(e.code, 422)
        return status, {"error": e.code, "message": e.message}
    return 404, {"error": "not_found", "message": f"{method} {path}"}
