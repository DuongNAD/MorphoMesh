"""
MorphoMesh: Blender Script Generators Package.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from morphomesh.bridge.constants import SENTINEL_END, SENTINEL_START
from morphomesh.bridge.scripts.base_scripts import (
    get_base_headless_snippet_part1,
    get_base_headless_snippet_part2,
    get_base_interactive_snippet,
)
from morphomesh.bridge.scripts.camera_scripts import (
    get_camera_headless_snippet,
    get_camera_interactive_snippet,
)
from morphomesh.bridge.scripts.creature_scripts import (
    get_creature_armature_headless_snippet,
    get_creature_assets_headless_snippet,
    get_creature_interactive_snippet,
)
from morphomesh.bridge.scripts.human_scripts import (
    generate_auto_rig_human_script,
    generate_create_human_asset_script,
    get_human_headless_snippet,
)


def build_interactive_script(method: str, params: Dict[str, Any]) -> str:
    """Generate an AST-safe in-Blender script without forbidden built-ins."""
    ser_params = json.dumps(params)
    header = f"""import bpy
import json
import math
import mathutils

_params = json.loads({repr(ser_params)})
_method = {repr(method)}
_morphomesh_result = {{"status": "success", "method": _method}}
"""
    body = (
        get_base_interactive_snippet()
        + get_camera_interactive_snippet()
        + get_creature_interactive_snippet()
    )
    return header + body


def build_headless_script(method: str, params: Dict[str, Any]) -> str:
    """Generate a standalone Python script embedding parameter JSON."""
    if method == "morphomesh.create_human_asset":
        return generate_create_human_asset_script(params)
    if method in ("morphomesh.auto_rig_human", "auto_rig_human"):
        return generate_auto_rig_human_script(params)

    serialized_params = json.dumps(params)
    c_arm_name = f"Armature_{params.get('creature_type', 'quadruped').title()}"

    header = f"""
import bpy
import json
import os
import math
import mathutils
import uuid
import tempfile

params = json.loads({repr(serialized_params)})
method = {repr(method)}

def emit_result(data):
    print("{SENTINEL_START}")
    print(json.dumps(data))
    print("{SENTINEL_END}")

def ensure_auto_camera(scene=None):
    if scene is None:
        scene = bpy.context.scene
    if scene.camera and scene.camera.name in scene.objects:
        return scene.camera

    # Compute bounding box of all mesh objects
    mesh_objs = [o for o in scene.objects if o.type == 'MESH']
    min_x, min_y, min_z = float('inf'), float('inf'), float('inf')
    max_x, max_y, max_z = float('-inf'), float('-inf'), float('-inf')
    for o in mesh_objs:
        for corner in o.bound_box:
            mat = o.matrix_world
            wc = mat @ mathutils.Vector(corner)
            min_x = min(min_x, wc.x)
            min_y = min(min_y, wc.y)
            min_z = min(min_z, wc.z)
            max_x = max(max_x, wc.x)
            max_y = max(max_y, wc.y)
            max_z = max(max_z, wc.z)

    if min_x == float('inf'):
        center = mathutils.Vector((0.0, 0.0, 1.0))
        radius = 2.0
    else:
        center = mathutils.Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
        radius = max(max_x - min_x, max_y - min_y, max_z - min_z) / 2.0 or 2.0

    cam_data = bpy.data.cameras.new(name="MorphoMesh_AutoCam")
    cam_obj = bpy.data.objects.new(name="MorphoMesh_AutoCam", object_data=cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    dist = radius * 3.5
    cam_obj.location = center + mathutils.Vector((dist * 0.7, -dist * 0.7, dist * 0.5))
    direction = center - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    return cam_obj

try:
"""
    body = (
        get_base_headless_snippet_part1()
        + get_creature_armature_headless_snippet(c_arm_name)
        + get_base_headless_snippet_part2()
        + get_creature_assets_headless_snippet()
        + get_human_headless_snippet()
        + get_camera_headless_snippet()
    )
    trailer = f"""    else:
        emit_result({{"status": "error", "message": f"Unknown RPC method: {{method}}"}})


except Exception as e:
    import traceback
    emit_result({{"status": "error", "message": str(e), "traceback": traceback.format_exc()}})
"""
    return header + body + trailer


__all__ = [
    "build_interactive_script",
    "build_headless_script",
    "generate_create_human_asset_script",
    "generate_auto_rig_human_script",
]
