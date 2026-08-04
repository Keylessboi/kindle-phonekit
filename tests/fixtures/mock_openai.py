"""In-process OpenAI-compatible chat-completions mock for LLM scenario tests.

The real llm_server.py is launched as a subprocess and pointed at this mock,
which answers every POST /v1/chat/completions with a fixed reply so oracles are
deterministic. Failure mode: set ``reply=fail`` to make the handler return an
HTTP error, or ``refuse=True`` to accept but answer with a non-200 so the
client sees the connection fail differently.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_REPLY = "MOCK_REPLY_1"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        requests.append(raw.decode("utf-8", "replace"))

        if reply == "fail":
            # Simulate an upstream HTTP error (non-2xx after connecting).
            body = json.dumps({"error": {"message": "mock upstream exploded"}}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if refuse:
            # Simulate a connection accepted then dropped.
            self.connection.close()
            return

        payload = {"choices": [{"message": {"content": reply}}]}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


requests = []
reply = DEFAULT_REPLY
refuse = False


class MockOpenAI:
    """Context-manager mock OpenAI endpoint on an ephemeral local port."""

    def __init__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.host, self.port = self.httpd.server_address
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def url(self):
        return "http://127.0.0.1:%d/v1/chat/completions" % self.port

    def reset(self):
        requests.clear()

    def received_requests(self):
        return list(requests)