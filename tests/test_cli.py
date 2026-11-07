import json
import os

import pytest

from conftest import KEY, load


@pytest.fixture
def cli(maxxing_bin):
    return load("dokploy")


@pytest.fixture
def connected(cli, core, fake, state, maxxing_bin):
    maxxing_bin("DOKPLOY_API_KEY", KEY)
    core.connect(state, lambda n: KEY if n == "DOKPLOY_API_KEY" else None, fake.url)
    fake.calls.clear()
    return cli


def run(cli, capsys, *args):
    code = cli.main(list(args))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_the_key_never_reaches_the_environment_or_the_output(connected, capsys):
    code, out, err = run(connected, capsys, "list", "--json")
    assert code == 0 and KEY not in out + err and KEY not in "".join(os.environ.values())
    assert {s["id"] for s in json.loads(out)} == {"a1", "a2", "a3", "c1", "pg1"}


def test_status_before_and_after_connecting(cli, core, fake, state, maxxing_bin, capsys):
    assert run(cli, capsys, "status")[:2] == (1, "no key in Settings -> Keys  -\n")
    maxxing_bin("DOKPLOY_API_KEY", KEY)
    assert run(cli, capsys, "status")[1].startswith("not connected")
    core.connect(state, lambda n: KEY, fake.url)
    assert run(cli, capsys, "status")[:2] == (0, f"connected  {fake.url}\n")


def test_writes_need_yes(connected, fake, capsys):
    for args in (
        ["deploy", "a1"],
        ["redeploy", "c1"],
        ["domain", "add", "a1", "shop.example.com"],
        ["app", "create", "--environment", "e1", "--name", "x", "--repo", "https://github.com/acme/x.git"],
    ):
        code, _, err = run(connected, capsys, *args)
        assert code == 3 and "--yes" in err
    assert not fake.writes()
    code, out, _ = run(connected, capsys, "deploy", "acme-web-x1", "--yes")
    assert code == 0 and "started" in out and fake.writes()[-1][1] == "application.deploy"


def test_reads(connected, fake, capsys):
    assert "production" in run(connected, capsys, "environments")[1]
    assert "web.example.com" in run(connected, capsys, "domain", "list", "a1")[1]
    code, out, _ = run(connected, capsys, "deployments", "a1", "--json")
    assert code == 0 and [d["id"] for d in json.loads(out)] == ["d2", "d1"]
    code, _, err = run(connected, capsys, "logs", "a1")
    assert code == 2 and "remote_log" in err
    assert run(connected, capsys, "deploy", "nope", "--yes")[0] == 1


def test_an_exposed_key_is_flagged(connected, maxxing_bin, capsys):
    maxxing_bin("DOKPLOY_API_KEY", KEY, expose=True)
    assert "exposed to sessions" in run(connected, capsys, "status")[2]


def test_ambiguous_names_ask_for_the_id(connected, capsys):
    code, _, err = run(connected, capsys, "deploy", "web", "--yes")
    assert code == 2 and "ambiguous" in err


def test_sessions_cannot_write_to_a_protected_service_nor_lift_it(connected, core, state, fake, capsys):
    core.set_protected(state, "c1", True)
    for args in (["redeploy", "c1", "--yes"], ["domain", "add", "stack", "s.example.com", "--service", "web", "--yes"]):
        code, _, err = run(connected, capsys, *args)
        assert code == 2 and "protected" in err
    assert not fake.writes()
    out = run(connected, capsys, "list")[1]
    assert "[protected]" in out.splitlines()[[i for i, x in enumerate(out.splitlines()) if "stack" in x][0]]
    with pytest.raises(SystemExit):
        connected.main(["unprotect", "c1"])  # no such command: only the user lifts it, on the page
    capsys.readouterr()


def test_the_question_carries_the_risks(connected, capsys):
    err = run(connected, capsys, "deploy", "api")[2]
    assert "down for a few seconds" in err
    err = run(connected, capsys, "deploy", "a1")[2]
    assert "tell the user" not in err


def test_health_and_the_list_header(connected, capsys):
    code, out, _ = run(connected, capsys, "health", "stack")
    assert code == 0 and out.startswith("partial  1/2 running") and "Exited (1)" in out
    assert json.loads(run(connected, capsys, "health", "a1", "--json")[1])["state"] == "ok"
    assert run(connected, capsys, "list")[1].splitlines()[0].startswith("done ")  # no header: 1.x scripts parse it
