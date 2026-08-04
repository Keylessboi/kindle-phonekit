"""Static structure scenario tests (STATIC-STRUCT-001).

Read-only checks that every deliverable file parses in its native format.
"""

import json
import os
import re
import subprocess

import pytest

from conftest import EXT, LLM_DIR, XMPP_DIR

EXT = os.path.abspath(EXT)
EXTENSION_ROOT = os.path.dirname(EXT)  # .../phonekit (config.xml, menu.json)


def _all_shell_scripts():
    found = []
    for root, _dirs, files in os.walk(EXT):
        for fn in files:
            if fn.endswith(".sh"):
                found.append(os.path.join(root, fn))
    return sorted(found)


def test_all_shell_scripts_pass_sh_n():
    """Every *.sh under extensions/phonekit parses with sh -n."""
    scripts = _all_shell_scripts()
    assert scripts, "no shell scripts found under %s" % EXT
    for script in scripts:
        result = subprocess.run(
            ["sh", "-n", script], capture_output=True, text=True)
        assert result.returncode == 0, (
            "sh -n failed for %s:\n%s" % (script, result.stderr))


def test_menu_json_is_valid():
    with open(os.path.join(EXTENSION_ROOT, "menu.json")) as fh:
        data = json.load(fh)
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


def test_config_xml_is_valid():
    import xml.dom.minidom
    xml.dom.minidom.parse(os.path.join(EXTENSION_ROOT, "config.xml"))


def test_config_env_files_source_cleanly(tmp_path):
    """Each config.env sources in a POSIX shell with its documented keys set."""
    for cfg in ["llm/config.env", "xmpp/config.env"]:
        path = os.path.join(EXT, cfg)
        assert os.path.isfile(path), "missing %s" % path
        # Source it and print the keys we care about.
        script = (
            ". \"%s\"\n"
            'echo "URL=$PK_LLM_API_URL|JID=$PK_XMPP_JID|PORT=$PK_XMPP_PORT"\n'
            % path
        )
        result = subprocess.run(
            ["sh", "-c", script], capture_output=True, text=True)
        assert result.returncode == 0, (
            "config.env failed to source: %s\n%s" % (path, result.stderr))
        if cfg.startswith("llm"):
            assert "URL=http://127.0.0.1" in result.stdout
        else:
            assert "JID=" in result.stdout and "PORT=5222" in result.stdout


def _read_env_vars(script_path, prefix):
    """Every ``PREFIX_*`` var the script reads via os.environ.get()."""
    src = open(script_path, encoding="utf-8").read()
    return set(re.findall(r"%s_[A-Z0-9_]+" % prefix, src))


def _shell_exports(launcher_path):
    """Var names on the ``export`` line(s) of a launcher script."""
    src = open(launcher_path, encoding="utf-8").read()
    exported = set()
    for m in re.finditer(r"^export\s+(.+)$", src, re.M):
        exported.update(m.group(1).split())
    return exported


@pytest.mark.parametrize(
    "script_rel, launcher_rel, prefix",
    [
        ("xmpp/bridge.py", "xmpp/start_bridge.sh", "PK_XMPP"),
        ("llm/llm_server.py", "llm/start.sh", "PK_LLM"),
    ],
)
def test_launcher_exports_every_var_the_script_reads(
    script_rel, launcher_rel, prefix
):
    """STATIC-STRUCT-001 (regression): no silently-dropped env seam.

    A subtitle/launcher must export every ``PREFIX_*`` var the script reads,
    otherwise a user setting it in config.env never reaches the subprocess.
    """
    script = os.path.join(EXT, script_rel)
    launcher = os.path.join(EXT, launcher_rel)
    assert os.path.isfile(script), "missing %s" % script
    assert os.path.isfile(launcher), "missing %s" % launcher

    read_vars = _read_env_vars(script, prefix)
    exported = _shell_exports(launcher)
    # os.environ.get calls reference these canonically; drop read-side literals
    # that only appear in docstrings but have no real get() (none expected).
    missing = sorted(v for v in read_vars if v not in exported)
    assert missing == [], (
        "%s reads %s, which start/launcher does not export (- set in config.env, "
        "+ exported): %s" % (script_rel, prefix, missing)
    )

    # Every var a user can set should also be documented in config.env.
    cfg = os.path.join(EXT, script_rel.rsplit("/", 1)[0], "config.env")
    if os.path.isfile(cfg):
        cfg_src = open(cfg, encoding="utf-8").read()
        cfg_set = set(re.findall(r"%s_[A-Z0-9_]+" % prefix, cfg_src))
        undocumented = sorted(v for v in exported if v not in cfg_set)
        assert undocumented == [], (
            "%s exports %s but config.env does not document them: %s"
            % (launcher_rel, prefix, undocumented)
        )