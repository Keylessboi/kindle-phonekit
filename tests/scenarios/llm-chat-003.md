# Scenario: LLM /chat surfaces an upstream failure and rolls back the turn

- **ID:** LLM-CHAT-003
- **Behavior under test:** When the upstream endpoint errors, the page shows an
  error and the failed user turn is not retained in history (so a retry is
  clean).
- **Surface:** HTTP POST /chat on llm_server.py.
- **Compiled test:** tests/test_llm_server.py::test_chat_upstream_failure_rolls_back

## Preconditions

- The LLM server runs as a subprocess on an ephemeral port.
- `PK_LLM_API_URL` points at a closed/refusing port so every upstream request
  raises a connection error (URLError).

## Action

The user sends `POST /chat` with `msg=will%20fail`.

## Expected result (oracles)

1. The response is HTTP 200 (the page still renders; the server absorbs the
   upstream error).
2. The rendered page contains an error fragment (`URLError`) AND does **not**
   render the failed user turn as a normal turn (the error is not a user turn).
3. A subsequent `GET /` renders **no** user turns (the failed turn was rolled
   back / popped from history).

## Cleanup

- Terminate the LLM server subprocess.