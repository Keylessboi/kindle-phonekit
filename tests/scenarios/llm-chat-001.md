# Scenario: LLM /chat returns the upstream reply and appends the turn

- **ID:** LLM-CHAT-001
- **Behavior under test:** POST /chat sends the user message to the
  OpenAI-compatible endpoint and renders the upstream reply as a new AI turn.
- **Surface:** HTTP POST /chat on llm_server.py (real subprocess, stdlib server).
- **Compiled test:** tests/test_llm_server.py::test_chat_round_trip_appends_history

## Preconditions

- The LLM server runs as a subprocess on an ephemeral port.
- `PK_LLM_API_URL` points at a local mock endpoint that returns a fixed reply
  (`MOCK_REPLY_1`) for every chat completion request.
- History starts with only the system prompt (server started fresh).

## Action

The user sends `POST /chat` with `msg=hello%20kindle`.

## Expected result (oracles)

1. The response is HTTP 200 with `text/html` content.
2. The rendered page contains the user turn: `<b>You:</b> hello kindle`.
3. The rendered page contains the AI turn with the upstream reply:
   `<b>AI:</b> MOCK_REPLY_1`.
4. A subsequent `GET /` renders the same two turns (the turns persist in
   server-side history).
5. The mock upstream received exactly one chat completion request whose JSON
   body has `model` equal to the configured `PK_LLM_MODEL` and a `messages`
   array that contains the user message.

## Cleanup

- Terminate the LLM server subprocess.
- Stop the mock upstream server.
