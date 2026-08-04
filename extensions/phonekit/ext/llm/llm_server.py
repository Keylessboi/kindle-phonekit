#!/usr/bin/env python3
"""PhoneKit LLM bridge.

Runs a tiny HTTP server on the Kindle that serves a minimal chat page to the
Experimental Browser at http://127.0.0.1:8080. The browser only talks to this
server; this server talks to any OpenAI-compatible endpoint. The API key and
endpoint live on-device, and nothing except the API itself is ever contacted.

Configuration comes from environment variables set by start.sh (which sources
config.env):

    PK_LLM_API_URL   OpenAI-compatible chat completions endpoint
    PK_LLM_API_KEY   optional bearer token
    PK_LLM_MODEL     model name to request
    PK_LLM_SYSTEM    system prompt
    PK_LLM_PORT      local port to listen on (default 8080)
"""

import http.server
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

HOST = "127.0.0.1"
PORT = int(os.environ.get("PK_LLM_PORT", "8080"))
API_URL = os.environ.get(
    "PK_LLM_API_URL", "http://127.0.0.1:11434/v1/chat/completions"
)
API_KEY = os.environ.get("PK_LLM_API_KEY", "")
MODEL = os.environ.get("PK_LLM_MODEL", "local-model")
SYSTEM = os.environ.get(
    "PK_LLM_SYSTEM",
    "You are a helpful assistant running on an e-ink Kindle. "
    "Keep answers short and skimmable.",
)

HISTORY = [{"role": "system", "content": SYSTEM}]
MAX_TURNS = 12  # keep the rendered page small for e-ink


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def visible_history():
    turns = [m for m in HISTORY if m["role"] != "system"]
    return turns[-MAX_TURNS:]


def trim_history():
    # Keep the system prompt plus at most MAX_TURNS*2 recent turns.
    if len(HISTORY) > 1 + MAX_TURNS * 2:
        del HISTORY[1 : len(HISTORY) - MAX_TURNS * 2]


def render(message=None):
    body = []
    for m in visible_history():
        who = "You" if m["role"] == "user" else "AI"
        body.append("<p><b>%s:</b> %s</p>" % (who, esc(m["content"])))
    error = ""
    if message:
        error = '<p style="color:#a00">%s</p>' % esc(message)
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>LLM</title></head>\n"
        "<body style=\"font-family:sans-serif;margin:8px\">\n"
        "<h3>LLM &middot; %s</h3>\n%s%s\n"
        "<form method=\"post\" action=\"/chat\">\n"
        "<textarea name=\"msg\" rows=\"4\" style=\"width:100%%\"></textarea>\n"
        "<p><input type=\"submit\" value=\"Send\"> "
        "<a href=\"/clear\">Clear</a> <a href=\"/\">Refresh</a></p>\n"
        "</form></body></html>"
    ) % (esc(MODEL), error, "".join(body))


def chat_completion(messages):
    payload = {"model": MODEL, "messages": messages, "stream": False}
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = "Bearer " + API_KEY
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def _page(self, message=None):
        body = render(message).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/clear":
            del HISTORY[1:]  # keep the system prompt
            self._redirect("/")
            return
        self._page()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", "replace")
        match = re.search(r"(?:^|&)msg=([^&]*)", raw)
        msg = urllib.parse.unquote_plus(match.group(1)) if match else ""
        msg = msg.strip()
        if not msg:
            self._redirect("/")
            return
        HISTORY.append({"role": "user", "content": msg})
        error = None
        try:
            reply = chat_completion(HISTORY)
            HISTORY.append({"role": "assistant", "content": reply})
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:300]
            try:
                detail = json.loads(detail)["error"]["message"]
            except Exception:
                pass
            error = "Endpoint error HTTP %s: %s" % (err.code, detail)
            HISTORY.pop()  # undo the failed user turn so retry is clean
        except Exception as err:
            error = "%s: %s" % (type(err).__name__, err)
            HISTORY.pop()
        trim_history()
        self._page(message=error)


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
