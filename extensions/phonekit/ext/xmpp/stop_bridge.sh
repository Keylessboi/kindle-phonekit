#!/bin/sh
# PhoneKit XMPP bridge — stop the on-screen listener.

. "$(dirname "$0")/../common.sh"

pkill -f "bridge.py" 2>/dev/null
eips_center 20 "XMPP bridge stopped"
sleep 2
eips_clear