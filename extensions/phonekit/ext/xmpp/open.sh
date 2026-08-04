#!/bin/sh
# PhoneKit XMPP — open a browser-based XMPP client.
# KUAL params: pass a URL directly, or "custom" to use the configured URL.

. "$(dirname "$0")/../common.sh"
_DIR="$(dirname "$0")"

if [ -f "$_DIR/config.env" ]; then
    . "$_DIR/config.env"
fi

case "$1" in
    custom|"") _URL="$PK_XMPP_URL" ;;
    *)         _URL="$1" ;;
esac

eips_center 20 "Opening XMPP client..."
open_url "$_URL"
sleep 2
eips_clear