# PhoneKit tests

This directory tests the PhoneKit extension. The tests drive the real product
code, not a copy of it. They use only the Python standard library plus pytest.

## What the tests cover

The suite has four parts. Each part maps to Markdown scenarios in
`tests/scenarios/`. Each scenario names one behavior and states the expected
result as checkable facts.

### LLM server (`tests/test_llm_server.py`)

Scenarios: `tests/scenarios/llm-*.md`

The tests start `llm_server.py` as a real subprocess on a free port. The tests
point the server at a local mock that answers like an OpenAI-compatible API.
Then the tests send real HTTP requests and read the returned HTML.

- A chat message returns the upstream reply, sends the configured system
  prompt first, and keeps both turns in history.
- An empty message redirects and leaves history unchanged.
- `/clear` empties history.
- A failed upstream call shows an error and does not keep the failed turn.

### XMPP bridge (`tests/test_bridge.py`)

Scenarios: `tests/scenarios/xmpp-*.md`

The tests run `bridge.py` as a real subprocess. They connect it to a local mock
XMPP server over TLS. The mock uses a self-signed certificate, so the tests set
`PK_XMPP_NO_VERIFY=1`.

- SCRAM-SHA-1 matches the published RFC 5802 test vector.
- In listen mode the bridge authenticates, binds a resource, and writes an
  incoming message to the inbox file.
- In send mode the bridge exits 0 and delivers the message stanza, escaping
  XML-special characters in the body.
- The bridge source avoids `socket.makefile`, which would break reads under
  Python 3.14.

### Shell scripts (`tests/test_scripts.py`)

Scenarios: `tests/scenarios/*.md` for the scripts named below.

The tests copy the real shell scripts into a sandbox directory. The sandbox
replaces `date`, `sleep`, and `eips` with tiny stubs, so the tests run fast
and do not need a Kindle. They verify the scripts' own logic end to end.

- `weblinks.sh` maps a name to its URL.
- `clock.sh` uses the 24-hour format by default and the 12-hour AM/PM format
  when given the `12` argument.
- `timer.sh` counts down as an `MM:SS` label, and falls back to 300 seconds
  on a bad argument.

### Package structure (`tests/test_static.py`)

Scenario: `tests/scenarios/static-struct-001.md`

- Every `*.sh` file passes `sh -n`.
- `menu.json` is valid JSON.
- `config.xml` is valid XML.
- Each `config.env` sources cleanly and sets its documented keys.
- Each launcher script exports every key its server reads, and every key is
  documented in `config.env`. This regression caught a real gap: the bridge
  launcher was missing the exports for the popup, debug, and inbox keys.

## Isolation

Every test isolates its own state.

- Each server runs on an ephemeral port, so tests do not collide.
- Each test uses a fresh temporary directory.
- The bridge writes its inbox to a per-test path.
- Each run starts the server with a clean history.

The mock servers live in `tests/fixtures/`. `tests/conftest.py` holds the
pytest fixtures that launch the real subprocesses.

## How to run

From the project root:

```sh
python3 -m pytest tests/ -v
```

Run one file:

```sh
python3 -m pytest tests/test_llm_server.py -v
```

Run one scenario:

```sh
python3 -m pytest tests/test_bridge.py::test_scram_sha1_rfc5802_vector -v
```

## How to add a test

1. Write a scenario in `tests/scenarios/` that states one behavior and its
   expected result as facts.
2. Add a test that launches the real code and asserts each fact.
3. Link the test to the scenario by name.

## Limits

These tests do not exercise the Kindle's screen or its browser. They cover the
servers and the scripts' logic. Screen behavior needs a real device. The shell
tests use stub programs for `eips` and the clock, so they check the scripts'
control flow, not real pixels or wall-clock timing.