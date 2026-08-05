#!/bin/sh
# PhoneKit dashboard — start the local dashboard server and open it in the
# browser. Usage:
#     ./start.sh          start server, open it in the browser
#     ./start.sh boot      start server only (no browser), for auto-start
#
# AUTO-START: to make the dashboard come up on boot, copy this script to an
# init entry that runs it with the "boot" argument with no display, e.g. add
#     /mnt/us/extensions/phonekit/ext/dashboard/start.sh boot
# to an initd/cron @reboot hook. A shutdown script can be pointed at
# stop.sh. The server keeps its cached feed between refreshes, so booting the
# browser later just shows the last-rendered page.

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
export PK_DASH_PORT PK_DASH_URL PK_DASH_NAME

# Restart the server cleanly
pkill -f "dashboard_server.py" 2>/dev/null
sleep 1

cd "$_DIR"
nohup "$_PY" dashboard_server.py > /tmp/phonekit_dash.log 2>&1 &
sleep 2

_PORT="${PK_DASH_PORT:-8084}"

if [ "$1" = "boot" ]; then
    # No browser on boot: a cron/lipc wake opens /render later on schedule.
    eips_center 20 "Dashboard server up (boot)"
    sleep 2
    eips_clear
    exit 0
fi

eips_center 20 "Opening dashboard..."
open_url "http://127.0.0.1:$_PORT"
sleep 2
eips_clear