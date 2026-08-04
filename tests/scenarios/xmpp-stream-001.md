# Scenario: XMPP bridge reads the socket with raw recv(), never makefile()

- **ID:** XMPP-STREAM-001
- **Behavior under test:** The bridge's `StreamReader` must keep using raw
  `socket.recv()` + byte scanning. On Python 3.14.6, `socket.makefile().read()`
  blocks for the full socket timeout even when `select()` reports readable data,
  which hangs `iterparse()`-based stream parsing indefinitely.
- **Surface:** `bridge.py` source (design lock).
- **Compiled test:** tests/test_bridge.py::test_bridge_source_avoids_socket_makefile

## Preconditions

- None (static source check).

## Action

Tokenize `bridge.py` and check the identifier `makefile` does not appear in any
executable code position (comments and docstrings excluded by tokenizing).

## Expected result (oracles)

1. No `makefile` identifier in the bridge's executable code.

## Cleanup

- None.
