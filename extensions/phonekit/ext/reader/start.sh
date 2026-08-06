#!/bin/sh
# PhoneKit read-it-later — start the local server, then open it in the browser.

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
export PK_RIL_PORT PK_RIL_API_URL PK_RIL_API_KEY PK_RIL_MODEL

# Restart the server cleanly
pkill -f "reader_server.py" 2>/dev/null
sleep 1

cd "$_DIR" || { echo "cannot cd to $_DIR" >&2; exit 1; }
nohup "$_PY" reader_server.py > /tmp/phonekit_reader.log 2>&1 &
sleep 2

_PORT="${PK_RIL_PORT:-8081}"
eips_center 20 "Opening read-it-later..."
open_url "http://127.0.0.1:$_PORT"
sleep 2
eips_clear