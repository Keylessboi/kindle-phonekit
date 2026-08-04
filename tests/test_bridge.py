"""XMPP bridge scenario tests.

Covers tests/scenarios/xmpp-*.md:
  * SCRAM-SHA-1 client-final matches the RFC 5802 section-5 vector.
  * Listen mode authenticates, binds, and logs an inbound message to the inbox.
  * Send mode delivers a well-formed message stanza and exits 0.
  * Send mode escapes XML-special characters in the message body.
  * The stream reader avoids socket.makefile() (Python 3.14.6 hang).

The bridge is exercised as a REAL subprocess against the in-process XMPP mock
over self-signed TLS (PK_XMPP_NO_VERIFY=1).
"""

import io
import os
import re
import subprocess
import time
import tokenize

import pytest

from conftest import PY, XMPP_DIR


@pytest.fixture
def scram_sha1():
    """Import bridge.py's pure scram_sha1 without launching anything."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pk_bridge_test_import", os.path.join(XMPP_DIR, "bridge.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.scram_sha1


def test_scram_sha1_rfc5802_vector(scram_sha1):
    """XMPP-SCRAM-001."""
    password = "pencil"
    client_nonce = "fyko+d2lbbFgONRv9qkxdawL"
    server_nonce = "fyko+d2lbbFgONRv9qkxdawL3rfcNHYJY1ZVvWVs7j"
    c_first_bare = "n=user,r=%s" % client_nonce
    server_first = (
        "r=%s,s=QSXCR+Q6sek8bf92,i=4096" % server_nonce
    )
    result = scram_sha1(
        password, c_first_bare, server_first, client_nonce, server_nonce)
    assert result == (
        "c=biws,r=%s,"
        "p=v0X8v3Bz2T0CJGbJQyF0X+HI4Ts=" % server_nonce
    )


def _launch_bridge(argv, port, inbox=None):
    env = dict(os.environ)
    env.update({
        "PK_XMPP_JID": "user@localhost",
        "PK_XMPP_PASS": "pencil",
        "PK_XMPP_HOST": "127.0.0.1",
        "PK_XMPP_PORT": str(port),
        "PK_XMPP_NO_VERIFY": "1",
        "PK_XMPP_POPUP": "0",
        "PK_XMPP_DEBUG": "0",
    })
    if inbox:
        env["PK_XMPP_INBOX"] = inbox
    return subprocess.Popen(
        [PY, "bridge.py"] + argv,
        cwd=XMPP_DIR, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _wait_until(predicate, timeout=15, interval=0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_inbound_message_written_to_inbox(xmpp_mock, tmp_path):
    """XMPP-INBOUND-001."""
    inbox = tmp_path / "inbox.txt"
    proc = _launch_bridge(
        [], xmpp_mock.port, inbox=str(inbox))
    try:
        assert _wait_until(lambda: xmpp_mock.scram_verified is not None), (
            "bridge never completed SCRAM against mock")

        # 1. Mock verified the proof.
        assert xmpp_mock.scram_verified is True

        # 2. Mock received the bind set iq.
        assert xmpp_mock.received_bind is True

        # 3. Inbox received exactly one line for the pushed message.
        def saw_inbox():
            return inbox.exists() and inbox.read_text().strip() != ""

        assert _wait_until(saw_inbox), "bridge never wrote the inbox"
        lines = inbox.read_text().strip().splitlines()
        assert len(lines) == 1
        assert re.search(r"^\[\d\d:\d\d\] friend@localhost: hello from the mock server$", lines[0])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.parametrize("xmpp_mock", ["plain"], indirect=True)
def test_plain_fallback_auth_and_inbox(xmpp_mock, tmp_path):
    """XMPP-PLAIN-001: PLAIN SASL fallback still delivers the inbound message."""
    inbox = tmp_path / "inbox.txt"
    proc = _launch_bridge([], xmpp_mock.port, inbox=str(inbox))
    try:
        assert _wait_until(lambda: xmpp_mock.plain_verified is not None), (
            "bridge never sent PLAIN auth to mock")
        assert xmpp_mock.plain_verified is True
        assert _wait_until(lambda: xmpp_mock.received_bind is not None), (
            "bridge never completed bind against mock")
        assert xmpp_mock.received_bind is True

        def saw_inbox():
            return inbox.exists() and inbox.read_text().strip() != ""

        assert _wait_until(saw_inbox), "bridge never wrote the inbox"
        assert re.search(r"^\[\d\d:\d\d\] friend@localhost: hello from the mock server$",
                         inbox.read_text().strip())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.parametrize("xmpp_mock", ["send"], indirect=True)
def test_send_mode_escapes_body_special_chars(xmpp_mock):
    """XMPP-SEND-002: & < > in a body are XML-escaped in the stanza.

    Guards send_message()'s escaping so a body can't break out of <body>.
    """
    raw = "A & B < C > D"
    proc = _launch_bridge(["send", "friend@localhost", raw],
                          xmpp_mock.port)
    try:
        code = proc.wait(timeout=20)
        assert code == 0
        assert _wait_until(
            lambda: xmpp_mock.received_message_stanza is not None
        ), "bridge never delivered the send stanza"
        stanza = xmpp_mock.received_message_stanza
        assert b">A &amp; B &lt; C &gt; D</body>" in stanza
        assert b"&lt;" in stanza and b"&gt;" in stanza and b"&amp;" in stanza
        # No raw special char may appear inside the body.
        assert b">A & B" not in stanza
    finally:
        if proc.poll() is None:
            proc.terminate()


def test_bridge_source_avoids_socket_makefile():
    """XMPP-STREAM-001: bridge never calls socket.makefile().

    On Python 3.14.6 socket.makefile().read() blocks the full socket timeout
    even when select() reports readable data, which hangs the stream parser.
    Lock the raw-recv design against regression by asserting the identifier is
    absent from the bridge's executable code (comments/docstrings excluded via
    tokenize).
    """
    path = os.path.join(XMPP_DIR, "bridge.py")
    with open(path, "rb") as fh:
        idents = [
            t.string for t in tokenize.tokenize(fh.readline)
            if t.type == tokenize.NAME
        ]
    assert "makefile" not in idents, (
        "bridge.py must read the socket with raw recv(), not makefile() "
        "(Python 3.14.6 makefile().read() hangs on timeout)"
    )


@pytest.mark.parametrize("xmpp_mock", ["send"], indirect=True)
def test_send_mode_reaches_recipient(xmpp_mock):
    """XMPP-SEND-001 (send-capture mode mock)."""
    assert xmpp_mock.mode == "send"
    proc = _launch_bridge(["send", "friend@localhost", "hello from kindle"],
                          xmpp_mock.port)
    try:
        code = proc.wait(timeout=20)
        assert code == 0
        assert _wait_until(
            lambda: xmpp_mock.received_message_stanza is not None
        ), "bridge never delivered the send stanza"
        stanza = xmpp_mock.received_message_stanza
        assert b"to='friend@localhost'" in stanza
        assert b">hello from kindle</body>" in stanza
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()