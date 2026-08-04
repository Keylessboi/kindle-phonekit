#!/bin/sh
# PhoneKit Clock — full-screen e-ink clock.
# 24h by default; KUAL param "12" switches to 12h with AM/PM.
# Press Home to exit.

. "$(dirname "$0")/common.sh"

FMT="%H:%M:%S"
[ "$1" = "12" ] && FMT="%I:%M:%S %p"

# Fixed-width sample lets us center the clock on any screen size.
_SAMPLE=$(date +"$FMT")
_X=$(( (SCREEN_W - ${#_SAMPLE} * CH_W) / 2 ))
_Y=$(( (SCREEN_H / 2) - CH_H ))

eips_clear
_COUNT=0
trap 'eips_clear; exit 0' INT TERM HUP

while true; do
    NOW=$(date +"$FMT")
    eips "$_X" "$_Y" "$NOW"
    _COUNT=$((_COUNT + 1))
    # Full refresh once a minute to scrub e-ink ghosting.
    if [ "$_COUNT" -ge 60 ]; then
        eips_clear
        _COUNT=0
    fi
    sleep 1
done
