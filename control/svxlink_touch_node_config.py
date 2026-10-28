#!/usr/bin/env python3
"""Restricted SvxLink-Touch remote node configuration helper."""

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


CONFIG_FILE = Path("/etc/svxlink-touch/nodes.json")


def normalise_url(address):
    """Validate a node URL and supply its default port."""
    if not isinstance(address, str) or not address.strip():
        raise ValueError("Node address is required")

    address = address.strip()

    if "://" not in address:
        address = "http://" + address

    parsed = urlsplit(address)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS are supported")

    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Invalid node address")

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid node port") from error

    if port is None:
        port = 443 if parsed.scheme == "https" else 5000

    if not 1 <= port <= 65535:
        raise ValueError("Invalid node port")

    hostname = parsed.hostname

    if ":" in hostname:
        hostname = f"[{hostname}]"

    return f"{parsed.scheme}://{hostname}:{port}"


def validate_node_name(name):
    if not isinstance(name, str):
        raise ValueError("Invalid node name")

    name = name.strip()

    if not 1 <= len(name) <= 64:
        raise ValueError("Node name must contain 1–64 characters")

    return name


def validate_node_id(node_id):
    if (
        not isinstance(node_id, str)
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", node_id)
        or node_id == "local"
    ):
        raise ValueError("Invalid remote node ID")

    return node_id


def load_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    if (
        not isinstance(config, dict)
        or config.get("schema_version") != 1
        or not isinstance(config.get("nodes"), list)
    ):
        raise ValueError("Invalid node configuration")

    return config


def save_config(config):
    """Atomically replace configuration without changing ownership."""
    directory = CONFIG_FILE.parent
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".nodes-",
            suffix=".json",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)

            json.dump(config, handle, indent=4)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.chmod(temporary_path, 0o644)
        os.chown(temporary_path, 0, 0)
        os.replace(temporary_path, CONFIG_FILE)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def modify_config(request):
    """Apply one validated remote-node change."""
    if not isinstance(request, dict):
        raise ValueError("Invalid request")

    operation = request.get("operation")

    if operation not in ("add", "edit", "remove"):
        raise ValueError("Unsupported configuration operation")

    config = load_config()
    nodes = config["nodes"]

    if operation == "add":
        if set(request) != {"operation", "id", "name", "url"}:
            raise ValueError("Invalid Add request")

        node_id = validate_node_id(request["id"])

        if any(node.get("id") == node_id for node in nodes):
            raise ValueError("Node ID already exists")

        nodes.append({
            "id": node_id,
            "name": validate_node_name(request["name"]),
            "url": normalise_url(request["url"]),
            "enabled": True,
            "local": False,
        })

    else:
        if operation == "edit":
            required = {"operation", "id", "name", "url"}
        else:
            required = {"operation", "id"}

        if set(request) != required:
            raise ValueError("Invalid configuration request")

        node_id = validate_node_id(request["id"])

        matching = [
            node for node in nodes
            if isinstance(node, dict) and node.get("id") == node_id
        ]

        if len(matching) != 1:
            raise ValueError("Remote node not found")

        node = matching[0]

        if node.get("local") is not False:
            raise ValueError("Local node cannot be modified")

        if operation == "edit":
            node["name"] = validate_node_name(request["name"])
            node["url"] = normalise_url(request["url"])
        else:
            nodes.remove(node)

    save_config(config)

    return {
        "success": True,
        "operation": operation,
        "node_id": node_id,
    }


def main():
    if len(sys.argv) != 1:
        raise ValueError("Command-line arguments are not accepted")

    if os.geteuid() != 0:
        raise PermissionError("Root privileges required")

    request = json.load(sys.stdin)
    result = modify_config(request)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({
            "success": False,
            "error": str(error),
        }))
        sys.exit(1)
