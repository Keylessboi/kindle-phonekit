#!/bin/sh
# PhoneKit dashboard — stop the local dashboard server.

. "$(dirname "$0")/../common.sh"

pkill -f "dashboard_server.py" 2>/dev/null
eips_center 20 "Dashboard server stopped"
sleep 2
eips_clear