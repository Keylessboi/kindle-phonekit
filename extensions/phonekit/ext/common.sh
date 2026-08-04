#!/bin/sh
# PhoneKit shared helpers. Source this from every script:
#     . "$(dirname "$0")/common.sh"

export PATH=/usr/bin:/bin:/usr/sbin:/sbin:$PATH

# --- Screen geometry (pixels) ----------------------------------------------
SCREEN_W=600
SCREEN_H=800
if [ -r /sys/class/graphics/fb0/virtual_size ]; then
    _vs=$(cat /sys/class/graphics/fb0/virtual_size 2>/dev/null)
    case "$_vs" in
        *,*) SCREEN_W=${_vs%,*}; SCREEN_H=${_vs#*,};;
    esac
fi

# eips font metrics (approximate: 8px wide, 16px tall per glyph)
CH_W=8
CH_H=16

# --- eips helpers -----------------------------------------------------------
# eips_center <y> <text> : draw text centered horizontally at vertical offset y
eips_center() {
    _y=$1
    _text="$2"
    _x=$(( (SCREEN_W - ${#_text} * CH_W) / 2 ))
    [ "$_x" -lt 0 ] && _x=0
    eips "$_x" "$_y" "$_text"
}

eips_clear() {
    eips -c
}

# --- Python 3 discovery -----------------------------------------------------
# find_python3 : echo the path of a usable python3, or return nonzero
find_python3() {
    for _p in python3 /usr/bin/python3 /mnt/us/python3/bin/python3 /mnt/base-us/python3/bin/python3; do
        if command -v "$_p" >/dev/null 2>&1 || [ -x "$_p" ]; then
            echo "$_p"
            return 0
        fi
    done
    return 1
}

# --- Browser ----------------------------------------------------------------
# open_url <url> : open a URL in the Experimental Browser
open_url() {
    _url="$1"
    if [ -x /usr/bin/xopen ]; then
        /usr/bin/xopen "$_url"
        return 0
    fi
    lipc-set-prop com.lab126.appmgrd start app://com.lab126.browser 2>/dev/null
    sleep 1
    lipc-set-prop com.lab126.browser url "$_url" 2>/dev/null
    return 0
}
