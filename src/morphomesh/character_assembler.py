"""
MorphoMesh: Yu Nian An Master Character Assembler Facade.

Refactored into backward-compatible facade re-exporting all symbols from
the morphomesh.assembler modular sub-package.
"""

from __future__ import annotations

from morphomesh.assembler import (
    ALL_163_DEF_BONES,
    ALL_SEVEN_COLLECTIONS,
    ARKIT_52_BLENDSHAPES,
    BODY_DEF_BONES,
    CharacterAssembler,
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
    YuNianAnAssembler,
    YuNianAnCharacterAssembler,
    _MockEuler,
    _MockMathutils,
    _MockMatrix,
    _MockVector,
    _get_uv_unwrapping_script_snippet,
    _resolve_blender_binary,
    assemble_master_character,
    assign_texture_atlas_uvs,
    export_production_assets,
    generate_yu_nian_an_pbr_textures,
    get_export_script,
    get_master_assembly_script,
    logger,
    mathutils,
    scene_builder,
    pbr_baker,
    packager,
    assembler,
)

# Re-export upstream domain types for full backwards compatibility
from morphomesh.human_generator import (
    HumanAnatomyConfig,
    HumanMeshResult,
    generate_human_base_mesh,
    get_human_generation_script,
)
from morphomesh.human_grooming import (
    HairGroomConfig,
    get_default_hime_cut_layers,
    get_grooming_script,
)
from morphomesh.human_materials import (
    HumanMaterialConfig,
    HumanPBRSuite,
    get_material_setup_script,
)
from morphomesh.human_rigging import (
    HumanRigConfig,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
    get_rigging_script,
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
    get_wardrobe_script,
)

__all__ = [
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
    # Submodules
    "scene_builder",
    "pbr_baker",
    "packager",
    "assembler",
]
