#!/usr/bin/env python3
"""PhoneKit Notes + Todo.

Runs a tiny HTTP server on the Kindle that serves a minimal e-ink notes/todo
page to the Experimental Browser at http://127.0.0.1:8083. All Notes and Todos
live in a single plaintext file so they survive a reboot; the lists are rebuilt
from the file on every request, never kept in memory only.

Configuration comes from environment variables set by start.sh (which sources
config.env):

    PK_NOTES_FILE   plaintext data file (default /mnt/us/phonekit/notes.txt)
    PK_NOTES_PORT   local port to listen on (default 8083)

If the configured file cannot be written at runtime (for example /mnt/us is
missing on a dev machine), the server falls back to a local ./notes.txt next
to this script and logs which path it actually used.

The data file is simple lines, each prefixed with a marker:

    TODO  <text>   an unfinished todo item
    DONE  <text>   a crossed-off todo item
    NOTE  <text>   a saved note

A line's 0-based index in the file is its id, so toggle/delete routes re-read
the file and address lines by position; nothing is cached in memory.
"""

import http.server
import os
import sys
import urllib.parse

HOST = "127.0.0.1"
PORT = int(os.environ.get("PK_NOTES_PORT", "8083"))
LOCAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.txt")
DEFAULT_FILE = "/mnt/us/phonekit/notes.txt"
DATA_FILE = os.environ.get("PK_NOTES_FILE", DEFAULT_FILE)


def esc(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def ensure_file(path):
    """Make sure `path` is writable, creating parent dirs, else False."""
    directory = os.path.dirname(path)
    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "a", encoding="utf-8"):
            pass
        return True
    except OSError:
        return False


def read_lines():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def write_lines(lines):
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        if lines:
            fh.write("\n")


def parse(lines):
    """Return (notes, todos, done), each [(line_no, text), ...]."""
    notes, todos, done = [], [], []
    for i, line in enumerate(lines):
        if line.startswith("TODO: "):
            todos.append((i, line[len("TODO: ") :]))
        elif line.startswith("DONE: "):
            done.append((i, line[len("DONE: ") :]))
        elif line.startswith("NOTE: "):
            notes.append((i, line[len("NOTE: ") :]))
    return notes, todos, done


def delete_line(line_no):
    lines = read_lines()
    if 0 <= line_no < len(lines):
        lines.pop(line_no)
        write_lines(lines)


def toggle_line(line_no):
    lines = read_lines()
    if not (0 <= line_no < len(lines)):
        return
    line = lines[line_no]
    if line.startswith("TODO: "):
        lines[line_no] = "DONE: " + line[len("TODO: ") :]
    elif line.startswith("DONE: "):
        lines[line_no] = "TODO: " + line[len("DONE: ") :]
    else:
        return
    write_lines(lines)


def append_line(marker, text):
    lines = read_lines()
    lines.append("%s: %s" % (marker, text))
    write_lines(lines)


def render(message=None):
    notes, todos, done = parse(read_lines())

    error = ""
    if message:
        error = '<p style="color:#a00">%s</p>' % esc(message)

    trows = []
    for line_no, text in todos:
        trows.append(
            '<p><a href="/done?id=%d">&#9744;</a> %s '
            '<a href="/del-todo?id=%d">[del]</a></p>'
            % (line_no, esc(text), line_no)
        )
    for line_no, text in done:
        trows.append(
            '<p><a href="/done?id=%d">&#9745;</a> <s>%s</s> '
            '<a href="/del-todo?id=%d">[del]</a></p>'
            % (line_no, esc(text), line_no)
        )
    todos_html = "".join(trows) or "<p><i>Nothing here.</i></p>"

    nrows = ""
    for line_no, text in notes:
        nrows += (
            '<p>%s <a href="/del-note?id=%d">[del]</a></p>'
            % (esc(text), line_no)
        )
    notes_html = nrows or "<p><i>No notes yet.</i></p>"

    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Notes</title></head>\n"
        "<body style=\"font-family:sans-serif;margin:8px\">\n"
        "<h3>Todo</h3>\n%s%s\n"
        "<form method=\"post\" action=\"/add-todo\">\n"
        "<input type=\"text\" name=\"item\" style=\"width:80%%\"> "
        "<input type=\"submit\" value=\"Add\">\n"
        "</form>\n"
        "<h3>Notes</h3>\n%s\n"
        "<form method=\"post\" action=\"/add-note\">\n"
        "<textarea name=\"note\" rows=\"4\" style=\"width:100%%\"></textarea>\n"
        "<p><input type=\"submit\" value=\"Save\"> "
        "<a href=\"/\">Refresh</a></p>\n"
        "</form>%s</body></html>"
    ) % (error, todos_html, notes_html, "")


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
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if not query.get("id"):
            self._page()
            return
        try:
            line_no = int(query["id"][0])
        except ValueError:
            line_no = -1
        if parsed.path == "/done":
            toggle_line(line_no)
        elif parsed.path in ("/del-todo", "/del-note"):
            delete_line(line_no)
        else:
            self._page()
            return
        self._redirect("/")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", "replace")
        fields = urllib.parse.parse_qs(raw)
        if self.path == "/add-todo":
            text = "".join(fields.get("item", [])).strip()
            if text:
                append_line("TODO", text)
        elif self.path == "/add-note":
            text = "".join(fields.get("note", [])).strip()
            if text:
                append_line("NOTE", text)
        self._redirect("/")


if __name__ == "__main__":
    if not ensure_file(DATA_FILE):
        # Fall back to a local file that is guaranteed writable, and say so.
        DATA_FILE = LOCAL_FILE
        ensure_file(DATA_FILE)
        print("PK_NOTES_FILE not writable; using %s" % LOCAL_FILE, file=sys.stderr)
    print("notes data file: %s" % DATA_FILE, file=sys.stderr)
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()