
#!/usr/bin/env bash
#
# SvxLink-Touch — Initial Installation
# Target: Raspberry Pi OS Lite 64-bit (Debian Trixie)
#
# Installs the graphical dependencies confirmed during
# the initial Raspberry Pi 3B development.
#
set -Eeuo pipefail

log() {
    printf '[SvxLink-Touch] %s\n' "$*"
}

fail() {
    printf '[SvxLink-Touch] ERROR: %s\n' "$*" >&2
    exit 1
}

if [[ $EUID -ne 0 ]]; then
    fail "Run this installer with sudo."
fi

if [[ ! -r /etc/os-release ]]; then
    fail "Cannot identify the operating system."
fi

# shellcheck disable=SC1091
source /etc/os-release

if [[ "${VERSION_CODENAME:-}" != "trixie" ]]; then
    fail "This installer currently supports Debian Trixie only."
fi

ARCH="$(dpkg --print-architecture)"

if [[ "$ARCH" != "arm64" ]]; then
    fail "Expected arm64; detected $ARCH."
fi

log "Operating system: ${PRETTY_NAME:-unknown}"
log "Architecture: $ARCH"

if [[ -r /proc/device-tree/model ]]; then
    MODEL="$(tr -d '\0' < /proc/device-tree/model)"
    log "Hardware: $MODEL"
else
    log "Hardware model: unavailable"
fi

log "Checking display hardware..."

if [[ -d /dev/dri ]]; then
    ls -l /dev/dri/
else
    log "WARNING: DRM graphics devices not detected."
fi

log "Checking touchscreen input..."

if [[ -r /proc/bus/input/devices ]]; then
    grep -i -E 'touch|ft5x06|ft5406|goodix' \
        /proc/bus/input/devices || true
fi

log "Checking display modes..."

FOUND_MODE=0

for MODE_FILE in /sys/class/drm/card*-DSI-*/modes; do
    if [[ -f "$MODE_FILE" ]]; then
        log "$MODE_FILE:"
        cat "$MODE_FILE"
        FOUND_MODE=1
    fi
done

if [[ "$FOUND_MODE" -eq 0 ]]; then
    log "No DSI modes found; another display interface may be used."
fi

log "Updating package lists..."
apt-get update

log "Installing Cage and Chromium..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    cage \
    chromium

log "Installed versions:"

cage -v
chromium --version

log "Initial installation completed successfully."
log "Graphical launch and autostart are not yet configured."
