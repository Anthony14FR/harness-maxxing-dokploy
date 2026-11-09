"""A local fake Dokploy API (shapes of Dokploy v0.30) and a fake `maxxing keys` command."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

ROOT = Path(__file__).resolve().parent.parent
KEY = "dk-test-key"

PROJECTS = [
    {
        "projectId": "p1",
        "name": "acme",
        "environments": [
            {
                "environmentId": "e1",
                "name": "production",
                "applications": [
                    {
                        "applicationId": "a1",
                        "name": "web",
                        "appName": "acme-web-x1",
                        "applicationStatus": "done",
                        "buildType": "nixpacks",
                        "owner": "acme",
                        "repository": "web",
                        "sourceType": "github",
                        "replicas": 1,
                        "rollbackActive": True,
                        "updateConfigSwarm": {"Order": "start-first", "Parallelism": 1},
                        "domains": [{"host": "web.example.com", "https": True, "port": 3000, "path": "/"}],
                    },
                    {
                        "applicationId": "a2",
                        "name": "api",
                        "appName": "acme-api-x2",
                        "applicationStatus": "error",
                        "customGitUrl": "https://git.example.com/acme/api.git",
                        "sourceType": "git",
                        "domains": [],
                    },
                ],
                "compose": [
                    {
                        "composeId": "c1",
                        "name": "stack",
                        "appName": "acme-stack",
                        "composeStatus": "running",
                        "sourceType": "raw",
                        "composeType": "docker-compose",
                    }
                ],
                "postgres": [{"postgresId": "pg1", "name": "db", "appName": "acme-db"}],
            }
        ],
    },
    {
        "projectId": "p2",
        "name": "old",
        "applications": [{"applicationId": "a3", "name": "web", "appName": "old-web", "applicationStatus": "idle"}],
    },
]


CONTAINERS = {
    "acme-web-x1": [
        {"containerId": "1", "name": "acme-web-x1.1.abc", "state": "running", "status": "Up 2 hours"},
        {"containerId": "9", "name": "acme-web-x1-admin.1.zz", "state": "running", "status": "Up"},  # another app
    ],
    "acme-stack": [
        {"containerId": "2", "name": "acme-stack-web-1", "state": "running", "status": "Up 1 hour"},
        {"containerId": "3", "name": "acme-stack-worker-1", "state": "exited", "status": "Exited (1) 5 minutes ago"},
        {"containerId": "4", "name": "acme-stack-migrate-1", "state": "exited", "status": "Exited (0) 1 hour ago"},
        {"containerId": "5", "name": "acme-stacker-web-1", "state": "running", "status": "Up"},  # another stack
    ],
}

# docker inspect of a compose container routing its own hosts (no Dokploy domain); Env must never leave core
INSPECT = {
    "2": {
        "Id": "2",
        "Config": {
            "Env": ["SECRET_TOKEN=do-not-leak"],
            "Labels": {
                "com.docker.compose.service": "web",
                "traefik.enable": "true",
                "traefik.http.routers.shop.rule": "Host(`shop.example.com`) || Host(`WWW.shop.example.com`)",
                "traefik.http.routers.shop.entrypoints": "websecure",
                "traefik.http.routers.shop.tls.certresolver": "letsencrypt",
                "traefik.http.routers.shop-http.rule": "Host(`shop.example.com`)",
                "traefik.http.routers.shop-http.entrypoints": "web",
                "traefik.http.routers.api.rule": "Host(`api.shop.example.com`) && PathPrefix(`/v1`)",
                "traefik.http.routers.api.tls": "true",
                "traefik.http.routers.any.rule": "HostRegexp(`{sub:[a-z]+}.example.com`)",
            },
        },
    },
}


def _all(plural):
    for p in PROJECTS:
        for e in p.get("environments") or [p]:
            yield from e.get(plural) or []


def _slim():
    """What project.all really gives (v0.30): apps and stacks carry only id, name and state."""
    keep = {
        "applications": ("applicationId", "name", "applicationStatus"),
        "compose": ("composeId", "name", "composeStatus"),
    }

    def env(e):
        return {k: ([{f: x[f] for f in keep[k] if f in x} for x in v] if k in keep else v) for k, v in e.items()}

    return [
        {**p, **({"environments": [env(e) for e in p["environments"]]} if "environments" in p else env(p))}
        for p in PROJECTS
    ]


class FakeDokploy:
    def __init__(self, logs: Path):
        self.calls: list[tuple[str, str, dict]] = []
        self.logs = logs
        self.broken: set[str] = set()  # procedures that answer 500
        self.dokploy_version, self.dokploy_latest = "v0.30.10", "v0.31.0"
        fake = self

        class H(BaseHTTPRequestHandler):
            def _go(self, method):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                code, out = fake.handle(method, self.path, self.headers, raw)
                data = out if isinstance(out, bytes) else json.dumps(out).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                if code in (301, 302):
                    self.send_header("Location", "http://127.0.0.1:9/elsewhere")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._go("GET")

            def do_POST(self):
                self._go("POST")

            def log_message(self, *a):
                pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def handle(self, method, path, headers, raw):
        if headers.get("x-api-key") != KEY:
            return 401, {"message": "Unauthorized"}
        u = urlsplit(path)
        proc = u.path.removeprefix("/api/")
        data = json.loads(raw) if raw else dict(parse_qsl(u.query))
        self.calls.append((method, proc, data))
        if proc in self.broken:
            return 500, {"message": "boom"}
        if proc == "project.all":
            return 200, _slim()
        if proc == "redirect.me":
            return 302, b""
        if proc in ("application.one", "compose.one"):
            key, plural = ("applicationId", "applications") if proc == "application.one" else ("composeId", "compose")
            return next(((200, x) for x in _all(plural) if x[key] == data.get(key)), (404, {"message": "not found"}))
        if proc == "docker.getContainersByAppNameMatch":
            return 200, CONTAINERS.get(data.get("appName"), [])
        if proc == "docker.getConfig":
            if data.get("containerId") not in INSPECT:
                return 404, {"message": "No such container"}
            return 200, INSPECT[data["containerId"]]
        if proc == "docker.getStackContainersByAppName":
            return 200, [
                {"name": f"{data['appName']}_web.1", "state": "running", "currentState": "Running 2 hours ago"},
                {"name": f"{data['appName']}_web.1", "state": "shutdown", "currentState": "Shutdown 2 hours ago"},
                {"name": f"{data['appName']}_worker.1", "state": "shutdown", "currentState": "Failed 1 minute ago"},
            ]
        if proc == "settings.getDokployVersion":
            return 200, self.dokploy_version
        if proc == "settings.getUpdateData":
            return 200, {
                "latestVersion": self.dokploy_latest,
                "updateAvailable": self.dokploy_latest != self.dokploy_version,
            }
        if proc == "settings.updateServer":
            return 200, True
        if proc == "application.create":
            return 200, {"applicationId": "new1", "name": data["name"]}
        if proc == "deployment.all":
            return 200, [
                {
                    "deploymentId": "d0",
                    "title": "first",
                    "status": "done",
                    "createdAt": "2026-09-01T10:00:00+02:00",
                    "logPath": None,
                    "rollbackId": "r0",
                },
                {
                    "deploymentId": "d1",
                    "title": "old",
                    "status": "done",
                    "createdAt": "2026-10-01T10:00:00Z",
                    "logPath": str(self.logs / "acme-web-x1" / "d1.log"),
                    "rollbackId": "r1",
                },
                {
                    "deploymentId": "d2",
                    "title": "fix: build\n\nlong body",
                    "status": "error",
                    "createdAt": "2026-11-01T10:00:00Z",
                    "logPath": "/elsewhere/d2.log",
                },
            ]
        if proc in (
            "application.deploy",
            "application.redeploy",
            "compose.deploy",
            "compose.redeploy",
            "domain.create",
            "application.saveGitProvider",
            "application.saveBuildType",
            "application.stop",
            "application.start",
            "compose.stop",
            "compose.start",
            "rollback.rollback",
        ):
            return 200, b""
        return 404, {"message": "no such procedure"}

    def writes(self):
        return [c for c in self.calls if c[0] == "POST"]

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"t_{name}", ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def core():
    return load("dokploy_core")


@pytest.fixture
def keys(tmp_path):
    """The Keys vault as a dict: `secret` for api.py, and a fake `maxxing` command for dokploy.py."""
    return {}


@pytest.fixture
def fake(tmp_path, monkeypatch):
    logs = tmp_path / "dokploy-logs"
    monkeypatch.setenv("DOKPLOY_LOGS_DIR", str(logs))
    f = FakeDokploy(logs)
    yield f
    f.close()


@pytest.fixture
def state(tmp_path):
    d = tmp_path / "state" / "extensions" / "dokploy"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def maxxing_bin(tmp_path, keys, monkeypatch):
    """A fake `maxxing keys get|list --json` reading `keys`, so dokploy.py runs without Harness."""
    vault = tmp_path / "vault.json"
    script = tmp_path / "maxxing"
    script.write_text(f"""#!{sys.executable}
import json, sys
v = json.load(open({str(vault)!r}))
a = sys.argv[1:]
if a[:2] == ["keys", "get"]:
    k = v.get(a[2])
    print(k["value"]) if k else sys.exit(1)
elif a[:2] == ["keys", "list"]:
    print(json.dumps([{{"name": n, "expose": x["expose"]}} for n, x in v.items()]))
""")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)

    def put(name, value, expose=False):
        keys[name] = value
        data = json.loads(vault.read_text()) if vault.exists() else {}
        data[name] = {"value": value, "expose": expose}
        vault.write_text(json.dumps(data))

    put("UNRELATED", "x")
    monkeypatch.setenv("MAXXING_BIN", str(script))
    monkeypatch.setenv("MAXXING_STATE", str(tmp_path / "state"))
    return put


@pytest.fixture(autouse=True)
def _skill_copy(monkeypatch, tmp_path):
    """Tests link and write through the skill folder: give them a copy, never the repository's own files."""
    import shutil

    src = tmp_path / "shipped-skill" / "dokploy"
    shutil.copytree(ROOT / "skill" / "dokploy", src)
    monkeypatch.setenv("DOKPLOY_SKILL_SRC", str(src))


@pytest.fixture(autouse=True)
def _no_real_state(monkeypatch, tmp_path):
    monkeypatch.setenv("MAXXING_STATE", str(tmp_path / "state"))
    monkeypatch.delenv("DOKPLOY_API_KEY", raising=False)
    (tmp_path / "state").mkdir(exist_ok=True)  # the CLI reads the workspace here: never the real /root/maxxing
    (tmp_path / "state" / "config.json").write_text(json.dumps({"workspace": str(tmp_path / "workspace")}))
    os.umask(0o022)
