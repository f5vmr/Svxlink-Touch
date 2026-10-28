#!/usr/bin/env python3
"""SvxLink-Touch local web server."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import configparser
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
ASSETS_ROOT = PROJECT_ROOT / "assets"
SVXLINK_CONFIG_FILE = Path("/etc/svxlink/svxlink.conf")
TALKGROUP_FAVOURITES_FILE = Path(
    "/var/lib/svxlink-touch/talkgroups.json"
)
FEDERATION_TG_FILE = (
    PROJECT_ROOT / "config" / "federation_talkgroups.json"
)
# Use the installed configuration when available.
# Retain the existing repository configuration during migration.
INSTALLED_CONFIG_FILE = Path("/etc/svxlink-touch/nodes.json")
LEGACY_CONFIG_FILE = PROJECT_ROOT / "config" / "nodes.json"

CONFIG_FILE = (
    INSTALLED_CONFIG_FILE
    if INSTALLED_CONFIG_FILE.is_file()
    else LEGACY_CONFIG_FILE
)


def load_nodes():
    """Load the configured SvxLink nodes."""
    with CONFIG_FILE.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    if config.get("schema_version") != 1:
        raise ValueError("Unsupported node configuration schema")

    nodes = config.get("nodes")

    if not isinstance(nodes, list):
        raise ValueError("Node configuration must contain a nodes list")

    return [
        node for node in nodes
        if isinstance(node, dict) and node.get("enabled") is True
    ]
# Initial remote node for V0.4 testing.
REMOTE_NODE_URL = "http://192.168.1.214:5000/api/status"


def load_talkgroup_favourites():
    """Load and validate persistent touchscreen talkgroup favourites."""

    with TALKGROUP_FAVOURITES_FILE.open(
        "r", encoding="utf-8"
    ) as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Invalid favourites database")

    favourites = data.get("favorites")

    if not isinstance(favourites, list):
        raise ValueError("Missing favourites list")

    result = []
    seen = set()

    for entry in favourites:
        if not isinstance(entry, dict):
            raise ValueError("Invalid favourite entry")

        name = entry.get("name")
        number = entry.get("number")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid favourite name")

        if (
            type(number) is not int
            or number <= 0
        ):
            raise ValueError("Invalid favourite talkgroup number")

        if number in seen:
            continue

        seen.add(number)

        result.append({
            "name": name.strip(),
            "number": number,
            "source": "favourite",
        })

    return result


def load_monitored_talkgroups():
    """Discover locally monitored SvxReflector talkgroups."""

    parser = configparser.ConfigParser(
        interpolation=None,
        strict=False,
    )

    if not parser.read(SVXLINK_CONFIG_FILE):
        raise FileNotFoundError(
            f"Cannot read SvxLink configuration: {SVXLINK_CONFIG_FILE}"
        )

    if not parser.has_section("ReflectorLogic"):
        return []

    raw_value = parser.get(
        "ReflectorLogic",
        "MONITOR_TGS",
        fallback="",
    )

    with FEDERATION_TG_FILE.open(
        "r", encoding="utf-8"
    ) as handle:
        directory = json.load(handle)

    names = {
        entry["tg"]: entry["name"]
        for entry in directory["talkgroups"]
    }

    monitored = []
    seen = set()

    for item in raw_value.split(","):
        value = item.strip()

        if not value:
            continue

        if not value.isascii() or not value.isdecimal():
            raise ValueError(
                f"Invalid monitored talkgroup: {value}"
            )

        number = int(value)

        if number <= 0:
            raise ValueError(
                f"Invalid monitored talkgroup: {value}"
            )

        if number in seen:
            continue

        seen.add(number)

        monitored.append({
            "tg": number,
            "name": names.get(number, f"TG {number}"),
            "source": "monitored",
            "in_directory": number in names,
        })

    return monitored


class TouchHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        from urllib.parse import urlsplit

        request_path = urlsplit(self.path).path

        if request_path == "/api/node-status":
            self.handle_node_status()
            return

        if request_path == "/api/nodes":
            self.handle_nodes()
            return

        if request_path == "/api/talkgroups":
            self.handle_talkgroups()
            return

        if request_path == "/api/remote-status":
            self.handle_remote_status()
            return

        super().do_GET()

    def handle_talkgroup_control(self):
        """Forward an authorised local talkgroup request to the control service."""

        payload = {}
        status_code = 400

        try:
            origin = self.headers.get("Origin")

            if origin != "http://127.0.0.1:8080":
                raise ValueError(
                    "Control requests must originate from "
                    "the local SvxLink-Touch interface"
                )
            content_type = self.headers.get(
                "Content-Type", ""
            ).split(";", 1)[0].strip().lower()

            if content_type != "application/json":
                raise ValueError("JSON content required")

            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            if not 0 < content_length <= 4096:
                raise ValueError("Invalid request length")

            request_data = json.loads(
                self.rfile.read(content_length)
            )

            if (
                not isinstance(request_data, dict)
                or set(request_data) != {
                    "node_id", "action", "value"
                }
            ):
                raise ValueError("Invalid control request")

            node_id = request_data["node_id"]
            action = request_data["action"]
            value = request_data["value"]

            if (
                not isinstance(node_id, str)
                or action != "talkgroup"
                or type(value) is not int
                or value <= 0
            ):
                raise ValueError("Invalid talkgroup request")

            nodes = load_nodes()

            node = next(
                (
                    entry for entry in nodes
                    if entry.get("id") == node_id
                ),
                None,
            )

            if node is None:
                status_code = 404
                raise ValueError("Unknown or disabled node")

            if node.get("local") is not True:
                raise ValueError(
                    "Remote talkgroup control is not yet available"
                )

            # Authorise only the configured local node.
            # The control service independently validates
            # the talkgroup, active logic and PTY.
            control_request = {
                "action": "talkgroup",
                "value": value,
            }

            with socket.socket(
                socket.AF_UNIX,
                socket.SOCK_STREAM,
            ) as connection:
                connection.settimeout(3.0)
                connection.connect(
                    "/run/svxlink-touch/control.sock"
                )

                connection.sendall(
                    (
                        json.dumps(control_request) + "\n"
                    ).encode("utf-8")
                )

                with connection.makefile(
                    "r", encoding="utf-8"
                ) as response:
                    result = json.loads(
                        response.readline(4096)
                    )

            if not isinstance(result, dict):
                raise ValueError("Invalid control service response")

            payload = {
                "success": result.get("success") is True,
                "node_id": node_id,
                "command": result.get("command"),
                "transmitted": result.get("transmitted") is True,
                "error": result.get("error"),
            }

            status_code = (
                200 if payload["success"] else 400
            )

        except (ValueError, TypeError, KeyError) as error:
            payload = {
                "success": False,
                "transmitted": False,
                "error": str(error),
            }

        except (OSError, TimeoutError) as error:
            status_code = 503
            payload = {
                "success": False,
                "transmitted": False,
                "error": str(error),
            }

        result = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(result)

    def handle_node_status(self):
        """Retrieve status for a configured SvxLink node."""
        from urllib.parse import parse_qs, urlsplit

        query = parse_qs(urlsplit(self.path).query)
        node_id = query.get("id", [""])[0]

        try:
            nodes = load_nodes()

            node = next(
                (item for item in nodes if item["id"] == node_id),
                None,
            )

            if node is None:
                payload = {
                    "connected": False,
                    "error": "Unknown or disabled node",
                }
                status_code = 404

            else:
                endpoint = node["url"].rstrip("/") + "/api/status"

                try:
                    with urlopen(endpoint, timeout=5) as response:
                        data = json.load(response)

                    payload = {
                        "connected": True,
                        "node_id": node_id,
                        "name": node["name"],
                        "data": data,
                    }
                    status_code = 200

                except (HTTPError, URLError, TimeoutError, ValueError) as error:
                    payload = {
                        "connected": False,
                        "node_id": node_id,
                        "name": node["name"],
                        "error": str(error),
                    }
                    status_code = 502

        except (OSError, ValueError, KeyError, TypeError) as error:
            payload = {
                "connected": False,
                "error": str(error),
            }
            status_code = 500

        result = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(result)

    def handle_talkgroups(self):
        """Return shared favourites and locally monitored talkgroups."""
        from urllib.parse import parse_qs, urlsplit

        query = parse_qs(urlsplit(self.path).query)
        node_id = query.get("id", [""])[0]

        try:
            nodes = load_nodes()

            node = next(
                (item for item in nodes if item["id"] == node_id),
                None,
            )

            if node is None:
                payload = {
                    "available": False,
                    "error": "Unknown or disabled node",
                }
                status_code = 404

            else:
                favourites = load_talkgroup_favourites()

                monitored = (
                    load_monitored_talkgroups()
                    if node.get("local") is True
                    else []
                )

                payload = {
                    "available": True,
                    "node_id": node_id,
                    "talkgroups": monitored,
                    "favorites": favourites,
                }
                status_code = 200

        except (OSError, ValueError, KeyError, TypeError) as error:
            payload = {
                "available": False,
                "node_id": node_id,
                "talkgroups": [],
                "error": str(error),
            }
            status_code = 500

        result = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(result)

    def do_POST(self):
        """Route supported touchscreen control requests."""
        from urllib.parse import urlsplit

        request_path = urlsplit(self.path).path

        if request_path == "/api/talkgroup-control":
            self.handle_talkgroup_control()
            return

        self.send_error(404, "Unknown control endpoint")

    def handle_nodes(self):
        """Return the enabled nodes configured for SvxLink-Touch."""
        try:
            nodes = load_nodes()

            payload = {
                "nodes": [
                    {
                        "id": node["id"],
                        "name": node["name"],
                        "local": node.get("local", False),
                    }
                    for node in nodes
                ]
            }

            status_code = 200

        except (OSError, ValueError, KeyError, TypeError) as error:
            payload = {
                "nodes": [],
                "error": str(error),
            }

            status_code = 500

        result = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(result)

    def handle_remote_status(self):
        try:
            with urlopen(REMOTE_NODE_URL, timeout=5) as response:
                data = json.load(response)

            payload = {
                "connected": True,
                "source": REMOTE_NODE_URL,
                "data": data,
            }

            status_code = 200

        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            payload = {
                "connected": False,
                "source": REMOTE_NODE_URL,
                "error": str(error),
            }

            status_code = 502

        result = json.dumps(payload).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(result)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(result)

    def translate_path(self, path):
        from urllib.parse import unquote, urlsplit

        requested = unquote(urlsplit(path).path)

        if requested == "/assets" or requested.startswith("/assets/"):
            relative = requested.removeprefix("/assets").lstrip("/")
            root = ASSETS_ROOT
        else:
            relative = requested.lstrip("/")
            root = WEB_ROOT

        target = (root / relative).resolve()

        if not target.is_relative_to(root.resolve()):
            return str(WEB_ROOT / "__not_found__")

        return str(target)


def main():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 8080),
        TouchHandler,
    )

    print("SvxLink-Touch listening on http://127.0.0.1:8080",
          flush=True)

    server.serve_forever()


if __name__ == "__main__":
    main()
