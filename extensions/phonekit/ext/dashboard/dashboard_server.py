#!/usr/bin/env python3
"""PhoneKit dashboard.

Renders a glanceable, schedule-refreshable dashboard to the Kindle's
Experimental Browser at http://127.0.0.1:<port>. The browser only talks to this
server, which is the ONLY thing that ever reaches the network. All networking is
stdlib (urllib) so nothing extra needs installing on-device.

Configuration comes from environment variables set by start.sh (which sources
config.env):

    PK_DASH_PORT   local port to listen on (default 8084)
    PK_DASH_URL    optional external JSON data source (home-lab endpoint).
                   May be empty, in which case the clock/date panels still
                   render with a small "no data" hint.
    PK_DASH_NAME   short label shown at the top, e.g. "homelab"

The external feed is any JSON the user's own server exposes. Both of these are
understood and rendered as a small title/value/status list:

    {"uptime": "3d 4h", "disk": {"value": "71%", "status": "warn"}, "temp": "52C"}
    [{"title": "uptime", "value": "3d 4h"}, {"title": "temp", "value": "52C"}]

SCHEDULED REFRESH / the WiFi-sleep killer
------------------------------------------
The Kindle drops WiFi when it sleeps, and does not let the browser wake it up on
a timer. So the dashboard never trusts the browser to drive a schedule. Instead
an OUT-OF-BAND wake re-arms the screen and re-renders:

  * /render       renders the current cached feed (does not touch the network).
  * /refresh      re-fetches the external JSON into the cache, then re-renders.
  * /health       returns literal "ok" for a cheap poll.

To refresh on a cron schedule, point a device-side timer at the server. Two
common Kindle-isms:

  1) lipc via the standard freeze/unfreeze wake (pcmond pattern). A small
     watchdog in start.sh would do, per tick:
         lipc-set-prop com.lab126.powerd preventingSuspend 1   # wake
         lipc-set-prop com.lab126.appmgrd start app://com.lab126.browser
         lipc-set-prop com.lab126.browser url "http://127.0.0.1:8084/refresh"
         lipc-set-prop com.lab126.powerd preventingSuspend 0    # re-arm sleep
  2) Or a crontab entry (busybox crond) that curls the refresh URL:
         0 * * * *  sh -c 'curl -s http://127.0.0.1:8084/refresh >/dev/null && \\
             eips 0 0 "dashboard refreshed"'
  Either wakes the screen, triggers a fresh render, and the browser shows the
  updated page. The user never has to touch a button.
"""

import http.server
import json
import os
import time
import urllib.error
import urllib.request

HOST = "127.0.0.1"
PORT = int(os.environ.get("PK_DASH_PORT", "8084"))
SOURCE_URL = os.environ.get("PK_DASH_URL", "")
NAME = os.environ.get("PK_DASH_NAME", "homelab")
FETCH_TIMEOUT = 15

CACHE_DATA = None  # parsed external JSON; None until the first good fetch
CACHE_AT = ""
CACHE_WARN = ""
PENDING_WARN = ""  # newest fetch outcome, shown above stale cache


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def extract_entries(data):
    """Flatten a fetched JSON value into (title, value, status) triples."""
    out = []

    def push(title, value):
        status = ""
        if isinstance(value, dict):
            status = value.get("status", "")
            inner = value.get("value")
            value = inner if inner is not None else value
        out.append((str(title), fmt(value), str(status)))

    if isinstance(data, dict):
        for key, value in data.items():
            push(key, value)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                title = item.get("title") or item.get("label") or "item"
                push(title, item.get("value", ""))
            else:
                out.append((fmt(item), "", ""))
    else:
        out.append((fmt(data), "", ""))
    return out


def refresh_source():
    """Re-fetch the configured feed into the cache. Safe for any failure."""
    global CACHE_DATA, CACHE_AT, CACHE_WARN, PENDING_WARN
    if not SOURCE_URL:
        PENDING_WARN = "no data source (PK_DASH_URL unset)"
        return
    try:
        with urllib.request.urlopen(SOURCE_URL, timeout=FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        CACHE_DATA = data
        CACHE_AT = time.strftime("%H:%M  %a %d %b %Y")
        CACHE_WARN = ""
        PENDING_WARN = ""
    except urllib.error.URLError as err:
        PENDING_WARN = "source unreachable: %s" % (err.reason,)
    except Exception as err:
        PENDING_WARN = "%s: %s" % (type(err).__name__, err)


def render():
    now = time.localtime()
    clock = time.strftime("%H:%M:%S", now)
    date = time.strftime("%A %d %B %Y", now)

    top = "<h1 style=\"font-size:42px\">%s</h1>\n" % esc(clock)
    top += "<p><b>%s</b> &middot; %s</p>\n" % (esc(NAME), esc(date))

    lines = []
    if CACHE_DATA is not None:
        for title, value, status in extract_entries(CACHE_DATA):
            cell = "<b>%s:</b> %s" % (esc(title), esc(value))
            if status:
                cell += " <i>[%s]</i>" % esc(status)
            lines.append("<p>%s</p>" % cell)

    if CACHE_WARN:
        lines.append("<p style=\"color:#a00\">%s</p>" % esc(CACHE_WARN))
    if PENDING_WARN:
        lines.append("<p style=\"color:#a00\">no data now: %s</p>" % esc(PENDING_WARN))
    elif not lines:
        lines.append("<p style=\"color:#888\">no data yet &mdash; hit /refresh</p>")
    if CACHE_AT:
        lines.append("<p style=\"color:#888\">updated %s</p>" % esc(CACHE_AT))

    links = "<p>[ <a href=\"/refresh\">refresh feed</a> | <a href=\"/\">home</a> ]</p>"

    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Dashboard</title>\n"
        "<style>body{font-family:sans-serif;margin:12px}"
        "h1,h2{margin:0 0 4px}p{margin:4px 0;font-size:20px}</style></head>\n"
        "<body>\n%s%s%s\n</body></html>"
    ) % (top, "".join(lines), links)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _page(self, body, ctype="text/html; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        if self.path in ("/health", "/healthz"):
            self._page("ok", "text/plain; charset=utf-8")
        elif self.path in ("/refresh", "/refresh-render"):
            refresh_source()
            self._page(render())
        elif self.path in ("/", "/render"):
            # render current cache immediately (no network on this path)
            if CACHE_DATA is None and not PENDING_WARN:
                refresh_source()  # prime the cache on first hit
            self._page(render())
        else:
            self.send_error(404)


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()