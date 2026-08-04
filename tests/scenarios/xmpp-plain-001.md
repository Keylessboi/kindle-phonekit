# Scenario: XMPP bridge authenticates with PLAIN when SCRAM-SHA-1 is not offered

- **ID:** XMPP-PLAIN-001
- **Behavior under test:** `bridge.py` falls back to SASL PLAIN when the server
  advertises only `PLAIN` (per the module docstring and README: SCRAM-SHA-1 when
  offered, PLAIN otherwise). The inbound delivery path still completes.
- **Surface:** `bridge.py` `_sasl()` PLAIN branch, real subprocess against the
  in-process XMPP mock in `plain` mode.
- **Compiled test:** tests/test_bridge.py::test_plain_fallback_auth_and_inbox

## Preconditions

- XMPP mock running in `plain` mode (advertises only `PLAIN`).

## Action

Listen-mode bridge connects and authenticates with PLAIN over STARTTLS.

## Expected result (oracles)

1. The mock receives and verifies the PLAIN auth payload (`\0user\0pencil`),
   so `plain_verified` is True.
2. Resource binding succeeds (`received_bind` is True).
3. An inbound message is written to the inbox.

## Cleanup

- Bridge subprocess terminated (and reaped) in the test's `finally` block.