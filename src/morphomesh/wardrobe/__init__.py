"""
MorphoMesh: Parametric Digital Human Wardrobe & Magic Props Subsystem.

Decomposed modular wardrobe package providing:
- skinning: Rigify DEF bone weights, vertex group mapping, pin weights, and material aliases.
- props: Luminous white swallowtail butterflies, upward vortex flocking, and crimson marionette strings.
- garments: White slip dress (bodice, 20-pleat skirt), empire waist sash & bow, strappy flat sandals.
- scripts: Standalone Blender 4.5+ LTS script generator and dress_human entrypoint.
"""

from __future__ import annotations

from .garments import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_organic_skirt,
    generate_dress_pleated_skirt,
    generate_dress_skirt,
    generate_dress_waist_sash,
    generate_flat_sandals,
    generate_flat_strappy_sandals,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_yu_nian_an_wardrobe,
)
from .props import (
    BUTTERFLY_FLUTTER_POSITIONS,
    generate_catenary_magic_strings,
    generate_glowing_butterflies,
    generate_marionette_red_strings,
    generate_marionette_strings,
    generate_swallowtail_butterfly,
    generate_swallowtail_quad_butterfly,
    get_butterfly_flutter_positions,
    get_butterfly_vortex_positions,
)
from .scripts import (
    dress_human,
    get_wardrobe_script,
)
from .skinning import (
    FINGER_DEF_BONE_ALIASES,
    FINGER_DEF_BONE_KEYS,
    MATERIAL_NAME_ALIASES,
    assign_bodice_skin_weights,
    assign_dress_pin_weights,
    assign_sash_skin_weights,
    assign_skirt_skin_weights,
    compute_dress_waist_radii,
    compute_wardrobe_skin_weights,
    resolve_finger_def_bone_name,
)

__all__ = [
    # Sub-modules
    "garments",
    "props",
    "scripts",
    "skinning",
    # Constants & Aliases
    "FINGER_DEF_BONE_KEYS",
    "FINGER_DEF_BONE_ALIASES",
    "MATERIAL_NAME_ALIASES",
    "BUTTERFLY_FLUTTER_POSITIONS",
    "resolve_finger_def_bone_name",
    # Configuration
    "WardrobeConfig",
    # Skinning & Pinning
    "compute_dress_waist_radii",
    "assign_dress_pin_weights",
    "assign_bodice_skin_weights",
    "assign_skirt_skin_weights",
    "assign_sash_skin_weights",
    "compute_wardrobe_skin_weights",
    # Garment Generators
    "generate_dress_bodice",
    "generate_dress_waist_sash",
    "generate_dress_organic_skirt",
    "generate_dress_pleated_skirt",
    "generate_dress_skirt",
    "generate_organic_dress",
    "generate_waist_sash_and_bow",
    "generate_flat_strappy_sandals",
    "generate_flat_sandals",
    "generate_yu_nian_an_wardrobe",
    # Magic Props Generators
    "get_butterfly_vortex_positions",
    "get_butterfly_flutter_positions",
    "generate_catenary_magic_strings",
    "generate_marionette_red_strings",
    "generate_marionette_strings",
    "generate_swallowtail_quad_butterfly",
    "generate_swallowtail_butterfly",
    "generate_glowing_butterflies",
    # Scripts & Entrypoints
    "get_wardrobe_script",
    "dress_human",
]
