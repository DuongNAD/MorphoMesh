"""
MorphoMesh: Volumetric Fur & Digital Human Hair Curves Grooming Subsystem.

Decomposed modular grooming package providing:
- hime_cut: 6-stratum hime cut hair strata definitions, parameters, and 3D spline curves generator.
- ribbons: Offline & real-time polygonal quad ribbon mesh extrusion from hair curves.
- curves_pipeline: Blender 4.5+ Geometry Nodes hair modifier network builder.
- scripts: Standalone Blender script generator and groom_human entrypoint.
- creature: Quadruped volumetric fur grooming engine and biological flow vector fields.
"""

from __future__ import annotations

from .creature import (
    FULL_FUR_GROUPS,
    MODULATED_FUR_GROUPS,
    ZERO_FUR_GROUPS,
    CreatureGroomingEngine,
    FurLayerConfig,
    compute_biological_flow_vector,
    evaluate_fur_ribbons_for_gltf,
    get_default_guard_hair_config,
    get_default_undercoat_config,
    setup_volumetric_fur,
)
from .curves_pipeline import build_hair_geom_node_tree
from .hime_cut import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    _calc_spline_length,
    generate_6_stratum_hime_cut_splines,
    generate_hime_cut_splines,
    get_6_stratum_hime_cut_layers,
    get_default_hime_cut_layers,
)
from .ribbons import convert_curves_to_ribbon_mesh
from .scripts import (
    get_grooming_script,
    groom_human,
)

__all__ = [
    # Sub-modules
    "creature",
    "curves_pipeline",
    "hime_cut",
    "ribbons",
    "scripts",
    # Human Hair Grooming Configs & Dataclasses
    "HairLayerConfig",
    "HairGroomConfig",
    "HairCurveSpline",
    # Human Hair Functions
    "_calc_spline_length",
    "get_6_stratum_hime_cut_layers",
    "get_default_hime_cut_layers",
    "generate_hime_cut_splines",
    "generate_6_stratum_hime_cut_splines",
    "convert_curves_to_ribbon_mesh",
    "build_hair_geom_node_tree",
    "get_grooming_script",
    "groom_human",
    # Creature Volumetric Fur Grooming
    "ZERO_FUR_GROUPS",
    "FULL_FUR_GROUPS",
    "MODULATED_FUR_GROUPS",
    "FurLayerConfig",
    "get_default_undercoat_config",
    "get_default_guard_hair_config",
    "compute_biological_flow_vector",
    "CreatureGroomingEngine",
    "setup_volumetric_fur",
    "evaluate_fur_ribbons_for_gltf",
]
