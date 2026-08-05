#!/bin/sh
# PhoneKit read-it-later — stop the local server.

. "$(dirname "$0")/../common.sh"

pkill -f "reader_server.py" 2>/dev/null
eips_center 20 "Reader server stopped"
sleep 2
eips_clear