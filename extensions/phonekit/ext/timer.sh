#!/bin/sh
# PhoneKit Timer — countdown in seconds. Default 5 minutes.
# Change the "params" for this item in menu.json (300 = 5 min, 900 = 15 min).
# Press Home to exit. The full-screen flash at the end is the "alarm"
# (Kindles have no speaker).

. "$(dirname "$0")/common.sh"

_SECS=${1:-300}
case "$_SECS" in
    *[!0-9]*) _SECS=300;;
esac
_END=$(( $(date +%s) + _SECS ))

# "MM:SS" is always 5 characters wide
_X=$(( (SCREEN_W - 5 * CH_W) / 2 ))
_Y=$(( (SCREEN_H / 2) - CH_H ))

eips_clear
trap 'eips_clear; exit 0' INT TERM HUP

while [ "$(date +%s)" -lt "$_END" ]; do
    _LEFT=$(( _END - $(date +%s) ))
    _LABEL=$(printf '%02d:%02d' $((_LEFT / 60)) $((_LEFT % 60)))
    eips "$_X" "$_Y" "$_LABEL"
    sleep 1
done

eips_clear
eips_center $((SCREEN_H / 2 - CH_H)) "TIMER DONE"
eips -f
sleep 5
eips_clear
