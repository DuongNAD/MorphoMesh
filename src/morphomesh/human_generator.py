"""
MorphoMesh: Anthropometric Procedural Human Generator Facade.

Refactored into backward-compatible facade re-exporting all symbols from
the morphomesh.human modular sub-package.
"""

from __future__ import annotations

from morphomesh.human import (
    ARKIT_52_BLENDSHAPES,
    PRESET_ALIASES,
    PROPORTION_PRESETS,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    BoundingBox,
    HumanAnatomyConfig,
    HumanAnatomyGenerator,
    HumanAssetResult,
    HumanMeshResult,
    MeshGeometry,
    _BASE_LANDMARKS_CACHE,
    _BASE_MOLD_CACHE,
    _get_templates_dir,
    add_quad_cap,
    add_quad_ellipsoid,
    compute_quad_metrics,
    compute_relaxed_vertex_normals,
    compute_standardized_vertex_groups,
    enforce_quad_closure,
    extract_makehuman_joint_landmarks,
    generate_human_base_mesh,
    generate_human_body,
    get_human_generation_script,
    load_anatomical_base_mold,
    resolve_human_anatomy_config,
)

__all__ = [
    "STANDARDIZED_HUMAN_VERTEX_GROUPS",
    "ARKIT_52_BLENDSHAPES",
    "PROPORTION_PRESETS",
    "PRESET_ALIASES",
    "HumanMeshResult",
    "HumanAnatomyGenerator",
    "HumanAnatomyConfig",
    "HumanAssetResult",
    "BoundingBox",
    "MeshGeometry",
    "compute_quad_metrics",
    "add_quad_cap",
    "add_quad_ellipsoid",
    "_get_templates_dir",
    "load_anatomical_base_mold",
    "extract_makehuman_joint_landmarks",
    "enforce_quad_closure",
    "compute_relaxed_vertex_normals",
    "compute_standardized_vertex_groups",
    "resolve_human_anatomy_config",
    "generate_human_base_mesh",
    "generate_human_body",
    "get_human_generation_script",
]
