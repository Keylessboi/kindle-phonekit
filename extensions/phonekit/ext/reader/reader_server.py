#!/usr/bin/env python3
"""PhoneKit read-it-later.

Runs a tiny HTTP server on the Kindle that serves a minimal reading page to the
Experimental Browser at http://127.0.0.1:8081. Paste a URL, the server fetches
it, strips the page down to clean readable text, and keeps a small inbox on
disk so articles survive a reboot. Nothing is ever written back to the source
site; only the target URL is contacted.

Configuration comes from environment variables set by start.sh (which sources
config.env):

    PK_RIL_PORT     local port to listen on (default 8081)
    PK_RIL_API_URL  optional OpenAI-compatible chat completions endpoint
    PK_RIL_API_KEY  optional bearer token for that endpoint
    PK_RIL_MODEL    model name to request

When PK_RIL_API_URL is empty the /summarize button is hidden entirely, so the
summary feature degrades gracefully on devices with no API configured.
"""

import http.server
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "127.0.0.1"
PORT = int(os.environ.get("PK_RIL_PORT", "8081"))
API_URL = os.environ.get("PK_RIL_API_URL", "")
API_KEY = os.environ.get("PK_RIL_API_KEY", "")
MODEL = os.environ.get("PK_RIL_MODEL", "qwen2.5:7b-instruct")
SUMMARY_SYS = (
    "You summarize articles for an e-ink Kindle reader. "
    "Reply with exactly 5 bullet lines, each under 60 words, no preamble."
)
INBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inbox.json")
FETCH_TIMEOUT = 20
MAX_RAW = 1 << 20  # never read more than 1 MB of page source
MAX_TEXT = 30000  # cap cleaned text so the rendered page stays small

STORE = {"next_id": 1, "items": []}


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_store():
    global STORE
    try:
        with open(INBOX, "r", encoding="utf-8") as fh:
            STORE = json.load(fh)
    except (IOError, ValueError):
        STORE = {"next_id": 1, "items": []}


def save_store():
    try:
        with open(INBOX, "w", encoding="utf-8") as fh:
            json.dump(STORE, fh, ensure_ascii=False)
    except IOError:
        pass


def get_item(item_id):
    for item in STORE["items"]:
        if item["id"] == item_id:
            return item
    return None


def strip_html(raw):
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    title = ""
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    if match:
        title = re.sub(r"\s+", " ", html_unescape(match.group(1))).strip()
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|blockquote)>", "\n", text)
    text = re.sub(r"(?i)<h[1-6][^>]*>", "\n\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = text.strip()[:MAX_TEXT]
    return title or raw.split("\n")[0][:80] or "Untitled", text


def html_unescape(text):
    import html

    return html.unescape(text)


def fetch_page(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Kindle"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        data = resp.read(MAX_RAW)
    charset = resp.headers.get_content_charset() or "utf-8"
    return data.decode(charset, "replace")


def chat_completion(prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SUMMARY_SYS},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = "Bearer " + API_KEY
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def layout(title, inner):
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title></head>\n"
        "<body style=\"font-family:sans-serif;margin:8px;"
        "font-size:18px;line-height:1.6\">\n%s\n</body></html>"
    ) % (esc(title), inner)


def page_index(message=None):
    error = ""
    if message:
        error = '<p style="color:#a00">%s</p>' % esc(message)
    return layout(
        "Read It Later",
        "<h3>Read It Later</h3>\n%s\n"
        "<form method=\"post\" action=\"/add\">\n"
        "<p><input type=\"text\" name=\"url\" size=\"40\" "
        "value=\"https://\"></p>\n"
        "<p><input type=\"submit\" value=\"Save\"> "
        "<a href=\"/list\">Inbox</a></p>\n"
        "</form>" % error,
    )


def page_list(message=None):
    items = sorted(STORE["items"], key=lambda i: i["id"], reverse=True)
    rows = []
    if not items:
        rows.append("<p>Inbox is empty. <a href=\"/\">Add a URL</a>.</p>")
    for item in items:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["ts"]))
        rows.append(
            "<p><a href=\"/read?id=%d\">%s</a>"
            "<br><small>%s &middot; <a href=\"/delete?id=%d\">delete</a>"
            "</small></p>" % (item["id"], esc(item["title"]), when, item["id"])
        )
    notice = ""
    if message:
        notice = '<p style="color:#a00">%s</p>' % esc(message)
    return layout(
        "Inbox",
        "<h3>Inbox (%d)</h3>\n%s%s\n<p><a href=\"/\">Add a URL</a></p>"
        % (len(STORE["items"]), notice, "".join(rows)),
    )


def page_read(item, message=None):
    summary = ""
    if item.get("summary"):
        summary = "<h4>Summary</h4>\n<p>%s</p>\n" % (
            "<br>".join(esc(line) for line in item["summary"].splitlines())
        )
    notice = ""
    if message:
        notice = '<p style="color:#a00">%s</p>' % esc(message)
    paras = "".join(
        "<p>%s</p>\n" % esc(para)
        for para in re.split(r"\n\s*\n", item["text"].strip())
        if para.strip()
    )
    buttons = ['<a href="/delete?id=%d">Delete</a> <a href="/list">Inbox</a>'
               % item["id"]]
    if API_URL:
        buttons.append(
            '<form method="post" action="/summarize" style="display:inline">'
            '<input type="hidden" name="id" value="%d">'
            '<input type="submit" value="Summarize"></form>' % item["id"]
        )
    return layout(
        item["title"],
        "<h3>%s</h3>\n%s%s%s<p>%s</p>\n"
        % (
            esc(item["title"]),
            summary,
            notice,
            paras,
            " ".join(buttons),
        ),
    )


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def _page(self, body):
        payload = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _field(self, raw, name):
        match = re.search(r"(?:^|&)" + name + r"=([^&]*)", raw)
        return urllib.parse.unquote_plus(match.group(1)).strip() if match else ""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/list":
            self._page(page_list())
            return
        if parsed.path == "/read":
            item_id = self._field(parsed.query, "id")
            item = get_item(int(item_id)) if item_id.isdigit() else None
            if item is None:
                self._page(page_list(message="Item not found."))
            else:
                self._page(page_read(item))
            return
        if parsed.path == "/delete":
            item_id = self._field(parsed.query, "id")
            if item_id.isdigit():
                STORE["items"] = [i for i in STORE["items"] if i["id"] != int(item_id)]
                save_store()
            self._redirect("/list")
            return
        self._page(page_index())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", "replace")
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/add":
            url = self._field(raw, "url")
            if not url.startswith("http://") and not url.startswith("https://"):
                self._page(page_index(message="Enter a full http(s) URL."))
                return
            try:
                title, text = strip_html(fetch_page(url))
                item = {
                    "id": STORE["next_id"],
                    "url": url,
                    "title": title,
                    "text": text,
                    "ts": int(time.time()),
                }
                STORE["next_id"] += 1
                STORE["items"].append(item)
                save_store()
                self._redirect("/read?id=%d" % item["id"])
            except urllib.error.HTTPError as err:
                self._page(page_index(message="HTTP %s from site." % err.code))
            except urllib.error.URLError as err:
                self._page(page_index(message="Could not reach site: %s" % err.reason))
            except Exception as err:
                self._page(
                    page_index(message="%s: %s" % (type(err).__name__, err))
                )
            return
        if parsed.path == "/summarize":
            if not API_URL:
                self._redirect("/list")
                return
            item_id = self._field(raw, "id")
            item = get_item(int(item_id)) if item_id.isdigit() else None
            if item is None:
                self._redirect("/list")
                return
            try:
                item["summary"] = chat_completion(item["text"][:8000])
                save_store()
                self._redirect("/read?id=%d" % item["id"])
            except urllib.error.HTTPError as err:
                self._page(page_read(item, message="Summary failed: HTTP %s" % err.code))
            except Exception as err:
                self._page(
                    page_read(
                        item,
                        message="Summary failed: %s: %s"
                        % (type(err).__name__, err),
                    )
                )
            return
        self._redirect("/")


if __name__ == "__main__":
    load_store()
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
