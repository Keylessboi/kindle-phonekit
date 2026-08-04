#!/bin/sh
# PhoneKit XMPP bridge — run the on-screen XMPP listener in the background.

. "$(dirname "$0")/../common.sh"
_DIR="$(dirname "$0")"
_PY=$(find_python3) || {
    eips_center 20 "python3 not found on device"
    sleep 3
    eips_clear
    exit 1
}

if [ -f "$_DIR/config.env" ]; then
    . "$_DIR/config.env"
fi
export PK_XMPP_JID PK_XMPP_PASS PK_XMPP_HOST PK_XMPP_PORT PK_XMPP_NO_VERIFY PK_XMPP_POPUP PK_XMPP_DEBUG PK_XMPP_INBOX

if [ -z "$PK_XMPP_JID" ] || [ -z "$PK_XMPP_PASS" ]; then
    eips_center 20 "Set PK_XMPP_JID/PASS first"
    sleep 3
    eips_clear
    exit 1
fi

pkill -f "bridge.py" 2>/dev/null
sleep 1

cd "$_DIR"
nohup "$_PY" bridge.py > /tmp/phonekit_xmpp.log 2>&1 &
sleep 3

eips_center 20 "XMPP bridge started"
sleep 2
eips_clear