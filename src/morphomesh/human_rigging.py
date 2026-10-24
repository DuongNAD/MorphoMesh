"""
MorphoMesh: Rigify Human Rigging & 52 ARKit FACS Blendshapes Facade.

Refactored into backward-compatible facade re-exporting all symbols from
the morphomesh.rigging modular sub-package.
"""

from __future__ import annotations

from morphomesh.rigging import (
    ALL_163_DEF_BONES,
    ARKIT_52_BLENDSHAPES,
    BODY_DEF_BONES,
    BoneDefinition,
    FACIAL_DEF_BONES,
    HumanRigConfig,
    MetarigStructure,
    SkinWeightMap,
    _point_to_segment_distance,
    align_rigify_metarig_pivots,
    auto_rig_human,
    calculate_anti_pinch_weights,
    generate_arkit_52_blendshapes,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
    get_rigging_script,
)

__all__ = [
    "BODY_DEF_BONES",
    "FACIAL_DEF_BONES",
    "ALL_163_DEF_BONES",
    "ARKIT_52_BLENDSHAPES",
    "HumanRigConfig",
    "BoneDefinition",
    "MetarigStructure",
    "SkinWeightMap",
    "_point_to_segment_distance",
    "get_default_human_landmarks",
    "generate_rigify_human_metarig",
    "align_rigify_metarig_pivots",
    "calculate_anti_pinch_weights",
    "generate_arkit_52_blendshapes",
    "get_rigging_script",
    "auto_rig_human",
]
