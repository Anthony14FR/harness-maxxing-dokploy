"""Dokploy API client shared by api.py (the page) and dokploy.py (sessions); standard library only."""

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

KEY = "DOKPLOY_API_KEY"
DEFAULT_URL = "http://127.0.0.1:3000"
LOGS = Path("/etc/dokploy/logs")
TIMEOUT = 20
LOG_MAX_LINES = 2000
DB_KINDS = ("postgres", "mysql", "mariadb", "mongo", "redis")
KINDS = ("application", "compose") + DB_KINDS
BUILD_TYPES = ("dockerfile", "nixpacks", "railpack", "heroku_buildpacks", "paketo_buildpacks", "static")
TAILNET = ipaddress.ip_network("100.64.0.0/10")
HOST_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]$")
BRANCH_RE = re.compile(r"^(?!-)[A-Za-z0-9._/-]{1,200}$")
NAME_RE = re.compile(r"^(?!-)[A-Za-z0-9 ._-]{1,63}$")
PATH_RE = re.compile(r"^/[A-Za-z0-9._~/-]*$")
GIT_URL_RE = re.compile(r"^(https://|ssh://)[^\s'\"\\]+$|^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[^\s'\"\\-][^\s'\"\\]*$")

_ID = {
    "application": "applicationId",
    "compose": "composeId",
    "postgres": "postgresId",
    "mysql": "mysqlId",
    "mariadb": "mariadbId",
    "mongo": "mongoId",
    "redis": "redisId",
}
_STATUS = {"application": "applicationStatus", "compose": "composeStatus"}
_PLURAL = {"application": "applications", "compose": "compose"}

Secret = Callable[[str], "str | None"]


class DokployError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


# ---- settings ------------------------------------------------------------------------------------------------
def logs_dir() -> Path:
    return Path(os.environ.get("DOKPLOY_LOGS_DIR") or LOGS)


def fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def load_settings(state_dir: str | Path) -> dict:
    """{} when there is none yet; an unreadable file fails closed, so protected services never silently open."""
    f = Path(state_dir) / "settings.json"
    if not f.exists():
        return {}
    try:
        s = json.loads(f.read_text())
    except (OSError, ValueError):
        s = None
    if not isinstance(s, dict) or not isinstance(s.get("protected", []), list):
        raise DokployError("bad_settings", f"{f} cannot be read: fix or delete it, then connect again")
    return s


@contextlib.contextmanager
def _locked(state_dir: str | Path):
    """Serialises read-modify-write of settings.json between the page's requests and sessions."""
    d = Path(state_dir)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / ".settings.lock", "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield


def save_settings(state_dir: str | Path, settings: dict | None) -> None:
    """Atomic write, readable by root only; None removes the file."""
    d = Path(state_dir)
    f = d / "settings.json"
    if settings is None:
        f.unlink(missing_ok=True)
        return
    d.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".settings-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(settings, fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, f)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def check_url(url: str) -> str:
    """The URL without trailing slash; plain http only to this machine or a private network (the key goes in clear)."""
    u = (url or "").strip().rstrip("/")
    p = urllib.parse.urlsplit(u)
    try:
        _ = p.port  # out of range raises here, not in the request
    except ValueError:
        raise DokployError("invalid_url", "the Dokploy URL has an invalid port") from None
    if (
        p.scheme not in ("http", "https")
        or not p.hostname
        or p.username
        or p.password
        or p.query
        or p.fragment
        or p.path not in ("", "/")
    ):
        raise DokployError("invalid_url", "the Dokploy URL must be http(s)://host[:port]")
    if p.scheme == "http" and not _private(p.hostname):
        raise DokployError("invalid_url", "use https for a Dokploy on another network: the key would travel in clear")
    return u


def _private(host: str) -> bool:
    h = host.lower()
    if h == "localhost" or h.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    if ip.is_link_local:  # 169.254.x (cloud metadata) is never a Dokploy
        return False
    return ip.is_loopback or ip.is_private or ip in TAILNET


def status(state_dir: str | Path, secret: Secret) -> dict:
    """{connected, url, key_present, key_changed}; no network call."""
    s = load_settings(state_dir)
    key = (secret(KEY) or "").strip()
    changed = bool(s.get("url") and key and s.get("key") != fingerprint(key))
    return {
        "connected": bool(s.get("url") and key and not changed),
        "url": s.get("url") or None,
        "key_present": bool(key),
        "key_changed": changed,
    }


def connect(state_dir: str | Path, secret: Secret, url: str) -> dict:
    """Checks the key from Keys against `url` with project.all, then remembers the URL and the key's fingerprint."""
    base, key = check_url(url or DEFAULT_URL), (secret(KEY) or "").strip()
    if not key:
        raise DokployError("no_key", f"add {KEY} in Settings -> Keys first (Dokploy -> Profile -> API keys)")
    projects = Client(base, key).get("project.all")
    if not isinstance(projects, list):
        raise DokployError("bad_response", "project.all did not answer a list")
    with _locked(state_dir):
        save_settings(state_dir, {**load_settings(state_dir), "url": base, "key": fingerprint(key)})
    return {"connected": True, "url": base, "projects": len(projects)}


def disconnect(state_dir: str | Path) -> bool:
    """Forgets the address and the key's fingerprint; protected services stay protected."""
    with _locked(state_dir):
        s = load_settings(state_dir)
        rest = {k: v for k, v in s.items() if k not in ("url", "key")}
        save_settings(state_dir, rest or None)
    return bool(s.get("url"))


def protected(state_dir: str | Path) -> set[str]:
    p = load_settings(state_dir).get("protected")
    return {x for x in p if isinstance(x, str)} if isinstance(p, list) else set()


def set_protected(state_dir: str | Path, svc_id: str, on: bool) -> set[str]:
    """Only the page calls this; dokploy.py has no command for it."""
    with _locked(state_dir):
        ids = protected(state_dir)
        (ids.add if on else ids.discard)(svc_id)
        save_settings(state_dir, {**load_settings(state_dir), "protected": sorted(ids)})
    return ids


def guard(state_dir: str | Path, svc: dict) -> None:
    """Every write goes through this first: a protected service is read-only."""
    if svc["id"] in protected(state_dir):
        raise DokployError("protected", f"{svc['name']} is protected: lift it on the Dokploy page in Harness first")


def risks(svc: dict) -> list[str]:
    """What a deploy does beyond the obvious, for the confirmation: downtime, nothing rebuilt."""
    out = []
    if svc["kind"] in _PLURAL and svc.get("detailed") is False:
        return ["downtime", "unknown"]  # Dokploy did not give its details: assume the worst
    if svc["kind"] == "compose" or (svc["kind"] == "application" and not svc.get("start_first")):
        out.append("downtime")  # compose recreates its containers; a swarm app stops first unless start-first
    if svc.get("source") in ("raw", "docker", "drop"):
        out.append("no_rebuild")  # no git source: the same image(s) start again
    return out


def client(state_dir: str | Path, secret: Secret, timeout: float = TIMEOUT) -> Client:
    s = load_settings(state_dir)
    if not s.get("url"):
        raise DokployError("not_connected", "Dokploy is not connected: open the Dokploy page in Harness")
    key = (secret(KEY) or "").strip()
    if not key:
        raise DokployError("no_key", f"{KEY} is missing in Settings -> Keys")
    if s.get("key") != fingerprint(key):
        raise DokployError("key_changed", f"{KEY} changed: check it again on the Dokploy page")
    return Client(s["url"], key, timeout)


# ---- the skill sessions read ---------------------------------------------------------------------------------
SKILL_SRC = Path(  # DOKPLOY_SKILL_SRC: tests only, so they never link or write the repository's own files
    os.environ.get("DOKPLOY_SKILL_SRC") or Path(__file__).resolve().parent / "skill" / "dokploy"
).resolve()


def skill_dest(workspace: str | Path) -> Path:
    return Path(workspace) / ".claude" / "skills" / "dokploy"


def _files(d: Path) -> dict[str, bytes]:
    return {f.name: f.read_bytes() for f in d.iterdir() if f.is_file()} if d.is_dir() else {}


def _custom(dest: Path) -> list[str]:
    """What in a real skill folder is not a plain copy of the shipped files (the user's own: never removed)."""
    ours = _files(SKILL_SRC)
    return sorted(f.name for f in dest.iterdir() if f.name not in ours or f.is_symlink() or not f.is_file())


def skill_state(workspace: str | Path | None) -> str:
    """ok, missing, copied (a 1.x copy, still read), custom (a copy with the user's files), linked, broken; no raise."""
    try:
        if not _files(SKILL_SRC):
            return "broken"
        dest = skill_dest(workspace)
        if dest.is_symlink():
            if dest.resolve() == SKILL_SRC:
                return "ok"
            return "linked" if dest.exists() else "missing"  # a dead link is repaired like a missing skill
        if dest.is_dir() and (dest / "SKILL.md").is_file():
            return "custom" if _custom(dest) else "copied"
        if not dest.exists() or (dest.is_dir() and not any(dest.iterdir())):
            return "missing"  # nothing, or an empty folder: install_skill replaces it
        return "custom"
    except (OSError, TypeError, ValueError):
        return "missing"


_SKILL_LOCK = threading.Lock()  # one link at a time: the update route and the button can run together


def install_skill(workspace: str | Path, replace_copy: bool = True) -> Path:
    with _SKILL_LOCK:
        return _install_skill(workspace, replace_copy)


def _install_skill(workspace: str | Path, replace_copy: bool) -> Path:
    """Links <workspace>/.claude/skills/dokploy to this extension's skill (a link follows every git pull).

    A 1.x copy is replaced only when `replace_copy` and it holds nothing but the shipped files; it is moved aside
    first and put back if anything fails, so the sessions never lose their skill.
    """
    dest = skill_dest(workspace)
    if not _files(SKILL_SRC):
        raise DokployError("skill_failed", f"{SKILL_SRC} is empty: update the extension (git pull)")
    if dest.is_symlink() and dest.resolve() == SKILL_SRC:
        return dest
    if dest.is_symlink() and dest.exists():
        raise DokployError("skill_linked", f"{dest} links to another folder: remove that link first")
    claude = dest.parent.parent  # <workspace>/.claude: the aside copy never sits among the skills Claude reads
    for old in dest.parent.glob(".dokploy-link-*"):
        with contextlib.suppress(OSError):  # a temp link an interrupted run left
            old.unlink()
    for old in claude.glob(".dokploy-old-*"):  # a copy an interrupted run moved aside
        with contextlib.suppress(OSError):
            if not dest.exists() and not dest.is_symlink():
                os.rename(old, dest)  # it may be the only copy left: give it back first
            else:
                shutil.rmtree(old)
    tag = uuid.uuid4().hex[:12]
    aside, tmp = claude / f".dokploy-old-{tag}", dest.with_name(f".dokploy-link-{tag}")
    moved = False
    try:
        if dest.exists() and not dest.is_symlink():
            if not dest.is_dir() or _custom(dest):
                found = ", ".join(_custom(dest)) if dest.is_dir() else "not a folder"
                raise DokployError("skill_custom", f"{dest} holds your own files ({found}): it is left as it is")
            if not replace_copy:
                return dest  # the 1.x copy keeps working; the page offers to link it
            os.rename(dest, aside)
            moved = True
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp.unlink(missing_ok=True)
        tmp.symlink_to(SKILL_SRC, target_is_directory=True)
        os.replace(tmp, dest)  # atomic, also over a dead link
    except OSError as e:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        if moved:
            with contextlib.suppress(OSError):
                os.rename(aside, dest)  # put the copy back: never leave the sessions without a skill
        raise DokployError("skill_failed", f"cannot link the skill at {dest}: {e.strerror or e}") from None
    if moved:
        shutil.rmtree(aside, ignore_errors=True)
    return dest


# ---- updates: this extension (git) and Dokploy -----------------------------------------------------------
EXT_DIR = Path(__file__).resolve().parent
GITHUB_API = "https://api.github.com"
GITHUB_RE = re.compile(
    r"^(?:https://(?:[^@/]+@)?|ssh://git@|git@)github\.com[:/]([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$"
)
CHECK_BUDGET = 22  # seconds for a whole check: Harness stops an extension request at 30
DOKPLOY_UPDATE_WAIT = 300  # seconds during which a started Dokploy update is not started again
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}  # no prompt (no tty either), messages in English


class _GitTimeout(Exception):
    pass


def _git(ext_dir: Path, *args: str, timeout: float = 5, deadline: float | None = None) -> tuple[int, str, str]:
    """(rc, stdout, stderr) of git in its own session, killed whole on timeout: a stuck helper never hangs Harness."""
    if deadline is not None:
        timeout = min(timeout, deadline - time.monotonic())
        if timeout <= 0:
            return 124, "", "timeout"
    try:
        proc = subprocess.Popen(
            ["git", "-C", str(ext_dir), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            env={**os.environ, **GIT_ENV},
        )
    except OSError:
        return 127, "", "git not found"
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, 9)
        try:
            proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:  # a helper that left the group still holds the pipes
            for f in (proc.stdout, proc.stderr):
                with contextlib.suppress(OSError):
                    f.close()
        return 124, "", "timeout"
    return proc.returncode, (out or "").strip(), (err or "").strip()


def _g(ext_dir: Path, deadline: float, *args: str, timeout: float = 5) -> tuple[int, str, str]:
    """_git for ext_check: a timeout ends the whole check as `timeout`, never as a misleading state."""
    r = _git(ext_dir, *args, timeout=timeout, deadline=deadline)
    if r[0] == 124:
        raise _GitTimeout
    return r


def ci_state(remote_url: str, sha: str, deadline: float | None = None) -> str:
    """success, failure, pending, rate_limited or unknown: GitHub checks of `sha` (public API, no token)."""
    m = GITHUB_RE.search(remote_url or "")
    if not m or not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        return "unknown"
    base = os.environ.get("DOKPLOY_EXT_GITHUB_API") or GITHUB_API
    req = urllib.request.Request(
        f"{base}/repos/{m[1]}/{m[2]}/commits/{sha}/check-runs?per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "harness-maxxing-dokploy"},
    )
    wait = 8 if deadline is None else min(8, deadline - time.monotonic())
    if wait <= 0:
        return "unknown"
    try:
        with _OPENER.open(req, timeout=wait) as r:
            data = json.loads(r.read(1_000_000))
    except urllib.error.HTTPError as e:
        return "rate_limited" if e.code in (403, 429) else "unknown"
    except (urllib.error.URLError, OSError, ValueError):
        return "unknown"
    runs = [x for x in (data.get("check_runs") or []) if isinstance(x, dict)] if isinstance(data, dict) else []
    if not runs or data.get("total_count", len(runs)) != len(runs):
        return "unknown"  # none, or more than one page: not enough to call it green
    if any(x.get("status") != "completed" for x in runs):
        return "pending"
    if any(x.get("conclusion") not in ("success", "skipped", "neutral") for x in runs):
        return "failure"
    return "success" if any(x.get("conclusion") == "success" for x in runs) else "unknown"


def _changes(old: str, new_changelog: str) -> str:
    """The CHANGELOG sections above the installed version's heading."""
    out = []
    for line in new_changelog.splitlines():
        if line.startswith("## ") and line[3:].split(" ")[0] == old:
            break
        out.append(line)
    return "\n".join(x for x in out if not x.startswith("# ")).strip()[:4000]


def _manifest(text: str) -> dict:
    try:
        m = json.loads(text)
    except ValueError:
        return {}
    return m if isinstance(m, dict) else {}


def ext_check(
    ext_dir: Path = EXT_DIR, supported_api: int = 1, fetch: bool = True, budget: float = CHECK_BUDGET
) -> dict:
    """What updating this extension would do, and why it is refused: never changes the folder."""
    deadline = time.monotonic() + budget
    try:
        cur = _manifest((ext_dir / "manifest.json").read_text())
    except OSError:
        cur = {}
    out: dict[str, Any] = {
        "current": cur.get("version"),
        "new": None,
        "commit": None,
        "changes": "",
        "ci": None,
        "blockers": [],
    }
    if not cur.get("id"):
        return {**out, "state": "bad_manifest"}
    try:
        return {**out, **_ext_check(ext_dir, supported_api, fetch, deadline, cur)}
    except _GitTimeout:
        return {**out, "state": "timeout"}


def _ext_check(ext_dir: Path, supported_api: int, fetch: bool, deadline: float, cur: dict) -> dict:
    rc, top, err = _g(ext_dir, deadline, "rev-parse", "--show-toplevel")
    if "dubious ownership" in err:
        return {"state": "dubious_owner"}  # git refuses a folder owned by another user
    if rc != 0 or Path(top).resolve() != ext_dir.resolve():
        return {"state": "not_git"}  # installed by copy (or inside another repository): update it by hand
    if fetch and _g(ext_dir, deadline, "fetch", "--quiet", timeout=15)[0] != 0:
        return {"state": "unreachable"}
    branch = _g(ext_dir, deadline, "symbolic-ref", "--quiet", "--short", "HEAD")[1]
    remote = _g(ext_dir, deadline, "config", "--get", f"branch.{branch}.remote")[1] if branch else ""
    rc, new, _ = _g(ext_dir, deadline, "rev-parse", "--verify", "--quiet", "@{u}")
    if rc != 0 or not new or not remote or remote.startswith("-") or remote == ".":
        return {"state": "no_upstream"}
    head = _g(ext_dir, deadline, "rev-parse", "HEAD")[1]
    if head == new:
        return {"state": "up_to_date", "new": cur.get("version"), "commit": new}
    if _g(ext_dir, deadline, "merge-base", "--is-ancestor", "@{u}", "HEAD")[0] == 0:
        return {"state": "ahead", "commit": head}  # a newer checkout than the repository: nothing to fetch
    man = _manifest(_g(ext_dir, deadline, "show", "@{u}:manifest.json")[1])
    api = man.get("api", 1)
    blockers = []
    if _g(ext_dir, deadline, "status", "--porcelain", "--untracked-files=no")[1]:
        blockers.append("local_changes")
    if _g(ext_dir, deadline, "merge-base", "--is-ancestor", "HEAD", "@{u}")[0] != 0:
        blockers.append("not_fast_forward")
    if man.get("id") != cur.get("id"):
        blockers.append("not_this_extension")
    elif not isinstance(api, int) or isinstance(api, bool):
        blockers.append("bad_manifest")
    elif api > supported_api:
        blockers.append("needs_newer_harness")
    url = _g(ext_dir, deadline, "remote", "get-url", remote)[1]
    changes = _changes(str(cur.get("version")), _g(ext_dir, deadline, "show", "@{u}:CHANGELOG.md")[1])
    ci = ci_state(url, new, deadline)
    if ci != "success":
        blockers.append(f"ci_{ci}")
    return {
        "state": "blocked" if blockers else "available",
        "new": man.get("version"),
        "commit": new,
        "changes": changes,
        "ci": ci,
        "blockers": blockers,
    }


def ext_update(ext_dir: Path, supported_api: int, confirmed: str) -> dict:
    """Fast-forwards to the commit the user confirmed, only when the check (on what was fetched) still allows it."""
    chk = ext_check(ext_dir, supported_api, fetch=False, budget=8)  # same @{u} as the user saw: no second fetch
    if chk["state"] != "available":
        raise DokployError("update_refused", f"this update is not clean any more ({chk['state']}): check again")
    if chk["commit"] != confirmed:
        raise DokployError("target_changed", "a newer version appeared since you checked: check again")
    rc, _, err = _git(ext_dir, "merge", "--ff-only", "--quiet", confirmed, timeout=15)
    if rc == 124:
        raise DokployError("update_failed", f"git took too long: check `git -C {ext_dir} status`, then update by hand")
    if rc != 0:
        raise DokployError("update_failed", f"git could not fast-forward the extension folder: {err[:200]}")
    return chk


def dokploy_check(c: Client) -> dict:
    v = c.get("settings.getDokployVersion")
    d = c.post("settings.getUpdateData", {})
    d = d if isinstance(d, dict) else {}
    return {
        "current": v if isinstance(v, str) else None,
        "latest": d.get("latestVersion"),
        "available": bool(d.get("updateAvailable")),
    }


def dokploy_update(c: Client, confirmed: str, state_dir: str | Path) -> dict:
    """Dokploy updates itself to its latest release; its page is away about two minutes, Traefik and apps run on."""
    marker = Path(state_dir) / "dokploy-update-started"
    marker.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(FileNotFoundError):
        if not 0 <= time.time() - marker.stat().st_mtime < DOKPLOY_UPDATE_WAIT:
            marker.unlink()  # old, or dated in the future by a clock change
    try:
        os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))  # one update at a time, atomically
    except FileExistsError:
        raise DokployError(
            "update_in_progress", "a Dokploy update was started a few minutes ago: wait for it"
        ) from None
    started = False
    try:
        chk = dokploy_check(c)
        if not chk["available"]:
            raise DokployError("up_to_date", "Dokploy is already up to date")
        if chk["latest"] != confirmed:
            raise DokployError("target_changed", "a newer Dokploy appeared since you checked: check again")
        try:
            c.post("settings.updateServer", {})
        except DokployError as e:
            if e.code != "unreachable":
                raise
        started = True  # also when the request dropped: Dokploy restarts under it
    finally:
        if not started:
            marker.unlink(missing_ok=True)  # nothing started: a retry must not wait five minutes
    return chk


# ---- HTTP ----------------------------------------------------------------------------------------------------
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a: Any, **k: Any) -> None:
        return None  # the key is never resent to another address


_OPENER = urllib.request.build_opener(_NoRedirect)


class Client:
    def __init__(self, base: str, key: str, timeout: float = TIMEOUT):
        self.base = base.rstrip("/") + "/api/"
        self.key = key
        self.timeout = timeout

    def _do(self, method: str, proc: str, params: dict | None = None, body: dict | None = None) -> Any:
        url = self.base + proc + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "x-api-key": self.key,
                "Accept": "application/json",
                "User-Agent": "harness-maxxing-dokploy",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with _OPENER.open(req, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise self._error(proc, e.code, e.read()[:2000]) from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise DokployError("unreachable", f"Dokploy does not answer ({type(e).__name__})") from None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            raise DokployError("bad_response", "Dokploy answered something that is not JSON") from None

    @staticmethod
    def _error(proc: str, code: int, raw: bytes) -> DokployError:
        if code in (401, 403):
            return DokployError("refused", "the Dokploy key is refused")
        if code == 404:
            return DokployError("not_found", f"Dokploy: {proc} not found")
        if 300 <= code < 400:
            return DokployError("redirected", "Dokploy redirected the request: check its URL")
        try:
            j = json.loads(raw)
            msg = str((j.get("message") if isinstance(j, dict) else None) or j)
        except ValueError:
            msg = raw.decode("utf-8", "replace")
        return DokployError("api_error", f"Dokploy answered {code} to {proc}: {msg[:200]}")

    def get(self, proc: str, params: dict | None = None) -> Any:
        return self._do("GET", proc, params=params)

    def post(self, proc: str, body: dict) -> Any:
        return self._do("POST", proc, body=body)


# ---- services --------------------------------------------------------------------------------------------------
def _repo(a: dict) -> str | None:
    if a.get("owner") and a.get("repository"):
        return f"{a['owner']}/{a['repository']}"
    return a.get("customGitUrl") or a.get("gitlabPathNamespace") or None


def _service(kind: str, s: dict, p: dict, e: dict) -> dict:
    return {
        "kind": kind,
        "id": s[_ID[kind]],
        "name": s.get("name") or s.get("appName") or s[_ID[kind]],
        "app_name": s.get("appName"),
        "project": p.get("name"),
        "project_id": p.get("projectId"),
        "environment": e.get("name") if e is not p else None,
        "environment_id": e.get("environmentId"),
        "status": s.get(_STATUS.get(kind, "applicationStatus")) or None,  # kept for 1.x scripts: last_deployment
        "last_deployment": s.get(_STATUS.get(kind, "applicationStatus")) or None,
        "domains": [
            {"host": d.get("host"), "https": bool(d.get("https")), "port": d.get("port"), "path": d.get("path") or "/"}
            for d in s.get("domains") or []
            if isinstance(d, dict) and d.get("host")
        ],
        "repo": _repo(s) if kind in _PLURAL else None,
        "build": s.get("buildType") if kind == "application" else None,
        "source": s.get("sourceType") if kind in _PLURAL else None,
        "start_first": _start_first(s) if kind == "application" else None,
        "replicas": s.get("replicas") if kind == "application" else None,
        "rollback_active": s.get("rollbackActive") if kind == "application" else None,
        "compose_type": s.get("composeType") if kind == "compose" else None,
        "server_id": s.get("serverId"),
    }


def _start_first(a: dict) -> bool | None:
    u = a.get("updateConfigSwarm")
    return (u.get("Order") == "start-first") if isinstance(u, dict) else None


def services(projects: Any) -> list[dict]:
    """project.all flattened: one entry per application, compose stack and database."""
    out: list[dict] = []
    for p in projects if isinstance(projects, list) else []:
        if not isinstance(p, dict):
            continue
        envs = p.get("environments") if isinstance(p.get("environments"), list) else [p]
        for e in envs:
            if not isinstance(e, dict):
                continue
            for kind in KINDS:
                for s in e.get(_PLURAL.get(kind, kind)) or []:
                    if isinstance(s, dict) and s.get(_ID[kind]):
                        out.append(_service(kind, s, p, e))
    return out


def environments(projects: Any) -> list[dict]:
    """Where an app can be created: {id, name, project, project_id}."""
    return [
        {"id": e["environmentId"], "name": e.get("name"), "project": p.get("name"), "project_id": p.get("projectId")}
        for p in (projects if isinstance(projects, list) else [])
        if isinstance(p, dict)
        for e in p.get("environments") or []
        if isinstance(e, dict) and e.get("environmentId")
    ]


def detail(c: Client, s: dict) -> dict:
    """<kind>.one completes an app or stack: project.all (v0.30) gives them only id, name and state."""
    if s["kind"] not in _PLURAL:
        return s
    try:
        full = c.get(f"{s['kind']}.one", {_ID[s["kind"]]: s["id"]})
    except DokployError:
        return {**s, "detailed": False}  # shown with what project.all gave
    if not isinstance(full, dict):
        return {**s, "detailed": False}
    more = _service(
        s["kind"],
        {**full, _ID[s["kind"]]: s["id"]},
        {"name": s["project"], "projectId": s["project_id"]},
        {"name": s["environment"], "environmentId": s["environment_id"]},
    )
    return {
        **s,
        **{k: v for k, v in more.items() if v not in (None, [], "") or k == "domains"},
        "environment": s["environment"],
        "detailed": True,
    }


def inventory(c: Client) -> list[dict]:
    """Every service, apps and stacks completed (one call each, 8 at a time)."""
    svcs = services(c.get("project.all"))
    todo = [s for s in svcs if s["kind"] in _PLURAL]
    if todo:
        with ThreadPoolExecutor(max_workers=min(8, len(todo))) as ex:
            done = {s["id"]: x for s, x in zip(todo, ex.map(lambda x: detail(c, x), todo), strict=True)}
        svcs = [done.get(s["id"], s) for s in svcs]
    return svcs


def lookup(c: Client, ref: str) -> dict:
    """One service by id or name, completed: project.all plus a single .one call, not the whole inventory."""
    try:
        return detail(c, find(services(c.get("project.all")), ref))
    except DokployError as e:
        if e.code != "not_found":
            raise
    return find(inventory(c), ref)  # an app name (acme-web-x1) is only known after the .one calls


def find(svcs: list[dict], ref: str) -> dict:
    """By id, then name or app name (case-insensitive); `ambiguous` lists the candidates."""
    r = (ref or "").strip()
    hit = [s for s in svcs if s["id"] == r]
    if not hit:
        low = r.lower()
        hit = [s for s in svcs if low in ((s["name"] or "").lower(), (s["app_name"] or "").lower())]
    if not hit:
        raise DokployError("not_found", f"no Dokploy service named {r!r} (see: list)")
    if len(hit) > 1:
        names = ", ".join(f"{s['project']}/{s['name']} ({s['kind']}, {s['id']})" for s in hit)
        raise DokployError("ambiguous", f"{r!r} matches several services: {names} - use the id")
    return hit[0]


def _deployable(svc: dict) -> None:
    if svc["kind"] not in _PLURAL:
        raise DokployError("not_deployable", f"{svc['name']} is a {svc['kind']} database: nothing to deploy")


def _check(value: str, rx: re.Pattern, what: str) -> str:
    """Values a (possibly prompt-injected) session passes on to Dokploy: git clone, Traefik rules, names."""
    v = (value or "").strip()
    if not rx.match(v):
        raise DokployError("invalid_value", f"invalid {what}: {v[:80]!r}")
    return v


# ---- writes (callers get the user's agreement first) -----------------------------------------------------------
def deploy(c: Client, svc: dict, title: str | None = None, again: bool = False) -> None:
    _deployable(svc)
    body: dict[str, Any] = {_ID[svc["kind"]]: svc["id"]}
    if title:
        body["title"] = title.strip()[:120]
    c.post(f"{svc['kind']}.{'redeploy' if again else 'deploy'}", body)


def power(c: Client, svc: dict, on: bool) -> None:
    """Start or stop an app or a stack (its containers), without rebuilding anything."""
    _deployable(svc)
    c.post(f"{svc['kind']}.{'start' if on else 'stop'}", {_ID[svc["kind"]]: svc["id"]})


def rollback_target(c: Client, svc: dict) -> dict:
    """The deployment a rollback goes back to: the newest earlier successful one that kept a rollback image."""
    _deployable(svc)
    if svc["kind"] != "application":
        raise DokployError("not_supported", "Dokploy rolls back applications only: redeploy the stack instead")
    if not svc.get("rollback_active"):
        raise DokployError(
            "rollback_off", f"rollbacks are off for {svc['name']}: turn them on in Dokploy (they need a registry)"
        )
    deps = deployments(c, svc)
    if deps and deps[0]["status"] in ("running", "queued"):
        raise DokployError("deploy_in_progress", f"a deployment of {svc['name']} is running: wait for it first")
    done = [d for d in deps if d["status"] == "done"]  # done[0] is what runs now (a failed deploy keeps the old one)
    target = next((d for d in done[1:] if d.get("rollback_id")), None)
    if not target:
        raise DokployError("no_rollback", f"{svc['name']} has no earlier deployment to go back to")
    return target


def rollback(c: Client, svc: dict, target: dict, confirmed: str | None = None) -> None:
    """`confirmed`: the deployment id the user agreed to; refused if the target moved since."""
    if confirmed is not None and confirmed != target["id"]:
        raise DokployError(
            "target_changed", "the deployments changed since you confirmed: look again before rolling back"
        )
    c.post("rollback.rollback", {"rollbackId": target["rollback_id"]})


def domain_add(
    c: Client,
    svc: dict,
    host: str,
    port: int | None = None,
    https: bool = True,
    path: str | None = None,
    service: str | None = None,
) -> None:
    _deployable(svc)
    host = _check((host or "").lower(), HOST_RE, "host name")
    if port is not None and not 1 <= int(port) <= 65535:
        raise DokployError("invalid_value", "the port must be 1-65535")
    if path is not None and not PATH_RE.match(path):
        raise DokployError("invalid_value", "the path must start with / and use letters, digits, . _ ~ - /")
    if svc["kind"] == "compose" and not service:
        raise DokployError("service_needed", "a compose stack needs --service: the service of the stack to serve")
    body: dict[str, Any] = {
        "host": host,
        "https": https,
        "certificateType": "letsencrypt" if https else "none",
        "domainType": svc["kind"],
        _ID[svc["kind"]]: svc["id"],
    }
    if port:
        body["port"] = int(port)
    if path:
        body["path"] = path
    if service:
        body["serviceName"] = _check(service, NAME_RE, "service name")
    c.post("domain.create", body)


def app_create(
    c: Client,
    environment_id: str,
    name: str,
    repo: str,
    branch: str = "main",
    build: str = "nixpacks",
    build_path: str = "/",
) -> str:
    """application.create, then its git source and build type; returns the new application id."""
    if build not in BUILD_TYPES:
        raise DokployError("invalid_value", f"build must be one of {', '.join(BUILD_TYPES)}")
    environment_id = _check(environment_id, re.compile(r"^[A-Za-z0-9_-]{1,64}$"), "environment id")
    name = _check(name, NAME_RE, "app name")
    repo = _check(repo, GIT_URL_RE, "git URL (https://, ssh:// or git@host:path)")
    branch = _check(branch, BRANCH_RE, "branch")
    if not PATH_RE.match(build_path or "") or ".." in build_path:
        raise DokployError("invalid_value", "the build path must start with / and stay inside the repository")
    app = c.post("application.create", {"name": name, "environmentId": environment_id})
    app_id = app.get("applicationId") if isinstance(app, dict) else None
    if not app_id:
        raise DokployError("bad_response", "application.create did not give the new application id")
    c.post(
        "application.saveGitProvider",
        {
            "applicationId": app_id,
            "customGitUrl": repo,
            "customGitBranch": branch,
            "customGitBuildPath": build_path,
            "watchPaths": None,
        },
    )
    c.post(
        "application.saveBuildType",
        {
            "applicationId": app_id,
            "buildType": build,
            "dockerfile": None,
            "dockerContextPath": None,
            "dockerBuildStage": None,
            "herokuVersion": None,
            "railpackVersion": None,
        },
    )
    return app_id


# ---- reads -----------------------------------------------------------------------------------------------------
def _mine(name: str, app: str, kind: str) -> bool:
    """Keeps only this service's containers: Dokploy's name match would also catch another app sharing the prefix."""
    if kind == "application":
        return name == app or name.startswith(app + ".")
    return name.startswith(app + "_") or bool(re.match(rf"^{re.escape(app)}-[A-Za-z0-9._-]+-\d+$", name))


_ROUTER = re.compile(r"^traefik\.http\.routers\.([^.]+)\.rule$")
_RULE_HOST = re.compile(r"\bHost\(([^)]*)\)")
_RULE_PREFIX = re.compile(r"\bPathPrefix\(`([^`]+)`\)")
LABEL_CONTAINERS = 10  # docker.getConfig calls per compose, at most


def label_domains(labels: Any) -> list[dict]:
    """Hosts a container's own Traefik labels route: {host, https, port, path}, one per host."""
    if not isinstance(labels, dict) or str(labels.get("traefik.enable", "true")).lower() == "false":
        return []
    out: dict[str, dict] = {}
    for key, rule in labels.items():
        m = _ROUTER.match(str(key))
        if not m or not isinstance(rule, str):
            continue
        r = f"traefik.http.routers.{m[1]}."
        https = (
            "websecure" in str(labels.get(r + "entrypoints") or "")
            or str(labels.get(r + "tls") or "").lower() == "true"
            or bool(labels.get(r + "tls.certresolver"))
        )
        prefix = _RULE_PREFIX.search(rule)
        path = prefix[1] if prefix and PATH_RE.match(prefix[1]) else "/"
        for args in _RULE_HOST.findall(rule):
            for host in re.findall(r"`([^`]+)`", args):
                host = host.lower()
                if not HOST_RE.match(host):
                    continue
                d = out.setdefault(host, {"host": host, "https": False, "port": None, "path": path})
                d["https"] = d["https"] or https  # an http router that redirects sits next to the https one
    return list(out.values())


def _routed(c: Client, svc: dict, rows: list[dict]) -> list[dict]:
    """Domains a compose routes through its own Traefik labels, beyond its Dokploy domains (labels only: the rest of
    docker inspect, env included, is dropped here)."""
    known = {str(d.get("host") or "").lower() for d in svc.get("domains") or []}
    out: dict[str, dict] = {}
    ids = [str(r["containerId"]) for r in rows if r.get("containerId") and r.get("state") == "running"]
    for cid in ids[:LABEL_CONTAINERS]:
        params = {"containerId": cid, **({"serverId": svc["server_id"]} if svc.get("server_id") else {})}
        try:
            cfg = c.get("docker.getConfig", params)
        except DokployError:
            continue  # a container gone between the two calls, or an older Dokploy: its domains stay unknown
        labels = ((cfg or {}).get("Config") or {}).get("Labels") if isinstance(cfg, dict) else None
        for d in label_domains(labels):
            if d["host"] not in known:
                out.setdefault(d["host"], d)
    return list(out.values())


def health(c: Client, svc: dict) -> dict:
    """Containers really running, not the last deployment; state: ok, partial, down, stopped or unknown."""
    _deployable(svc)
    app = svc.get("app_name")
    if not app:
        return {"state": "unknown", "running": 0, "expected": None, "containers": []}
    params = {"appName": app, **({"serverId": svc["server_id"]} if svc.get("server_id") else {})}
    stack = svc["kind"] == "compose" and svc.get("compose_type") == "stack"
    if svc["kind"] == "compose" and not stack:
        params["appType"] = "docker-compose"
    rows = c.get("docker.getStackContainersByAppName" if stack else "docker.getContainersByAppNameMatch", params) or []
    rows = [r for r in rows if isinstance(r, dict) and _mine(str(r.get("name") or ""), app, svc["kind"])]
    boxes = [
        {"name": str(r.get("name") or ""), "state": r.get("state"), "status": r.get("status") or r.get("currentState")}
        for r in rows
    ]
    if stack:  # swarm keeps old tasks: a slot (service.N) is up when one of its tasks runs
        slots: dict[str, bool] = {}
        for b in boxes:
            if b["state"] != "complete":  # a one-shot task that finished is not a slot to keep up
                slots[b["name"]] = slots.get(b["name"], False) or b["state"] == "running"
        running, expected = sum(slots.values()), len(slots)
        if not slots:
            return {"state": "unknown", "running": 0, "expected": None, "containers": boxes}
    else:
        done = [b for b in boxes if b["state"] == "exited" and str(b["status"] or "").startswith("Exited (0)")]
        live = [b for b in boxes if b not in done]  # a one-shot that exited cleanly (migration, init) is not down
        running = sum(b["state"] == "running" for b in live)
        replicas = svc.get("replicas")  # Dokploy's default is one replica
        expected = (1 if replicas is None else int(replicas)) if svc["kind"] == "application" else len(live)
        if svc["kind"] == "compose" and not boxes:  # custom container_name, or nothing created: cannot tell
            return {"state": "unknown", "running": 0, "expected": None, "containers": []}
    if expected == 0:  # an app scaled to 0, or a compose whose containers all exited cleanly
        state = "stopped"
    elif running == 0:
        state = "down"
    else:
        state = "ok" if running >= expected else "partial"
    out = {"state": state, "running": running, "expected": expected, "containers": boxes}
    if svc["kind"] == "compose" and not stack:  # a swarm stack's labels sit on its services, not its containers
        out["routed"] = _routed(c, svc, rows)
    return out


def deployments(c: Client, svc: dict) -> list[dict]:
    """Newest first: {id, title, status, created, log_path}."""
    _deployable(svc)
    proc, key = (
        ("deployment.all", "applicationId")
        if svc["kind"] == "application"
        else ("deployment.allByCompose", "composeId")
    )
    rows = c.get(proc, {key: svc["id"]}) or []
    out = [
        {
            "id": d.get("deploymentId"),
            "title": (d.get("title") or "").strip().split("\n")[0][:120] or None,
            "status": d.get("status"),
            "created": d.get("createdAt"),
            "log_path": d.get("logPath"),
            "rollback_id": d.get("rollbackId"),
        }
        for d in rows
        if isinstance(d, dict)
    ]  # Dokploy titles a git deployment with the whole commit message
    return sorted(out, key=lambda d: _when(d["created"]), reverse=True)


def _when(stamp: str | None) -> dt.datetime:
    """Dokploy's ISO timestamps as dates (a string sort breaks on other offsets); none sorts oldest."""
    try:
        t = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return dt.datetime.min.replace(tzinfo=dt.UTC)
    return t if t.tzinfo else t.replace(tzinfo=dt.UTC)


def log(dep: dict, lines: int = 200) -> str:
    """Tail of a deployment log; only a regular file under Dokploy's log folder of this server is read."""
    raw = dep.get("log_path")
    if not raw:
        raise DokployError("no_log", "this deployment has no log file")
    root = logs_dir().resolve()
    p = Path(raw).resolve()
    if root not in p.parents or not p.is_file():
        raise DokployError("remote_log", "the log is not on this server: open it in Dokploy")
    n = max(1, min(int(lines), LOG_MAX_LINES))
    with p.open("rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 256 * 1024))
        tail = f.read().decode("utf-8", "replace").splitlines()
    return "\n".join(tail[-n:])
