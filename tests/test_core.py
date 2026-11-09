import pytest

from conftest import KEY


def secret_of(keys):
    return lambda name: keys.get(name)


@pytest.mark.parametrize(
    "u",
    [
        "ftp://h",
        "http://dokploy.example.com",
        "https://u:p@h.example.com",
        "",
        "h:3000",
        "http://169.254.169.254",
        "http://127.0.0.1:99999",
        "https://h.example.com/api",
        "https://h.example.com/?x=1",
    ],
)
def test_check_url_refuses_unsafe_urls(core, u):
    with pytest.raises(core.DokployError) as e:
        core.check_url(u)
    assert e.value.code == "invalid_url"


@pytest.mark.parametrize(
    "u",
    [
        "http://127.0.0.1:3000/",
        "http://localhost:3000",
        "http://10.0.0.5:3000",
        "http://100.101.102.103:3000",
        "https://dokploy.example.com",
    ],
)
def test_check_url_accepts_local_http_and_any_https(core, u):
    assert core.check_url(u) == u.rstrip("/")


def test_connect_needs_the_key_in_keys(core, fake, state):
    with pytest.raises(core.DokployError) as e:
        core.connect(state, lambda n: None, fake.url)
    assert e.value.code == "no_key" and not fake.calls


def test_connect_checks_the_key_and_keeps_only_its_fingerprint(core, fake, state):
    r = core.connect(state, secret_of({core.KEY: KEY}), fake.url)
    assert r == {"connected": True, "url": fake.url, "projects": 2}
    raw = (state / "settings.json").read_text()
    assert KEY not in raw and fake.url in raw  # the key itself is never written here
    assert (state / "settings.json").stat().st_mode & 0o077 == 0
    assert core.status(state, secret_of({core.KEY: KEY}))["connected"]


def test_a_refused_key_is_not_saved(core, fake, state):
    with pytest.raises(core.DokployError) as e:
        core.connect(state, secret_of({core.KEY: "wrong"}), fake.url)
    assert e.value.code == "refused" and not (state / "settings.json").exists()


def test_a_key_changed_in_keys_is_not_sent_before_a_new_check(core, fake, state):
    core.connect(state, secret_of({core.KEY: KEY}), fake.url)
    fake.calls.clear()
    other = secret_of({core.KEY: "another-key"})
    assert core.status(state, other) == {"connected": False, "url": fake.url, "key_present": True, "key_changed": True}
    with pytest.raises(core.DokployError) as e:
        core.client(state, other)
    assert e.value.code == "key_changed" and not fake.calls


def test_redirects_are_not_followed(core, fake):
    with pytest.raises(core.DokployError) as e:
        core.Client(fake.url, KEY).get("redirect.me")
    assert e.value.code == "redirected"


def test_unreachable(core):
    with pytest.raises(core.DokployError) as e:
        core.Client("http://127.0.0.1:9", KEY).get("project.all")
    assert e.value.code == "unreachable"


def test_inventory_completes_apps_with_their_one_call(core, fake):
    svcs = core.inventory(core.Client(fake.url, KEY))
    web = core.find(svcs, "a1")
    assert web["app_name"] == "acme-web-x1" and web["repo"] == "acme/web" and web["build"] == "nixpacks"
    assert web["domains"] == [{"host": "web.example.com", "https": True, "port": 3000, "path": "/"}]
    assert web["project"] == "acme" and web["environment"] == "production"
    assert [s["kind"] for s in svcs].count("postgres") == 1
    assert core.find(svcs, "a3")["environment"] is None  # an older Dokploy without environments
    assert core.environments(fake_projects(fake, core)) == [
        {"id": "e1", "name": "production", "project": "acme", "project_id": "p1"}
    ]


def fake_projects(fake, core):
    return core.Client(fake.url, KEY).get("project.all")


def test_find_by_name_app_name_and_ambiguity(core, fake):
    svcs = core.inventory(core.Client(fake.url, KEY))
    assert core.find(svcs, "API")["id"] == "a2" and core.find(svcs, "acme-api-x2")["id"] == "a2"
    with pytest.raises(core.DokployError) as e:
        core.find(svcs, "web")
    assert e.value.code == "ambiguous" and "a1" in e.value.message and "a3" in e.value.message
    with pytest.raises(core.DokployError):
        core.find(svcs, "nope")


def test_deploy_redeploy_and_databases(core, fake):
    c = core.Client(fake.url, KEY)
    svcs = core.inventory(c)
    core.deploy(c, core.find(svcs, "a1"), "from a session")
    core.deploy(c, core.find(svcs, "c1"), again=True)
    assert fake.writes() == [
        ("POST", "application.deploy", {"applicationId": "a1", "title": "from a session"}),
        ("POST", "compose.redeploy", {"composeId": "c1"}),
    ]
    with pytest.raises(core.DokployError) as e:
        core.deploy(c, core.find(svcs, "pg1"))
    assert e.value.code == "not_deployable"


@pytest.mark.parametrize(
    "kw",
    [
        {"repo": "--upload-pack=touch /tmp/x"},
        {"repo": "ext::sh -c id"},
        {"repo": "file:///etc"},
        {"repo": "https://github.com/acme/x.git; rm -rf /"},
        {"branch": "-x"},
        {"branch": "main dev"},
        {"name": "-rf"},
        {"build_path": "/../../etc"},
        {"env": "e1;x"},
    ],
)
def test_app_create_refuses_values_git_or_dokploy_could_misread(core, fake, kw):
    a = {"repo": "https://github.com/acme/x.git", "branch": "main", "name": "x", "build_path": "/", "env": "e1", **kw}
    with pytest.raises(core.DokployError) as e:
        core.app_create(
            core.Client(fake.url, KEY), a["env"], a["name"], a["repo"], a["branch"], "nixpacks", a["build_path"]
        )
    assert e.value.code == "invalid_value" and not fake.writes()


def test_app_create_sets_source_and_build(core, fake):
    c = core.Client(fake.url, KEY)
    for repo in ("ssh://git@git.example.com/acme/x.git", "git@github.com:acme/x.git"):
        assert core.app_create(c, "e1", "x", repo, "release/1.2", "dockerfile") == "new1"
    procs = [w[1] for w in fake.writes()]
    assert procs[:3] == ["application.create", "application.saveGitProvider", "application.saveBuildType"]
    assert fake.writes()[1][2]["customGitUrl"] == "ssh://git@git.example.com/acme/x.git"


@pytest.mark.parametrize(
    "host, port, path",
    [
        ("bad host", None, None),
        ("x.example.com", 70000, None),
        ("x.example.com", None, "no-slash"),
        ("-x.example.com", None, None),
    ],
)
def test_domain_add_refuses_bad_values(core, fake, host, port, path):
    c = core.Client(fake.url, KEY)
    with pytest.raises(core.DokployError):
        core.domain_add(c, core.find(core.inventory(c), "a1"), host, port, True, path)
    assert not fake.writes()


def test_domain_add_app_and_compose(core, fake):
    c = core.Client(fake.url, KEY)
    svcs = core.inventory(c)
    core.domain_add(c, core.find(svcs, "a1"), "Shop.Example.com", 3000)
    with pytest.raises(core.DokployError) as e:
        core.domain_add(c, core.find(svcs, "c1"), "stack.example.com", 80)
    assert e.value.code == "service_needed"
    core.domain_add(c, core.find(svcs, "c1"), "stack.example.com", 80, False, service="web")
    bodies = [w[2] for w in fake.writes()]
    assert bodies[0] == {
        "host": "shop.example.com",
        "https": True,
        "certificateType": "letsencrypt",
        "domainType": "application",
        "applicationId": "a1",
        "port": 3000,
    }
    assert bodies[1]["serviceName"] == "web" and bodies[1]["certificateType"] == "none"


def test_deployments_newest_first_with_a_one_line_title(core, fake):
    c = core.Client(fake.url, KEY)
    deps = core.deployments(c, core.find(core.inventory(c), "a1"))
    assert [d["id"] for d in deps] == ["d2", "d1", "d0"] and deps[0]["title"] == "fix: build"


def test_logs_stay_inside_the_dokploy_folder(core, fake, tmp_path):
    (fake.logs / "acme-web-x1").mkdir(parents=True)
    (fake.logs / "acme-web-x1" / "d1.log").write_text("".join(f"line {i}\n" for i in range(500)))
    assert core.log({"log_path": str(fake.logs / "acme-web-x1" / "d1.log")}, 3) == "line 497\nline 498\nline 499"
    outside = tmp_path / "secret.txt"
    outside.write_text("root only\n")
    (fake.logs / "link.log").symlink_to(outside)
    for p in ("/elsewhere/d2.log", str(fake.logs / ".." / "secret.txt"), str(fake.logs / "link.log")):
        with pytest.raises(core.DokployError) as e:
            core.log({"log_path": p})
        assert e.value.code == "remote_log"


def test_risks_follow_the_kind_the_source_and_the_update_order(core, fake):
    svcs = core.inventory(core.Client(fake.url, KEY))
    assert core.risks(core.find(svcs, "a1")) == []  # git source, start-first update
    assert core.risks(core.find(svcs, "a2")) == ["downtime"]  # swarm default: stop first
    assert core.risks(core.find(svcs, "c1")) == ["downtime", "no_rebuild"]  # raw compose
    assert core.find(svcs, "c1")["source"] == "raw" and core.find(svcs, "a1")["start_first"] is True


def test_protection_is_kept_across_reconnect_and_disconnect(core, fake, state):
    sec = secret_of({core.KEY: KEY})
    core.connect(state, sec, fake.url)
    svc = core.find(core.inventory(core.client(state, sec)), "c1")
    core.guard(state, svc)  # not protected yet
    assert core.set_protected(state, "c1", True) == {"c1"}
    core.connect(state, sec, fake.url)
    assert core.disconnect(state) and core.protected(state) == {"c1"}
    assert not core.status(state, sec)["connected"]
    with pytest.raises(core.DokployError) as e:
        core.guard(state, svc)
    assert e.value.code == "protected"
    core.set_protected(state, "c1", False)
    core.guard(state, svc)


def test_an_unreadable_settings_file_fails_closed(core, fake, state):
    sec = secret_of({core.KEY: KEY})
    core.connect(state, sec, fake.url)
    svc = core.find(core.inventory(core.client(state, sec)), "a1")
    for bad in ("{not json", '{"url": "x", "protected": "a1"}', "[]"):
        (state / "settings.json").write_text(bad)
        with pytest.raises(core.DokployError) as e:
            core.guard(state, svc)
        assert e.value.code == "bad_settings"
        with pytest.raises(core.DokployError):
            core.set_protected(state, "a1", True)  # never overwrites a file it cannot read
        assert (state / "settings.json").read_text() == bad


def test_concurrent_protects_keep_every_id(core, state):
    import threading

    ids = [f"s{i}" for i in range(20)]
    threads = [threading.Thread(target=core.set_protected, args=(state, i, True)) for i in ids]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert core.protected(state) == set(ids)


def test_a_service_without_details_is_assumed_risky(core, fake):
    fake.broken.add("application.one")
    svcs = core.inventory(core.Client(fake.url, KEY))
    a1 = core.find(svcs, "a1")
    assert a1["detailed"] is False and core.risks(a1) == ["downtime", "unknown"]
    assert core.find(svcs, "c1")["detailed"] is True


def test_no_update_config_means_stop_first(core):
    app = {"kind": "application", "source": "git", "start_first": None, "detailed": True}
    assert core.risks(app) == ["downtime"]
    assert core.risks({**app, "start_first": True, "source": "docker"}) == ["no_rebuild"]


def test_health_counts_only_this_service_real_containers(core, fake):
    c = core.Client(fake.url, KEY)
    svcs = core.inventory(c)
    a1 = core.health(c, core.find(svcs, "a1"))
    assert (a1["state"], a1["running"], a1["expected"]) == ("ok", 1, 1)
    assert [b["name"] for b in a1["containers"]] == ["acme-web-x1.1.abc"]  # not the prefix-sharing sibling
    assert core.health(c, core.find(svcs, "a2"))["state"] == "down"
    stack = core.health(c, core.find(svcs, "c1"))
    assert (stack["state"], stack["running"], stack["expected"]) == ("partial", 1, 2)  # migrate exited 0: not down
    assert {b["name"] for b in stack["containers"]} == {
        "acme-stack-web-1",
        "acme-stack-worker-1",
        "acme-stack-migrate-1",
    }
    assert ("GET", "docker.getContainersByAppNameMatch", {"appName": "acme-stack", "appType": "docker-compose"}) in (
        fake.calls
    )
    with pytest.raises(core.DokployError):
        core.health(c, core.find(svcs, "pg1"))


def test_health_of_a_swarm_stack_counts_slots(core, fake):
    c = core.Client(fake.url, KEY)
    c1 = core.find(core.inventory(c), "c1")
    swarm = core.health(c, {**c1, "compose_type": "stack", "server_id": "srv1"})
    assert (swarm["state"], swarm["running"], swarm["expected"]) == ("partial", 1, 2)  # web up, worker failed
    assert fake.calls[-1][1:] == ("docker.getStackContainersByAppName", {"appName": "acme-stack", "serverId": "srv1"})


def test_health_replicas_and_edge_cases(core, fake):
    c = core.Client(fake.url, KEY)
    a1 = core.find(core.inventory(c), "a1")
    assert core.health(c, {**a1, "replicas": 2})["state"] == "partial"
    assert core.health(c, {**a1, "replicas": 0})["state"] == "stopped"
    assert core.health(c, {**a1, "replicas": None, "detailed": False})["expected"] == 1  # Dokploy's default
    assert core.health(c, {**a1, "app_name": None}) == {
        "state": "unknown",
        "running": 0,
        "expected": None,
        "containers": [],
    }
    core.health(c, {**a1, "server_id": "srv2"})
    assert fake.calls[-1][2] == {"appName": "acme-web-x1", "serverId": "srv2"}


def test_lookup_reads_one_service_not_the_inventory(core, fake):
    c = core.Client(fake.url, KEY)
    fake.calls.clear()
    assert core.lookup(c, "stack")["source"] == "raw"
    assert [x[1] for x in fake.calls] == ["project.all", "compose.one"]


def test_last_deployment_is_named_as_such(core, fake):
    a2 = core.find(core.inventory(core.Client(fake.url, KEY)), "a2")
    assert a2["last_deployment"] == a2["status"] == "error"


def test_health_unknown_and_stopped_composes(core, fake):
    c = core.Client(fake.url, KEY)
    c1 = core.find(core.inventory(c), "c1")
    assert core.health(c, {**c1, "app_name": "custom-names"})["state"] == "unknown"  # no container matched
    from conftest import CONTAINERS

    CONTAINERS["all-done"] = [{"name": "all-done-job-1", "state": "exited", "status": "Exited (0) 1 day ago"}]
    try:
        assert core.health(c, {**c1, "app_name": "all-done"})["state"] == "stopped"
    finally:
        del CONTAINERS["all-done"]


def test_lookup_falls_back_to_app_names_and_keeps_ambiguity(core, fake):
    c = core.Client(fake.url, KEY)
    assert core.lookup(c, "acme-api-x2")["id"] == "a2"
    with pytest.raises(core.DokployError) as e:
        core.lookup(c, "web")
    assert e.value.code == "ambiguous"


def test_stop_and_start(core, fake):
    c = core.Client(fake.url, KEY)
    svcs = core.inventory(c)
    core.power(c, core.find(svcs, "a1"), False)
    core.power(c, core.find(svcs, "c1"), True)
    assert fake.writes() == [
        ("POST", "application.stop", {"applicationId": "a1"}),
        ("POST", "compose.start", {"composeId": "c1"}),
    ]
    with pytest.raises(core.DokployError):
        core.power(c, core.find(svcs, "pg1"), False)


def test_rollback_goes_back_before_what_runs_now(core, fake):
    c = core.Client(fake.url, KEY)
    svcs = core.inventory(c)
    a1 = core.find(svcs, "a1")
    target = core.rollback_target(c, a1)
    assert (target["id"], target["rollback_id"]) == ("d0", "r0")  # d2 failed, so d1 still runs: go before it
    with pytest.raises(core.DokployError) as e:
        core.rollback(c, a1, target, confirmed="d1")
    assert e.value.code == "target_changed" and not fake.writes()
    core.rollback(c, a1, target, confirmed="d0")
    assert fake.writes() == [("POST", "rollback.rollback", {"rollbackId": "r0"})]
    for svc, code in ((core.find(svcs, "c1"), "not_supported"), ({**a1, "rollback_active": False}, "rollback_off")):
        with pytest.raises(core.DokployError) as e:
            core.rollback_target(c, svc)
        assert e.value.code == code


def test_no_rollback_during_a_deployment(core, fake, monkeypatch):
    c = core.Client(fake.url, KEY)
    a1 = core.find(core.inventory(c), "a1")
    deps = [{"id": "d5", "status": "running", "rollback_id": None}, {"id": "d4", "status": "done", "rollback_id": "r4"}]
    monkeypatch.setattr(core, "deployments", lambda c, s: deps)
    with pytest.raises(core.DokployError) as e:
        core.rollback_target(c, a1)
    assert e.value.code == "deploy_in_progress"


def test_deployments_sort_on_real_dates(core):
    assert core._when("2026-09-01T10:00:00+02:00") < core._when("2026-09-01T09:00:00Z")
    assert core._when(None) < core._when("2000-01-01T00:00:00Z")


def test_no_earlier_deployment_to_roll_back_to(core, fake, monkeypatch):
    c = core.Client(fake.url, KEY)
    a1 = core.find(core.inventory(c), "a1")
    monkeypatch.setattr(core, "deployments", lambda c, s: [{"id": "d9", "status": "done", "rollback_id": "r9"}])
    with pytest.raises(core.DokployError) as e:
        core.rollback_target(c, a1)  # the only one is the current deployment
    assert e.value.code == "no_rollback"


def test_the_skill_is_linked_for_sessions(core, tmp_path):
    ws = tmp_path / "ws"
    assert core.skill_state(ws) == "missing"
    dest = core.install_skill(ws)
    assert dest.is_symlink() and dest.resolve() == core.SKILL_SRC and core.skill_state(ws) == "ok"
    assert core.install_skill(ws) == dest  # idempotent


def test_a_copy_from_1x_keeps_working_until_it_is_linked(core, tmp_path):
    ws = tmp_path / "ws"
    old = core.skill_dest(ws)
    old.mkdir(parents=True)
    (old / "SKILL.md").write_text("the 1.1.0 skill")  # an older, stale copy: still a skill Claude can read
    assert core.skill_state(ws) == "copied"
    core.install_skill(ws)
    assert old.is_symlink() and core.skill_state(ws) == "ok"


@pytest.mark.parametrize("setup", ["notes", "subdir", "filelink", "file"])
def test_a_copy_holding_the_users_files_is_never_touched(core, tmp_path, setup):
    ws, outside = tmp_path / "ws", tmp_path / "outside.md"
    outside.write_text("keep me")
    dest = core.skill_dest(ws)
    dest.parent.mkdir(parents=True)
    if setup == "file":
        dest.write_text("not a folder")
    else:
        dest.mkdir()
        (dest / "SKILL.md").write_text("copy")
        if setup == "notes":
            (dest / "my-notes.md").write_text("the user's")
        if setup == "subdir":
            (dest / "SKILL.md").unlink()
            (dest / "SKILL.md").mkdir()
        if setup == "filelink":
            (dest / "SKILL.md").unlink()
            (dest / "SKILL.md").symlink_to(outside)
    before = sorted(str(p) for p in dest.parent.rglob("*"))
    with pytest.raises(core.DokployError) as e:
        core.install_skill(ws)
    assert e.value.code == "skill_custom" and sorted(str(p) for p in dest.parent.rglob("*")) == before
    assert outside.read_text() == "keep me"


def test_a_link_elsewhere_is_refused(core, tmp_path):
    ws, other = tmp_path / "ws", tmp_path / "users-own-skill"
    other.mkdir()
    (other / "SKILL.md").write_text("mine")
    core.skill_dest(ws).parent.mkdir(parents=True)
    core.skill_dest(ws).symlink_to(other)
    assert core.skill_state(ws) == "linked"
    with pytest.raises(core.DokployError) as e:
        core.install_skill(ws)
    assert e.value.code == "skill_linked" and (other / "SKILL.md").read_text() == "mine"


def test_skill_errors_never_break_status(core, tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    (ws / ".claude").mkdir(parents=True)
    (ws / ".claude" / "skills").write_text("a file where a folder should be")
    assert core.skill_state(ws) == "missing"
    with pytest.raises(core.DokployError) as e:
        core.install_skill(ws)
    assert e.value.code == "skill_failed"
    assert core.skill_state(None) == "missing"
    monkeypatch.setattr(core, "SKILL_SRC", tmp_path / "nothing")
    assert core.skill_state(ws) == "broken"
    with pytest.raises(core.DokployError) as e:
        core.install_skill(ws)
    assert e.value.code == "skill_failed"


def test_tests_never_use_the_repository_skill_folder(core):
    from conftest import ROOT

    assert (ROOT / "skill" / "dokploy").resolve() != core.SKILL_SRC and (core.SKILL_SRC / "SKILL.md").is_file()
