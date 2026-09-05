"""
MorphoMesh: Blender Addon Package Root.

Registers viewport UI panel, creature generation operators, and launches
the background non-blocking socket listener synchronized via bpy.app.timers.
"""

bl_info = {
    "name": "MorphoMesh Bridge",
    "author": "MorphoMesh Core Architecture Team",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > MorphoMesh",
    "description": "MorphoMesh AI 3D Creature Generation & Google Antigravity 2.0 Bridge",
    "category": "3D View",
}

import bpy
from .operators import register_operators, unregister_operators
from .listener import get_server


def register():
    register_operators()
    # Start the non-blocking timer server automatically
    server = get_server()
    if not server.is_running():
        server.start()


def unregister():
    server = get_server()
    if server.is_running():
        server.stop()
    unregister_operators()


if __name__ == "__main__":
    register()
