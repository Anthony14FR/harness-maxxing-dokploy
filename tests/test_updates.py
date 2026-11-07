import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import KEY, load

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "init.defaultBranch=main"]


def git(cwd, *args):
    return subprocess.run([*GIT, "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


def release(src, version, api=1, ext_id="dokploy"):
    (src / "manifest.json").write_text(json.dumps({"id": ext_id, "version": version, "api": api}))
    old = (src / "CHANGELOG.md").read_text() if (src / "CHANGELOG.md").exists() else "# Changelog\n"
    head, _, rest = old.partition("\n")
    (src / "CHANGELOG.md").write_text(f"{head}\n\n## {version} - 2026-11-07\n\n- change of {version}\n{rest}")
    git(src, "add", "-A")
    git(src, "commit", "-qm", f"release {version}")
    git(src, "push", "-q", "origin", "main")
    return git(src, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path, core, monkeypatch):
    """origin.git, a maintainer's clone (src) and the installed extension (ext), all local."""
    origin, src, ext = tmp_path / "origin.git", tmp_path / "src", tmp_path / "ext"
    subprocess.run([*GIT, "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run([*GIT, "clone", "-q", str(origin), str(src)], check=True, capture_output=True)
    release(src, "1.0.0")
    subprocess.run([*GIT, "clone", "-q", str(origin), str(ext)], check=True)
    monkeypatch.setattr(core, "ci_state", lambda url, sha: "success")
    return {"origin": origin, "src": src, "ext": ext}


def test_up_to_date_then_a_clean_update(core, repo):
    assert core.ext_check(repo["ext"])["state"] == "up_to_date"
    sha = release(repo["src"], "1.1.0")
    chk = core.ext_check(repo["ext"])
    assert (chk["state"], chk["current"], chk["new"], chk["commit"], chk["ci"]) == (
        "available",
        "1.0.0",
        "1.1.0",
        sha,
        "success",
    )
    assert "change of 1.1.0" in chk["changes"] and "1.0.0" not in chk["changes"]
    with pytest.raises(core.DokployError) as e:
        core.ext_update(repo["ext"], 1, "0" * 40)
    assert e.value.code == "target_changed"
    core.ext_update(repo["ext"], 1, sha)
    assert json.loads((repo["ext"] / "manifest.json").read_text())["version"] == "1.1.0"
    assert core.ext_check(repo["ext"])["state"] == "up_to_date"


@pytest.mark.parametrize(
    "setup, blocker",
    [
        ("local", "local_changes"),
        ("api", "needs_newer_harness"),
        ("other", "not_this_extension"),
        ("ci", "ci_failure"),
        ("diverged", "not_fast_forward"),
    ],
)
def test_unclean_updates_are_refused(core, repo, monkeypatch, setup, blocker):
    if setup == "local":
        (repo["ext"] / "manifest.json").write_text('{"id": "dokploy", "version": "1.0.0-mine"}')
    if setup == "diverged":
        (repo["ext"] / "notes.md").write_text("x")
        git(repo["ext"], "add", "notes.md")
        git(repo["ext"], "commit", "-qm", "local commit")
    sha = release(
        repo["src"], "2.0.0", api=2 if setup == "api" else 1, ext_id="other" if setup == "other" else "dokploy"
    )
    if setup == "ci":
        monkeypatch.setattr(core, "ci_state", lambda url, s: "failure")
    chk = core.ext_check(repo["ext"])
    assert chk["state"] == "blocked" and blocker in chk["blockers"]
    before = git(repo["ext"], "rev-parse", "HEAD")
    with pytest.raises(core.DokployError) as e:
        core.ext_update(repo["ext"], 1, sha)
    assert e.value.code == "update_refused" and git(repo["ext"], "rev-parse", "HEAD") == before


def test_states_without_a_usable_repository(core, repo, tmp_path):
    plain = tmp_path / "copied"
    plain.mkdir()
    (plain / "manifest.json").write_text('{"id": "dokploy", "version": "1.0.0"}')
    assert core.ext_check(plain)["state"] == "not_git"
    lone = tmp_path / "lone"
    subprocess.run([*GIT, "init", "-q", str(lone)], check=True)
    (lone / "manifest.json").write_text('{"id": "dokploy", "version": "1.0.0"}')
    assert core.ext_check(lone, fetch=False)["state"] == "no_upstream"
    import shutil

    shutil.rmtree(repo["origin"])
    assert core.ext_check(repo["ext"])["state"] == "unreachable"


@pytest.fixture
def github(monkeypatch):
    runs = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            sha = self.path.split("/commits/")[1].split("/")[0]
            data = json.dumps({"check_runs": runs.get(sha, [])}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("DOKPLOY_EXT_GITHUB_API", f"http://127.0.0.1:{srv.server_address[1]}")
    yield runs
    srv.shutdown()
    srv.server_close()


def test_ci_state_reads_github_checks(core, github):
    url = "https://github.com/acme/harness-maxxing-dokploy.git"
    ok, wip, bad, none = "a" * 40, "b" * 40, "c" * 40, "d" * 40
    github[ok] = [{"status": "completed", "conclusion": "success"}, {"status": "completed", "conclusion": "skipped"}]
    github[wip] = [{"status": "in_progress", "conclusion": None}]
    github[bad] = [{"status": "completed", "conclusion": "success"}, {"status": "completed", "conclusion": "failure"}]
    assert [core.ci_state(url, x) for x in (ok, wip, bad, none)] == ["success", "pending", "failure", "unknown"]
    assert core.ci_state("git@github.com:acme/harness-maxxing-dokploy.git", ok) == "success"
    assert core.ci_state("/srv/git/ext.git", ok) == "unknown"  # not on GitHub: cannot be checked
    assert core.ci_state(url, "not-a-sha") == "unknown"


def test_dokploy_update_only_to_the_confirmed_version(core, fake):
    c = core.Client(fake.url, KEY)
    assert core.dokploy_check(c) == {"current": "v0.30.10", "latest": "v0.31.0", "available": True}
    with pytest.raises(core.DokployError) as e:
        core.dokploy_update(c, "v0.30.99")
    assert e.value.code == "target_changed" and not [w for w in fake.writes() if w[1] == "settings.updateServer"]
    core.dokploy_update(c, "v0.31.0")
    assert [w[1] for w in fake.writes()][-1] == "settings.updateServer"
    fake.dokploy_latest = "v0.30.10"
    with pytest.raises(core.DokployError) as e:
        core.dokploy_update(c, "v0.31.0")
    assert e.value.code == "up_to_date"


def test_the_page_checks_and_updates(core, repo, fake, state, monkeypatch, tmp_path):
    api = load("api")
    monkeypatch.setattr(api.core, "EXT_DIR", repo["ext"])
    monkeypatch.setattr(api.core, "ci_state", lambda url, sha: "success")
    ctx = {
        "id": "dokploy",
        "workspace": str(tmp_path / "ws"),
        "state_dir": str(state),
        "secret": {"DOKPLOY_API_KEY": KEY}.get,
    }
    r = api.handle(ctx, "GET", "updates", {}, None)
    assert r["extension"]["state"] == "up_to_date" and r["dokploy"]["error"] == "not_connected"
    assert r["harness"] == "/settings/updates"
    api.handle(ctx, "POST", "connect", {}, {"url": fake.url})
    sha = release(repo["src"], "1.1.0")
    r = api.handle(ctx, "GET", "updates", {}, None)
    assert r["extension"]["commit"] == sha and r["dokploy"]["latest"] == "v0.31.0"
    assert api.handle(ctx, "POST", "update", {}, {"what": "extension", "to": sha}) == {
        "updated": "extension",
        "version": "1.1.0",
    }
    assert api.handle(ctx, "POST", "update", {}, {"what": "dokploy", "to": "v0.31.0"})["version"] == "v0.31.0"
    assert api.handle(ctx, "POST", "update", {}, {"what": "harness"})[0] == 400


def test_sessions_only_read_updates(core, repo, monkeypatch, maxxing_bin, capsys):
    cli = load("dokploy")
    monkeypatch.setattr(cli.core, "EXT_DIR", repo["ext"])
    assert cli.main(["updates"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("extension  1.0.0 -> 1.0.0  up_to_date") and "the user's" in out
    with pytest.raises(SystemExit):
        cli.main(["update", "extension"])  # no such command for sessions
    capsys.readouterr()
