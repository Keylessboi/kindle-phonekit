# Scenario: XMPP bridge receives a message and logs it to the inbox

- **ID:** XMPP-INBOUND-001
- **Behavior under test:** Running the bridge in listen mode against a mock XMPP
  server completes STARTTLS, authenticates with SCRAM-SHA-1, binds a resource,
  sends presence, and logs an incoming chat message to the inbox file.
- **Surface:** bridge.py run as a subprocess (listen mode) against a local mock
  XMPP server over a self-signed TLS cert; `PK_XMPP_NO_VERIFY=1`.
- **Compiled test:** tests/test_bridge.py::test_inbound_message_written_to_inbox

## Preconditions

- A mock XMPP server listens on an ephemeral port, offers STARTTLS + SCRAM-SHA-1,
  verifies the client proof, binds the resource, and then sends one chat
  message: `hello from the mock server`.
- The bridge runs with `PK_XMPP_JID=user@localhost`, `PK_XMPP_PASS=pencil`,
  `PK_XMPP_HOST=127.0.0.1`, `PK_XMPP_PORT=<ephemeral>`, `PK_XMPP_NO_VERIFY=1`,
  `PK_XMPP_POPUP=0`, and `PK_XMPP_INBOX=<tmp>/inbox.txt`.
- The inbox file does not exist yet.

## Action

Run the bridge in listen mode and wait for it to receive the pushed message.

## Expected result (oracles)

1. The mock server logs `SCRAM proof verified OK` (the bridge's proof was valid).
2. The mock server received the bind `<iq type='set' id='pk-bind'>` request.
3. The inbox file contains exactly one line matching
   `\[HH:MM\] friend@localhost: hello from the mock server` where `HH:MM` is the
   current local time.

## Cleanup

- Terminate the bridge subprocess.
- Terminate the mock server and remove its TLS cert.