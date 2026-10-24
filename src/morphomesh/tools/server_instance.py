"""
MorphoMesh Tools Subsystem: FastMCP Server Instance & Factory.

Initializes the default FastMCP server, registers all 19 pipeline tools,
and attaches runtime environment tool gating.
"""

from __future__ import annotations

import os
from mcp.server.fastmcp import FastMCP

from morphomesh.tools.gating import apply_tool_gating
from morphomesh.tools.registry import register_all_tools

mcp: FastMCP = FastMCP(
    name="MorphoMeshServer",
    instructions=(
        "Authoritative 3D creature generation pipeline and Blender bridge. "
        "Coordinates prompt engineering, image-to-3D diffusion, quad retopology, "
        "biomechanical auto-rigging, scene assembly, and EEVEE Next turntable rendering."
    ),
    host=os.environ.get("MORPHOMESH_HOST", "127.0.0.1"),
    port=int(os.environ.get("MORPHOMESH_PORT", "8765")),
)

# Register all 19 tools onto the server instance
register_all_tools(mcp)

# Apply runtime environment-variable tool gating
apply_tool_gating(mcp)


def create_mcp_server() -> FastMCP:
    """Factory creating configured FastMCP server instance."""
    return mcp


__all__ = [
    "mcp",
    "create_mcp_server",
]
