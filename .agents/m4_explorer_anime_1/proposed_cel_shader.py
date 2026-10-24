"""
Master Cel-Shading & Angel Ring Node Orchestrator (Features F14 & F15).
Target: anime_pipeline/shading/cel_shader.py

Aggregates and exposes:
- Stepped Cel-Shading Node Trees from toon_materials.py (F14)
- Procedural Hair Angel Ring from angel_ring.py (F15)
"""

from __future__ import annotations

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

__all__ = [
    # Colors
    "SKIN_BASE_COLOR",
    "SKIN_SHADOW_COLOR",
    "CLOTHES_PRESETS",
    "EYE_IRIS_COLOR",
    "EYE_PUPIL_COLOR",
    "EYE_HIGHLIGHT_COLOR",
    "EYE_SCLERA_COLOR",
    "OUTLINE_COLOR",
    "HAIR_BASE_COLOR",
    "HAIR_SHADOW_COLOR",
    "ANGEL_RING_COLOR",
    "DEFAULT_CROWN_Z_MIN",
    "DEFAULT_CROWN_Z_MAX",
    # Functions
    "hex_to_rgba",
    "get_or_create_material",
    "build_anime_skin_material",
    "build_anime_clothes_material",
    "build_anime_eye_material",
    "build_anime_outline_material",
    "apply_all_toon_materials",
    "compute_hair_crown_z_bounds",
    "build_procedural_angel_ring_material",
    "apply_angel_ring_to_hair",
]
