#!/bin/sh
# PhoneKit Notes — stop the notes server.

. "$(dirname "$0")/../common.sh"

pkill -f "notes_server.py" 2>/dev/null
eips_center 20 "Notes server stopped"
sleep 2
eips_clear