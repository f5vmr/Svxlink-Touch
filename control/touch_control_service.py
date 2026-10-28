
#!/usr/bin/env python3

"""
SvxLink-Touch V0.4
Restricted DTMF control-service handler.

Accepts authorised talkgroup and module requests through
the systemd-activated Unix socket.

Validates the requested command and SvxLink destination.
Transmits DTMF only when explicitly enabled in the
operational configuration.
"""

import json
import sys
import socket

from dtmf_control import (
    build_module_command,
    build_talkgroup_command,
    write_validated_dtmf,
)

from svxlink_config import (
    discover_dtmf_logics,
    select_dtmf_logic,
    validate_dtmf_destination,
    validate_runtime_pty,
    get_monitored_talkgroups,
    get_configured_macros,
)

from pathlib import Path

TALKGROUP_FAVOURITES_FILE = Path(
    "/var/lib/svxlink-touch/talkgroups.json"
)


def load_favourites():
    """Read SvxLink-Touch's persistent talkgroup favourites."""

    with TALKGROUP_FAVOURITES_FILE.open(
        "r", encoding="utf-8"
    ) as handle:
        data = json.load(handle)

    favourites = data.get("favorites")

    if not isinstance(favourites, list):
        raise ValueError("Invalid talkgroup favourites database")

    return favourites


# Live transmission is subject to request and PTY validation.
ENABLE_DTMF_TRANSMISSION = True

def discover_control_destination(logic_name=None, config_path=None):
    """
    Discover and validate an active SvxLink DTMF destination.

    Single radio logic: selected automatically.
    Multiple radio logics: explicit selection required.

    No PTY is opened and no DTMF is transmitted.
    """

    if config_path is None:
        destinations = discover_dtmf_logics()
    else:
        destinations = discover_dtmf_logics(config_path)

    destination = select_dtmf_logic(
        destinations,
        logic_name=logic_name,
    )

    if logic_name is None:
        logic_name = next(
            name
            for name, entry in destinations.items()
            if entry is destination
        )

    pty = validate_dtmf_destination(
        logic_name,
        destination,
    )

    return {
        "logic": logic_name,
        "type": destination["type"],
        "pty": pty,
    }


def load_touch_control_config():
    """
    Build Touch operational control settings from
    the actual SvxLink radio logic configuration.

    No DTMF is transmitted.
    """

    destinations = discover_dtmf_logics()

    if len(destinations) != 1:
        raise ValueError(
            "Exactly one radio DTMF logic is required"
        )

    destination = discover_control_destination()

    return {
        "control": {
            "node_type": destination["type"],
            "transmission_enabled": True,
        },
        "modules": [],
    }


def process_request(request, config):
    """
    Validate and process an authorised DTMF control request.

    Only named operations are permitted.
    Arbitrary DTMF strings are not accepted.
    """

    if not isinstance(request, dict):
        raise ValueError("Request must be a JSON object")

    if set(request) != {"action", "value"}:
        raise ValueError("Invalid request fields")

    action = request["action"]
    value = request["value"]

    if action == "talkgroup":

        # Authorise against the persistent operational
        # favourites database, not the installation defaults.
        favourites = load_favourites()

        matching = [
            entry
            for entry in favourites
            if (
                type(value) is int
                and entry["number"] == value
            )
        ]

        if matching:
            authorised_number = matching[0]["number"]

        else:
            # Monitored TGs may be selected without
            # first being saved as favourites.
            monitored = get_monitored_talkgroups()

            if (
                type(value) is not int
                or not any(
                    entry["tg"] == value
                    for entry in monitored
                )
            ):
                raise ValueError(
                    "Talkgroup is neither a favourite "
                    "nor a monitored talkgroup"
                )

            authorised_number = value

        command = build_talkgroup_command(
            authorised_number
        )

    elif action == "module":

        modules = config["modules"]

        matching = [
            entry
            for entry in modules
            if entry["name"] == value
        ]

        if not matching:
            raise ValueError(
                "Module is not configured"
            )

        command = build_module_command(
            matching[0]["dtmf_id"]
        )

    elif action == "macro":

        # Macro identifiers are strings.
        # Leading zeros must be preserved.
        if (
            type(value) is not str
            or not value
            or not value.isascii()
            or not value.isdecimal()
        ):
            raise ValueError(
                "Invalid macro identifier"
            )

        # Read the actual SvxLink configuration.
        # Do not trust macro definitions supplied
        # through the control socket.
        macro_config = get_configured_macros()

        matching = [
            entry
            for entry in macro_config["macros"]
            if entry["id"] == value
        ]

        if not matching:
            raise ValueError(
                "Macro is not configured"
            )

        # The macro invocation is constructed by
        # the trusted configuration parser.
        # Its definition is executed by SvxLink,
        # not by the Touch control service.
        command = matching[0]["command"]

    else:
        raise ValueError(
            "Unsupported control action"
        )

    # Resolve the destination from the actual SvxLink
    # configuration, not from a caller-supplied PTY.
    #
    # A single radio logic is selected automatically.
    # Multiple radio logics are rejected until an
    # explicit port-selection mechanism is provided.

    destination = discover_control_destination()

    # Validate the actual SvxLink PTY before
    # attempting authorised DTMF transmission.
    resolved_pty = validate_runtime_pty(
        destination["pty"]
    )

    transmitted = False

    control = config.get("control", {})

    configured_type = control.get("node_type")
    actual_type = destination["type"]

    if (
        ENABLE_DTMF_TRANSMISSION
        and control.get("transmission_enabled") is True
        and configured_type != actual_type
    ):
        raise ValueError(
            f"Touch node type '{configured_type}' does not match "
            f"SvxLink logic type '{actual_type}'"
        )

    live_enabled = (
        ENABLE_DTMF_TRANSMISSION
        and control.get("transmission_enabled") is True
        and configured_type == actual_type
        and len(discover_dtmf_logics()) == 1
    )

    if live_enabled:
        write_validated_dtmf(
            command,
            destination["pty"],
        )
        transmitted = True

    return {
        "success": True,
        "action": action,
        "command": command,
        "logic": destination["logic"],
        "pty": destination["pty"],
        "resolved_pty": resolved_pty,
        "transmitted": transmitted,
    }


def main():
    """
    Process repeated requests through a systemd-activated
    Unix socket.

    Process authorised requests through a systemd-activated Unix socket.
    """

    import os

    listen_fds = int(os.environ.get("LISTEN_FDS", "0"))
    listen_pid = int(os.environ.get("LISTEN_PID", "0"))

    if listen_fds != 1 or listen_pid != os.getpid():
        raise RuntimeError(
            "Expected one systemd-activated socket"
        )

    with socket.socket(fileno=3) as server:

        try:
            config = load_touch_control_config()
            control = config.get("control", {})

            live_enabled = (
                ENABLE_DTMF_TRANSMISSION
                and control.get("transmission_enabled") is True
            )

            if live_enabled:
                destination = discover_control_destination()

                live_enabled = (
                    control.get("node_type") == destination["type"]
                    and len(discover_dtmf_logics()) == 1
                )

            mode = (
                "live transmission enabled"
                if live_enabled
                else "preview only"
            )

        except (ValueError, OSError, KeyError) as exc:
            mode = f"control unavailable: {exc}"

        print(
            f"SvxLink-Touch control service ready ({mode})",
            flush=True,
        )

        while True:

            connection, _ = server.accept()

            with connection:

                try:
                    connection.settimeout(3.0)

                    with connection.makefile(
                        "r",
                        encoding="utf-8",
                    ) as reader:
                        request = json.loads(
                            reader.readline(4096)
                        )

                    config = load_touch_control_config()

                    result = process_request(
                        request,
                        config,
                    )

                except (
                    ValueError,
                    TypeError,
                    KeyError,
                    OSError,
                ) as error:

                    result = {
                        "success": False,
                        "error": str(error),
                        "transmitted": False,
                    }

                try:
                    connection.sendall(
                        (
                            json.dumps(result) + "\n"
                        ).encode("utf-8")
                    )
                except OSError:
                    pass


if __name__ == "__main__":
    main()
