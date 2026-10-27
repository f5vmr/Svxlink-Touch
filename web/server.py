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

# Initial remote node for V0.4 testing.
REMOTE_NODE_URL = "http://192.168.1.214:5000/api/status"


class TouchHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        from urllib.parse import urlsplit

        if urlsplit(self.path).path == "/api/remote-status":
            self.handle_remote_status()
            return

        super().do_GET()

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
