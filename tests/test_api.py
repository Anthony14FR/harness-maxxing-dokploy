import json
from pathlib import Path

import pytest

from conftest import KEY, ROOT, load


@pytest.fixture
def api():
    return load("api")


def ctx(state, keys):
    return {
        "id": "dokploy",
        "workspace": "/tmp/ws",
        "state_dir": str(state),
        "secret": keys.get,
        "config": {"timezone": "UTC", "language": "en", "public_url": ""},
    }


def test_manifest_follows_the_community_rules():
    m = json.loads((ROOT / "manifest.json").read_text())
    assert m["id"] == "dokploy" and m["type"] == "page" and m["api"] == 1
    assert set(m["name"]) == {"en", "fr"}


def test_status_then_connect_then_services(api, fake, state):
    keys = {}
    assert api.handle(ctx(state, keys), "GET", "status", {}, None)["key_present"] is False
    code, err = api.handle(ctx(state, keys), "GET", "services", {}, None)
    assert code == 409 and err["error"] == "not_connected"
    keys["DOKPLOY_API_KEY"] = KEY
    r = api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert r["connected"] and r["projects"] == 2
    names = [s["name"] for s in api.handle(ctx(state, keys), "GET", "services", {}, None)["services"]]
    assert names.count("web") == 2 and "stack" in names


def test_deploy_from_the_page(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert api.handle(ctx(state, keys), "POST", "deploy", {}, {"id": "a1", "again": True}) == {"started": "a1"}
    assert ("POST", "application.redeploy", {"applicationId": "a1", "title": "Harness Maxxing"}) in fake.writes()


def test_deployments_hide_server_paths_and_log_reads_the_last(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    deps = api.handle(ctx(state, keys), "GET", "deployments", {"id": "a1"}, None)["deployments"]
    assert [d["id"] for d in deps] == ["d2", "d1"] and all("log_path" not in d for d in deps)
    code, err = api.handle(ctx(state, keys), "GET", "log", {"id": "a1"}, None)  # d2 lives on another server
    assert code == 422 and err["error"] == "remote_log"
    (fake.logs / "acme-web-x1").mkdir(parents=True)
    (fake.logs / "acme-web-x1" / "d1.log").write_text("built\n")
    assert api.handle(ctx(state, keys), "GET", "log", {"id": "a1", "deployment": "d1"}, None)["log"] == "built"


def test_unknown_route_and_disconnect(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert api.handle(ctx(state, keys), "DELETE", "services", {}, None)[0] == 404
    assert api.handle(ctx(state, keys), "POST", "disconnect", {}, None) == {"disconnected": True}
    assert not Path(state, "settings.json").exists()
