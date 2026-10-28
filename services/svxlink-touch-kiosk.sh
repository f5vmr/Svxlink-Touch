
#!/usr/bin/env bash
#
# SvxLink-Touch kiosk launcher
# Raspberry Pi OS Lite / Debian Trixie
#
set -Eeuo pipefail

URL="${SVXLINK_TOUCH_URL:-http://127.0.0.1:8080/}"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Wait for the SvxLink-Touch web interface to accept connections.
if [[ "$URL" == http://127.0.0.1:8080/* ]]; then
    for attempt in {1..30}; do
        if /usr/bin/curl --silent --fail --output /dev/null \
            --max-time 1 http://127.0.0.1:8080/; then
            break
        fi
        sleep 1
    done
fi

exec /usr/bin/cage -s -- /usr/bin/chromium \
    --ozone-platform=wayland \
    --no-first-run \
    --no-default-browser-check \
    --disk-cache-size=0 \
    --kiosk \
    "$URL"
