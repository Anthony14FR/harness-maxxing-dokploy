import datetime as dt
import shutil
import socket
import ssl
import subprocess
import threading

import pytest


@pytest.fixture
def tls_server(tmp_path):
    """A local TLS server with a throwaway self-signed certificate for shop.example.com (made here, never stored)."""
    if not shutil.which("openssl"):
        pytest.skip("openssl is needed to make the test certificate")
    key, crt = tmp_path / "k.pem", tmp_path / "c.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "30",
            "-subj",
            "/CN=shop.example.com",
            "-keyout",
            str(key),
            "-out",
            str(crt),
        ],
        check=True,
        capture_output=True,
    )
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(crt, key)
    srv = socket.create_server(("127.0.0.1", 0))
    stop = threading.Event()

    def serve():
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue
            try:
                with ctx.wrap_socket(conn, server_side=True):
                    pass
            except (ssl.SSLError, OSError):
                conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    yield srv.getsockname()[1], crt
    stop.set()
    t.join(2)
    srv.close()


def test_the_served_certificate_is_read_even_when_not_trusted(core, tls_server):
    port, crt = tls_server
    r = core.check_certificate("127.0.0.1", "shop.example.com", port)
    assert r["valid"] is False and "self" in r["error"].lower()  # self-signed: a browser would refuse it
    assert r["days_left"] in (29, 30)
    der = ssl.PEM_cert_to_DER_cert(crt.read_text())
    assert core.cert_not_after(der).isoformat() == r["not_after"]


def test_no_tls_answer_is_said(core):
    with socket.create_server(("127.0.0.1", 0)) as s:
        port = s.getsockname()[1]
    r = core.check_certificate("127.0.0.1", "shop.example.com", port)  # nothing listens there any more
    assert r["valid"] is False and r["error"].startswith("no TLS answer") and r["days_left"] is None


def test_garbage_is_not_a_date(core):
    assert core.cert_not_after(b"") is None and core.cert_not_after(b"\x30\x03\x02\x01\x01") is None


def test_certificate_alerts(core):
    now = dt.datetime(2026, 11, 10, tzinfo=dt.UTC).timestamp()
    certs = [
        {"host": "a.example.com", "valid": True, "days_left": 9, "not_after": "2026-11-19T00:00:00+00:00"},
        {
            "host": "b.example.com",
            "valid": False,
            "days_left": 60,
            "not_after": "2027-01-09T00:00:00+00:00",
            "error": "self-signed certificate",
        },
        {"host": "c.example.com", "valid": True, "days_left": 80, "not_after": "2027-01-29T00:00:00+00:00"},
        {"host": "d.example.com", "valid": False, "days_left": None, "not_after": None, "error": "no TLS answer"},
    ]
    issues = core.alert_issues({"certs": certs}, now)
    assert issues["cert-exp:a.example.com"]["title"] == "Certificate of a.example.com expires in 9 days"
    assert issues["cert:b.example.com"]["body"] == "self-signed certificate"
    assert not {k for k in issues if "c.example.com" in k or "d.example.com" in k}  # fine, or nothing served yet
