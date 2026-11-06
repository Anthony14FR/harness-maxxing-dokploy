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
    assert [d["id"] for d in deps] == ["d2", "d1"] and deps[0]["title"] == "fix: build"


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
