#!/bin/sh
# PhoneKit XMPP — send a one-tap status check-in to PK_XMPP_CHECKIN_JID.
#
# Usage: checkin.sh <preset|text>
# Presets live in bridge.py (CHECKINS): here, away, busy, ok, night.
# Any other argument is sent verbatim as the message body.

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
export PK_XMPP_JID PK_XMPP_PASS PK_XMPP_HOST PK_XMPP_PORT \
    PK_XMPP_NO_VERIFY PK_XMPP_CHECKIN_JID

if [ "$#" -lt 1 ]; then
    eips_center 20 "usage: checkin.sh <preset|text>"
    sleep 3
    eips_clear
    exit 2
fi

"$_PY" "$_DIR/bridge.py" checkin "$@"
exit $?