
#!/usr/bin/env bash
#
# SvxLink-Touch kiosk launcher
# Raspberry Pi OS Lite / Debian Trixie
#
set -Eeuo pipefail

URL="${SVXLINK_TOUCH_URL:-http://127.0.0.1:5000/status}"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

exec /usr/bin/cage -s -- /usr/bin/chromium \
    --ozone-platform=wayland \
    --no-first-run \
    --no-default-browser-check \
    --kiosk \
    "$URL"
