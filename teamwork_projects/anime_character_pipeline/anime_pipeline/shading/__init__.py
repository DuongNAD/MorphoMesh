"""
Anime Shading Package (Milestone 4).
Exposes Stepped Cel-Shading, Procedural Angel Ring, and Inverted Hull Outlines.
"""

from .toon_materials import (
    SKIN_BASE_COLOR,
    SKIN_SHADOW_COLOR,
    CLOTHES_PRESETS,
    EYE_IRIS_COLOR,
    EYE_PUPIL_COLOR,
    EYE_HIGHLIGHT_COLOR,
    EYE_SCLERA_COLOR,
    OUTLINE_COLOR,
    hex_to_rgba,
    get_or_create_material,
    build_anime_skin_material,
    build_anime_clothes_material,
    build_anime_eye_material,
    build_anime_outline_material,
    apply_all_toon_materials,
    apply_toon_materials_to_scene,
)

from .angel_ring import (
    HAIR_BASE_COLOR,
    HAIR_SHADOW_COLOR,
    ANGEL_RING_COLOR,
    DEFAULT_CROWN_Z_MIN,
    DEFAULT_CROWN_Z_MAX,
    compute_hair_crown_z_bounds,
    build_procedural_angel_ring_material,
    apply_angel_ring_to_hair,
)

from .inverted_hull import (
    OUTLINE_MODIFIER_NAME,
    OUTLINE_MATERIAL_NAME,
    DEFAULT_OUTLINE_THICKNESS,
    DEFAULT_OUTLINE_OFFSET,
    DEFAULT_OUTLINE_COLOR,
    DEFAULT_OUTLINE_STRENGTH,
    SOLIDIFY_OUTLINE_THICKNESS,
    CANONICAL_MESH_NAMES,
    OutlineConfig,
    OutlineResult,
    create_or_get_outline_material,
    apply_outline_modifier_to_object,
    apply_inverted_hull_outline,
    apply_inverted_hull_outlines,
    remove_inverted_hull_outline,
    validate_solidify_outline_dict,
)

from .cel_shader import *
