#!/bin/sh
# PhoneKit LLM — stop the local chat server.

. "$(dirname "$0")/../common.sh"

pkill -f "llm_server.py" 2>/dev/null
eips_center 20 "LLM server stopped"
sleep 2
eips_clear