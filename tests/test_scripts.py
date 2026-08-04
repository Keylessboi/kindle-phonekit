"""Deterministic behavior of the device-bound shell scripts.

Each script is copied verbatim into a temp sandbox with a minimal fake
``common.sh`` (so ``dirname $0`` resolves) and stub ``date``/``sleep``/``eips``
on PATH. The product logic under test runs untouched; only the Kindle platform
is replaced. This keeps the oracles fully deterministic (no wall-clock races).
"""

import os
import re
import shutil
import subprocess
import tempfile

from conftest import EXT

FAKE_COMMON = (
    "SCREEN_W=600\n"
    "SCREEN_H=800\n"
    "CH_W=8\n"
    "CH_H=16\n"
    "eips_center(){ :; }\n"
    "eips_clear(){ :; }\n"
    "export PATH=\"$STUB_DIR\":/usr/bin:/bin:/usr/sbin:/sbin\n"
)

MONOTONIC_CLOCK = {
    "date": 'val=$(cat "$STUB_DIR/now" 2>/dev/null || echo 1000); echo "$val"\n',
    "sleep": 'val=$(cat "$STUB_DIR/now" 2>/dev/null || echo 1000); '
             'echo $((val + 1)) > "$STUB_DIR/now"\n',
    "eips": '[ $# -eq 3 ] && echo "$3"\n',
}


def _run_sandboxed(name, args=(), stubs=None, timeout=None):
    """Execute the real ``name`` script with stubbed platform binaries."""
    sandbox = tempfile.mkdtemp(prefix="pk-script-")
    bin_dir = os.path.join(sandbox, "bin")
    os.makedirs(bin_dir)
    try:
        shutil.copy2(os.path.join(EXT, name), os.path.join(sandbox, name))
        with open(os.path.join(sandbox, "common.sh"), "w") as fh:
            fh.write(FAKE_COMMON)
        env = dict(os.environ, STUB_DIR=bin_dir)
        for stub, body in (stubs or MONOTONIC_CLOCK).items():
            path = os.path.join(bin_dir, stub)
            with open(path, "w") as fh:
                fh.write("#!/bin/sh\n" + body)
            os.chmod(path, 0o755)
        argv = ["sh", os.path.join(sandbox, name)] + list(args)
        if timeout:
            argv = ["timeout", str(timeout)] + argv
        result = subprocess.run(
            argv, capture_output=True, text=True, env=env)
        return result.returncode, result.stdout, result.stderr
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def test_weblinks_maps_name_to_url():
    """WEBLINK-MAP-001: each known alias launches its documented URL."""
    weblinks_stubs = {
        "date": 'exec /bin/date "$@"\n',
        "sleep": 'exec /bin/sleep "$@"\n',
        "eips": "exit 0\n",
        "open_url": 'echo "OPEN_URL:$*"\n',
    }
    expected = {
        "openwebui": "http://192.168.1.50:8080",
        "chatgpt": "https://chatgpt.com",
        "claude": "https://claude.ai",
        "gemini": "https://gemini.google.com",
    }
    for alias, url in expected.items():
        code, out, _err = _run_sandboxed("weblinks.sh", [alias], weblinks_stubs)
        assert code == 0
        assert "OPEN_URL:%s" % url in out, (
            "%s should map to %s, got %r" % (alias, url, out))


def test_clock_format_is_24h_by_default():
    """CLOCK-FMT-001: with no argument the clock uses the 24h format."""
    code, _out, err = _run_sandboxed(
        "clock.sh",
        stubs={"date": 'echo "FMT:$*" >&2; echo 12:00:00\n',
               "sleep": "exit 0\n",
               "eips": "exit 0\n"},
        timeout=2,
    )
    assert code in (0, 124)  # 124 = killed by timeout (infinite loop)
    assert "%H" in err, err


def test_clock_12h_argument_selects_am_pm():
    """CLOCK-FMT-001: the '12' argument selects the AM/PM (12h) format."""
    code, _out, err = _run_sandboxed(
        "clock.sh", ["12"],
        stubs={"date": 'echo "FMT:$*" >&2; echo 12:00:00\n',
               "sleep": "exit 0\n",
               "eips": "exit 0\n"},
        timeout=2,
    )
    assert code in (0, 124)  # 124 = killed by timeout (infinite loop)
    assert "%I" in err and "%p" in err, err


def test_timer_countdown_labels():
    """TIMER-MMSS-001: the MM:SS label counts down the remaining seconds."""
    code, out, _err = _run_sandboxed("timer.sh", ["5"])
    assert code == 0
    labels = re.findall(r"^\d\d:\d\d$", out, re.M)
    assert labels == ["00:05", "00:04", "00:03", "00:02", "00:01"], labels


def test_timer_defaults_to_300_seconds_on_bad_arg():
    """TIMER-MMSS-001: a non-integer argument falls back to the 300s default."""
    code, out, _err = _run_sandboxed("timer.sh", ["abc"], timeout=2)
    assert code in (0, 124)  # 124 = killed after first label proves default
    # A 300s countdown from t=1000 emits 05:00 first, proving the default ran.
    labels = re.findall(r"^\d\d:\d\d$", out, re.M)
    assert labels and labels[0] == "05:00", labels