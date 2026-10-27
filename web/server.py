#!/usr/bin/env python3
"""SvxLink-Touch local web server."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
ASSETS_ROOT = PROJECT_ROOT / "assets"
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

        if request_path == "/api/remote-status":
            self.handle_remote_status()
            return

        super().do_GET()

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
