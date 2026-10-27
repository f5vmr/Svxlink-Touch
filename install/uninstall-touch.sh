
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
        TOUCH_AUTLOGIN_REMOVED=1
        log "Removed SvxLink-Touch tty2 autologin configuration."
    else
        log "Preserving externally managed tty2 configuration."
    fi
fi

rmdir \
    /etc/systemd/system/getty@tty2.service.d \
    2>/dev/null || true
# Disable tty2 autostart only when our configuration was removed.
if [[ "${TOUCH_AUTLOGIN_REMOVED:-0}" == "1" ]]; then
    log "Disabling SvxLink-Touch tty2 autostart..."
    systemctl disable getty@tty2.service
fi

# Remove the SvxLink-Touch console activation service.
CONSOLE_SERVICE="/etc/systemd/system/svxlink-touch-console.service"

if [[ -f "$CONSOLE_SERVICE" ]]; then
    log "Disabling SvxLink-Touch console activation..."

    systemctl disable svxlink-touch-console.service

    rm -f "$CONSOLE_SERVICE"

    log "Removed SvxLink-Touch console activation service."
fi

# Remove the SvxLink-Touch web service.
WEB_SERVICE="/etc/systemd/system/svxlink-touch-web.service"

if [[ -f "$WEB_SERVICE" ]]; then
    log "Stopping and disabling SvxLink-Touch web service..."

    systemctl disable --now svxlink-touch-web.service

    rm -f "$WEB_SERVICE"

    log "Removed SvxLink-Touch web service."
fi

# Remove SvxLink-Touch DTMF control units.
CONTROL_SOCKET="/etc/systemd/system/svxlink-touch-control.socket"
CONTROL_SERVICE="/etc/systemd/system/svxlink-touch-control.service"

if [[ -f "$CONTROL_SOCKET" || -f "$CONTROL_SERVICE" ]]; then
    log "Removing SvxLink-Touch DTMF control service..."

    systemctl disable --now svxlink-touch-control.socket 2>/dev/null || true
    systemctl stop svxlink-touch-control.service 2>/dev/null || true

    rm -f "$CONTROL_SOCKET" "$CONTROL_SERVICE"

    log "Removed SvxLink-Touch DTMF control units."
fi

# Preserve installation-specific node configuration.
if [[ -f /etc/svxlink-touch/nodes.json ]]; then
    log "Preserving node configuration: /etc/svxlink-touch/nodes.json"
fi

# Preserve installation-specific talkgroup favourites.
if [[ -f /var/lib/svxlink-touch/talkgroups.json ]]; then
    log "Preserving talkgroup favourites: /var/lib/svxlink-touch/talkgroups.json"
fi

systemctl daemon-reload

log "Kiosk integration removed."
log "Existing graphical session has not been terminated."
log "SvxLink, Dashboard, Cage and Chromium remain installed."
log "A subsequent tty2 login will use its remaining configuration."
