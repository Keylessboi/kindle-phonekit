"""LLM server scenario tests.

Each test drives the REAL llm_server.py subprocess over HTTP and asserts the
oracles declared in tests/scenarios/llm-*.md.
"""

import json
import os
import socket
import subprocess
import urllib.parse
import urllib.request
from http.client import HTTPConnection

import pytest

from conftest import LLM_DIR, PY, free_port, wait_http


def request(port, method, path, data=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path, body=data)
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, resp.getheaders(), raw
    finally:
        conn.close()


def get(port, path="/"):
    with urllib.request.urlopen(
            "http://127.0.0.1:%d%s" % (port, path), timeout=5) as r:
        return r.status, r.read().decode("utf-8")


def post_chat(port, msg):
    body = urllib.parse.urlencode({"msg": msg})
    return request(port, "POST", "/chat", data=body.encode("utf-8"))


def test_chat_round_trip_appends_history(llm_server):
    """LLM-CHAT-001."""
    port, upstream, _ = (llm_server["port"], llm_server["upstream"], llm_server["proc"])
    upstream.reset()

    status, headers, raw = post_chat(port, "hello kindle")
    page = raw.decode("utf-8")

    # 1. HTTP 200 text/html.
    assert status == 200
    ct = dict(headers).get("Content-Type", "")
    assert "text/html" in ct

    # 2. User turn rendered.
    assert "<b>You:</b> hello kindle" in page

    # 3. AI turn with the fixed upstream reply rendered.
    assert "<b>AI:</b> MOCK_REPLY_1" in page

    # 4. A fresh GET / still shows both turns (history persisted).
    _, page2 = get(port, "/")
    assert "<b>You:</b> hello kindle" in page2
    assert "<b>AI:</b> MOCK_REPLY_1" in page2

    # 5. Upstream received exactly one request with the right model + message.
    reqs = upstream.received_requests()
    assert len(reqs) == 1
    payload = json.loads(reqs[0])
    assert payload["model"] == "test-model"
    msgs = payload["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "You are a tiny deterministic test system prompt."
    assert any(m.get("role") == "user" and m.get("content") == "hello kindle"
               for m in msgs)


def test_chat_empty_message_redirects(llm_server):
    """LLM-CHAT-002."""
    port, upstream, _ = (llm_server["port"], llm_server["upstream"], llm_server["proc"])
    upstream.reset()

    status, headers, _ = request(port, "POST", "/chat", data=b"msg=")
    assert status == 303
    assert dict(headers).get("Location") == "/"

    # No upstream call.
    assert upstream.received_requests() == []

    # History unchanged (no turns).
    _, page = get(port, "/")
    assert "<b>You:</b>" not in page
    assert "<b>AI:</b>" not in page


def test_clear_resets_history(llm_server):
    """LLM-CLEAR-001."""
    port, upstream, _ = (llm_server["port"], llm_server["upstream"], llm_server["proc"])
    upstream.reset()

    # First build some history.
    post_chat(port, "hello kindle")
    _, before = get(port, "/")
    assert "<b>You:</b> hello kindle" in before

    status, headers, _ = request(port, "GET", "/clear")
    assert status == 303
    assert dict(headers).get("Location") == "/"

    _, after = get(port, "/")
    assert "<b>You:</b>" not in after
    assert "<b>AI:</b>" not in after
    # Model badge header still present (system state intact).
    assert "test-model" in after


def test_chat_upstream_failure_rolls_back():
    """LLM-CHAT-003.

    Spin a fresh server pointed at a closed (refusing) port so every chat
    completion raises a URLError. The failed user turn must not be retained in
    history.
    """
    dead_port = free_port()
    # Close the socket we just freed to guarantee refusal.
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    refused = s.getsockname()[1]
    s.close()

    env = dict(os.environ)
    env.update({
        "PK_LLM_API_URL": "http://127.0.0.1:%d/v1/chat/completions" % refused,
        "PK_LLM_MODEL": "test-model",
        "PK_LLM_PORT": str(dead_port),
        "PK_LLM_API_KEY": "",
    })
    proc = subprocess.Popen(
        [PY, "llm_server.py"],
        cwd=LLM_DIR, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        assert wait_http(dead_port), "llm_server.py did not come up"

        status, headers, raw = post_chat(dead_port, "will fail")
        assert status == 200
        fail_page = raw.decode("utf-8")

        # Oracle 2: the page shows an error fragment (URLError / refuse).
        assert "URLError" in fail_page or "Connection refused" in fail_page

        # Refresh page: the failed user turn must NOT be rendered.
        _, page = get(dead_port, "/")
        assert "<b>You:</b> will fail" not in page
        assert "<b>AI:</b>" not in page
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()