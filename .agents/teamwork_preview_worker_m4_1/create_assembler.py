import os

with open('src/morphomesh/character_assembler.py', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()

# Lines 1504 to 1923
# Line 1504 is class YuNianAnAssembler
# Line 1923 is return assembler.assemble(output_path=target_output)
body_lines = lines[1504:1924]

header = '''"""
MorphoMesh: Yu Nian An Character Assembler Orchestrator Subsystem.

Coordinates the end-to-end procedural assembly and validation of the complete
digital human character scene (7-tier collection hierarchy, PBR materials,
Rigify 163 DEF armature, 52 ARKit blendshapes, 6-strata hair curves,
physically draped wardrobe, and magical marionette props).
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
    ROOT_COLLECTION_NAME,
    TIER_COLLECTION_NAMES,
    SEVEN_TIER_COLLECTION_HIERARCHY,
    ALL_SEVEN_COLLECTIONS,
    FINGER_LANDMARK_KEYS,
    FINGER_DEF_BONE_KEYS,
    MATERIAL_NAMES,
    STANDARD_HUMAN_MATERIALS,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    ALL_163_DEF_BONES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    ARKIT_52_BLENDSHAPES,
    MasterAssemblyConfig,
    get_master_assembly_script,
    HAS_BPY,
)
from morphomesh.human_generator import (
    HumanAnatomyConfig,
    HumanMeshResult,
    generate_human_base_mesh,
)
from morphomesh.human_grooming import (
    HairGroomConfig,
    get_default_hime_cut_layers,
)
from morphomesh.human_materials import (
    HumanMaterialConfig,
    HumanPBRSuite,
)
from morphomesh.human_rigging import (
    HumanRigConfig,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.wardrobe import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_pleated_skirt,
    generate_dress_waist_sash,
    generate_flat_sandals,
    generate_marionette_red_strings,
    generate_swallowtail_butterfly,
    generate_yu_nian_an_wardrobe,
)

from .pbr_baker import generate_yu_nian_an_pbr_textures
from .packager import (
    _resolve_blender_binary,
    get_export_script,
    export_production_assets,
)

try:
    import bpy
except (ImportError, ModuleNotFoundError):
    bpy = None

logger = logging.getLogger("morphomesh.assembler.assembler")

'''

content = header + '\n'.join(body_lines) + '\n'

content += '''
YuNianAnCharacterAssembler = YuNianAnAssembler

__all__ = [
    "YuNianAnAssembler",
    "CharacterAssembler",
    "YuNianAnCharacterAssembler",
    "assemble_master_character",
]
'''

with open('src/morphomesh/assembler/assembler.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("assembler.py created successfully!")
