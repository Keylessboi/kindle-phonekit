# Scenario: Package structure is syntactically valid

- **ID:** STATIC-STRUCT-001
- **Behavior under test:** Every deliverable file parses in its native format:
  all shell scripts pass `sh -n`, the KUAL menu.json is valid JSON, config.xml
  is valid XML, and the config.env files parse as shell variable assignments.
- **Surface:** Files under `extensions/phonekit/`.
- **Compiled test:** tests/test_static.py

## Preconditions

- The extension tree exists and matches the packaged layout.

## Actions

1. Run `sh -n` on every `*.sh` file under `extensions/phonekit`.
2. Parse `menu.json` with a JSON parser.
3. Parse `config.xml` with an XML parser.
4. Source each `config.env` in a POSIX shell and confirm the documented keys are
   set.

## Expected result (oracles)

1. `sh -n` exits 0 for every shell script.
2. `menu.json` parses as valid JSON.
3. `config.xml` parses as valid XML.
4. Each `config.env` sources without error and exports its documented keys
   (e.g. `PK_LLM_API_URL`, `PK_XMPP_JID`, `PK_XMPP_PORT`).

## Cleanup

- None (read-only checks).