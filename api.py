"""HTTP API of the Dokploy page: /api/ext/dokploy/<path>, called by page.js for a signed-in user only."""

from __future__ import annotations

import contextlib
import importlib.util
import sys
import time
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


AUTO_PIN_DELAY = 5.0  # seconds after Harness loads this file: its scan must be over before the pin reads the registry


def _auto_pin(ext_id: str, state_dir: Path) -> bool:
    """Pins the page in the sidebar once, on its first load: never again after, so a user's unpin is kept."""
    mark = state_dir / "auto-pinned"
    if mark.exists():
        return False
    try:
        from maxxing import extensions  # Harness's own module: absent outside Harness, may change in a later version

        if ext_id not in extensions.pinned_ids() and not extensions.set_pinned(ext_id, True):
            return False
        state_dir.mkdir(parents=True, exist_ok=True)
        mark.write_text("1\n")
        with contextlib.suppress(Exception):  # open tabs redraw their sidebar now, as after the Settings switch
            from maxxing import bus

            bus.invalidate("extensions")
        return True
    except Exception:  # noqa: BLE001 - the README says how to pin it by hand
        return False


def _schedule_auto_pin() -> None:
    if "maxxing.extensions" not in sys.modules:  # loaded by tests or the CLI, not by Harness
        return
    import os
    import threading

    ext_dir = Path(__file__).resolve().parent
    try:
        from maxxing import config  # the same folder Harness gives handle() as ctx["state_dir"]

        state = Path(config.state_dir("extensions", ext_dir.name))
    except Exception:  # noqa: BLE001
        state = Path(os.environ.get("MAXXING_STATE") or "/var/lib/claude-maxxing") / "extensions" / ext_dir.name
    t = threading.Timer(AUTO_PIN_DELAY, _auto_pin, (ext_dir.name, state))
    t.daemon = True
    t.start()


_schedule_auto_pin()


def _supported_api() -> int:
    """The extension contract this Harness runs (1 when it does not say)."""
    try:
        from maxxing.extensions import EXT_API

        return int(EXT_API)
    except Exception:  # noqa: BLE001 - outside Harness (tests) or an older layout
        return 1


def handle(ctx, method, path, query, body):
    state, secret = ctx["state_dir"], ctx["secret"]
    body = body if isinstance(body, dict) else {}
    try:
        if path == "status" and method == "GET":
            return {
                **core.status(state, secret),
                "skill": core.skill_state(ctx.get("workspace")),
                "ext_dir": str(core.EXT_DIR),
            }
        if path == "skill" and method == "POST":  # the user's button: link the skill for Claude sessions
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
        if path == "updates" and method == "GET":  # a check only, within Harness's 30 s per request
            start = time.monotonic()
            try:
                dok = core.dokploy_check(core.client(state, secret, timeout=4))
            except core.DokployError as e:
                dok = {"error": e.code, "message": e.message}
            try:
                trf = core.traefik_check(core.client(state, secret, timeout=4))
            except core.DokployError as e:
                trf = {"error_code": e.code, "message": e.message}
            budget = max(1.0, core.CHECK_BUDGET + 4 - (time.monotonic() - start))  # 26 s in all, Dokploy reads included
            ext = core.ext_check(core.EXT_DIR, _supported_api(), budget=min(core.CHECK_BUDGET, budget))
            return {"extension": ext, "dokploy": dok, "traefik": trf, "harness": "/settings/updates"}
        if path == "stats" and method == "GET":  # sampled every few seconds while the Server tab is open
            return core.live_stats(core.client(state, secret, timeout=10))
        if path == "traefik" and method == "GET":  # the page follows a Traefik update with it
            return core.traefik_check(core.client(state, secret, timeout=6))
        if path == "update" and method == "POST":  # after the user confirmed exactly this version
            what, to = body.get("what"), str(body.get("to") or "")
            if what == "extension":
                chk = core.ext_update(core.EXT_DIR, _supported_api(), to)
                if ctx.get("workspace"):
                    with contextlib.suppress(
                        core.DokployError
                    ):  # links only a missing skill: a copy waits for the user
                        core.install_skill(ctx["workspace"], replace_copy=False)
                return {"updated": "extension", "version": chk["new"]}
            if what == "dokploy":
                chk = core.dokploy_update(core.client(state, secret, timeout=8), to, state)
                return {"updated": "dokploy", "version": chk["latest"]}
            if what == "traefik":
                chk = core.traefik_update(core.client(state, secret, timeout=20), to)
                return {"updated": "traefik", "version": chk["recommended"]}
            return 400, {"error": "bad_target", "message": "what must be extension, dokploy or traefik"}
        if path == "dashboard" and method == "GET":  # short timeout: 14 reads must fit in Harness's 30 s
            return core.dashboard(core.client(state, secret, timeout=8))
        c = core.client(state, secret)
        if path == "cleanup" and method == "POST":  # the build cache only: nothing else can be named here
            if body.get("what") != "build-cache":
                return 400, {"error": "bad_target", "message": "only the build cache can be cleared from here"}
            return core.clear_build_cache(core.client(state, secret, timeout=25))
        if path == "container-log" and method == "GET":  # what the container prints now (read only)
            svc = core.lookup(c, str(query.get("id") or ""))
            try:
                lines = int(query.get("lines") or 200)
            except ValueError:
                return 400, {"error": "bad_value", "message": "lines must be a number"}
            return core.container_logs(
                c,
                svc,
                query.get("container") or None,
                lines,
                str(query.get("since") or "all"),
                str(query.get("search") or ""),
            )
        if path == "backup" and method == "POST":  # runs one existing backup now, after the page asked
            return core.run_backup(core.client(state, secret, timeout=25), str(body.get("id") or ""))
        if path == "deployment-log" and method == "GET":
            return core.deployment_log(c, str(query.get("id") or ""))
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
        if path == "restart" and method == "POST":  # one container of the service, after the page asked the user
            svc = core.lookup(c, str(body.get("id") or ""))
            core.guard(state, svc)
            return core.restart_container(c, svc, str(body.get("container") or ""))
        if path == "scale" and method == "POST":  # replicas of an application, after the page asked the user
            svc = core.lookup(c, str(body.get("id") or ""))
            core.guard(state, svc)
            return core.scale(c, svc, body.get("replicas"))
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
            "bad_value": 400,
            "rollback_off": 409,
            "no_rollback": 409,
            "not_supported": 409,
            "deploy_in_progress": 409,
            "target_changed": 409,
            "skill_linked": 409,
            "skill_custom": 409,
            "skill_failed": 409,
            "update_refused": 409,
            "update_failed": 409,
            "up_to_date": 409,
            "update_in_progress": 409,
            "not_found": 404,
            "no_log": 404,
        }.get(e.code, 422)
        return status, {"error": e.code, "message": e.message}
    return 404, {"error": "not_found", "message": f"{method} {path}"}
