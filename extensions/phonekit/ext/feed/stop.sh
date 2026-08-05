#!/bin/sh
# PhoneKit Feed Reader - stop the local feed server.

. "$(dirname "$0")/../common.sh"

pkill -f "feed_server.py" 2>/dev/null
eips_center 20 "Feed reader stopped"
sleep 2
eips_clear