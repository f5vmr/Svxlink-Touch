
#!/usr/bin/env bash
#
# SvxLink-Touch tty2 startup integration
#
# Intended to be sourced from the kiosk user's login profile.
#

if [[ "$(tty)" == "/dev/tty2" ]] &&
   [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
    /usr/local/bin/svxlink-touch-kiosk
fi
