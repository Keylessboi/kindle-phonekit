#!/usr/bin/env python3
"""PhoneKit feed reader.

Runs a tiny HTTP server on the Kindle that serves an RSS/Atom reader to the
Experimental Browser at http://127.0.0.1:8082. The built-in browser is the only
input; there is no audio, GPU, or touch, so every page is minimal HTML with a
large font, generous line-height, and no JavaScript or images.

The server reads the feed list from feeds.txt (one URL per line, lines starting
with "#" are ignored), fetches each feed with urllib, parses the items with
xml.etree.ElementTree, and caches them in cache.json next to this file. Nothing
but those two files and the on-device network is ever touched.

HOW TO ADD FEEDS
----------------
Add a feed by one of two ways:

  1. Edit feeds.txt, starting a new line with a feed URL (RSS 2.0 or Atom),
     e.g.:

        https://news.ycombinator.com/rss
        https://www.theverge.com/rss/index.xml

  2. From the web UI: open the home page, tap "Add feed", enter a URL, and
     submit. The URL is appended to feeds.txt.

Either way, hit "Refresh now" (GET /refresh) to fetch and cache the new feed
before it appears with items.

Configuration comes from environment variables set by start.sh (which sources
config.env):

    PK_FEED_PORT       local port to listen on (default 8082)
    PK_FEED_TIMEOUT    per-feed fetch timeout in seconds (default 20)
    PK_FEED_FEEDS      path to the feed list file (default: feeds.txt beside
                       this file)
    PK_FEED_CACHE      path to the JSON cache file (default: cache.json beside
                       this file)

If an https feed cannot be fetched (old device CA store, flaky TLS) the server
retries that feed over plain http once before reporting an error.
"""

import html
import html.parser
import http.server
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HOST = "127.0.0.1"
PORT = int(os.environ.get("PK_FEED_PORT", "8082"))
FETCH_TIMEOUT = int(os.environ.get("PK_FEED_TIMEOUT", "20"))
_BASE = os.path.dirname(os.path.abspath(__file__))
FEEDS_FILE = os.environ.get("PK_FEED_FEEDS", os.path.join(_BASE, "feeds.txt"))
CACHE_FILE = os.environ.get("PK_FEED_CACHE", os.path.join(_BASE, "cache.json"))
USER_AGENT = "PhoneKit-FeedReader/1.0"
MAX_ITEMS = 50  # keep the cached item list small for e-ink


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_feeds():
    """Return the list of configured feed URLs from feeds.txt."""
    try:
        with open(FEEDS_FILE, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if not line.lstrip().startswith("#")]
        return [u for u in urls if u]
    except OSError:
        return []


def add_feed(url):
    """Append url to feeds.txt unless present. Returns True when a feed is added."""
    if url in load_feeds():
        return False
    content = ""
    if os.path.exists(FEEDS_FILE):
        with open(FEEDS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    with open(FEEDS_FILE, "a", encoding="utf-8") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        f.write(url + "\n")
    return True


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(cache):
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, CACHE_FILE)


def fetch_raw(url):
    """Fetch url's bytes, retrying once over http if https fails."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as resp:
            return resp.read()
    except (urllib.error.URLError, ssl.SSLError):
        if not url.startswith("https://"):
            raise
        fallback_url = "http://" + url[len("https://"):]
        request = urllib.request.Request(
            fallback_url, headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as resp:
            return resp.read()


def localname(tag):
    return tag.rsplit("}", 1)[-1]


def child_text(node, name):
    for child in node:
        if localname(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def child_link(node):
    """Best link/local-name href for an <item> or <entry>."""
    best = ""
    for child in node:
        if localname(child.tag) != "link":
            continue
        if child.get("rel") == "alternate":
            href = child.get("href")
            if href:
                return href.strip()
        if child.text and child.text.strip():
            best = child.text.strip()
        elif not best and child.get("href"):
            best = child.get("href").strip()
    return best


def feed_title(root):
    """The feed/channel title: the first <title> in document order."""
    for node in root.iter():
        if localname(node.tag) == "title" and node.text:
            return node.text.strip()
    return ""


def feed_items(root):
    items = []
    for node in root.iter():
        if localname(node.tag) not in ("item", "entry"):
            continue
        desc = child_text(node, "description")
        if not desc:
            desc = child_text(node, "summary")
        if not desc:
            desc = child_text(node, "content")
        if not desc:
            desc = child_text(node, "encoded")
        items.append(
            {
                "title": child_text(node, "title") or "(untitled)",
                "link": child_link(node),
                "desc": desc,
            }
        )
    return items


def refresh_one(url):
    try:
        root = ET.fromstring(fetch_raw(url))
    except urllib.error.HTTPError as err:
        return {"title": "", "items": [], "error": "HTTP %s" % err.code}
    except urllib.error.URLError as err:
        return {"title": "", "items": [], "error": "net: %s" % err.reason}
    except ssl.SSLError as err:
        return {"title": "", "items": [], "error": "ssl: %s" % err}
    except ET.ParseError as err:
        return {"title": "", "items": [], "error": "parse: %s" % err}
    except Exception as err:
        return {"title": "", "items": [], "error": "%s: %s" % (type(err).__name__, err)}
    return {"title": feed_title(root), "items": feed_items(root)[:MAX_ITEMS], "error": None}


def refresh_all():
    cache = {}
    for url in load_feeds():
        cache[url] = refresh_one(url)
    save_cache(cache)
    return cache


class _TextExtractor(html.parser.HTMLParser):
    """Collect visible text from an HTML fragment, preserving blank lines."""

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)


def clean_html(raw):
    """Turn an HTML description/summary into plain paragraphs of text."""
    if not raw:
        return ""
    extractor = _TextExtractor()
    extractor.feed(raw)
    text = "".join(extractor._parts)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return text


def page(body, title="Feed Reader"):
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>%s</title></head>\n"
        "<body style=\"font-family:sans-serif;margin:8px;font-size:18px;"
        "line-height:1.6\">\n"
        "%s\n</body></html>"
    ) % (esc(title), body)


def nav(*links):
    return " &middot; ".join('<a href="%s">%s</a>' % (esc(href), esc(label)) for label, href in links)


def home_page(cache):
    urls = load_feeds()
    rows = []
    for idx, url in enumerate(urls, 1):
        entry = cache.get(url, {})
        count = len(entry.get("items", []))
        title = html.unescape(entry.get("title") or url)
        if entry.get("error"):
            meta = '<span style="color:#a00">error: %s</span>' % esc(entry["error"])
        else:
            meta = "%d items%s" % (count, " (not refreshed)" if not entry else "")
        rows.append(
            '<p><a href="/feed?id=%d"><b>%s</b></a><br><small>%s</small></p>'
            % (idx, esc(title), meta)
        )
    list_html = "".join(rows) if rows else '<p>No feeds configured. <a href="/add">Add one.</a></p>'
    body = "<h3>Feeds</h3>\n" + nav(("Refresh now", "/refresh"), ("Add feed", "/add")) + "\n"
    return page(body + list_html, "Feeds")


def feed_page(cache, idx, urls):
    try:
        url = urls[idx - 1]
    except IndexError:
        return page('<p>No such feed. <a href="/">Back to feeds</a>.</p>', "Feed")
    entry = cache.get(url, {})
    items = entry.get("items", [])
    title = html.unescape(entry.get("title") or url)
    if entry.get("error"):
        error = '<p style="color:#a00">Error: %s</p>\n' % esc(entry["error"])
    else:
        error = ""
    rows = [
        '<p><a href="/read?id=%d&amp;i=%d">%s</a></p>'
        % (idx, m, esc(html.unescape(item.get("title", "(untitled)"))))
        for m, item in enumerate(items, 1)
    ]
    if not items:
        rows.append('<p>No items yet. <a href="/refresh">Refresh feeds.</a></p>')
    body = "<h3>%s</h3>\n" % esc(title)
    body += nav(("Back to feeds", "/"), ("Refresh now", "/refresh")) + "\n" + error
    return page(body + "".join(rows), title)


ADD_FORM = (
    "<h3>Add a feed</h3>\n"
    "<p>Enter the URL of an RSS or Atom feed and submit:</p>\n"
    '<form method="get" action="/add">\n'
    '<input type="text" name="url" size="40" style="width:100%%">\n'
    '<p><input type="submit" value="Add feed"> <a href="/">Cancel</a></p>\n'
    "</form>\n"
)


def add_page(raw_url):
    url = urllib.parse.unquote_plus(raw_url or "").strip()
    if not url:
        return page(ADD_FORM, "Add feed")
    if not re.match(r"^https?://", url):
        body = '<p>Invalid URL (must start with http:// or https://). <a href="/add">Try again.</a></p>'
        return page(body, "Add feed")
    added = add_feed(url)
    note = "Added" if added else "Already configured"
    body = (
        '<p><b>%s:</b> %s</p>\n'
        '<p><a href="/refresh">Refresh now</a> &middot; <a href="/">Back to feeds</a></p>'
        % (note, esc(url))
    )
    return page(body, "Feed added")


def read_page(cache, idx, item_no, urls):
    try:
        url = urls[idx]
        item = cache.get(url, {}).get("items", [])[item_no - 1]
    except (IndexError, TypeError):
        return page('<p>Item not found. <a href="/">Back to feeds</a>.</p>', "Item")
    title = html.unescape(item.get("title", "(untitled)"))
    paras = [esc(p) for p in clean_html(item.get("desc", "")).split("\n\n")]
    body = "<h3>%s</h3>\n" % esc(title)
    body += nav(("Back to feed", "/feed?id=%d" % (idx + 1)), ("Feeds", "/")) + "\n"
    if item.get("link"):
        body += '<p><a href="%s">Open original</a></p>\n' % esc(item["link"])
    if paras:
        body += "".join("<p>%s</p>" % p for p in paras)
    else:
        body += "<p><i>(no description)</i></p>"
    return page(body, title)


def _int(qs, key, default):
    try:
        return int(qs.get(key, ["0"])[0])
    except ValueError:
        return default


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def _page(self, body):
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        path = parsed.path
        if path == "/refresh":
            refresh_all()
            self._redirect("/")
        elif path == "/feed":
            urls = load_feeds()
            self._page(feed_page(load_cache(), _int(qs, "id", 1), urls))
        elif path == "/read":
            urls = load_feeds()
            self._page(
                read_page(
                    load_cache(),
                    _int(qs, "id", 1) - 1,
                    _int(qs, "i", 1),
                    urls,
                )
            )
        elif path == "/add":
            self._page(add_page(qs.get("url", [""])[0]))
        else:
            self._page(home_page(load_cache()))


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()