#!/bin/sh
# PhoneKit Feed Reader - start the local feed server, then open it in the browser.

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
export PK_FEED_PORT PK_FEED_TIMEOUT PK_FEED_FEEDS PK_FEED_CACHE

# Restart the server cleanly
pkill -f "feed_server.py" 2>/dev/null
sleep 1

cd "$_DIR" || { echo "cannot cd to $_DIR" >&2; exit 1; }
nohup "$_PY" feed_server.py > /tmp/phonekit_feed.log 2>&1 &
sleep 2

_PORT="${PK_FEED_PORT:-8082}"
eips_center 20 "Opening feed reader..."
open_url "http://127.0.0.1:$_PORT"
sleep 2
eips_clear