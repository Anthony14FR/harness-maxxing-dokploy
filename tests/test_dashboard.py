import json
import sys
import types

import pytest

from conftest import DASH, KEY, load


@pytest.fixture
def api():
    return load("api")


def ctx(state):
    return {
        "id": "dokploy",
        "workspace": str(state.parent.parent / "ws"),
        "state_dir": str(state),
        "secret": {"DOKPLOY_API_KEY": KEY}.get,
    }


@pytest.fixture
def dash(api, fake, state):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    return api.handle(ctx(state), "GET", "dashboard", {}, None)


def test_dashboard_reads_the_whole_dokploy(dash):
    assert dash["stats"]["services"] == 5 and dash["stats"]["status"] == {"running": 3, "error": 1, "idle": 1}
    r = dash["resources"]
    assert (r["cpus"], r["mem_used"], r["disk_total"], r["containers"], r["cpu_reserved"]) == (4, 6e9, 1e11, 6, 1.5)
    assert dash["infra"] == {"postgres": "healthy", "traefik": "healthy"}
    assert dash["traefik"] == {
        "state": "running",
        "version": "3.6.25",
        "recommended": "3.7.16",
        "version_status": "outdated",
        "started": "2026-11-10T07:00:00Z",
        "updating": None,
        "error": None,  # Dokploy gave an object there: never passed on
    }
    assert dash["ip"] == "203.0.113.10" and dash["queue"] == 1
    assert dash["log_cleanup"] == {"enabled": True, "cron": "0 0 * * *"}
    assert dash["disk_usage"][0]["reclaimable"] == "3.2GB (42%)"
    assert dash["servers"] == [{"id": "s1", "name": "edge", "ip": "198.51.100.7", "status": "active", "type": None}]


def test_no_secret_dokploy_nests_reaches_the_page(dash, fake):
    # ssh keys of servers, S3 keys of backup destinations, Traefik error objects: nested values never pass
    assert "leak-" not in json.dumps(dash)
    procs = {p for _, p, _ in fake.calls}
    assert not procs & {"settings.getWebServerSettings", "certificates.all", "destination.all", "sshKey.all"}


def test_deployments_are_named_sorted_and_trimmed(dash):
    deps = dash["deployments"]
    assert [d["id"] for d in deps] == ["x2", "x3", "x1"]  # newest first
    x2 = deps[0]
    assert (x2["service"], x2["title"], x2["error"], x2["kind"], x2["has_log"]) == (
        "web",
        "fix: checkout",
        "build failed",
        "application",
        True,
    )
    assert deps[1]["kind"] == "backup" and deps[1]["service"] is None
    assert all("log_path" not in d and "logPath" not in d for d in deps)


def test_domains_add_the_hosts_a_compose_routes_itself(dash):
    doms = {d["host"]: d for d in dash["domains"]}
    assert doms["web.example.com"]["https"] and not doms["web.example.com"]["routed"]
    assert not doms["shop.example.com"]["routed"]  # declared in Dokploy: not repeated from the labels
    assert doms["www.shop.example.com"]["routed"] and doms["www.shop.example.com"]["service"] == "stack"
    assert doms["api.shop.example.com"]["path"] == "/v1"


def test_backups_show_their_last_run(dash):
    (b,) = dash["backups"]
    assert (b["id"], b["schedule"], b["keep"], b["db_type"]) == ("b1", "0 3 * * *", 7, "postgres")
    assert b["last_run"] == {"status": "done", "at": "2026-11-10T03:00:00Z"}


def test_an_older_dokploy_gives_empty_parts_not_an_error(api, fake, state):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    fake.broken |= set(DASH)
    d = api.handle(ctx(state), "GET", "dashboard", {}, None)
    assert all(v is None for v in d.values())


def test_deployment_log_by_id(api, fake, state):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    code, err = api.handle(ctx(state), "GET", "deployment-log", {"id": "x2"}, None)
    assert err["error"] == "remote_log"  # outside Dokploy's log folder of this server: never read
    code, err = api.handle(ctx(state), "GET", "deployment-log", {"id": "x1"}, None)
    assert (code, err["error"]) == (404, "no_log")
    code, err = api.handle(ctx(state), "GET", "deployment-log", {"id": "nope"}, None)
    assert (code, err["error"]) == (404, "not_found")


@pytest.fixture
def harness(monkeypatch):
    """A stand-in for Harness's own extensions module, as api.py finds it when Harness loads it."""
    pins: list[str] = []
    mod = types.ModuleType("maxxing.extensions")
    mod.pinned_ids = lambda: set(pins)
    mod.set_pinned = lambda eid, on: (pins.append(eid) if on else pins.remove(eid)) or True
    pkg = types.ModuleType("maxxing")
    pkg.extensions = mod
    monkeypatch.setitem(sys.modules, "maxxing", pkg)
    monkeypatch.setitem(sys.modules, "maxxing.extensions", mod)
    return pins


def test_the_page_is_pinned_once_and_an_unpin_is_kept(api, harness, state):
    assert api._auto_pin("dokploy", state) and harness == ["dokploy"]
    harness.clear()  # the user unpins it
    assert not api._auto_pin("dokploy", state) and harness == []
    assert (state / "auto-pinned").exists()


def test_already_pinned_is_only_recorded(api, harness, state):
    harness.append("dokploy")
    assert api._auto_pin("dokploy", state) and harness == ["dokploy"]


def test_no_pin_outside_harness(api, state, monkeypatch):
    monkeypatch.delitem(sys.modules, "maxxing.extensions", raising=False)
    monkeypatch.setitem(sys.modules, "maxxing", None)  # import fails as it does in tests and the CLI
    assert not api._auto_pin("dokploy", state) and not (state / "auto-pinned").exists()


def test_databases_get_their_name_from_the_overview(core, fake, monkeypatch):
    # Dokploy v0.31's project.all gives a database only its id: the page showed the id instead of the name
    c = core.Client(fake.url, KEY)
    slim = [
        {
            "projectId": "p9",
            "name": "shop",
            "environments": [{"environmentId": "e9", "name": "production", "postgres": [{"postgresId": "a1"}]}],
        }
    ]
    real_get = c.get
    monkeypatch.setattr(c, "get", lambda proc, params=None: slim if proc == "project.all" else real_get(proc, params))
    (db,) = core.inventory(c)
    assert (db["name"], db["app_name"], db["status"]) == ("web", "acme-web-x1", "done")  # from overview.services


def test_a_backup_run_older_than_the_list_is_still_found(core):
    deps = [{"deploymentId": f"d{i}", "status": "done", "applicationId": "a1"} for i in range(80)]
    deps.append({"deploymentId": "old", "status": "error", "backupId": "b1", "createdAt": "2026-01-01T00:00:00Z"})
    (b,) = core._backups([{"backupId": "b1"}], deps)
    assert b["last_run"] == {"status": "error", "at": "2026-01-01T00:00:00Z"}


def test_credentials_in_urls_are_hidden(core):
    assert (
        core.redact("fatal: https://bot:ghp_secret@github.com/acme/web.git")
        == "fatal: https://***@github.com/acme/web.git"
    )
    assert core._deployment({"errorMessage": "clone https://x:tok@git.example.com/r failed"}, {})["error"] == (
        "clone https://***@git.example.com/r failed"
    )


def test_an_odd_health_shape_gives_empty_values_not_an_error(core):
    r = core._resources({"resources": [], "disk": "n/a", "containers": None})
    assert r["cpus"] is None and r["disk_total"] is None
    with pytest.raises(core.DokployError):
        core.log({"log_path": 42})


def test_traefik_update_runs_only_the_confirmed_version(api, fake, state):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    chk = api.handle(ctx(state), "GET", "updates", {}, None)["traefik"]
    assert (chk["version"], chk["recommended"], chk["available"]) == ("3.6.25", "3.7.16", True)
    code, err = api.handle(ctx(state), "POST", "update", {}, {"what": "traefik", "to": "3.8.0"})
    assert (code, err["error"]) == (409, "target_changed") and ("POST", "settings.updateTraefik", {}) not in fake.calls
    assert api.handle(ctx(state), "POST", "update", {}, {"what": "traefik", "to": "3.7.16"}) == {
        "updated": "traefik",
        "version": "3.7.16",
    }
    assert ("POST", "settings.updateTraefik", {}) in fake.calls


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"versionStatus": "up-to-date"}, "up_to_date"),
        ({"state": "exited"}, "update_refused"),
        ({"isUpdating": True}, "update_in_progress"),
    ],
)
def test_traefik_update_refusals(api, fake, state, monkeypatch, change, error):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    monkeypatch.setitem(DASH, "settings.getTraefikOverview", {**DASH["settings.getTraefikOverview"], **change})
    code, err = api.handle(ctx(state), "POST", "update", {}, {"what": "traefik", "to": "3.7.16"})
    assert (code, err["error"]) == (409, error)
    assert ("POST", "settings.updateTraefik", {}) not in fake.calls


def test_traefik_last_error_is_shown_masked(api, fake, state, monkeypatch):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    bad = {**DASH["settings.getTraefikOverview"], "lastUpdateError": "pull https://u:tok@registry.example.com failed"}
    monkeypatch.setitem(DASH, "settings.getTraefikOverview", bad)
    assert api.handle(ctx(state), "GET", "traefik", {}, None)["error"] == "pull https://***@registry.example.com failed"
    assert api.handle(ctx(state), "GET", "dashboard", {}, None)["traefik"]["error"].startswith("pull https://***@")


def test_only_the_build_cache_can_be_cleared(api, fake, state, monkeypatch):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    for what in ("volumes", "images", "all", None):
        code, err = api.handle(ctx(state), "POST", "cleanup", {}, {"what": what})
        assert (code, err["error"]) == (400, "bad_target")
    monkeypatch.setitem(DASH, "deployment.queueList", [])
    monkeypatch.setitem(DASH, "dockerDiskUsage.pruneBuildCache", True)
    usage = [{"type": "Build Cache", "sizeBytes": 3_000_000_000}, {"type": "Local Volumes", "sizeBytes": 9e9}]
    monkeypatch.setitem(DASH, "settings.getDockerDiskUsage", usage)
    r = api.handle(ctx(state), "POST", "cleanup", {}, {"what": "build-cache"})
    assert r["before"] == 3_000_000_000
    prunes = [p for m, p, _ in fake.calls if m == "POST" and ("prune" in p.lower() or "clean" in p.lower())]
    assert prunes == ["dockerDiskUsage.pruneBuildCache"]  # nothing else is ever pruned


def test_no_cleanup_while_a_build_runs(api, fake, state):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})  # the fake's queue holds one deployment
    code, err = api.handle(ctx(state), "POST", "cleanup", {}, {"what": "build-cache"})
    assert (code, err["error"]) == (409, "deploy_in_progress")
    assert not [p for m, p, _ in fake.calls if m == "POST" and "prune" in p.lower()]


def test_an_older_dokploy_uses_its_own_builder_cleanup(api, fake, state, monkeypatch):
    api.handle(ctx(state), "POST", "connect", {}, {"url": fake.url})
    monkeypatch.setitem(DASH, "deployment.queueList", [])
    monkeypatch.setitem(DASH, "settings.cleanDockerBuilder", True)  # no pruneBuildCache: 404 then the old name
    api.handle(ctx(state), "POST", "cleanup", {}, {"what": "build-cache"})
    assert ("POST", "settings.cleanDockerBuilder", {}) in fake.calls
