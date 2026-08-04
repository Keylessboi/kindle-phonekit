"""Pytest fixtures for PhoneKit scenario tests.

Fixtures launch the REAL product servers as subprocesses against local mock
upstreams, keeping every test deterministic and isolated (ephemeral ports,
tmp inbox, fresh history per run).
"""

import os
import socket
import subprocess
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(REPO, "extensions", "phonekit", "ext")
LLM_DIR = os.path.join(EXT, "llm")
XMPP_DIR = os.path.join(EXT, "xmpp")
PY = sys.executable


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_http(port, path="/", timeout=10):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=1).read()
            return True
        except Exception:
            time.sleep(0.25)
    return False


@pytest.fixture
def cert_files(tmp_path):
    """Generate a self-signed cert/key pair for the XMPP mock TLS."""
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key), "-out", str(cert), "-days", "1", "-nodes",
            "-subj", "/CN=localhost",
        ],
        check=True, capture_output=True,
    )
    return str(cert), str(key)


@pytest.fixture
def llm_server(tmp_path):
    """Launch llm_server.py (real subprocess) on an ephemeral port."""
    from fixtures.mock_openai import MockOpenAI

    with MockOpenAI() as upstream:
        port = free_port()
        env = dict(os.environ)
        env.update({
            "PK_LLM_API_URL": upstream.url,
            "PK_LLM_MODEL": "test-model",
            "PK_LLM_SYSTEM": "You are a tiny deterministic test system prompt.",
            "PK_LLM_PORT": str(port),
            "PK_LLM_API_KEY": "",
        })
        proc = subprocess.Popen(
            [PY, "llm_server.py"],
            cwd=LLM_DIR, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            assert wait_http(port), "llm_server.py did not come up"
            yield {"port": port, "upstream": upstream, "proc": proc}
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture
def xmpp_mock(request, cert_files, tmp_path):
    """Run the in-process XMPP mock; yield its host/port + captured results."""
    from fixtures.mock_xmpp import XMPPMock

    mode = getattr(request, "param", "inbound")
    mock = XMPPMock(cert_files[0], cert_files[1], mode=mode)
    mock.start()
    yield mock
    mock.stop()