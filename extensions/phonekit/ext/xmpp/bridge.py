#!/usr/bin/env python3
"""PhoneKit XMPP bridge (experimental).

A dependency-free XMPP client (Python standard library only) for a jailbroken
Kindle.

Listen mode (default): connect to your account, then log every incoming chat
message to /tmp/phonekit_xmpp.txt and flash new ones on the e-ink screen.

Send mode: python3 bridge.py send <jid> <message>

Configuration via environment variables (see xmpp/config.env):
    PK_XMPP_JID        user@server
    PK_XMPP_PASS       password
    PK_XMPP_HOST       server host (default: JID domain)
    PK_XMPP_PORT       port (default 5222)
    PK_XMPP_NO_VERIFY  1 to skip TLS certificate checks (self-signed servers)

Notes:
  * Uses SASL SCRAM-SHA-1 when offered, PLAIN as a fallback.
  * SASLprep is not implemented; plain UTF-8 passwords work with most servers.
    For exotic passwords, prefer a normal client.
  * The socket is read with raw recv() plus a hand-rolled XML scanner.  Never
    use socket.makefile() here: on Python 3.14.6 its read() blocks for the
    full socket timeout even when the OS reports readable data, which hangs
    iterparse()-based stream parsers indefinitely.
"""

import base64
import hashlib
import hmac
import os
import socket
import ssl
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

JID = os.environ.get("PK_XMPP_JID", "")
PASS = os.environ.get("PK_XMPP_PASS", "")
HOST = os.environ.get("PK_XMPP_HOST", (JID.split("@")[1] if "@" in JID else JID))
PORT = int(os.environ.get("PK_XMPP_PORT", "5222"))
POPUP = os.environ.get("PK_XMPP_POPUP", "1") == "1"
NO_VERIFY = os.environ.get("PK_XMPP_NO_VERIFY", "0") == "1"
DEBUG = os.environ.get("PK_XMPP_DEBUG", "0") == "1"


def dbg(*parts):
    if DEBUG:
        sys.stdout.write("[dbg] " + " ".join(str(p) for p in parts) + "\n")
        sys.stdout.flush()


NS_CLIENT = "jabber:client"
NS_STREAM = "http://etherx.jabber.org/streams"
NS_TLS = "urn:ietf:params:xml:ns:xmpp-tls"
NS_SASL = "urn:ietf:params:xml:ns:xmpp-sasl"
NS_BIND = "urn:ietf:params:xml:ns:xmpp-bind"
INBOX = os.environ.get("PK_XMPP_INBOX", "/tmp/phonekit_xmpp.txt")


class XMPPError(Exception):
    pass


def b64(blob):
    return base64.b64encode(blob).decode("ascii")


def b64d(text):
    return base64.b64decode(text)


def escape_sasl(text):
    # RFC 5802 username escaping (backslash first)
    return text.replace("\\", "\\5c").replace(",", "\\2c").replace("=", "\\3d")


def scram_sha1(password, c_first_bare, server_first, client_nonce, server_nonce):
    """Compute the SCRAM-SHA-1 client-final message (RFC 5802)."""
    parts = dict(p.split("=", 1) for p in server_first.split(","))
    salt = b64d(parts["s"])
    iterations = int(parts["i"])
    if not server_nonce.startswith(client_nonce):
        raise XMPPError("SASL nonce mismatch")
    salted = hashlib.pbkdf2_hmac("sha1", password.encode("utf-8"), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha1).digest()
    stored_key = hashlib.sha1(client_key).digest()
    c_final_no_proof = "c=biws,r=%s" % server_nonce
    auth_message = c_first_bare + "," + server_first + "," + c_final_no_proof
    client_signature = hmac.new(
        stored_key, auth_message.encode("utf-8"), hashlib.sha1
    ).digest()
    client_proof = bytes(a ^ b for a, b in zip(client_key, client_signature))
    return c_final_no_proof + ",p=" + b64(client_proof)


def parse_fragment(fragment):
    """Parse one complete XML element (bytes) and return its children.

    A stanza inside a stream is not a well-formed document on its own, so we
    wrap it in a synthetic root that carries the client and stream namespaces.
    """
    wrapped = (
        b"<_root xmlns='" + NS_CLIENT.encode("ascii") + b"' "
        b"xmlns:stream='" + NS_STREAM.encode("ascii") + b"'>"
        + fragment
        + b"</_root>"
    )
    return list(ET.fromstring(wrapped))


class StreamReader:
    """Buffered reader that yields complete XML elements from raw recv().

    Everything here uses raw socket.recv() and byte scanning.  socket.makefile()
    is deliberately avoided: on Python 3.14.6 its read() blocks for the full
    socket timeout even when select() reports readable data, which hangs
    iterparse()-based stream parsers indefinitely.
    """

    _WS = b" \t\r\n"

    def __init__(self, sock, debug=False):
        self.sock = sock
        self.buf = b""
        self.debug = debug
        try:
            self.sock.settimeout(5)
        except (OSError, ValueError):
            pass

    def _recv(self):
        """Pull one chunk into the buffer.  False on timeout, EOFError on close."""
        try:
            data = self.sock.recv(4096)
        except socket.timeout:
            return False
        if not data:
            raise EOFError("connection closed by peer")
        self.buf += data
        if self.debug:
            sys.stdout.write("[recv %d] %r\n" % (len(data), data))
            sys.stdout.flush()
        return True

    def read_stream_header(self, timeout=15):
        """Return the server's opening '<stream:stream ...>' tag, or None."""
        deadline = time.monotonic() + timeout
        while True:
            header = self._extract_stream_header()
            if header is not None:
                return header
            if time.monotonic() > deadline:
                return None
            if not self._recv():
                continue

    def _extract_stream_header(self):
        buf = self.buf
        i = 0
        n = len(buf)
        while i < n and buf[i] in self._WS:
            i += 1
        if buf.startswith(b"<?", i):
            end = buf.find(b"?>", i + 2)
            if end == -1:
                return None
            i = end + 2
        if i < len(buf) and buf[i] == ord("<"):
            gt = buf.find(b">", i)
            if gt == -1:
                return None
            header = buf[i:gt + 1]
            self.buf = buf[gt + 1:]
            return header
        return None

    def read_element(self, timeout=30):
        """Return the next complete XML element as bytes, or None on timeout."""
        deadline = time.monotonic() + timeout
        while True:
            elem = self._extract_element()
            if elem is not None:
                return elem
            if time.monotonic() > deadline:
                return None
            if not self._recv():
                continue

    def _extract_element(self):
        buf = self.buf
        n = len(buf)
        i = 0
        while i < n and buf[i] in self._WS:
            i += 1
        if i:
            buf = buf[i:]
            n = len(buf)
        if not n:
            self.buf = b""
            return None
        if buf[0] != ord("<"):
            # Unexpected garbage; drop one byte rather than wedging the reader.
            self.buf = buf[1:]
            return None
        end = self._find_element_end(buf)
        if end is None:
            return None
        elem = buf[:end]
        self.buf = buf[end:]
        return elem

    @staticmethod
    def _find_element_end(buf):
        """Index just past the closing '>' of the element starting at buf[0]."""
        n = len(buf)
        if buf.startswith(b"<?", 0):
            end = buf.find(b"?>", 2)
            return end + 2 if end != -1 else None
        if buf.startswith(b"<!--", 0):
            end = buf.find(b"-->", 4)
            return end + 3 if end != -1 else None
        if buf.startswith(b"</", 0):
            end = buf.find(b">", 2)
            return end + 1 if end != -1 else None
        gt = buf.find(b">", 0)
        if gt == -1:
            return None
        if buf[gt - 1:gt] == b"/":
            return gt + 1  # self-closing tag
        # depth-count to the matching close tag
        depth = 1
        j = gt + 1
        while j < n:
            lt = buf.find(b"<", j)
            if lt == -1:
                return None
            if buf.startswith(b"<!--", lt):
                c = buf.find(b"-->", lt + 4)
                if c == -1:
                    return None
                j = c + 3
                continue
            if buf.startswith(b"<?", lt):
                c = buf.find(b"?>", lt + 2)
                if c == -1:
                    return None
                j = c + 2
                continue
            gt2 = buf.find(b">", lt)
            if gt2 == -1:
                return None
            if buf.startswith(b"</", lt):
                depth -= 1
                if depth == 0:
                    return gt2 + 1
            elif buf[gt2 - 1:gt2] != b"/":
                depth += 1
            j = gt2 + 1
        return None


class Client:
    def __init__(self, jid, password, host, port):
        self.jid = jid
        self.user = jid.split("@")[0]
        self.password = password
        self.host = host
        self.port = port
        self.sock = None
        self.reader = None

    # ---- transport -------------------------------------------------------
    def connect(self):
        dbg("connecting to", self.host, self.port)
        self.sock = socket.create_connection((self.host, self.port), timeout=30)
        self.reader = StreamReader(self.sock, debug=DEBUG)
        dbg("connected")

    def upgrade_tls(self):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if NO_VERIFY:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        dbg("starting TLS")
        self.sock = ctx.wrap_socket(self.sock, server_hostname=self.host)
        self.reader = StreamReader(self.sock, debug=DEBUG)
        dbg("TLS up")

    def send(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.sock.sendall(data)

    # ---- stream ----------------------------------------------------------
    def open_stream(self):
        self.send(
            "<?xml version='1.0'?><stream:stream to='%s' xmlns='%s' "
            "xmlns:stream='%s' version='1.0'>"
            % (self.host, NS_CLIENT, NS_STREAM)
        )
        header = self.reader.read_stream_header()
        if header is None:
            raise XMPPError("timeout waiting for the server stream header")
        dbg("server stream:", header)

    def wait_for(self, matcher, timeout=30):
        deadline = time.time() + timeout
        while True:
            fragment = self.reader.read_element(timeout=5)
            if fragment is None:
                if time.time() > deadline:
                    raise XMPPError("timeout waiting for a stream event")
                continue
            for elem in parse_fragment(fragment):
                if matcher(elem):
                    dbg("got element", elem.tag)
                    return elem

    # ---- login -----------------------------------------------------------
    def login(self):
        dbg("opening stream")
        self.open_stream()
        features = self.wait_for(lambda e: e.tag == "{%s}features" % NS_STREAM)
        dbg("got features")

        if features.find("{%s}starttls" % NS_TLS) is not None:
            dbg("server offers STARTTLS, requesting it")
            self.send("<starttls xmlns='%s'/>" % NS_TLS)
            self.wait_for(lambda e: e.tag == "{%s}proceed" % NS_TLS, timeout=15)
            dbg("got proceed, upgrading to TLS")
            self.upgrade_tls()
            self.open_stream()
            dbg("reopened stream over TLS")
            features = self.wait_for(lambda e: e.tag == "{%s}features" % NS_STREAM)
            dbg("got features over TLS")

        self._sasl(features)

        # Resource binding
        dbg("binding resource")
        self.send(
            "<iq type='set' id='pk-bind'><bind xmlns='%s'>"
            "<resource>phonekit</resource></bind></iq>" % NS_BIND
        )
        iq = self.wait_for(
            lambda e: e.tag == "{%s}iq" % NS_CLIENT and e.get("id") == "pk-bind"
        )
        if iq is None or iq.get("type") == "error":
            raise XMPPError("resource binding failed")
        dbg("bound ok")

    def _sasl(self, features):
        mechs = []
        mechanisms = features.find("{%s}mechanisms" % NS_SASL)
        if mechanisms is not None:
            mechs = [m.text for m in mechanisms.findall("{%s}mechanism" % NS_SASL)]
        if "SCRAM-SHA-1" in mechs:
            self._sasl_scram()
        elif "PLAIN" in mechs:
            payload = b64(("\0%s\0%s" % (self.user, self.password)).encode("utf-8"))
            self.send(
                "<auth xmlns='%s' mechanism='PLAIN'>%s</auth>" % (NS_SASL, payload)
            )
            self._sasl_result()
        else:
            raise XMPPError("no usable SASL mechanism: %s" % ",".join(mechs))

    def _sasl_scram(self):
        client_nonce = b64(os.urandom(16)).rstrip("=")
        c_first_bare = "n=%s,r=%s" % (escape_sasl(self.user), client_nonce)
        self.send(
            "<auth xmlns='%s' mechanism='SCRAM-SHA-1'>%s</auth>"
            % (NS_SASL, b64(("n,," + c_first_bare).encode("utf-8")))
        )
        challenge = self.wait_for(lambda e: e.tag == "{%s}challenge" % NS_SASL)
        server_first = b64d(challenge.text).decode("utf-8")
        server_nonce = dict(
            p.split("=", 1) for p in server_first.split(",")
        )["r"]
        c_final = scram_sha1(
            self.password, c_first_bare, server_first, client_nonce, server_nonce
        )
        self.send(
            "<response xmlns='%s'>%s</response>" % (NS_SASL, b64(c_final.encode("utf-8")))
        )
        self._sasl_result()

    def _sasl_result(self):
        elem = self.wait_for(
            lambda e: e.tag
            in ("{%s}success" % NS_SASL, "{%s}failure" % NS_SASL)
        )
        if elem.tag == "{%s}failure" % NS_SASL:
            raise XMPPError("SASL authentication failed")
        self.open_stream()  # the stream restarts after SASL success
        self.wait_for(lambda e: e.tag == "{%s}features" % NS_STREAM)

    # ---- messaging -------------------------------------------------------
    def send_presence(self):
        self.send("<presence/>")

    def send_message(self, to, body):
        safe = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.send(
            "<message type='chat' to='%s'><body>%s</body></message>" % (to, safe)
        )

    def _handle(self, elem):
        tag = elem.tag
        if tag == "{%s}message" % NS_CLIENT:
            body_elem = elem.find("{%s}body" % NS_CLIENT)
            if body_elem is not None and body_elem.text:
                from_jid = elem.get("from", "?")
                line = "[%s] %s: %s" % (
                    time.strftime("%H:%M"), from_jid, body_elem.text,
                )
                with open(INBOX, "a") as fh:
                    fh.write(line + "\n")
                if POPUP:
                    self._popup(from_jid, body_elem.text)
        elif tag == "{%s}stream" % NS_STREAM:
            raise XMPPError("server closed the stream")

    def _popup(self, from_jid, body):
        max_chars = 60
        try:
            with open("/sys/class/graphics/fb0/virtual_size") as fh:
                w, h = [int(x) for x in fh.read().strip().split(",")]
            max_chars = max(20, w // 8)
        except Exception:
            w, h = 600, 800
        head = "<%s>" % from_jid.split("@")[0]
        text = " ".join(body.split())[:max_chars]
        args = [
            ["0", str(h - 48), head[:max_chars]],
            ["0", str(h - 32), text],
        ]
        for arg in args:
            for prog in ("/usr/sbin/eips", "/usr/bin/eips"):
                try:
                    subprocess.Popen(
                        [prog] + arg,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    break
                except OSError:
                    continue

    def listen(self):
        def keepalive():
            while True:
                time.sleep(60)
                try:
                    self.sock.sendall(b" ")
                except Exception:
                    break

        threading.Thread(target=keepalive, daemon=True).start()
        while True:
            fragment = self.reader.read_element(timeout=60)
            if fragment is None:
                continue
            for elem in parse_fragment(fragment):
                self._handle(elem)


def main():
    args = sys.argv[1:]
    mode = "listen"
    if args and args[0] == "send":
        mode = "send"
        args = args[1:]

    if not JID or not PASS:
        sys.stderr.write("Set PK_XMPP_JID and PK_XMPP_PASS in xmpp/config.env\n")
        return 2

    client = Client(JID, PASS, HOST, PORT)
    try:
        client.connect()
        client.login()
        if mode == "send":
            if len(args) < 2:
                sys.stderr.write("usage: bridge.py send <jid> <message>\n")
                return 2
            client.send_message(args[0], " ".join(args[1:]))
            time.sleep(1.5)  # let the TLS buffer flush before we close
            print("sent")
            return 0
        client.send_presence()
        client.listen()
    except EOFError:
        sys.stderr.write("server closed the connection\n")
        return 1
    except XMPPError as exc:
        sys.stderr.write("xmpp error: %s\n" % exc)
        return 1
    except Exception as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
