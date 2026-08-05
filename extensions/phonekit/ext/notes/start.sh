#!/bin/sh
# PhoneKit Notes + Todo — start the notes server, then open it in the browser.

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
export PK_NOTES_FILE PK_NOTES_PORT

# Restart the server cleanly
pkill -f "notes_server.py" 2>/dev/null
sleep 1

cd "$_DIR"
nohup "$_PY" notes_server.py > /tmp/phonekit_notes.log 2>&1 &
sleep 2

_PORT="${PK_NOTES_PORT:-8083}"
eips_center 20 "Opening Notes..."
open_url "http://127.0.0.1:$_PORT"
sleep 2
eips_clear