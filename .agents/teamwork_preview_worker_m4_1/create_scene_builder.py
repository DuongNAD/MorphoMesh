import os
import json

with open('src/morphomesh/character_assembler.py', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()

# Lines 50 to 1498
# Line 50 is logger = ...
# Line 1498 is return master_script
body_lines = lines[49:1499]

header = '''"""
MorphoMesh: Character Assembly Scene Builder Subsystem.

Manages in-Blender collection hierarchy (7-tier architecture),
calibrated studio 3-point lighting setups, multi-angle camera rigs
(turntable, front/side ortho, hero 3/4 portrait, canonical beauty cameras),
and authoritative master assembly script generation for Yu Nian An.
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
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

'''

content = header + '\n'.join(body_lines) + '\n'

# Add __all__
export_names = [
    "ROOT_COLLECTION_NAME",
    "TIER_COLLECTION_NAMES",
    "SEVEN_TIER_COLLECTION_HIERARCHY",
    "ALL_SEVEN_COLLECTIONS",
    "FINGER_LANDMARK_KEYS",
    "FINGER_DEF_BONE_KEYS",
    "MATERIAL_NAMES",
    "STANDARD_HUMAN_MATERIALS",
    "STANDARDIZED_HUMAN_VERTEX_GROUPS",
    "ALL_163_DEF_BONES",
    "BODY_DEF_BONES",
    "FACIAL_DEF_BONES",
    "ARKIT_52_BLENDSHAPES",
    "MasterAssemblyConfig",
    "_get_uv_unwrapping_script_snippet",
    "assign_texture_atlas_uvs",
    "get_master_assembly_script",
    # Helper mocks & re-exports
    "HAS_BPY",
    "_MockVector",
    "_MockEuler",
    "_MockMatrix",
    "_MockMathutils",
    "Vector",
    "Euler",
    "Matrix",
    "mathutils",
]

content += f"\n__all__ = {json.dumps(export_names, indent=4)}\n"

with open('src/morphomesh/assembler/scene_builder.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("scene_builder.py created successfully!")
