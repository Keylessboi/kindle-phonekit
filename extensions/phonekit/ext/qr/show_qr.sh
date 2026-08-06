#!/bin/sh
# PhoneKit QR — render text as a QR code on the e-ink screen via `eips -g`.
#
# Usage: show_qr.sh <text ...>
# The QR encoder is pure Python (stdlib only) and lives in ext/qr/qr.py.
# Intended for pairing: show a WiFi join string, a contact vCard, or a URL
# that the phone can scan.

. "$(dirname "$0")/../common.sh"

_PY=$(find_python3) || {
    eips_center 20 "python3 not found on device"
    sleep 3
    eips_clear
    exit 1
}

if [ "$#" -lt 1 ]; then
    eips_center 20 "usage: show_qr.sh <text>"
    sleep 3
    eips_clear
    exit 2
fi

eips_clear
"$_PY" "$(dirname "$0")/qr.py" "$@"
exit $?