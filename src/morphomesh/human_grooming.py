"""
MorphoMesh: Digital Human Geometry Nodes Hair Curves Grooming Facade.

Refactored into backward-compatible facade re-exporting all symbols from
the morphomesh.grooming modular sub-package.
"""

from __future__ import annotations

from morphomesh.grooming import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    _calc_spline_length,
    build_hair_geom_node_tree,
    convert_curves_to_ribbon_mesh,
    generate_6_stratum_hime_cut_splines,
    generate_hime_cut_splines,
    get_6_stratum_hime_cut_layers,
    get_default_hime_cut_layers,
    get_grooming_script,
    groom_human,
)

__all__ = [
    "HairLayerConfig",
    "HairGroomConfig",
    "HairCurveSpline",
    "_calc_spline_length",
    "get_6_stratum_hime_cut_layers",
    "get_default_hime_cut_layers",
    "generate_hime_cut_splines",
    "generate_6_stratum_hime_cut_splines",
    "convert_curves_to_ribbon_mesh",
    "build_hair_geom_node_tree",
    "get_grooming_script",
    "groom_human",
]
