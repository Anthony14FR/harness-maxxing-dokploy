import datetime as dt
import json

import pytest

from conftest import KEY, load

NOW = dt.datetime(2026, 11, 10, 8, 0, tzinfo=dt.UTC).timestamp()


@pytest.fixture
def cli():
    return load("dokploy")


def dash(**over):
    base = {
        "deployments": [
            {
                "id": "x2",
                "status": "error",
                "created": "2026-11-10T07:30:00Z",
                "service": "web",
                "error": "build failed",
            },
            {"id": "x1", "status": "error", "created": "2026-11-09T07:30:00Z", "service": "web"},  # a day old: ignored
            {"id": "x3", "status": "error", "created": "2026-11-10T07:00:00Z", "kind": "backup", "service": "db"},
        ],
        "services": [
            {"id": "a1", "name": "web", "app_name": "acme-web-x1", "kind": "application", "status": "done"},
            {"id": "c1", "name": "shop", "app_name": "acme-shop", "kind": "compose", "status": "done"},
            {"id": "a9", "name": "old", "app_name": "acme-old", "kind": "application", "status": "idle"},  # stopped
        ],
        "containers": [
            {"name": "acme-web-x1.1.abc", "state": "exited"},
            {"name": "acme-shop-web-1", "state": "running"},
        ],
        "resources": {"disk_used": 92, "disk_total": 100, "mem_used": 50, "mem_total": 100},
        "traefik": {"error": "pull failed", "updating": None},
    }
    return {**base, **over}


def test_what_is_wrong_now(core):
    issues = core.alert_issues(dash(), NOW)
    assert set(issues) == {"deploy:x2", "backup:x3", "down:a1", "disk", "traefik"}
    assert issues["deploy:x2"]["title"] == "Deployment of web failed" and issues["deploy:x2"]["once"]
    assert issues["down:a1"]["ok"] == "web is back up"
    assert core.alert_issues(dash(), NOW, "fr")["disk"]["title"] == "Disque du serveur Dokploy plein à 92 %"
    assert set(core.alert_issues(None, NOW, error="timeout")) == {"unreachable"}
    calm = dash(
        deployments=[], containers=[{"name": "acme-web-x1.1.abc", "state": "running"}], resources={}, traefik={}
    )
    assert core.alert_issues(calm, NOW) == {}


def test_each_problem_is_posted_once_then_its_end(core):
    posts, state = core.alert_diff({}, core.alert_issues(dash(), NOW), NOW)
    assert {p["title"] for p in posts} == {
        "Deployment of web failed",
        "Backup of db failed",
        "web is down",
        "Dokploy server disk 92% full",
        "Traefik update failed",
    }
    again, state = core.alert_diff(state, core.alert_issues(dash(), NOW + 300), NOW + 300)
    assert again == []  # nothing new five minutes later
    fixed = dash(containers=[{"name": "acme-web-x1.1.abc", "state": "running"}], resources={}, traefik={})
    ends, state = core.alert_diff(state, core.alert_issues(fixed, NOW + 600), NOW + 600)
    assert {(p["level"], p["title"]) for p in ends} == {
        ("success", "web is back up"),
        ("success", "Dokploy server disk below 90%"),
        ("success", "Traefik update error cleared"),
    }
    assert state["active"] == {} and "deploy:x2" in state["seen"]


def test_the_cli_posts_to_the_feed_and_keeps_quiet_next_time(cli, core, fake, state, maxxing_bin, tmp_path, capsys):
    maxxing_bin("DOKPLOY_API_KEY", KEY)
    core.connect(state, lambda n: KEY if n == "DOKPLOY_API_KEY" else None, fake.url)
    assert cli.main(["alerts", "--dry-run"]) == 0
    assert not (tmp_path / "feed.jsonl").exists() and not (state / "alerts.json").exists()  # a dry run posts nothing
    assert cli.main(["alerts"]) == 0
    feed = [json.loads(x) for x in (tmp_path / "feed.jsonl").read_text().splitlines()]
    assert feed and all(p[p.index("--source") + 1] == "Dokploy" for p in feed)
    assert all(p[p.index("--dedupe") + 1].startswith("dokploy:") for p in feed)
    n = len(feed)
    assert cli.main(["alerts"]) == 0
    assert len((tmp_path / "feed.jsonl").read_text().splitlines()) == n  # the same problems: no new post
    capsys.readouterr()


def test_the_cli_says_when_it_cannot_check(cli, core, fake, state, maxxing_bin, tmp_path, capsys):
    maxxing_bin("DOKPLOY_API_KEY", KEY)
    assert cli.main(["alerts"]) == 0  # not connected yet: nothing posted, no error for the cron job
    assert "alerts skipped" in capsys.readouterr().out and not (tmp_path / "feed.jsonl").exists()


def test_dokploy_away_is_an_alert(cli, core, fake, state, maxxing_bin, tmp_path, capsys):
    from conftest import DASH

    maxxing_bin("DOKPLOY_API_KEY", KEY)
    core.connect(state, lambda n: KEY if n == "DOKPLOY_API_KEY" else None, fake.url)
    fake.broken |= set(DASH)  # every dashboard read fails, as when Dokploy is down
    assert cli.main(["alerts"]) == 0
    titles = [json.loads(x)[0] for x in (tmp_path / "feed.jsonl").read_text().splitlines()]
    assert titles == ["Dokploy does not answer"]
    fake.broken.clear()
    assert cli.main(["alerts"]) == 0
    assert "Dokploy answers again" in (tmp_path / "feed.jsonl").read_text()
    capsys.readouterr()
