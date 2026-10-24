"""
Empirical Adversarial Challenger Test Suite: Milestone 4 Visual Critic Subsystem.
Author: Challenger M4-2 (Empirical Challenger)
Target: PurePythonBVHTree, Möller-Trumbore ray tracing, Eberly point-triangle distance,
        Möller triangle-triangle intersection, penetration detection, proportion metrics,
        deformation volume conservation, and quality critique reporter.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

from morphomesh.models import (
    ActionableRecommendation,
    BoundingBox3D,
    DefectCategory,
    DefectItem,
    DefectSeverity,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)
from morphomesh.critic import (
    ANTHROPOMETRIC_PRESETS,
    AnthropometricMetrics,
    JointDeformationMetrics,
    PurePythonAABB,
    PurePythonBVHNode,
    PurePythonBVHTree,
    _add_vec,
    _compute_vertex_normals,
    _coplanar_triangle_triangle_intersection_2d,
    _cross_product,
    _dot_product,
    _find_garment_boundary_edges,
    _norm_vec,
    _point_in_triangle_2d,
    _scale_vec,
    _segments_intersect_2d,
    _sub_vec,
    _vec_len,
    benchmark_defect_detection,
    compute_bounding_slice_volume,
    compute_mesh_dihedral_creases,
    compute_mesh_signed_volume,
    create_grooming_fixture,
    create_penetration_fixture,
    create_proportion_fixture,
    create_skinning_fixture,
    evaluate_body_proportions,
    evaluate_hair_grooming_intersections,
    evaluate_mesh_penetration,
    evaluate_rig_skinning_deformation,
    get_bvh_tree,
    make_procedural_cylinder,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    run_defect_detection_benchmark,
    run_visual_critique,
    triangle_triangle_intersection_moller,
)


# ==============================================================================
# 1. PURE PYTHON BVH ADVERSARIAL STRESS TESTS
# ==============================================================================

class TestPurePythonBVHAdversarialStress:
    """Adversarial stress-testing of PurePythonBVHTree spatial indexing and queries."""

    def test_bvh_empty_mesh_queries_graceful_handling(self):
        """Constructing BVH on completely empty mesh returns valid empty tree with None queries."""
        tree = PurePythonBVHTree.FromPolygons([], [])
        assert tree.root is None
        assert tree.triangles == []
        assert tree.tri_orig_indices == []

        # Queries on empty tree must return None/empty tuple without raising
        loc, norm, idx, dist = tree.find_nearest((0.0, 0.0, 0.0))
        assert loc is None
        assert norm is None
        assert idx is None
        assert dist is None

        # Ray cast on empty tree
        r_loc, r_norm, r_idx, r_dist = tree.ray_cast((0.0, 0.0, -1.0), (0.0, 0.0, 1.0))
        assert r_loc is None
        assert r_norm is None
        assert r_idx is None
        assert r_dist is None

        # Overlap with empty tree and non-empty tree
        assert tree.overlap(tree) == []

        non_empty = PurePythonBVHTree.FromPolygons(
            [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
            [(0, 1, 2)],
        )
        assert tree.overlap(non_empty) == []
        assert non_empty.overlap(tree) == []

    def test_bvh_point_cloud_and_isolated_vertices(self):
        """Constructing BVH on vertices without polygons or degenerate single-vertex polygons."""
        # Vertices without polygons
        tree_no_poly = PurePythonBVHTree.FromPolygons([(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)], [])
        assert tree_no_poly.root is None
        assert tree_no_poly.find_nearest((0.0, 0.0, 0.0)) == (None, None, None, None)

        # Degenerate 1-point and 2-point polygons (should be ignored since len < 3)
        tree_degenerate = PurePythonBVHTree.FromPolygons(
            [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)],
            [(0,), (0, 1)],
        )
        assert tree_degenerate.root is None

    def test_bvh_collinear_and_flat_mesh_deep_recursion(self):
        """
        Adversarial flat coplanar mesh: 1000 triangles on Z=0 plane.
        Extents on Z is 0.0. Tree must successfully partition along X or Y without recursion error.
        """
        verts = []
        polys = []
        # Create a grid of triangles on Z=0
        n_side = 25
        for i in range(n_side):
            for j in range(n_side):
                verts.append((float(i), float(j), 0.0))

        for i in range(n_side - 1):
            for j in range(n_side - 1):
                v00 = i * n_side + j
                v10 = (i + 1) * n_side + j
                v01 = i * n_side + (j + 1)
                v11 = (i + 1) * n_side + (j + 1)
                polys.append((v00, v10, v01))
                polys.append((v10, v11, v01))

        assert len(polys) == 2 * (n_side - 1) * (n_side - 1)  # 1152 triangles
        tree = PurePythonBVHTree.FromPolygons(verts, polys)
        assert tree.root is not None

        # Ray cast perpendicular from +Z to Z=0 plane
        hit_loc, hit_norm, hit_idx, hit_dist = tree.ray_cast((5.5, 5.5, 10.0), (0.0, 0.0, -1.0))
        assert hit_loc is not None
        assert math.isclose(hit_loc[2], 0.0, abs_tol=1e-5)
        assert math.isclose(hit_dist, 10.0, abs_tol=1e-5)
        assert hit_norm == (0.0, 0.0, 1.0)

        # Nearest neighbor query for a point above the grid
        cp, norm, idx, d = tree.find_nearest((10.2, 10.2, 5.0))
        assert cp is not None
        assert math.isclose(cp[2], 0.0, abs_tol=1e-5)
        assert math.isclose(d, 5.0, abs_tol=1e-5)

    def test_bvh_duplicate_overlapping_triangles(self):
        """Tree with 50 identical overlapping triangles: sorting along centroid axis has equal values."""
        verts = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        polys = [(0, 1, 2) for _ in range(50)]
        tree = PurePythonBVHTree.FromPolygons(verts, polys)
        assert tree.root is not None

        loc, norm, idx, dist = tree.find_nearest((0.2, 0.2, 1.0))
        assert loc is not None
        assert math.isclose(dist, 1.0, abs_tol=1e-6)

    def test_bvh_ray_cast_edge_cases(self):
        """Ray cast edge cases: zero direction vector, grazing rays, opposite direction, distance bounds."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (2.0, 0.0, 0.0)
        v2 = (0.0, 2.0, 0.0)
        tree = PurePythonBVHTree.FromPolygons([v0, v1, v2], [(0, 1, 2)])

        # 1. Zero-length direction vector: _norm_vec falls back to (0, 0, 1)
        loc, _, _, _ = tree.ray_cast((0.5, 0.5, -2.0), (0.0, 0.0, 0.0))
        # Direction becomes (0, 0, 1), pointing directly at triangle from z=-2
        assert loc is not None
        assert math.isclose(loc[2], 0.0, abs_tol=1e-6)

        # 2. Ray pointing away from triangle (negative distance)
        loc_away, _, _, _ = tree.ray_cast((0.5, 0.5, 2.0), (0.0, 0.0, 1.0))
        assert loc_away is None

        # 3. Ray parallel to triangle face (grazing ray in plane z=0.5)
        loc_parallel, _, _, _ = tree.ray_cast((0.5, 0.5, 0.5), (1.0, 0.0, 0.0))
        assert loc_parallel is None

        # 4. Ray max_dist cutoff: actual hit is at t=5.0, max_dist=3.0
        loc_cut, _, _, _ = tree.ray_cast((0.5, 0.5, 5.0), (0.0, 0.0, -1.0), distance=3.0)
        assert loc_cut is None

        # 5. Ray hit within max_dist: max_dist=6.0
        loc_hit, _, _, dist = tree.ray_cast((0.5, 0.5, 5.0), (0.0, 0.0, -1.0), distance=6.0)
        assert loc_hit is not None
        assert math.isclose(dist, 5.0, abs_tol=1e-6)

        # 6. Ray starting directly on the face (origin at z=0)
        # Standard epsilon t < 1e-8 prevents immediate self-hit
        loc_self, _, _, _ = tree.ray_cast((0.5, 0.5, 0.0), (0.0, 0.0, -1.0))
        assert loc_self is None

    def test_bvh_nearest_neighbor_branch_and_bound_bounds(self):
        """find_nearest with extreme distance points, negative max_dist, and zero max_dist."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (1.0, 0.0, 0.0)
        v2 = (0.0, 1.0, 0.0)
        tree = PurePythonBVHTree.FromPolygons([v0, v1, v2], [(0, 1, 2)])

        # Max dist zero or negative
        loc_neg, _, _, _ = tree.find_nearest((0.5, 0.5, 1.0), max_dist=-0.1)
        assert loc_neg is None

        # Max dist smaller than actual distance
        loc_tight, _, _, _ = tree.find_nearest((0.5, 0.5, 1.0), max_dist=0.5)
        assert loc_tight is None

        # Extreme distant query point (1e8, 1e8, 1e8)
        loc_far, _, _, dist_far = tree.find_nearest((1e6, 0.0, 0.0), max_dist=2e6)
        assert loc_far is not None
        # Closest point on triangle to (1e6, 0, 0) is (1.0, 0.0, 0.0)
        assert math.isclose(loc_far[0], 1.0, abs_tol=1e-4)
        assert math.isclose(dist_far, 1e6 - 1.0, abs_tol=1e-3)

    def test_bvh_quad_polygon_fan_triangulation(self):
        """Verifies quad and n-gon polygon fan triangulation in FromPolygons."""
        # A quad face (4 vertices)
        verts = [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)]
        polys = [(0, 1, 2, 3)]
        tree = PurePythonBVHTree.FromPolygons(verts, polys)
        # Should create 2 triangles with orig_index = 0
        assert len(tree.triangles) == 2
        assert tree.tri_orig_indices == [0, 0]

        # Query in second triangle (e.g. at (0.2, 1.8, 1.0))
        loc, _, idx, d = tree.find_nearest((0.2, 1.8, 1.0))
        assert loc is not None
        assert idx == 0
        assert math.isclose(d, 1.0, abs_tol=1e-6)


# ==============================================================================
# 2. GEOMETRY MATH & PRIMITIVE SOLVERS ADVERSARIAL TESTS
# ==============================================================================

class TestGeometryMathAdversarialPrecision:
    """Adversarial stress-testing of Möller-Trumbore, Eberly, and Möller triangle intersection."""

    def test_moller_trumbore_barycentric_boundaries(self):
        """Möller-Trumbore ray cast precisely on triangle edges and vertices."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (3.0, 0.0, 0.0)
        v2 = (0.0, 3.0, 0.0)

        # Centroid hit
        res_c = ray_triangle_intersection_moller_trumbore(
            (1.0, 1.0, 5.0), (0.0, 0.0, -1.0), v0, v1, v2
        )
        assert res_c is not None
        hit_pt, norm, t = res_c
        assert math.isclose(t, 5.0, abs_tol=1e-7)
        assert norm == (0.0, 0.0, 1.0)
        assert hit_pt == (1.0, 1.0, 0.0)

        # Ray through exact hypotenuse boundary (u + v = 1.0)
        res_edge = ray_triangle_intersection_moller_trumbore(
            (1.5, 1.5, 5.0), (0.0, 0.0, -1.0), v0, v1, v2
        )
        assert res_edge is not None
        assert math.isclose(res_edge[2], 5.0, abs_tol=1e-7)

        # Just outside hypotenuse (u + v = 1.0001)
        res_out = ray_triangle_intersection_moller_trumbore(
            (1.501, 1.501, 5.0), (0.0, 0.0, -1.0), v0, v1, v2
        )
        assert res_out is None

    def test_moller_trumbore_extreme_scale_perturbations(self):
        """
        Möller-Trumbore under scale perturbations:
        - Millimeter scale (1e-3 m): successfully intersects.
        - Macroscale (1e3 m, 1km): successfully intersects.
        - Microscale boundary (< 1e-5 m): det < 1e-10 triggers parallel/degenerate cutoff.
        """
        # 1. Millimeter scale (1 mm = 1e-3 m)
        s_milli = 1e-3
        v0 = (0.0, 0.0, 0.0)
        v1 = (s_milli, 0.0, 0.0)
        v2 = (0.0, s_milli, 0.0)
        res_milli = ray_triangle_intersection_moller_trumbore(
            (s_milli * 0.25, s_milli * 0.25, s_milli * 5.0),
            (0.0, 0.0, -1.0),
            v0, v1, v2,
        )
        assert res_milli is not None
        assert math.isclose(res_milli[2], s_milli * 5.0, rel_tol=1e-4)

        # 2. Macroscale (1,000 m = 1 km)
        s_macro = 1e3
        v0_m = (0.0, 0.0, 0.0)
        v1_m = (s_macro, 0.0, 0.0)
        v2_m = (0.0, s_macro, 0.0)
        res_macro = ray_triangle_intersection_moller_trumbore(
            (s_macro * 0.25, s_macro * 0.25, s_macro * 5.0),
            (0.0, 0.0, -1.0),
            v0_m, v1_m, v2_m,
        )
        assert res_macro is not None
        assert math.isclose(res_macro[2], s_macro * 5.0, rel_tol=1e-4)

        # 3. Microscale boundary (< 1e-5 m): det = s^2 < 1e-10 returns None
        s_micro = 1e-6
        res_micro = ray_triangle_intersection_moller_trumbore(
            (s_micro * 0.25, s_micro * 0.25, s_micro * 5.0),
            (0.0, 0.0, -1.0),
            (0.0, 0.0, 0.0), (s_micro, 0.0, 0.0), (0.0, s_micro, 0.0),
        )
        # Empirically verified: Möller-Trumbore rejects triangles with det < 1e-10
        assert res_micro is None

    def test_eberly_all_7_voronoi_regions_analytical(self):
        """
        Validates David Eberly's point-to-triangle algorithm across all 7 Voronoi regions:
        Region 0: Interior of triangle
        Region 1: Edge opposite v0 (edge v1-v2)
        Region 2: Vertex v2
        Region 3: Edge v0-v2
        Region 4: Vertex v0
        Region 5: Edge v0-v1
        Region 6: Vertex v1
        """
        v0 = (0.0, 0.0, 0.0)
        v1 = (2.0, 0.0, 0.0)
        v2 = (0.0, 2.0, 0.0)

        # Region 0: Point directly above interior (0.5, 0.5, 1.0)
        p0 = (0.5, 0.5, 1.0)
        cp0, n0, d0 = point_to_triangle_distance_eberly(p0, v0, v1, v2)
        assert math.isclose(cp0[0], 0.5, abs_tol=1e-7)
        assert math.isclose(cp0[1], 0.5, abs_tol=1e-7)
        assert math.isclose(cp0[2], 0.0, abs_tol=1e-7)
        assert math.isclose(d0, 1.0, abs_tol=1e-7)

        # Region 1: Beyond hypotenuse edge v1-v2 (1.5, 1.5, 0.0) -> closest on edge is (1.0, 1.0, 0.0)
        p1 = (1.5, 1.5, 0.0)
        cp1, _, d1 = point_to_triangle_distance_eberly(p1, v0, v1, v2)
        assert math.isclose(cp1[0], 1.0, abs_tol=1e-7)
        assert math.isclose(cp1[1], 1.0, abs_tol=1e-7)
        expected_d1 = math.sqrt((1.5 - 1.0)**2 + (1.5 - 1.0)**2)
        assert math.isclose(d1, expected_d1, abs_tol=1e-7)

        # Region 2: Closest to vertex v2 (0.0, 2.0, 0.0) -> query at (-0.5, 3.0, 0.0)
        p2 = (-0.5, 3.0, 0.0)
        cp2, _, d2 = point_to_triangle_distance_eberly(p2, v0, v1, v2)
        assert math.isclose(cp2[0], v2[0], abs_tol=1e-7)
        assert math.isclose(cp2[1], v2[1], abs_tol=1e-7)

        # Region 3: Closest to edge v0-v2 (x=0, 0 <= y <= 2) -> query at (-1.0, 1.0, 0.0)
        p3 = (-1.0, 1.0, 0.0)
        cp3, _, d3 = point_to_triangle_distance_eberly(p3, v0, v1, v2)
        assert math.isclose(cp3[0], 0.0, abs_tol=1e-7)
        assert math.isclose(cp3[1], 1.0, abs_tol=1e-7)
        assert math.isclose(d3, 1.0, abs_tol=1e-7)

        # Region 4: Closest to vertex v0 (0.0, 0.0, 0.0) -> query at (-1.0, -1.0, 0.0)
        p4 = (-1.0, -1.0, 0.0)
        cp4, _, d4 = point_to_triangle_distance_eberly(p4, v0, v1, v2)
        assert math.isclose(cp4[0], v0[0], abs_tol=1e-7)
        assert math.isclose(cp4[1], v0[1], abs_tol=1e-7)
        expected_d4 = math.sqrt((-1.0)**2 + (-1.0)**2)
        assert math.isclose(d4, expected_d4, abs_tol=1e-7)

        # Region 5: Closest to edge v0-v1 (y=0, 0 <= x <= 2) -> query at (1.0, -1.0, 0.0)
        p5 = (1.0, -1.0, 0.0)
        cp5, _, d5 = point_to_triangle_distance_eberly(p5, v0, v1, v2)
        assert math.isclose(cp5[0], 1.0, abs_tol=1e-7)
        assert math.isclose(cp5[1], 0.0, abs_tol=1e-7)
        assert math.isclose(d5, 1.0, abs_tol=1e-7)

        # Region 6: Closest to vertex v1 (2.0, 0.0, 0.0) -> query at (3.0, -0.5, 0.0)
        p6 = (3.0, -0.5, 0.0)
        cp6, _, d6 = point_to_triangle_distance_eberly(p6, v0, v1, v2)
        assert math.isclose(cp6[0], v1[0], abs_tol=1e-7)
        assert math.isclose(cp6[1], v1[1], abs_tol=1e-7)

    def test_eberly_unit_normal_invariance_and_scale(self):
        """Normal returned by Eberly is always a unit vector (norm == 1.0) under various scales."""
        for scale in [1e-4, 1.0, 1e4]:
            v0 = (0.0, 0.0, 0.0)
            v1 = (scale, 0.0, 0.0)
            v2 = (0.0, scale, 0.0)
            _, norm, _ = point_to_triangle_distance_eberly((0.1 * scale, 0.1 * scale, 1.0), v0, v1, v2)
            norm_mag = math.sqrt(sum(x * x for x in norm))
            assert math.isclose(norm_mag, 1.0, abs_tol=1e-6)

    def test_coplanar_triangle_intersection_oblique_plane(self):
        """Möller coplanar triangle intersection on an oblique 3D plane (not aligned with coordinate axes)."""
        # Plane defined by x + y + z = 1
        t1 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        # Triangle shifted slightly on the same plane
        t2_overlap = ((0.5, 0.5, 0.0), (0.5, 0.0, 0.5), (0.0, 0.5, 0.5))
        assert triangle_triangle_intersection_moller(t1[0], t1[1], t1[2], t2_overlap[0], t2_overlap[1], t2_overlap[2])

        # Disjoint triangle on the same plane
        t2_disjoint = ((2.0, -1.0, 0.0), (3.0, -2.0, 0.0), (2.0, -2.0, 1.0))
        assert not triangle_triangle_intersection_moller(t1[0], t1[1], t1[2], t2_disjoint[0], t2_disjoint[1], t2_disjoint[2])


# ==============================================================================
# 3. PENETRATION & GROOMING COLLISION EVALUATOR TESTS
# ==============================================================================

class TestPenetrationDefectEvaluatorStress:
    """Stress tests for evaluate_mesh_penetration and clearance boundaries."""

    def test_penetration_clearance_boundary_threshold(self):
        """
        Tests clearance boundary around tolerance 0.0005m (0.5mm):
        Displacement of -0.4mm (< 0.5mm) should not trigger penetration.
        Displacement of -0.6mm (> 0.5mm) must trigger penetration.
        """
        # Base body cylinder R=0.20m, Garment R=0.20m
        b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=0.40, num_rings=10, num_segments=16)

        # Case A: Garment displaced inward by -0.4mm -> depth = 0.4mm < 0.5mm tolerance
        g_verts_sub = np.copy(b_verts)
        for i, v in enumerate(g_verts_sub):
            if abs(v[2]) <= 0.1:
                # Displace inward by 0.4mm
                g_verts_sub[i][0] *= (0.1996 / 0.20)
                g_verts_sub[i][1] *= (0.1996 / 0.20)

        defects_sub = evaluate_mesh_penetration(
            body_obj_name="Body",
            garment_obj_names=["GarmentSub"],
            clearance_tolerance=0.0005,
            body_geo=(b_verts, b_faces),
            garment_geos={"GarmentSub": (g_verts_sub, b_faces)},
        )
        # Should be clean (no penetration defect)
        assert not any(d.category == DefectCategory.PENETRATION and d.defect_type != "FACE_OVERLAP" for d in defects_sub)

        # Case B: Garment displaced inward by -0.8mm -> depth = 0.8mm > 0.5mm tolerance
        g_verts_sup = np.copy(b_verts)
        for i, v in enumerate(g_verts_sup):
            if abs(v[2]) <= 0.1:
                g_verts_sup[i][0] *= (0.1992 / 0.20)
                g_verts_sup[i][1] *= (0.1992 / 0.20)

        defects_sup = evaluate_mesh_penetration(
            body_obj_name="Body",
            garment_obj_names=["GarmentSup"],
            clearance_tolerance=0.0005,
            body_geo=(b_verts, b_faces),
            garment_geos={"GarmentSup": (g_verts_sup, b_faces)},
        )
        pen_defects = [d for d in defects_sup if d.category == DefectCategory.PENETRATION and d.defect_type != "FACE_OVERLAP"]
        assert len(pen_defects) > 0
        d_item = pen_defects[0]
        assert d_item.penetration_depth_mm >= 0.7  # ~0.8mm
        # Valid ActionableRecommendation
        assert d_item.recommendation is not None
        assert d_item.recommendation.action == "APPLY_SHRINKWRAP_CLEARANCE"
        assert d_item.recommendation.suggested_modifier == "Shrinkwrap"

    def test_penetration_recommendation_formula_precision(self):
        """Recommendation offset formula d_rec = 1.25 * d_pen + 1.0mm verified empirically."""
        (b_v, b_f), (g_v, g_f) = create_penetration_fixture(defective=True)
        defects = evaluate_mesh_penetration(
            body_obj_name="Body",
            garment_obj_names=["Dress"],
            body_geo=(b_v, b_f),
            garment_geos={"Dress": (g_v, g_f)},
        )
        assert len(defects) > 0
        pen_defect = [d for d in defects if d.category == DefectCategory.PENETRATION][0]
        rec = pen_defect.recommendation
        assert rec is not None
        d_pen_mm = pen_defect.penetration_depth_mm
        expected_rec_mm = round(1.25 * d_pen_mm + 1.0, 2)
        actual_rec_mm = rec.parameters.get("offset_mm")
        assert math.isclose(actual_rec_mm, expected_rec_mm, abs_tol=0.1)

    def test_penetration_empty_and_disjoint_inputs(self):
        """Evaluator handles empty geometry or far disjoint meshes cleanly when geometries provided."""
        b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=0.40, num_rings=6, num_segments=8)
        # Empty body
        assert evaluate_mesh_penetration("Body", ["Garm"], body_geo=([], [])) == []

        # Disjoint garment 10 meters away
        g_far = np.copy(b_verts) + np.array([10.0, 0.0, 0.0])
        defects_far = evaluate_mesh_penetration(
            body_obj_name="Body",
            garment_obj_names=["FarGarm"],
            body_geo=(b_verts, b_faces),
            garment_geos={"FarGarm": (g_far, b_faces)},
        )
        assert len(defects_far) == 0

    def test_empirical_finding_penetration_name_error_missing_has_blender(self):
        """
        REMEDIATED BUG VERIFICATION:
        In src/morphomesh/critic/penetration.py:168:
        'elif HAS_BLENDER and bpy and bpy.data.objects.get(g_name):'
        When a garment name is not in garment_geos, Python evaluates the elif condition.
        HAS_BLENDER and bpy are now imported, so no NameError is raised and fallback succeeds.
        """
        b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=0.40, num_rings=6, num_segments=8)
        res = evaluate_mesh_penetration("Body", ["MissingGarm"], body_geo=(b_verts, b_faces), garment_geos={})
        assert isinstance(res, list)


# ==============================================================================
# 4. ANTHROPOMETRIC PROPORTION METRICS TESTS
# ==============================================================================

class TestAnthropometricProportionsStress:
    """Stress tests for evaluate_body_proportions across presets and scale perturbations."""

    def test_proportions_scale_invariance(self):
        """
        Uniform scaling of a humanoid character (scale factor 0.5x, 1.0x, 2.0x)
        leaves head-to-body ratio and arm span index strictly invariant.
        """
        for scale in [0.5, 1.0, 2.0]:
            verts, faces, landmarks = create_proportion_fixture(fixture_type="clean")
            s_verts = verts * scale
            s_landmarks = {k: (v[0] * scale, v[1] * scale, v[2] * scale) for k, v in landmarks.items()}

            metrics, defects = evaluate_body_proportions(
                body_obj_name="Heroine",
                target_preset="stylized_heroine",
                landmarks=s_landmarks,
                body_geo=(s_verts, faces),
            )
            assert math.isclose(metrics.head_ratio, 7.41, abs_tol=0.05)
            assert math.isclose(metrics.arm_span_ratio, 0.98, abs_tol=0.05)
            assert metrics.is_head_ratio_valid
            assert metrics.is_arm_span_valid
            assert len(defects) == 0

    def test_proportions_across_all_supported_presets(self):
        """Verifies proportion evaluation against all 6 canonical presets."""
        presets = ["realistic_human", "stylized_heroine", "chibi_petite", "realistic_female", "heroic_male", "chibi"]
        for p_name in presets:
            assert p_name in ANTHROPOMETRIC_PRESETS
            conf = ANTHROPOMETRIC_PRESETS[p_name]
            # Create a character tailored to nominal ratio
            h_tot = 1.70
            h_nom = conf["head_ratio_nominal"]
            h_head = h_tot / h_nom
            landmarks = {
                "head_top": (0.0, 0.0, h_tot),
                "chin": (0.0, 0.0, h_tot - h_head),
                "shoulder_L": (-0.2, 0.0, h_tot * 0.8),
                "shoulder_R": (0.2, 0.0, h_tot * 0.8),
                "elbow_L": (-0.45, 0.0, h_tot * 0.8),
                "elbow_R": (0.45, 0.0, h_tot * 0.8),
                "wrist_L": (-0.70, 0.0, h_tot * 0.8),
                "wrist_R": (0.70, 0.0, h_tot * 0.8),
                "fingers_L": (-0.85, 0.0, h_tot * 0.8),
                "fingers_R": (0.85, 0.0, h_tot * 0.8),
            }
            verts, faces = make_procedural_cylinder(radius=0.15, height=h_tot, num_rings=6, num_segments=8, center_z=h_tot / 2.0)
            metrics, defects = evaluate_body_proportions(
                body_obj_name="Body",
                target_preset=p_name,
                landmarks=landmarks,
                body_geo=(verts, faces),
            )
            assert metrics.is_head_ratio_valid

    def test_proportions_inverted_and_degenerate_landmarks(self):
        """Inverted landmarks (chin higher than head_top) handles division gracefully without crash."""
        landmarks_inverted = {
            "head_top": (0.0, 0.0, 1.0),
            "chin": (0.0, 0.0, 1.5),  # chin higher than head_top!
        }
        verts, faces = make_procedural_cylinder(radius=0.15, height=1.65, num_rings=6, num_segments=8, center_z=0.825)
        metrics, defects = evaluate_body_proportions(
            body_obj_name="Body",
            target_preset="stylized_heroine",
            landmarks=landmarks_inverted,
            body_geo=(verts, faces),
        )
        assert not metrics.is_head_ratio_valid
        assert len(defects) > 0
        head_defect = [d for d in defects if d.category == DefectCategory.PROPORTION][0]
        assert head_defect.defect_id == "PROP_HEAD_TOO_SMALL"
        assert not math.isnan(metrics.head_ratio)


# ==============================================================================
# 5. DEFORMATION VOLUME CONSERVATION & DIHEDRAL CREASING TESTS
# ==============================================================================

class TestDeformationVolumeAndCreasingStress:
    """Stress tests for compute_mesh_signed_volume and compute_mesh_dihedral_creases."""

    def test_signed_volume_analytical_cube_and_sphere(self):
        """
        Divergence theorem signed volume on analytical polyhedra:
        Cube side 2.0: volume = 8.0 m^3.
        Inverted winding faces: volume remains 8.0 m^3 due to abs(vol)/6.0.
        """
        # Unit cube from -1 to 1: volume = 2^3 = 8.0
        cube_verts = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
        # CCW winding
        cube_faces = [
            (0, 3, 2, 1),  # bottom (-Z)
            (4, 5, 6, 7),  # top (+Z)
            (0, 1, 5, 4),  # front (-Y)
            (2, 3, 7, 6),  # back (+Y)
            (0, 4, 7, 3),  # left (-X)
            (1, 2, 6, 5),  # right (+X)
        ]
        v_cube = compute_mesh_signed_volume(cube_verts, cube_faces)
        assert math.isclose(v_cube, 8.0, abs_tol=1e-5)

        # Inverted winding faces
        cube_faces_inv = [f[::-1] for f in cube_faces]
        v_cube_inv = compute_mesh_signed_volume(cube_verts, cube_faces_inv)
        assert math.isclose(v_cube_inv, 8.0, abs_tol=1e-5)

    def test_dihedral_creasing_angular_spectrum(self):
        """
        Detects dihedral creases across fold angles:
        theta = 0 deg (normals identical, flat sheet): cos theta = 1.0 (no crease)
        theta = 90 deg (perpendicular faces): cos theta = 0.0 (no crease)
        theta = 150 deg (acute fold, 30 deg remaining): cos theta = -0.866 < -0.85 (MAJOR crease)
        theta = 170 deg (sharp acute fold, 10 deg remaining): cos theta = -0.985 < -0.95 (CRITICAL crease)
        """
        for angle_deg, expected_crease in [(0.0, False), (90.0, False), (150.0, True), (170.0, True)]:
            rad = math.radians(angle_deg)
            # T1: v0=(0,0,0), v1=(1,0,0), v2=(0.5,1,0) -> n1 = (0, 0, 1)
            # T2: shared edge v1=(1,0,0) to v0=(0,0,0). v3=(0.5, y3, z3).
            # e1 = (-1, 0, 0), e2 = (-0.5, y3, z3) -> e1 x e2 = (0, z3, -y3)
            # Normal n2 = (0, z3, -y3). For n1 . n2 = cos(rad), set y3 = -cos(rad), z3 = sin(rad).
            y3 = -math.cos(rad)
            z3 = math.sin(rad)
            t1 = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0)]
            t2_v3 = (0.5, y3, z3)
            verts = [t1[0], t1[1], t1[2], t2_v3]
            faces = [(0, 1, 2), (1, 0, 3)]

            creases = compute_mesh_dihedral_creases(verts, faces, cos_threshold=-0.85)
            if expected_crease:
                assert len(creases) == 1
                assert creases[0]["cos_theta"] < -0.85
            else:
                assert len(creases) == 0

    def test_empirical_finding_proportions_name_error_missing_has_blender(self):
        """
        REMEDIATED BUG VERIFICATION:
        In src/morphomesh/critic/proportions.py:124:
        'elif HAS_BLENDER and bpy and bpy.data.objects.get(body_obj_name):'
        When body_geo is None, Python evaluates elif condition.
        HAS_BLENDER and bpy are now imported, so no NameError is raised and fallback metrics return.
        """
        metrics, defects = evaluate_body_proportions("Body", body_geo=None)
        assert metrics is not None
        assert isinstance(defects, list)

    def test_empirical_finding_deformation_name_error_missing_has_blender(self):
        """
        REMEDIATED BUG VERIFICATION:
        In src/morphomesh/critic/deformation.py:309:
        'if not HAS_BLENDER or not bpy or not bpy.data.objects.get(mesh_obj_name):'
        HAS_BLENDER and bpy are now imported, so no NameError is raised and empty defect list returns.
        """
        from morphomesh.critic.deformation import evaluate_rig_skinning_pinch
        res = evaluate_rig_skinning_pinch("Rig", "Mesh")
        assert res == []

    def test_empirical_finding_reporter_import_evaluate_rig_skinning_pinch(self):
        """
        REMEDIATED BUG VERIFICATION:
        In src/morphomesh/critic/reporter.py:
        evaluate_rig_skinning_pinch must be cleanly imported from .deformation.
        """
        from morphomesh.critic.reporter import evaluate_rig_skinning_pinch as reporter_pinch
        from morphomesh.critic.deformation import evaluate_rig_skinning_pinch as def_pinch
        assert reporter_pinch is def_pinch

    def test_skinning_deformation_evaluator_collapse_detection(self):
        """evaluate_rig_skinning_deformation detects candy-wrapper collapse on defective arm fixture."""
        r_v, posed_v, faces, j_specs = create_skinning_fixture(defective=True)
        metrics, defects = evaluate_rig_skinning_deformation(
            list(r_v), list(posed_v), [tuple(f) for f in faces], j_specs, object_name="ArmMesh"
        )
        assert len(metrics) > 0
        m = metrics[0]
        assert not m.is_volume_conserved or not m.is_crease_free
        # Defect items generated
        assert len(defects) > 0
        crease_defects = [d for d in defects if d.category == DefectCategory.SKINNING_PINCH]
        assert len(crease_defects) > 0


# ==============================================================================
# 6. QUALITY REPORTER & BENCHMARK SUITE TESTS
# ==============================================================================

class TestQualityReporterAndBenchmarking:
    """Stress tests for benchmark_defect_detection and run_visual_critique."""

    def test_benchmark_defect_detection_accuracy(self):
        """Empirical execution of benchmark_defect_detection achieves 100% accuracy and 0% FPR."""
        results = benchmark_defect_detection()
        assert results["tests_run"] == 9
        assert results["accuracy"] == 100.0
        assert results["false_positive_rate"] == 0.0
        assert results["true_positives"] == 5
        assert results["true_negatives"] == 4

    def test_run_visual_critique_offline_execution(self):
        """run_visual_critique executes cleanly in offline mode and outputs valid VisualCritiqueOutput."""
        # Clean baseline execution
        out_clean = run_visual_critique(
            target_object="Body",
            target_preset="stylized_heroine",
        )
        assert isinstance(out_clean, VisualCritiqueOutput)
        assert out_clean.status == "success"
        assert out_clean.passed is True
        assert out_clean.quality_score == 100.0
        assert out_clean.defect_count == 0

        # Pydantic v2 serialization round-trip
        json_str = out_clean.model_dump_json()
        deserialized = VisualCritiqueOutput.model_validate_json(json_str)
        assert deserialized.passed == out_clean.passed
        assert deserialized.quality_score == out_clean.quality_score
        assert deserialized.status == out_clean.status

    def test_run_visual_critique_dict_and_kwargs_inputs(self):
        """run_visual_critique accepts dict input or keyword arguments seamlessly."""
        inp_dict = {
            "target_object": "Heroine_Mesh",
            "target_preset": "realistic_female",
            "camera_angles": ["front", "side"],
        }
        out = run_visual_critique(inp_dict)
        assert out.status == "success"
        assert out.evaluated_angles == ["front", "side"]
