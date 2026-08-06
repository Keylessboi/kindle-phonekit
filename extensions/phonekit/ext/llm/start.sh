#!/bin/sh
# PhoneKit LLM — start the local chat server, then open it in the browser.

. "$(dirname "$0")/../common.sh"

_DIR="$(dirname "$0")"
_PY=$(find_python3) || {
    eips_center 20 "python3 not found on device"
    sleep 3
    eips_clear
    exit 1
}

# Load config into the environment
if [ -f "$_DIR/config.env" ]; then
    . "$_DIR/config.env"
fi
export PK_LLM_API_URL PK_LLM_API_KEY PK_LLM_MODEL PK_LLM_SYSTEM PK_LLM_PORT

# Restart the server cleanly
pkill -f "llm_server.py" 2>/dev/null
sleep 1

cd "$_DIR" || { echo "cannot cd to $_DIR" >&2; exit 1; }
nohup "$_PY" llm_server.py > /tmp/phonekit_llm.log 2>&1 &
sleep 2

_PORT="${PK_LLM_PORT:-8080}"
eips_center 20 "Opening LLM chat..."
open_url "http://127.0.0.1:$_PORT"
sleep 2
eips_clear