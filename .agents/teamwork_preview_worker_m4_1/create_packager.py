import os
import json

with open('src/morphomesh/character_assembler.py', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()

# Lines 1928 to 2066 (functions _resolve_blender_binary, get_export_script)
# Line 1928 is def _resolve_blender_binary
# Line 2066 is return script
# Lines 2343 to 2430 (export_production_assets)
part1 = lines[1928:2067]
part2 = lines[2343:2431]

header = '''"""
MorphoMesh: Production Multi-Format Packager Subsystem.

Provides automated packaging, bundling, and multi-format asset export
(glTF 2.0 binary, FBX with ARKit FACS morph targets and Rigify DEF armature,
Blend scenes, textures, and export documentation manifests).
"""

from __future__ import annotations

import logging
import os
import sys
import json
import math
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from .scene_builder import (
    _get_uv_unwrapping_script_snippet,
    assign_texture_atlas_uvs,
    HAS_BPY,
)
from .pbr_baker import generate_yu_nian_an_pbr_textures

try:
    import bpy
except (ImportError, ModuleNotFoundError):
    bpy = None

logger = logging.getLogger("morphomesh.assembler.packager")

'''

code_body = '\n'.join(part1) + '\n\n' + '\n'.join(part2) + '\n'

# Update FBX export block to bake_anim=True, use_mesh_modifiers=False so ARKit FACS blendshapes export to FBX
old_fbx = '''    primary_bone_axis='Y',
    secondary_bone_axis='X',
    bake_anim=False,
)'''

new_fbx = '''    primary_bone_axis='Y',
    secondary_bone_axis='X',
    bake_anim=True,
    use_mesh_modifiers=False,
)'''

code_body = code_body.replace(old_fbx, new_fbx)

content = header + code_body

content += '''
__all__ = [
    "_resolve_blender_binary",
    "get_export_script",
    "export_production_assets",
]
'''

with open('src/morphomesh/assembler/packager.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("packager.py created successfully!")
