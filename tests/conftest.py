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

# Dashboard reads (Dokploy v0.31); "leak-*" values sit where Dokploy nests secrets: they must never reach the page
DASH = {
    "project.homeStats": {
        "projects": 2,
        "environments": 2,
        "applications": 3,
        "compose": 1,
        "databases": 1,
        "services": 5,
        "status": {"running": 3, "error": 1, "idle": 1},
    },
    "docker.getServerHealth": {
        "checkedAt": "2026-11-10T08:00:00Z",
        "containers": {"containerCount": 6, "serviceCount": 2},
        "resources": {"memTotalBytes": 8_000_000_000, "memUsedBytes": 6_000_000_000, "cpuCount": 4},
        "disk": {"totalBytes": 100_000_000_000, "usedBytes": 90_000_000_000},
        "reservation": {"memoryReservedBytes": 1_000_000_000, "cpuReservedNanoCpus": 1_500_000_000},
    },
    "settings.checkInfrastructureHealth": {"postgres": {"status": "healthy"}, "traefik": {"status": "healthy"}},
    "settings.getTraefikOverview": {
        "state": "running",
        "currentVersion": "3.6.25",
        "recommendedVersion": "3.7.16",
        "versionStatus": "outdated",
        "startedAt": "2026-11-10T07:00:00Z",
        "lastUpdateError": {"leak": "leak-traefik"},
    },
    "settings.getIp": "203.0.113.10",
    "settings.getDockerDiskUsage": [
        {
            "type": "Images",
            "totalCount": 6,
            "active": 5,
            "size": "7.5GB",
            "reclaimable": "3.2GB (42%)",
            "sizeBytes": 8e9,
        }
    ],
    "settings.getLogCleanupStatus": {"enabled": True, "cronExpression": "0 0 * * *"},
    "server.all": [
        {
            "serverId": "s1",
            "name": "edge",
            "ipAddress": "198.51.100.7",
            "serverStatus": "active",
            "sshKey": {"privateKey": "leak-ssh-key"},
            "sshKeyId": "k1",
        }
    ],
    "overview.services": [
        {
            "id": "a1",
            "name": "web",
            "appName": "acme-web-x1",
            "type": "application",
            "status": "done",
            "projectName": "acme",
            "environmentName": "production",
            "lastDeployAt": "2026-11-10T07:30:00Z",
        },
        {
            "id": "c1",
            "name": "stack",
            "appName": "acme-stack",
            "type": "compose",
            "status": "done",
            "projectName": "acme",
            "environmentName": "production",
        },
        {"id": "pg1", "name": "db", "appName": "acme-db", "type": "postgres", "status": "done", "projectName": "acme"},
    ],
    # a database's own backups (overview.backups can be empty while they exist); its destination holds the S3 keys
    "postgres.one": {
        "postgresId": "pg1",
        "backups": [
            {
                "backupId": "b2",
                "schedule": "0 4 * * *",
                "enabled": True,
                "database": "shop",
                "databaseType": "postgres",
                "backupType": "database",
                "keepLatestCount": 3,
                "destination": {"name": "offsite", "secretAccessKey": "leak-dest-secret", "accessKey": "leak-dest-key"},
                "deployments": [{"status": "done", "createdAt": "2026-11-09T04:00:00Z"}],
            }
        ],
    },
    "backup.one": {
        "backupId": "b2",
        "databaseType": "postgres",
        "backupType": "database",
        "destination": {"secretAccessKey": "leak-dest-secret"},
    },
    "backup.manualBackupPostgres": True,
    "docker.restartContainer": True,
    "previewDeployment.all": [
        {
            "previewDeploymentId": "pv1",
            "branch": "feat/cart",
            "pullRequestNumber": "42",
            "previewStatus": "done",
            "pullRequestTitle": "New cart",
            "pullRequestURL": "https://github.com/acme/web/pull/42",
            "createdAt": "2026-11-10T07:00:00Z",
            "domain": {"host": "pr-42.web.example.com", "https": True},
            "deployments": [{"status": "error", "createdAt": "2026-11-10T07:05:00Z"}],
        },
        {
            "previewDeploymentId": "pv2",
            "pullRequestNumber": "43",
            "pullRequestURL": "javascript:alert(1)",
            "domain": {"host": "bad host"},
            "createdAt": "2026-11-09T07:00:00Z",
        },
    ],
    "previewDeployment.one": {"previewDeploymentId": "pv1", "applicationId": "a1"},
    "previewDeployment.redeploy": True,
    "swarm.getContainerStats": [
        {"Name": "acme-web-x1.1.abc", "CPUPerc": "12.50%", "MemPerc": "1.00%", "MemUsage": "80MiB / 8GiB"},
        {"Name": "acme-web-x1.2.def", "CPUPerc": "2.50%", "MemPerc": "0.50%", "MemUsage": "40MiB / 8GiB"},
        {"Name": "acme-stack-web-1", "CPUPerc": "1.00%", "MemPerc": "0.20%", "MemUsage": "16.5MB / 8GiB"},
        {"Name": "dokploy.1.zzz", "CPUPerc": "3.00%", "MemPerc": "4.00%", "MemUsage": "300MiB / 8GiB"},
        {"Name": "odd", "CPUPerc": "--", "MemPerc": "", "MemUsage": "n/a"},
    ],
    "application.update": True,
    "application.reload": True,
    "overview.domains": [
        {
            "host": "web.example.com",
            "path": "/",
            "port": 3000,
            "https": True,
            "certificateType": "letsencrypt",
            "enabled": True,
            "serviceName": "web",
            "serviceOwnerId": "a1",
            "serviceOwnerType": "application",
            "projectName": "acme",
            "environmentName": "production",
        },
        {
            "host": "shop.example.com",
            "path": "/",
            "port": 80,
            "https": False,
            "certificateType": "none",
            "enabled": True,
            "serviceName": "stack",
            "serviceOwnerId": "c1",
            "serviceOwnerType": "compose",
            "projectName": "acme",
            "environmentName": "production",
        },
    ],
    "overview.backups": [
        {
            "backupId": "b1",
            "schedule": "0 3 * * *",
            "enabled": True,
            "database": "shop",
            "databaseType": "postgres",
            "keepLatestCount": 7,
            "serviceName": "db",
            "destination": {"secretAccessKey": "leak-s3-secret"},
        }
    ],
    "deployment.allCentralized": [
        {
            "deploymentId": "x1",
            "title": "old",
            "status": "done",
            "applicationId": "a1",
            "createdAt": "2026-11-08T10:00:00Z",
            "finishedAt": "2026-11-08T10:01:00Z",
            "logPath": None,
        },
        {
            "deploymentId": "x2",
            "title": "fix: checkout\n\nbody",
            "status": "error",
            "applicationId": "a1",
            "createdAt": "2026-11-10T07:30:00Z",
            "startedAt": "2026-11-10T07:30:00Z",
            "finishedAt": "2026-11-10T07:31:05Z",
            "errorMessage": "build failed",
            "logPath": "/elsewhere/x2.log",
        },
        {
            "deploymentId": "x3",
            "title": "Backup",
            "status": "done",
            "backupId": "b1",
            "createdAt": "2026-11-10T03:00:00Z",
            "logPath": None,
        },
    ],
    "deployment.queueList": [{"id": "q1"}],
    "settings.updateTraefik": True,
    "application.readLogs": "GET / 200\nclone https://bot:tok@git.example.com/acme/web\n",
    "compose.readLogs": "nginx started\n",
    "postgres.readLogs": "database system is ready\n",
    "docker.getContainers": [
        {
            "containerId": "2",
            "name": "acme-stack-web-1",
            "state": "running",
            "status": "Up 1 hour",
            "image": "nginx",
            "ports": "80/tcp",
        },
        {"containerId": "7", "name": "acme-db.1.x", "state": "running", "status": "Up", "image": "postgres:16"},
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
        if proc in DASH:
            return 200, DASH[proc]
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
elif a[:2] == ["feed", "post"]:  # recorded, as Harness would add it to its feed
    with open({str(tmp_path / "feed.jsonl")!r}, "a") as f:
        f.write(json.dumps(a[2:]) + "\\n")
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
    monkeypatch.setenv("DOKPLOY_NO_TLS_CHECK", "1")  # certificate checks: only against the tests' own TLS server
    (tmp_path / "state").mkdir(exist_ok=True)  # the CLI reads the workspace here: never the real /root/maxxing
    (tmp_path / "state" / "config.json").write_text(json.dumps({"workspace": str(tmp_path / "workspace")}))
    os.umask(0o022)
