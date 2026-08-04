# Scenario: XMPP send escapes XML-special characters in the message body

- **ID:** XMPP-SEND-002
- **Behavior under test:** `bridge.py` send mode escapes `&`, `<`, `>` in the
  message body before embedding it in the `<body>` element, so a body cannot
  break out of the element (XML injection guard).
- **Surface:** `bridge.py` send mode, `send_message()` escaping.
- **Compiled test:** tests/test_bridge.py::test_send_mode_escapes_body_special_chars

## Preconditions

- XMPP mock running in send-capture mode (same fixture as XMPP-SEND-001).

## Action

Launch the bridge in send mode with the body `A & B < C > D`.

## Expected result (oracles)

1. The bridge exits 0.
2. The mock captures a message stanza whose `<body>` contains
   `A &amp; B &lt; C &gt; D`.
3. The stanza contains no raw `<body>A & B` (unescaped) sequence.

## Cleanup

- Bridge subprocess terminated (and reaped) in the test's `finally` block.
