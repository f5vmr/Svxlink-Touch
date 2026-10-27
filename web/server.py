#!/usr/bin/env python3
"""SvxLink-Touch local web server."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "web"
ASSETS_ROOT = PROJECT_ROOT / "assets"


class TouchHandler(SimpleHTTPRequestHandler):
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
