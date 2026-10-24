"""
MorphoMesh: Visual Quality Critique Subsystem.

Decomposed modular sub-package providing:
- geometry_math: 3D vector algebra, ray-triangle intersection (Möller–Trumbore),
  triangle-triangle collision (Möller), Eberly distance, and AABB primitives.
- bvh: PurePythonBVHTree spatial bounding volume hierarchy for fast ray casting and nearest-neighbor lookup.
- penetration: Cloth-body, cloth-cloth, hair-body mesh penetration detection and collision depth analysis.
- proportions: Anthropometric proportions evaluation (head ratios, limb lengths, golden ratio aesthetic critique).
- deformation: Extreme pose mesh deformation inspection, volume conservation, acute creases, joint collapse detection.
- reporter: Quality critique scoring, structured JSON/Markdown quality report generation, automated remediation suggestions.
"""

from __future__ import annotations

from .geometry_math import (
    PurePythonAABB,
    _add_vec,
    _coplanar_triangle_triangle_intersection_2d,
    _cross_product,
    _dot_product,
    _norm_vec,
    _point_in_triangle_2d,
    _scale_vec,
    _segments_intersect_2d,
    _sub_vec,
    _vec_len,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    triangle_triangle_intersection_moller,
)
from .bvh import (
    BlenderBVHTree,
    HAS_BLENDER,
    PurePythonBVHNode,
    PurePythonBVHTree,
    get_bvh_tree,
)
from .penetration import (
    _compute_vertex_normals,
    _find_garment_boundary_edges,
    evaluate_hair_grooming_intersections,
    evaluate_mesh_penetration,
)
from .proportions import (
    ANTHROPOMETRIC_PRESETS,
    AnthropometricMetrics,
    evaluate_body_proportions,
)
from .deformation import (
    JointDeformationMetrics,
    compute_bounding_slice_volume,
    compute_mesh_dihedral_creases,
    compute_mesh_signed_volume,
    evaluate_rig_skinning_deformation,
    evaluate_rig_skinning_pinch,
)
from .reporter import (
    benchmark_defect_detection,
    create_grooming_fixture,
    create_penetration_fixture,
    create_proportion_fixture,
    create_skinning_fixture,
    make_procedural_cylinder,
    run_defect_detection_benchmark,
    run_visual_critique,
)

__all__ = [
    # Sub-modules
    "geometry_math",
    "bvh",
    "penetration",
    "proportions",
    "deformation",
    "reporter",
    # Core Spatial & Geometric Primitives
    "PurePythonBVHTree",
    "PurePythonBVHNode",
    "PurePythonAABB",
    "get_bvh_tree",
    "BlenderBVHTree",
    "HAS_BLENDER",
    "point_to_triangle_distance_eberly",
    "ray_triangle_intersection_moller_trumbore",
    "triangle_triangle_intersection_moller",
    "_cross_product",
    "_dot_product",
    "_sub_vec",
    "_add_vec",
    "_scale_vec",
    "_norm_vec",
    "_vec_len",
    "_segments_intersect_2d",
    "_point_in_triangle_2d",
    "_coplanar_triangle_triangle_intersection_2d",
    # Evaluation Engines & Metrics
    "_compute_vertex_normals",
    "_find_garment_boundary_edges",
    "evaluate_mesh_penetration",
    "evaluate_hair_grooming_intersections",
    "ANTHROPOMETRIC_PRESETS",
    "AnthropometricMetrics",
    "evaluate_body_proportions",
    "JointDeformationMetrics",
    "compute_mesh_signed_volume",
    "compute_bounding_slice_volume",
    "compute_mesh_dihedral_creases",
    "evaluate_rig_skinning_deformation",
    "evaluate_rig_skinning_pinch",
    # Master Critique Orchestrator
    "run_visual_critique",
    # Fixture Generators & Benchmarks
    "make_procedural_cylinder",
    "create_penetration_fixture",
    "create_proportion_fixture",
    "create_skinning_fixture",
    "create_grooming_fixture",
    "run_defect_detection_benchmark",
    "benchmark_defect_detection",
]
