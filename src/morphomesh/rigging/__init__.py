"""
MorphoMesh: Rigify Human Rigging & 52 ARKit FACS Blendshapes Subsystem.

Decomposed modular rigging package providing:
- metarig: 163 DEF bones metarig generator, bone hierarchy, bone roll math, and biological joint pivots.
- anti_pinch: Anti-pinch vertex skin weights, volume preservation, and dual-bone twist decomposition.
- blendshapes: 52 Apple ARKit standard FACS facial blendshape deltas.
- scripts: Authoritative in-Blender runtime rigging script generator and auto_rig_human entrypoint.
"""

from __future__ import annotations

from .anti_pinch import (
    _point_to_segment_distance,
    calculate_anti_pinch_weights,
    SkinWeightMap,
)
from .blendshapes import (
    ARKIT_52_BLENDSHAPES,
    generate_arkit_52_blendshapes,
)
from .metarig import (
    ALL_163_DEF_BONES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    align_rigify_metarig_pivots,
    BoneDefinition,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
    HumanRigConfig,
    MetarigStructure,
)
from .scripts import (
    auto_rig_human,
    get_rigging_script,
)

__all__ = [
    # Sub-modules
    "anti_pinch",
    "blendshapes",
    "metarig",
    "scripts",
    # Constants
    "BODY_DEF_BONES",
    "FACIAL_DEF_BONES",
    "ALL_163_DEF_BONES",
    "ARKIT_52_BLENDSHAPES",
    # Classes & Dataclasses
    "HumanRigConfig",
    "BoneDefinition",
    "MetarigStructure",
    "SkinWeightMap",
    # Functions
    "_point_to_segment_distance",
    "get_default_human_landmarks",
    "generate_rigify_human_metarig",
    "align_rigify_metarig_pivots",
    "calculate_anti_pinch_weights",
    "generate_arkit_52_blendshapes",
    "get_rigging_script",
    "auto_rig_human",
]
