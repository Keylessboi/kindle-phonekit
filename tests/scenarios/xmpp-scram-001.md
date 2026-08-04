# Scenario: XMPP bridge authenticates with SCRAM-SHA-1 against RFC 5802

- **ID:** XMPP-SCRAM-001
- **Behavior under test:** The bridge's SCRAM-SHA-1 client-final message matches
  the published RFC 5802 section-5 test vector, proving the crypto math that the
  bridge and the mock server both rely on.
- **Surface:** `bridge.scram_sha1()` pure function.
- **Compiled test:** tests/test_bridge.py::test_scram_sha1_rfc5802_vector

## Preconditions

- None (pure computation).

## Action

Compute the client-final message for the RFC 5802 vector:
- username `user`, password `pencil`
- client nonce `fyko+d2lbbFgONRv9qkxdawL`
- server nonce `fyko+d2lbbFgONRv9qkxdawL3rfcNHYJY1ZVvWVs7j`
- salt `QSXCR+Q6sek8bf92`, iterations `4096`
- client-first-bare `n=user,r=fyko+d2lbbFgONRv9qkxdawL`

## Expected result (oracles)

1. The computed client-final message equals the published vector:
   `c=biws,r=fyko+d2lbbFgONRv9qkxdawL3rfcNHYJY1ZVvWVs7j,p=v0X8v3Bz2T0CJGbJQyF0X+HI4Ts=`

## Cleanup

- None.