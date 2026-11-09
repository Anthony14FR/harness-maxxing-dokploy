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
        "workspace": str(state.parent.parent / "ws"),
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
    assert [d["id"] for d in deps] == ["d2", "d1", "d0"] and all("log_path" not in d for d in deps)
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


def test_a_protected_service_cannot_be_deployed_from_the_page(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "stack", "on": True}) == {
        "id": "c1",
        "protected": True,
    }
    svcs = {s["id"]: s for s in api.handle(ctx(state, keys), "GET", "services", {}, None)["services"]}
    assert svcs["c1"]["protected"] and svcs["c1"]["risks"] == ["downtime", "no_rebuild"]
    assert not svcs["a1"]["protected"] and svcs["a1"]["risks"] == []
    code, err = api.handle(ctx(state, keys), "POST", "deploy", {}, {"id": "c1"})
    assert code == 409 and err["error"] == "protected" and not fake.writes()
    api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "c1", "on": False})
    assert api.handle(ctx(state, keys), "POST", "deploy", {}, {"id": "c1"}) == {"started": "c1"}


def test_protect_needs_a_real_service_but_lifting_does_not(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "nope", "on": True})[0] == 404
    api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "a1", "on": True})
    code, err = api.handle(ctx(state, keys), "POST", "deploy", {}, {"id": "a1", "again": True})
    assert code == 409 and err["error"] == "protected"
    keys["DOKPLOY_API_KEY"] = "changed"  # lifting still works with the key to re-check, and for a gone service
    assert api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "a1", "on": False}) == {
        "id": "a1",
        "protected": False,
    }
    assert api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "gone", "on": False})["protected"] is False


def test_health_route(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert api.handle(ctx(state, keys), "GET", "health", {"id": "stack"}, None)["state"] == "partial"


def test_health_of_an_unknown_service(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert api.handle(ctx(state, keys), "GET", "health", {"id": "nope"}, None)[0] == 404


def test_actions_from_the_page(api, fake, state):
    keys = {"DOKPLOY_API_KEY": KEY}
    api.handle(ctx(state, keys), "POST", "connect", {}, {"url": fake.url})
    assert api.handle(ctx(state, keys), "GET", "rollback", {"id": "a1"}, None)["deployment"] == "d0"
    code, err = api.handle(ctx(state, keys), "POST", "action", {}, {"id": "a1", "action": "rollback"})
    assert code == 409 and err["error"] == "target_changed"  # nothing confirmed: nothing runs
    body = {"id": "a1", "action": "rollback", "deployment": "d0"}
    assert api.handle(ctx(state, keys), "POST", "action", {}, body) == {
        "done": "rollback",
        "id": "a1",
    }
    assert api.handle(ctx(state, keys), "POST", "action", {}, {"id": "c1", "action": "stop"})["done"] == "stop"
    assert api.handle(ctx(state, keys), "POST", "action", {}, {"id": "c1", "action": "delete"})[0] == 400
    code, err = api.handle(ctx(state, keys), "GET", "rollback", {"id": "c1"}, None)
    assert code == 409 and err["error"] == "not_supported"
    api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "c1", "on": True})
    n = len(fake.writes())
    for action in ("start", "stop"):
        code, err = api.handle(ctx(state, keys), "POST", "action", {}, {"id": "c1", "action": action})
        assert code == 409 and err["error"] == "protected"
    api.handle(ctx(state, keys), "POST", "protect", {}, {"id": "a1", "on": True})
    code, err = api.handle(ctx(state, keys), "POST", "action", {}, body)
    assert code == 409 and err["error"] == "protected" and len(fake.writes()) == n


def test_the_page_offers_and_installs_the_skill(api, state):
    keys = {}
    assert api.handle(ctx(state, keys), "GET", "status", {}, None)["skill"] == "missing"
    assert api.handle(ctx(state, keys), "POST", "skill", {}, None) == {"skill": "ok"}
    assert (state.parent.parent / "ws" / ".claude" / "skills" / "dokploy").is_symlink()


def test_the_page_offers_to_link_a_1x_copy_and_never_touches_a_custom_one(api, state):
    keys = {}
    dest = state.parent.parent / "ws" / ".claude" / "skills" / "dokploy"
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("1.1.0 copy")
    (dest / "notes.md").write_text("the user's")
    assert api.handle(ctx(state, keys), "GET", "status", {}, None)["skill"] == "custom"
    code, err = api.handle(ctx(state, keys), "POST", "skill", {}, None)
    assert code == 409 and err["error"] == "skill_custom" and "notes.md" in err["message"]
    assert (dest / "notes.md").read_text() == "the user's"
    (dest / "notes.md").unlink()
    assert api.handle(ctx(state, keys), "GET", "status", {}, None)["skill"] == "copied"
    assert api.handle(ctx(state, keys), "POST", "skill", {}, None) == {"skill": "ok"}


def test_skill_errors_from_the_page(api, state):
    keys = {}
    ws = state.parent.parent / "ws"
    (ws / ".claude").mkdir(parents=True)
    (ws / ".claude" / "skills").write_text("not a folder")
    code, err = api.handle(ctx(state, keys), "POST", "skill", {}, None)
    assert code == 409 and err["error"] == "skill_failed"
    no_ws = {**ctx(state, keys), "workspace": None}
    assert api.handle(no_ws, "GET", "status", {}, None)["skill"] == "missing"
    assert api.handle(no_ws, "POST", "skill", {}, None)[0] == 409
