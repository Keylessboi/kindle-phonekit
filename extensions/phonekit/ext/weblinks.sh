#!/bin/sh
# PhoneKit AI Web Apps — aihub-style quick launcher for AI web UIs.
# aihub itself is an Android app (a WebView aggregator), so on a Kindle
# the equivalent is a browser launcher with your presets. Edit freely.

. "$(dirname "$0")/common.sh"

case "$1" in
    openwebui) URL="http://192.168.1.50:8080" ;;  # your self-hosted Open WebUI
    chatgpt)   URL="https://chatgpt.com" ;;
    claude)    URL="https://claude.ai" ;;
    gemini)    URL="https://gemini.google.com" ;;
    *)         URL="${1:-https://chatgpt.com}" ;;
esac

open_url "$URL"
