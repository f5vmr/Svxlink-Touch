
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


#
# SvxLink-Touch V0.2 — Kiosk installation
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

KIOSK_USER="${SVXLINK_TOUCH_USER:-${SUDO_USER:-pi}}"
KIOSK_HOME="$(getent passwd "$KIOSK_USER" | cut -d: -f6)"

if [[ -z "$KIOSK_HOME" || "$KIOSK_HOME" == "/" ]]; then
    fail "Cannot determine home directory for $KIOSK_USER."
fi

log "Installing kiosk for user: $KIOSK_USER"

# Configure tty2 automatic login.
AUTLOGIN_FILE="/etc/systemd/system/getty@tty2.service.d/autologin.conf"

if [[ -e "$AUTLOGIN_FILE" ]]; then
    if ! grep -Fq '# Managed by SvxLink-Touch' "$AUTLOGIN_FILE"; then
        fail "Existing tty2 autologin configuration found. Refusing to overwrite it."
    fi
fi

# Install the graphical launcher.
install -o root -g root -m 0755 \
    "$PROJECT_DIR/services/svxlink-touch-kiosk.sh" \
    /usr/local/bin/svxlink-touch-kiosk

# Install the tty2 startup integration.
install -d -o root -g root -m 0755 \
    /usr/local/lib/svxlink-touch

install -o root -g root -m 0644 \
    "$PROJECT_DIR/services/svxlink-touch-profile.sh" \
    /usr/local/lib/svxlink-touch/profile.sh

install -d -m 0755 \
    /etc/systemd/system/getty@tty2.service.d

cat > "$AUTLOGIN_FILE" <<EOF
# Managed by SvxLink-Touch
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $KIOSK_USER --noclear %I \$TERM
EOF

# Ensure the login shell invokes the kiosk integration.
BASH_PROFILE="$KIOSK_HOME/.bash_profile"
PROFILE_MARKER="# BEGIN SVXLINK-TOUCH"

if [[ ! -f "$BASH_PROFILE" ]]; then
    cat > "$BASH_PROFILE" <<'EOF'
# Load the normal user profile.
if [ -f "$HOME/.profile" ]; then
    . "$HOME/.profile"
fi
EOF
    chown "$KIOSK_USER:" "$BASH_PROFILE"
fi

if ! grep -Fq "$PROFILE_MARKER" "$BASH_PROFILE"; then
    cat >> "$BASH_PROFILE" <<'EOF'

# BEGIN SVXLINK-TOUCH
if [ -f /usr/local/lib/svxlink-touch/profile.sh ]; then
    . /usr/local/lib/svxlink-touch/profile.sh
fi
# END SVXLINK-TOUCH
EOF
fi

log "Validating tty2 configuration..."
systemd-analyze verify getty@tty2.service

log "Reloading systemd configuration..."
systemctl daemon-reload

log "Kiosk files installed."
log "Automatic startup will take effect at the next tty2 login."

log "SvxLink-Touch V0.2 installation completed successfully."
log "Kiosk startup configured for tty2."
log "The graphical session will start at the next tty2 login."
