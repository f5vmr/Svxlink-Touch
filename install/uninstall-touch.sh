
#!/usr/bin/env bash
#
# SvxLink-Touch — Kiosk Uninstaller V0.2
#
# Removes SvxLink-Touch kiosk integration.
# Preserves SvxLink, Dashboard, Cage and Chromium.
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
    fail "Run this uninstaller with sudo."
fi

KIOSK_USER="${SVXLINK_TOUCH_USER:-${SUDO_USER:-pi}}"
KIOSK_HOME="$(getent passwd "$KIOSK_USER" | cut -d: -f6)"

if [[ -z "$KIOSK_HOME" || "$KIOSK_HOME" == "/" ]]; then
    fail "Cannot determine home directory for $KIOSK_USER."
fi

PROFILE="$KIOSK_HOME/.bash_profile"

log "Removing SvxLink-Touch kiosk integration..."

# Remove only a complete SvxLink-Touch startup section.
if [[ -f "$PROFILE" ]] &&
   grep -Fxq '# BEGIN SVXLINK-TOUCH' "$PROFILE"; then

    if ! grep -Fxq '# END SVXLINK-TOUCH' "$PROFILE"; then
        fail "Incomplete SvxLink-Touch section in $PROFILE. Refusing to modify it."
    fi

    cp -p "$PROFILE" "${PROFILE}.svxlink-touch-backup"

    sed -i \
        '/^# BEGIN SVXLINK-TOUCH$/,/^# END SVXLINK-TOUCH$/d' \
        "$PROFILE"

    log "Removed kiosk startup from $PROFILE"
fi

# Remove application-owned files.
rm -f /usr/local/bin/svxlink-touch-kiosk

rm -f /usr/local/lib/svxlink-touch/profile.sh

rmdir /usr/local/lib/svxlink-touch 2>/dev/null || true

# Remove only an autologin configuration owned by SvxLink-Touch.
AUTLOGIN_FILE="/etc/systemd/system/getty@tty2.service.d/autologin.conf"

if [[ -f "$AUTLOGIN_FILE" ]]; then
    if grep -Fqx '# Managed by SvxLink-Touch' "$AUTLOGIN_FILE"; then
        rm -f "$AUTLOGIN_FILE"
        log "Removed SvxLink-Touch tty2 autologin configuration."
    else
        log "Preserving externally managed tty2 configuration."
    fi
fi

rmdir \
    /etc/systemd/system/getty@tty2.service.d \
    2>/dev/null || true

systemctl daemon-reload

log "Kiosk integration removed."
log "Existing graphical session has not been terminated."
log "SvxLink, Dashboard, Cage and Chromium remain installed."
log "A subsequent tty2 login will use its remaining configuration."
