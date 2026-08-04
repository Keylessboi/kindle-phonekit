# Scenario: LLM /chat with an empty message redirects without mutating history

- **ID:** LLM-CHAT-002
- **Behavior under test:** POST /chat with a blank message does not call the
  upstream and does not add a user turn.
- **Surface:** HTTP POST /chat on llm_server.py.
- **Compiled test:** tests/test_llm_server.py::test_chat_empty_message_redirects

## Preconditions

- The LLM server runs as a subprocess on an ephemeral port.
- History starts with only the system prompt.

## Action

The user sends `POST /chat` with an empty `msg` field (e.g. `msg=` or no `msg`
key at all).

## Expected result (oracles)

1. The response is a 303 redirect to `/`.
2. The mock upstream receives **zero** chat completion requests.
3. A subsequent `GET /` renders no user or AI turns (history unchanged).

## Cleanup

- Terminate the LLM server subprocess.