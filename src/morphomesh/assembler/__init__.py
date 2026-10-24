"""
MorphoMesh: Character Assembler Subsystem.

Decomposed modular sub-package providing:
- scene_builder: 7-tier collection hierarchy, calibrated 3-point lighting setups,
  orthographic / portrait / beauty camera rigs, and master assembly script generator.
- pbr_baker: 4K PBR procedural texture synthesis pipeline (BaseColor, Normal,
  Roughness, Metallic, SSS, Alpha, Height, packed ORM, HDRP MaskMap).
- packager: Multi-format production asset packaging (.blend, .fbx, .glb),
  archive generation, and documentation manifests.
- assembler: Core YuNianAnAssembler coordinating full mesh assembly, metarig alignment,
  wardrobe fitting, hair groom binding, and scene creation.
"""

from __future__ import annotations

import logging

from .scene_builder import (
    ALL_163_DEF_BONES,
    ALL_SEVEN_COLLECTIONS,
    ARKIT_52_BLENDSHAPES,
    BODY_DEF_BONES,
    Euler,
    FACIAL_DEF_BONES,
    FINGER_DEF_BONE_KEYS,
    FINGER_LANDMARK_KEYS,
    HAS_BPY,
    MATERIAL_NAMES,
    MasterAssemblyConfig,
    Matrix,
    ROOT_COLLECTION_NAME,
    SEVEN_TIER_COLLECTION_HIERARCHY,
    STANDARD_HUMAN_MATERIALS,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    TIER_COLLECTION_NAMES,
    Vector,
    _MockEuler,
    _MockMathutils,
    _MockMatrix,
    _MockVector,
    _get_uv_unwrapping_script_snippet,
    assign_texture_atlas_uvs,
    get_master_assembly_script,
    mathutils,
)
from .pbr_baker import generate_yu_nian_an_pbr_textures
from .packager import (
    _resolve_blender_binary,
    export_production_assets,
    get_export_script,
)
from .assembler import (
    CharacterAssembler,
    YuNianAnAssembler,
    YuNianAnCharacterAssembler,
    assemble_master_character,
)

logger = logging.getLogger("morphomesh.assembler")

__all__ = [
    # Sub-modules
    "scene_builder",
    "pbr_baker",
    "packager",
    "assembler",
    # Constants
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
    # Config & Assembler Classes
    "MasterAssemblyConfig",
    "YuNianAnAssembler",
    "CharacterAssembler",
    "YuNianAnCharacterAssembler",
    # Functions
    "_get_uv_unwrapping_script_snippet",
    "assign_texture_atlas_uvs",
    "get_master_assembly_script",
    "generate_yu_nian_an_pbr_textures",
    "_resolve_blender_binary",
    "get_export_script",
    "export_production_assets",
    "assemble_master_character",
    # Compatibility & Simulation Utilities
    "HAS_BPY",
    "Vector",
    "Euler",
    "Matrix",
    "mathutils",
    "_MockVector",
    "_MockEuler",
    "_MockMatrix",
    "_MockMathutils",
    "logger",
]
