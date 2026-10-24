"""
MorphoMesh: Anthropometric Procedural Human Subsystem.

Decomposed modular human generator package providing:
- mold_loader: MakeHuman CC0 base mold loading, caching, landmark extraction, and vertex group partitioning.
- morphology: Anthropometric proportions, quad dominance metrics, quad capping, and config resolution.
- anatomy: HumanAnatomyGenerator, HumanMeshResult, and high-level base mesh generators.
- scripts: Authoritative in-Blender runtime script generator.
"""

from __future__ import annotations

try:
    from morphomesh.geometry.mesh import MeshGeometry
    from morphomesh.models import BoundingBox, HumanAnatomyConfig, HumanAssetResult
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]
    from ..models import BoundingBox, HumanAnatomyConfig, HumanAssetResult  # type: ignore[no-redef]

from .anatomy import (
    ARKIT_52_BLENDSHAPES,
    HumanAnatomyGenerator,
    HumanMeshResult,
    generate_human_base_mesh,
    generate_human_body,
)
from .mold_loader import (
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    _BASE_LANDMARKS_CACHE,
    _BASE_MOLD_CACHE,
    _get_templates_dir,
    compute_relaxed_vertex_normals,
    compute_standardized_vertex_groups,
    enforce_quad_closure,
    extract_makehuman_joint_landmarks,
    load_anatomical_base_mold,
)
from .morphology import (
    PRESET_ALIASES,
    PROPORTION_PRESETS,
    add_quad_cap,
    add_quad_ellipsoid,
    compute_quad_metrics,
    resolve_human_anatomy_config,
)
from .scripts import get_human_generation_script

__all__ = [
    # Sub-modules
    "anatomy",
    "mold_loader",
    "morphology",
    "scripts",
    # Constants & Presets
    "STANDARDIZED_HUMAN_VERTEX_GROUPS",
    "ARKIT_52_BLENDSHAPES",
    "PROPORTION_PRESETS",
    "PRESET_ALIASES",
    # Classes & Dataclasses
    "HumanMeshResult",
    "HumanAnatomyGenerator",
    "HumanAnatomyConfig",
    "HumanAssetResult",
    "BoundingBox",
    "MeshGeometry",
    # Functions
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
