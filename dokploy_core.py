"""Dokploy API client shared by api.py (the page) and dokploy.py (sessions); standard library only."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

KEY = "DOKPLOY_API_KEY"
DEFAULT_URL = "http://127.0.0.1:3000"
LOGS = Path("/etc/dokploy/logs")
TIMEOUT = 20
LOG_MAX_LINES = 2000
DB_KINDS = ("postgres", "mysql", "mariadb", "mongo", "redis")
KINDS = ("application", "compose") + DB_KINDS
BUILD_TYPES = ("dockerfile", "nixpacks", "railpack", "heroku_buildpacks", "paketo_buildpacks", "static")
TAILNET = ipaddress.ip_network("100.64.0.0/10")
HOST_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]$")
BRANCH_RE = re.compile(r"^(?!-)[A-Za-z0-9._/-]{1,200}$")
NAME_RE = re.compile(r"^(?!-)[A-Za-z0-9 ._-]{1,63}$")
PATH_RE = re.compile(r"^/[A-Za-z0-9._~/-]*$")
GIT_URL_RE = re.compile(r"^(https://|ssh://)[^\s'\"\\]+$|^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[^\s'\"\\-][^\s'\"\\]*$")

_ID = {
    "application": "applicationId",
    "compose": "composeId",
    "postgres": "postgresId",
    "mysql": "mysqlId",
    "mariadb": "mariadbId",
    "mongo": "mongoId",
    "redis": "redisId",
}
_STATUS = {"application": "applicationStatus", "compose": "composeStatus"}
_PLURAL = {"application": "applications", "compose": "compose"}

Secret = Callable[[str], "str | None"]


class DokployError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


# ---- settings ------------------------------------------------------------------------------------------------
def logs_dir() -> Path:
    return Path(os.environ.get("DOKPLOY_LOGS_DIR") or LOGS)


def fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def load_settings(state_dir: str | Path) -> dict:
    """{} when there is none yet; an unreadable file fails closed, so protected services never silently open."""
    f = Path(state_dir) / "settings.json"
    if not f.exists():
        return {}
    try:
        s = json.loads(f.read_text())
    except (OSError, ValueError):
        s = None
    if not isinstance(s, dict) or not isinstance(s.get("protected", []), list):
        raise DokployError("bad_settings", f"{f} cannot be read: fix or delete it, then connect again")
    return s


@contextlib.contextmanager
def _locked(state_dir: str | Path):
    """Serialises read-modify-write of settings.json between the page's requests and sessions."""
    d = Path(state_dir)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / ".settings.lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield


def save_settings(state_dir: str | Path, settings: dict | None) -> None:
    """Atomic write, readable by root only; None removes the file."""
    d = Path(state_dir)
    f = d / "settings.json"
    if settings is None:
        f.unlink(missing_ok=True)
        return
    d.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".settings-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(settings, fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, f)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def check_url(url: str) -> str:
    """The URL without trailing slash; plain http only to this machine or a private network (the key goes in clear)."""
    u = (url or "").strip().rstrip("/")
    p = urllib.parse.urlsplit(u)
    try:
        _ = p.port  # out of range raises here, not in the request
    except ValueError:
        raise DokployError("invalid_url", "the Dokploy URL has an invalid port") from None
    if (
        p.scheme not in ("http", "https")
        or not p.hostname
        or p.username
        or p.password
        or p.query
        or p.fragment
        or p.path not in ("", "/")
    ):
        raise DokployError("invalid_url", "the Dokploy URL must be http(s)://host[:port]")
    if p.scheme == "http" and not _private(p.hostname):
        raise DokployError("invalid_url", "use https for a Dokploy on another network: the key would travel in clear")
    return u


def _private(host: str) -> bool:
    h = host.lower()
    if h == "localhost" or h.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    if ip.is_link_local:  # 169.254.x (cloud metadata) is never a Dokploy
        return False
    return ip.is_loopback or ip.is_private or ip in TAILNET


def status(state_dir: str | Path, secret: Secret) -> dict:
    """{connected, url, key_present, key_changed}; no network call."""
    s = load_settings(state_dir)
    key = (secret(KEY) or "").strip()
    changed = bool(s.get("url") and key and s.get("key") != fingerprint(key))
    return {
        "connected": bool(s.get("url") and key and not changed),
        "url": s.get("url") or None,
        "key_present": bool(key),
        "key_changed": changed,
    }


def connect(state_dir: str | Path, secret: Secret, url: str) -> dict:
    """Checks the key from Keys against `url` with project.all, then remembers the URL and the key's fingerprint."""
    base, key = check_url(url or DEFAULT_URL), (secret(KEY) or "").strip()
    if not key:
        raise DokployError("no_key", f"add {KEY} in Settings -> Keys first (Dokploy -> Profile -> API keys)")
    projects = Client(base, key).get("project.all")
    if not isinstance(projects, list):
        raise DokployError("bad_response", "project.all did not answer a list")
    with _locked(state_dir):
        save_settings(state_dir, {**load_settings(state_dir), "url": base, "key": fingerprint(key)})
    return {"connected": True, "url": base, "projects": len(projects)}


def disconnect(state_dir: str | Path) -> bool:
    """Forgets the address and the key's fingerprint; protected services stay protected."""
    with _locked(state_dir):
        s = load_settings(state_dir)
        rest = {k: v for k, v in s.items() if k not in ("url", "key")}
        save_settings(state_dir, rest or None)
    return bool(s.get("url"))


def protected(state_dir: str | Path) -> set[str]:
    p = load_settings(state_dir).get("protected")
    return {x for x in p if isinstance(x, str)} if isinstance(p, list) else set()


def set_protected(state_dir: str | Path, svc_id: str, on: bool) -> set[str]:
    """Only the page calls this; dokploy.py has no command for it."""
    with _locked(state_dir):
        ids = protected(state_dir)
        (ids.add if on else ids.discard)(svc_id)
        save_settings(state_dir, {**load_settings(state_dir), "protected": sorted(ids)})
    return ids


def guard(state_dir: str | Path, svc: dict) -> None:
    """Every write goes through this first: a protected service is read-only."""
    if svc["id"] in protected(state_dir):
        raise DokployError("protected", f"{svc['name']} is protected: lift it on the Dokploy page in Harness first")


def risks(svc: dict) -> list[str]:
    """What a deploy does beyond the obvious, for the confirmation: downtime, nothing rebuilt."""
    out = []
    if svc["kind"] in _PLURAL and svc.get("detailed") is False:
        return ["downtime", "unknown"]  # Dokploy did not give its details: assume the worst
    if svc["kind"] == "compose" or (svc["kind"] == "application" and not svc.get("start_first")):
        out.append("downtime")  # compose recreates its containers; a swarm app stops first unless start-first
    if svc.get("source") in ("raw", "docker", "drop"):
        out.append("no_rebuild")  # no git source: the same image(s) start again
    return out


def client(state_dir: str | Path, secret: Secret) -> Client:
    s = load_settings(state_dir)
    if not s.get("url"):
        raise DokployError("not_connected", "Dokploy is not connected: open the Dokploy page in Harness")
    key = (secret(KEY) or "").strip()
    if not key:
        raise DokployError("no_key", f"{KEY} is missing in Settings -> Keys")
    if s.get("key") != fingerprint(key):
        raise DokployError("key_changed", f"{KEY} changed: check it again on the Dokploy page")
    return Client(s["url"], key)


# ---- HTTP ----------------------------------------------------------------------------------------------------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a: Any, **k: Any) -> None:
        return None  # the key is never resent to another address


_OPENER = urllib.request.build_opener(_NoRedirect)


class Client:
    def __init__(self, base: str, key: str):
        self.base = base.rstrip("/") + "/api/"
        self.key = key

    def _do(self, method: str, proc: str, params: dict | None = None, body: dict | None = None) -> Any:
        url = self.base + proc + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "x-api-key": self.key,
                "Accept": "application/json",
                "User-Agent": "harness-maxxing-dokploy",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with _OPENER.open(req, timeout=TIMEOUT) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise self._error(proc, e.code, e.read()[:2000]) from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise DokployError("unreachable", f"Dokploy does not answer ({type(e).__name__})") from None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            raise DokployError("bad_response", "Dokploy answered something that is not JSON") from None

    @staticmethod
    def _error(proc: str, code: int, raw: bytes) -> DokployError:
        if code in (401, 403):
            return DokployError("refused", "the Dokploy key is refused")
        if code == 404:
            return DokployError("not_found", f"Dokploy: {proc} not found")
        if 300 <= code < 400:
            return DokployError("redirected", "Dokploy redirected the request: check its URL")
        try:
            j = json.loads(raw)
            msg = str((j.get("message") if isinstance(j, dict) else None) or j)
        except ValueError:
            msg = raw.decode("utf-8", "replace")
        return DokployError("api_error", f"Dokploy answered {code} to {proc}: {msg[:200]}")

    def get(self, proc: str, params: dict | None = None) -> Any:
        return self._do("GET", proc, params=params)

    def post(self, proc: str, body: dict) -> Any:
        return self._do("POST", proc, body=body)


# ---- services --------------------------------------------------------------------------------------------------
def _repo(a: dict) -> str | None:
    if a.get("owner") and a.get("repository"):
        return f"{a['owner']}/{a['repository']}"
    return a.get("customGitUrl") or a.get("gitlabPathNamespace") or None


def _service(kind: str, s: dict, p: dict, e: dict) -> dict:
    return {
        "kind": kind,
        "id": s[_ID[kind]],
        "name": s.get("name") or s.get("appName") or s[_ID[kind]],
        "app_name": s.get("appName"),
        "project": p.get("name"),
        "project_id": p.get("projectId"),
        "environment": e.get("name") if e is not p else None,
        "environment_id": e.get("environmentId"),
        "status": s.get(_STATUS.get(kind, "applicationStatus")) or None,
        "domains": [
            {"host": d.get("host"), "https": bool(d.get("https")), "port": d.get("port"), "path": d.get("path") or "/"}
            for d in s.get("domains") or []
            if isinstance(d, dict) and d.get("host")
        ],
        "repo": _repo(s) if kind in _PLURAL else None,
        "build": s.get("buildType") if kind == "application" else None,
        "source": s.get("sourceType") if kind in _PLURAL else None,
        "start_first": _start_first(s) if kind == "application" else None,
    }


def _start_first(a: dict) -> bool | None:
    u = a.get("updateConfigSwarm")
    return (u.get("Order") == "start-first") if isinstance(u, dict) else None


def services(projects: Any) -> list[dict]:
    """project.all flattened: one entry per application, compose stack and database."""
    out: list[dict] = []
    for p in projects if isinstance(projects, list) else []:
        if not isinstance(p, dict):
            continue
        envs = p.get("environments") if isinstance(p.get("environments"), list) else [p]
        for e in envs:
            if not isinstance(e, dict):
                continue
            for kind in KINDS:
                for s in e.get(_PLURAL.get(kind, kind)) or []:
                    if isinstance(s, dict) and s.get(_ID[kind]):
                        out.append(_service(kind, s, p, e))
    return out


def environments(projects: Any) -> list[dict]:
    """Where an app can be created: {id, name, project, project_id}."""
    return [
        {"id": e["environmentId"], "name": e.get("name"), "project": p.get("name"), "project_id": p.get("projectId")}
        for p in (projects if isinstance(projects, list) else [])
        if isinstance(p, dict)
        for e in p.get("environments") or []
        if isinstance(e, dict) and e.get("environmentId")
    ]


def inventory(c: Client) -> list[dict]:
    """project.all, then <kind>.one of each app and stack: project.all (v0.30) gives them only id, name and state."""
    svcs = services(c.get("project.all"))

    def one(s: dict) -> dict:
        try:
            full = c.get(f"{s['kind']}.one", {_ID[s["kind"]]: s["id"]})
        except DokployError:
            return {**s, "detailed": False}  # shown with what project.all gave
        if not isinstance(full, dict):
            return {**s, "detailed": False}
        more = _service(
            s["kind"],
            {**full, _ID[s["kind"]]: s["id"]},
            {"name": s["project"], "projectId": s["project_id"]},
            {"name": s["environment"], "environmentId": s["environment_id"]},
        )
        return {
            **s,
            **{k: v for k, v in more.items() if v not in (None, [], "") or k == "domains"},
            "environment": s["environment"],
            "detailed": True,
        }

    todo = [s for s in svcs if s["kind"] in _PLURAL]
    if todo:
        with ThreadPoolExecutor(max_workers=min(8, len(todo))) as ex:
            done = {s["id"]: x for s, x in zip(todo, ex.map(one, todo), strict=True)}
        svcs = [done.get(s["id"], s) for s in svcs]
    return svcs


def find(svcs: list[dict], ref: str) -> dict:
    """By id, then name or app name (case-insensitive); `ambiguous` lists the candidates."""
    r = (ref or "").strip()
    hit = [s for s in svcs if s["id"] == r]
    if not hit:
        low = r.lower()
        hit = [s for s in svcs if low in ((s["name"] or "").lower(), (s["app_name"] or "").lower())]
    if not hit:
        raise DokployError("not_found", f"no Dokploy service named {r!r} (see: list)")
    if len(hit) > 1:
        names = ", ".join(f"{s['project']}/{s['name']} ({s['kind']}, {s['id']})" for s in hit)
        raise DokployError("ambiguous", f"{r!r} matches several services: {names} - use the id")
    return hit[0]


def _deployable(svc: dict) -> None:
    if svc["kind"] not in _PLURAL:
        raise DokployError("not_deployable", f"{svc['name']} is a {svc['kind']} database: nothing to deploy")


def _check(value: str, rx: re.Pattern, what: str) -> str:
    """Values a (possibly prompt-injected) session passes on to Dokploy: git clone, Traefik rules, names."""
    v = (value or "").strip()
    if not rx.match(v):
        raise DokployError("invalid_value", f"invalid {what}: {v[:80]!r}")
    return v


# ---- writes (callers get the user's agreement first) -----------------------------------------------------------
def deploy(c: Client, svc: dict, title: str | None = None, again: bool = False) -> None:
    _deployable(svc)
    body: dict[str, Any] = {_ID[svc["kind"]]: svc["id"]}
    if title:
        body["title"] = title.strip()[:120]
    c.post(f"{svc['kind']}.{'redeploy' if again else 'deploy'}", body)


def domain_add(
    c: Client,
    svc: dict,
    host: str,
    port: int | None = None,
    https: bool = True,
    path: str | None = None,
    service: str | None = None,
) -> None:
    _deployable(svc)
    host = _check((host or "").lower(), HOST_RE, "host name")
    if port is not None and not 1 <= int(port) <= 65535:
        raise DokployError("invalid_value", "the port must be 1-65535")
    if path is not None and not PATH_RE.match(path):
        raise DokployError("invalid_value", "the path must start with / and use letters, digits, . _ ~ - /")
    if svc["kind"] == "compose" and not service:
        raise DokployError("service_needed", "a compose stack needs --service: the service of the stack to serve")
    body: dict[str, Any] = {
        "host": host,
        "https": https,
        "certificateType": "letsencrypt" if https else "none",
        "domainType": svc["kind"],
        _ID[svc["kind"]]: svc["id"],
    }
    if port:
        body["port"] = int(port)
    if path:
        body["path"] = path
    if service:
        body["serviceName"] = _check(service, NAME_RE, "service name")
    c.post("domain.create", body)


def app_create(
    c: Client,
    environment_id: str,
    name: str,
    repo: str,
    branch: str = "main",
    build: str = "nixpacks",
    build_path: str = "/",
) -> str:
    """application.create, then its git source and build type; returns the new application id."""
    if build not in BUILD_TYPES:
        raise DokployError("invalid_value", f"build must be one of {', '.join(BUILD_TYPES)}")
    environment_id = _check(environment_id, re.compile(r"^[A-Za-z0-9_-]{1,64}$"), "environment id")
    name = _check(name, NAME_RE, "app name")
    repo = _check(repo, GIT_URL_RE, "git URL (https://, ssh:// or git@host:path)")
    branch = _check(branch, BRANCH_RE, "branch")
    if not PATH_RE.match(build_path or "") or ".." in build_path:
        raise DokployError("invalid_value", "the build path must start with / and stay inside the repository")
    app = c.post("application.create", {"name": name, "environmentId": environment_id})
    app_id = app.get("applicationId") if isinstance(app, dict) else None
    if not app_id:
        raise DokployError("bad_response", "application.create did not give the new application id")
    c.post(
        "application.saveGitProvider",
        {
            "applicationId": app_id,
            "customGitUrl": repo,
            "customGitBranch": branch,
            "customGitBuildPath": build_path,
            "watchPaths": None,
        },
    )
    c.post(
        "application.saveBuildType",
        {
            "applicationId": app_id,
            "buildType": build,
            "dockerfile": None,
            "dockerContextPath": None,
            "dockerBuildStage": None,
            "herokuVersion": None,
            "railpackVersion": None,
        },
    )
    return app_id


# ---- reads -----------------------------------------------------------------------------------------------------
def deployments(c: Client, svc: dict) -> list[dict]:
    """Newest first: {id, title, status, created, log_path}."""
    _deployable(svc)
    proc, key = (
        ("deployment.all", "applicationId")
        if svc["kind"] == "application"
        else ("deployment.allByCompose", "composeId")
    )
    rows = c.get(proc, {key: svc["id"]}) or []
    out = [
        {
            "id": d.get("deploymentId"),
            "title": (d.get("title") or "").strip().split("\n")[0][:120] or None,
            "status": d.get("status"),
            "created": d.get("createdAt"),
            "log_path": d.get("logPath"),
        }
        for d in rows
        if isinstance(d, dict)
    ]  # Dokploy titles a git deployment with the whole commit message
    return sorted(out, key=lambda d: d["created"] or "", reverse=True)


def log(dep: dict, lines: int = 200) -> str:
    """Tail of a deployment log; only a regular file under Dokploy's log folder of this server is read."""
    raw = dep.get("log_path")
    if not raw:
        raise DokployError("no_log", "this deployment has no log file")
    root = logs_dir().resolve()
    p = Path(raw).resolve()
    if root not in p.parents or not p.is_file():
        raise DokployError("remote_log", "the log is not on this server: open it in Dokploy")
    n = max(1, min(int(lines), LOG_MAX_LINES))
    with p.open("rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 256 * 1024))
        tail = f.read().decode("utf-8", "replace").splitlines()
    return "\n".join(tail[-n:])
