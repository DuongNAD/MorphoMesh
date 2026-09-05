"""
MorphoMesh: CLI Entrypoint.

Provides the command-line interface for running the MorphoMesh FastMCP server,
probing Blender connectivity, and packaging the Blender addon.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from morphomesh import __version__
from morphomesh.blender_bridge import BlenderBridge
from morphomesh.server import mcp


def main() -> None:
    """Primary CLI dispatcher."""
    parser = argparse.ArgumentParser(
        prog="morphomesh",
        description="MorphoMesh: 3D Creature Generation Pipeline & FastMCP Server for Blender and Google Antigravity 2.0",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"MorphoMesh v{__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to execute")

    # 'server' / 'run' command
    server_parser = subparsers.add_parser("server", help="Start the FastMCP server")
    server_parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    server_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address for SSE transport (default: 127.0.0.1)",
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port number for SSE transport (default: 8765)",
    )
    server_parser.add_argument(
        "--backend",
        choices=["mock", "replicate", "huggingface"],
        default="mock",
        help="Inference engine backend (default: mock)",
    )
    server_parser.add_argument(
        "--blender-path",
        default=None,
        help="Path to Blender 5.2.1 LTS executable",
    )

    # 'ping' command
    subparsers.add_parser("ping", help="Probe connectivity to Blender")

    # 'status' command
    subparsers.add_parser("status", help="Inspect active Blender scene status")

    # 'package-addon' command
    subparsers.add_parser("package-addon", help="Package Blender addon into a zip distribution")

    args = parser.parse_args()

    # Default to running server over stdio if no subcommand is given
    cmd = args.command or "server"

    if cmd == "server":
        transport = getattr(args, "transport", "stdio")
        backend = getattr(args, "backend", "mock")
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8765)
        blender_path = getattr(args, "blender_path", None)

        os.environ["MORPHOMESH_BACKEND"] = backend
        os.environ["MORPHOMESH_HOST"] = host
        os.environ["MORPHOMESH_PORT"] = str(port)
        if blender_path:
            os.environ["BLENDER_BIN_PATH"] = blender_path

        mcp.settings.host = host
        mcp.settings.port = port

        # Run server
        mcp.run(transport=transport)

    elif cmd == "ping":
        bridge = BlenderBridge()
        connected = bridge.is_interactive_connected()
        print(f"Interactive TCP Socket (127.0.0.1:9876): {'CONNECTED' if connected else 'DISCONNECTED'}")
        print(f"Blender Binary Detected: {bridge.blender_bin_path or 'NOT FOUND'}")
        try:
            res = bridge.ping()
            print("Ping probe response:", res)
        except Exception as e:
            print("Ping probe failed:", e)
            sys.exit(1)

    elif cmd == "status":
        bridge = BlenderBridge()
        try:
            status = bridge.get_scene_status()
            print(f"Scene: {status.scene_name}")
            print(f"Blender Version: {status.blender_version}")
            print(f"Objects ({status.object_count}):")
            for obj in status.objects:
                print(f" - {obj.name} ({obj.type}): {obj.vertex_count} verts, {obj.face_count} faces")
        except Exception as e:
            print("Failed to query scene status:", e)
            sys.exit(1)

    elif cmd == "package-addon":
        from blender_addon.package_addon import package_addon
        zip_path = package_addon()
        print(f"Addon successfully packaged: {zip_path}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
