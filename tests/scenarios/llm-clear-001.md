# Scenario: LLM /clear resets conversation history

- **ID:** LLM-CLEAR-001
- **Behavior under test:** GET /clear removes all prior turns (keeps the
  system prompt) and redirects back to the chat page.
- **Surface:** HTTP GET /clear on llm_server.py.
- **Compiled test:** tests/test_llm_server.py::test_clear_resets_history

## Preconditions

- The LLM server runs as a subprocess on an ephemeral port.
- The user has already exchanged at least one turn (history contains user and
  assistant turns).

## Action

The user sends `GET /clear`.

## Expected result (oracles)

1. The response is a 303 redirect to `/`.
2. A subsequent `GET /` renders **no** user turns and **no** AI turns.
3. The page still renders the model badge header (system state intact).

## Cleanup

- Terminate the LLM server subprocess.