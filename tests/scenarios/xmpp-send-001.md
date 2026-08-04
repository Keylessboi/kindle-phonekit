# Scenario: XMPP bridge send mode emits a well-formed message stanza

- **ID:** XMPP-SEND-001
- **Behavior under test:** Running the bridge in send mode authenticates and
  delivers exactly one `<message type='chat'>` stanza to the recipient with the
  body text present and properly wrapped.
- **Surface:** bridge.py run as a subprocess (`send <jid> <message>`) against a
  local mock XMPP server over self-signed TLS; `PK_XMPP_NO_VERIFY=1`.
- **Compiled test:** tests/test_bridge.py::test_send_mode_reaches_recipient

## Preconditions

- A mock XMPP server listens on an ephemeral port, offers STARTTLS + SCRAM-SHA-1,
  verifies the client proof, binds the resource, and then waits to capture an
  outgoing message stanza.
- `PK_XMPP_JID=user@localhost`, `PK_XMPP_PASS=pencil`, `PK_XMPP_HOST=127.0.0.1`,
  `PK_XMPP_PORT=<ephemeral>`, `PK_XMPP_NO_VERIFY=1`.

## Action

Run `bridge.py send friend@localhost 'hello from kindle'`.

## Expected result (oracles)

1. The bridge exits with status 0.
2. The mock server logs the received message stanza with
   `to='friend@localhost'` and body `hello from kindle`.

## Cleanup

- Terminate the mock server and remove its TLS cert.