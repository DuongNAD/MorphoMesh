"""
MorphoMesh: Milestone 3 Adversarial Test Harness.
Penetration, Grooming & BVH Adversarial Challenger Test Suite.

Author: Challenger M3_1 (Empirical Challenger)
Target: PurePythonBVHTree, evaluate_mesh_penetration, evaluate_hair_grooming_intersections

Verifies:
1. PurePythonBVHTree Boundary & Degeneracy Testing:
   - Degenerate triangles: zero area (duplicate vertices, collinear vertices), inverted winding order.
   - Spatial boundary queries: Points strictly on triangle vertices, on edges, coplanar with triangle plane, and opposite back-face.
   - Triangle-triangle intersection overlap under edge-sharing, vertex-touching, coplanar overlapping, and non-intersecting close proximity.
2. Penetration Depth Analytical Accuracy:
   - Concentric geometric meshes (cylinders & spheres) with analytical radial separation d in [-25mm, -10mm, -1mm, -0.1mm, 0mm, +5mm].
   - Verifies evaluate_mesh_penetration computes signed penetration depth matching analytical truth within 10^-4 m.
3. Hair Grooming Curve Boundary Stress:
   - Splines with 0 to 100+ points, extreme zigzag curves, roots positioned precisely on boundary tolerance thresholds (-1.0mm, +4.0mm).
   - Verifies roots submerged deeper than -1.0mm are reliably flagged as GROOM_ROOT_SUBMERGED, and roots beyond +4.0mm are flagged as GROOM_ROOT_FLOATING / GROOMING_ROOT_DETACHED.
"""

import math
import pytest
import numpy as np
from typing import List, Tuple, Dict, Any

from morphomesh.visual_critic import (
    PurePythonBVHTree,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    triangle_triangle_intersection_moller,
    evaluate_mesh_penetration,
    evaluate_hair_grooming_intersections,
    make_procedural_cylinder,
    _sub_vec,
    _dot_product,
    _norm_vec,
)
from morphomesh.models import DefectCategory, DefectSeverity


# ==============================================================================
# 1. PURE PYTHON BVH BOUNDARY & DEGENERACY TEST CLASS
# ==============================================================================

class TestPurePythonBVHDegeneracyAndBoundaries:
    """Adversarial stress-testing of BVH tree and geometric solvers under degeneracies."""

    def test_zero_area_triangle_all_duplicate_vertices(self):
        """Zero-area triangle where all 3 vertices are identical."""
        p_query = (0.0, 0.0, 2.0)
        v = (1.0, 1.0, 1.0)
        cp, norm, dist = point_to_triangle_distance_eberly(p_query, v, v, v)
        # Closest point must be the degenerate point itself
        assert math.isclose(cp[0], 1.0, abs_tol=1e-7)
        assert math.isclose(cp[1], 1.0, abs_tol=1e-7)
        assert math.isclose(cp[2], 1.0, abs_tol=1e-7)
        expected_dist = math.sqrt((0 - 1)**2 + (0 - 1)**2 + (2 - 1)**2)
        assert math.isclose(dist, expected_dist, abs_tol=1e-7)
        # Normal vector should fall back gracefully without NaN
        assert not any(math.isnan(x) for x in norm)

    def test_zero_area_triangle_two_duplicate_vertices(self):
        """Zero-area triangle where 2 vertices are identical (line segment)."""
        p_query = (0.5, 2.0, 0.0)
        v0 = (0.0, 0.0, 0.0)
        v1 = (1.0, 0.0, 0.0)
        v2 = (0.0, 0.0, 0.0)  # v2 == v0 -> det == 0
        cp, norm, dist = point_to_triangle_distance_eberly(p_query, v0, v1, v2)
        # Verifies no uncaught exceptions, zero division, or NaNs
        assert not any(math.isnan(x) for x in cp)
        assert not any(math.isnan(x) for x in norm)
        assert not math.isnan(dist)
        assert dist >= 0.0

        # Also verify mesh with such degenerate triangles can be indexed and queried via BVH
        tree = PurePythonBVHTree.FromPolygons([v0, v1, v2], [(0, 1, 2)])
        loc, _, idx, d = tree.find_nearest(p_query)
        assert loc is not None
        assert not math.isnan(d)

    def test_zero_area_triangle_collinear_vertices(self):
        """Zero-area triangle where all 3 vertices lie on a straight line."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (1.0, 0.0, 0.0)
        v2 = (3.0, 0.0, 0.0)
        # Query point closest to middle of line segment
        cp, norm, dist = point_to_triangle_distance_eberly((2.0, 1.5, 0.0), v0, v1, v2)
        assert not any(math.isnan(x) for x in cp)
        assert not any(math.isnan(x) for x in norm)
        assert not math.isnan(dist)
        assert dist >= 0.0

    def test_inverted_winding_order_invariance(self):
        """Inverting triangle vertex winding (CW vs CCW) preserves closest point and flips normal."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (2.0, 0.0, 0.0)
        v2 = (0.0, 2.0, 0.0)
        p_query = (0.5, 0.5, 1.5)

        # CCW winding: normal points +Z
        cp_ccw, norm_ccw, dist_ccw = point_to_triangle_distance_eberly(p_query, v0, v1, v2)
        # CW winding: normal points -Z
        cp_cw, norm_cw, dist_cw = point_to_triangle_distance_eberly(p_query, v0, v2, v1)

        # Distance and closest point must be mathematically identical
        assert math.isclose(dist_ccw, dist_cw, abs_tol=1e-9)
        assert math.isclose(dist_ccw, 1.5, abs_tol=1e-7)
        for i in range(3):
            assert math.isclose(cp_ccw[i], cp_cw[i], abs_tol=1e-9)

        # Normal directions must be exact opposites
        for i in range(3):
            assert math.isclose(norm_ccw[i], -norm_cw[i], abs_tol=1e-7)

    def test_extreme_coordinate_ranges(self):
        """Tests triangle distance under millimeter (0.005m) and macro (10,000m) coordinates."""
        # Millimeter-scale geometry (5mm triangle)
        s_mm = 0.005
        v0_m = (0.0, 0.0, 0.0)
        v1_m = (s_mm, 0.0, 0.0)
        v2_m = (0.0, s_mm, 0.0)
        cp_m, _, dist_m = point_to_triangle_distance_eberly((s_mm * 0.5, s_mm * 0.5, 0.01), v0_m, v1_m, v2_m)
        assert math.isclose(dist_m, 0.01, abs_tol=1e-6)
        assert math.isclose(cp_m[0], s_mm * 0.5, abs_tol=1e-6)
        assert math.isclose(cp_m[1], s_mm * 0.5, abs_tol=1e-6)

        # Macro-scale geometry (10km triangle)
        scale = 10000.0
        v0_M = (0.0, 0.0, 0.0)
        v1_M = (scale, 0.0, 0.0)
        v2_M = (0.0, scale, 0.0)
        cp_M, _, dist_M = point_to_triangle_distance_eberly((scale * 0.5, scale * 0.5, 50.0), v0_M, v1_M, v2_M)
        assert math.isclose(dist_M, 50.0, abs_tol=1e-3)
        assert math.isclose(cp_M[0], scale * 0.5, abs_tol=1e-3)
        assert math.isclose(cp_M[1], scale * 0.5, abs_tol=1e-3)

    def test_spatial_boundary_queries_exact_vertices(self):
        """Points strictly identical to triangle vertices must yield distance 0.0."""
        v0 = (1.2, 3.4, -0.5)
        v1 = (5.6, 7.8, 2.1)
        v2 = (-1.0, 4.0, 3.0)

        for v in [v0, v1, v2]:
            cp, _, dist = point_to_triangle_distance_eberly(v, v0, v1, v2)
            assert math.isclose(dist, 0.0, abs_tol=1e-9)
            assert all(math.isclose(cp[i], v[i], abs_tol=1e-9) for i in range(3))

    def test_spatial_boundary_queries_exact_edges(self):
        """Points strictly on triangle edges must yield distance 0.0."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (4.0, 0.0, 0.0)
        v2 = (0.0, 4.0, 0.0)

        edges = [
            (0.5 * (v0[0] + v1[0]), 0.5 * (v0[1] + v1[1]), 0.5 * (v0[2] + v1[2])),
            (0.5 * (v1[0] + v2[0]), 0.5 * (v1[1] + v2[1]), 0.5 * (v1[2] + v2[2])),
            (0.5 * (v2[0] + v0[0]), 0.5 * (v2[1] + v0[1]), 0.5 * (v2[2] + v0[2])),
        ]

        for p_edge in edges:
            cp, _, dist = point_to_triangle_distance_eberly(p_edge, v0, v1, v2)
            assert math.isclose(dist, 0.0, abs_tol=1e-9)
            assert all(math.isclose(cp[i], p_edge[i], abs_tol=1e-9) for i in range(3))

    def test_spatial_boundary_queries_coplanar_interior_and_exterior(self):
        """Points coplanar with triangle plane: interior vs exterior regions."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (3.0, 0.0, 0.0)
        v2 = (0.0, 3.0, 0.0)

        # Interior: centroid
        centroid = (1.0, 1.0, 0.0)
        cp, _, dist = point_to_triangle_distance_eberly(centroid, v0, v1, v2)
        assert math.isclose(dist, 0.0, abs_tol=1e-9)

        # Exterior across hypotenuse: (2.5, 2.5, 0.0)
        # Closest point on hypotenuse x + y = 3 is (1.5, 1.5, 0.0)
        p_ext_hyp = (2.5, 2.5, 0.0)
        cp, _, dist = point_to_triangle_distance_eberly(p_ext_hyp, v0, v1, v2)
        assert math.isclose(cp[0], 1.5, abs_tol=1e-6)
        assert math.isclose(cp[1], 1.5, abs_tol=1e-6)
        assert math.isclose(dist, math.sqrt((2.5 - 1.5)**2 + (2.5 - 1.5)**2), abs_tol=1e-6)

        # Exterior across vertex v0: (-1.0, -1.0, 0.0)
        p_ext_v0 = (-1.0, -1.0, 0.0)
        cp, _, dist = point_to_triangle_distance_eberly(p_ext_v0, v0, v1, v2)
        assert math.isclose(cp[0], 0.0, abs_tol=1e-6)
        assert math.isclose(cp[1], 0.0, abs_tol=1e-6)
        assert math.isclose(dist, math.sqrt(2.0), abs_tol=1e-6)

    def test_spatial_boundary_queries_opposite_backface(self):
        """Points directly behind triangle plane (-Z) report correct geometric distance."""
        v0 = (0.0, 0.0, 0.0)
        v1 = (3.0, 0.0, 0.0)
        v2 = (0.0, 3.0, 0.0)

        p_front = (1.0, 1.0, 4.0)
        p_back = (1.0, 1.0, -4.0)

        cp_f, norm_f, d_f = point_to_triangle_distance_eberly(p_front, v0, v1, v2)
        cp_b, norm_b, d_b = point_to_triangle_distance_eberly(p_back, v0, v1, v2)

        assert math.isclose(d_f, 4.0, abs_tol=1e-7)
        assert math.isclose(d_b, 4.0, abs_tol=1e-7)
        assert cp_f == cp_b == (1.0, 1.0, 0.0)
        assert norm_f == norm_b == (0.0, 0.0, 1.0)

    def test_bvh_tree_with_degenerate_mesh_elements(self):
        """PurePythonBVHTree successfully indexes and queries meshes containing degenerate faces."""
        verts = [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0),  # duplicate
            (2.0, 0.0, 0.0),
            (3.0, 0.0, 0.0),  # collinear
        ]
        faces = [
            (0, 1, 2),  # valid triangle
            (0, 0, 0),  # 3 duplicate
            (0, 1, 0),  # 2 duplicate
            (1, 4, 5),  # collinear
        ]
        tree = PurePythonBVHTree.FromPolygons(verts, faces)
        assert tree.root is not None
        # Nearest query to valid triangle
        loc, norm, idx, dist = tree.find_nearest((0.2, 0.2, 1.0))
        assert loc is not None
        assert idx == 0
        assert math.isclose(dist, 1.0, abs_tol=1e-6)

    def test_bvh_tree_empty_mesh_handling(self):
        """PurePythonBVHTree handles empty vertex and polygon lists gracefully."""
        tree = PurePythonBVHTree.FromPolygons([], [])
        assert tree.root is None
        loc, norm, idx, dist = tree.find_nearest((0.0, 0.0, 0.0))
        assert loc is None and dist is None
        hit, _, _, _ = tree.ray_cast((0, 0, 0), (0, 0, 1))
        assert hit is None
        assert tree.overlap(tree) == []


# ==============================================================================
# 2. TRIANGLE-TRIANGLE INTERSECTION ADVERSARIAL TEST CLASS
# ==============================================================================

class TestTriangleTriangleIntersectionAdversarial:
    """Adversarial stress-testing of Tomas Möller 3D triangle-triangle intersection algorithm."""

    def test_non_coplanar_edge_sharing_triangles(self):
        """Two non-coplanar triangles sharing an entire edge (e.g. open book)."""
        # Shared edge is along (0,0,0) -> (1,0,0)
        t1_v0, t1_v1, t1_v2 = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
        t2_v0, t2_v1, t2_v2 = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
        # Because they meet along the intersection line (the shared edge), interval overlaps
        res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
        assert res is True

    def test_non_coplanar_vertex_touching_triangles(self):
        """Two non-coplanar triangles touching only at a single vertex."""
        t1_v0, t1_v1, t1_v2 = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
        t2_v0, t2_v1, t2_v2 = (0.0, 0.0, 0.0), (0.0, -1.0, 1.0), (0.0, 1.0, 1.0)
        res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
        assert res is True

    def test_coplanar_overlapping_triangles(self):
        """Authentic Möller returns True for overlapping coplanar triangles via 2D dominant plane projection."""
        t1_v0, t1_v1, t1_v2 = (0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)
        t2_v0, t2_v1, t2_v2 = (0.5, 0.5, 0.0), (2.5, 0.5, 0.0), (0.5, 2.5, 0.0)
        res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
        assert res is True

        # Disjoint coplanar triangles return False
        t_dis_v0, t_dis_v1, t_dis_v2 = (5.0, 5.0, 0.0), (7.0, 5.0, 0.0), (5.0, 7.0, 0.0)
        res_dis = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t_dis_v0, t_dis_v1, t_dis_v2)
        assert res_dis is False

    def test_close_proximity_non_intersecting_parallel(self):
        """Parallel triangles separated by 1e-4m (0.1mm) do NOT intersect."""
        t1_v0, t1_v1, t1_v2 = (0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)
        t2_v0, t2_v1, t2_v2 = (0.0, 0.0, 1e-4), (2.0, 0.0, 1e-4), (0.0, 2.0, 1e-4)
        res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
        assert res is False

    def test_close_proximity_non_intersecting_skew(self):
        """Transverse/skew triangles hovering at 1e-5m distance without piercing do NOT intersect."""
        t1_v0, t1_v1, t1_v2 = (-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 2.0)
        # t2 sits at y=1e-5, piercing plane y=0 would require crossing y=0, but all y > 0
        t2_v0, t2_v1, t2_v2 = (0.0, 1e-5, 0.5), (0.0, 1.0, 0.5), (0.0, 0.5, 1.5)
        res = triangle_triangle_intersection_moller(t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2)
        assert res is False

    def test_piercing_intersection_various_angles(self):
        """Piercing triangles intersecting at perpendicular and acute angles."""
        t_base = ((-1.0, -1.0, 0.0), (1.0, -1.0, 0.0), (0.0, 1.0, 0.0))

        # Perpendicular piercing
        t_perp = ((0.0, 0.0, -1.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.5))
        assert triangle_triangle_intersection_moller(*t_base, *t_perp) is True

        # Acute angle piercing (45 degrees)
        t_acute = ((0.0, -0.5, -0.5), (0.0, 0.5, 0.5), (0.5, 0.0, 0.0))
        assert triangle_triangle_intersection_moller(*t_base, *t_acute) is True


# ==============================================================================
# 3. PENETRATION DEPTH ANALYTICAL ACCURACY TEST CLASS
# ==============================================================================

class TestPenetrationDepthAnalyticalAccuracy:
    """Empirically verifies signed distance accuracy against analytical ground truth within 10^-4 m."""

    @pytest.mark.parametrize("separation_mm, expect_defect", [
        (-25.0, True),
        (-10.0, True),
        (-1.0, True),
        (-0.1, True),
        (0.0, False),
        (5.0, False),
    ])
    def test_concentric_cylinders_analytical_penetration(self, separation_mm: float, expect_defect: bool):
        """
        Constructs concentric cylinders with analytical radial separation d in
        [-25mm, -10mm, -1mm, -0.1mm, 0mm, +5mm].
        Asserts evaluate_mesh_penetration matches analytical truth within 10^-4 m (0.1mm).
        """
        R_body = 0.20  # 200mm body radius
        height = 0.40
        # High resolution (256 segments) -> chord error = R * (1 - cos(pi/256)) = 1.5e-5 m << 1e-4 m
        num_segs = 256
        num_rings = 10

        b_verts, b_faces = make_procedural_cylinder(radius=R_body, height=height, num_rings=num_rings, num_segments=num_segs)

        d_m = separation_mm / 1000.0
        R_garm = R_body + d_m
        g_verts, g_faces = make_procedural_cylinder(radius=R_garm, height=height * 0.7, num_rings=num_rings, num_segments=num_segs)

        # Set tolerance to 0.05mm (5e-5m) to cleanly resolve -0.1mm while ignoring numerical eps
        defects = evaluate_mesh_penetration(
            body_obj_name="Body_Cylinder",
            garment_obj_names=["Garment_Cylinder"],
            clearance_tolerance=0.00005,
            body_geo=(b_verts, b_faces),
            garment_geos={"Garment_Cylinder": (g_verts, g_faces)},
        )

        pen_defects = [d for d in defects if d.category == DefectCategory.PENETRATION and d.defect_type != "FACE_OVERLAP"]

        if expect_defect:
            assert len(pen_defects) > 0, f"Expected penetration defect for d = {separation_mm}mm"
            measured_depth_mm = pen_defects[0].penetration_depth_mm
            assert measured_depth_mm is not None
            measured_depth_m = measured_depth_mm / 1000.0
            expected_depth_m = -d_m
            err_m = abs(measured_depth_m - expected_depth_m)
            # Must match analytical truth within 10^-4 m
            assert err_m <= 1e-4, f"Penetration error {err_m:.6f}m exceeds 1e-4m tolerance for separation {separation_mm}mm"
        else:
            # For d >= 0, no penetration defects should be emitted
            assert len(pen_defects) == 0, f"False positive penetration defect for separation {separation_mm}mm"

    def test_concentric_spheres_analytical_penetration(self):
        """
        Constructs concentric sphere meshes with analytical radial separation and
        validates penetration depth within 10^-4 m.
        """
        def make_sphere_ccw(radius: float, num_lat: int = 40, num_lon: int = 80):
            verts = []
            faces = []
            for i in range(num_lat + 1):
                phi = math.pi * i / num_lat
                for j in range(num_lon):
                    theta = 2.0 * math.pi * j / num_lon
                    x = radius * math.sin(phi) * math.cos(theta)
                    y = radius * math.sin(phi) * math.sin(theta)
                    z = radius * math.cos(phi)
                    verts.append([x, y, z])
            for i in range(num_lat):
                for j in range(num_lon):
                    next_j = (j + 1) % num_lon
                    p1 = i * num_lon + j
                    p2 = i * num_lon + next_j
                    p3 = (i + 1) * num_lon + next_j
                    p4 = (i + 1) * num_lon + j
                    # Counter-clockwise winding for outward-pointing normal
                    faces.append([p1, p4, p3, p2])
            return np.array(verts, dtype=float), np.array(faces, dtype=int)

        R_body = 0.15
        b_verts, b_faces = make_sphere_ccw(R_body, num_lat=40, num_lon=80)

        for sep_mm in [-20.0, -5.0, -0.5]:
            d_m = sep_mm / 1000.0
            R_garm = R_body + d_m
            g_verts, g_faces = make_sphere_ccw(R_garm, num_lat=30, num_lon=60)

            defects = evaluate_mesh_penetration(
                body_obj_name="Body_Sphere",
                garment_obj_names=["Garment_Sphere"],
                clearance_tolerance=0.0001,
                body_geo=(b_verts, b_faces),
                garment_geos={"Garment_Sphere": (g_verts, g_faces)},
            )
            pen_defs = [d for d in defects if d.category == DefectCategory.PENETRATION and d.defect_type != "FACE_OVERLAP"]
            assert len(pen_defs) > 0
            measured_depth_m = pen_defs[0].penetration_depth_mm / 1000.0
            expected_depth_m = -d_m
            assert abs(measured_depth_m - expected_depth_m) <= 1e-4

        # Positive separation (+5.0mm) should yield zero penetration defects
        g_verts_pos, g_faces_pos = make_sphere_ccw(R_body + 0.005, num_lat=30, num_lon=60)
        defects_pos = evaluate_mesh_penetration(
            body_obj_name="Body_Sphere",
            garment_obj_names=["Garment_Sphere"],
            clearance_tolerance=0.0005,
            body_geo=(b_verts, b_faces),
            garment_geos={"Garment_Sphere": (g_verts_pos, g_faces_pos)},
        )
        pen_pos = [d for d in defects_pos if d.category == DefectCategory.PENETRATION and d.defect_type != "FACE_OVERLAP"]
        assert len(pen_pos) == 0

    def test_reverse_penetration_skin_burst_analytical_accuracy(self):
        """Body protruding through garment is flagged as SKIN_BURST with exact depth."""
        R_garm = 0.20
        height = 0.40
        b_verts, b_faces = make_procedural_cylinder(radius=0.19, height=height, num_rings=12, num_segments=64)
        g_verts, g_faces = make_procedural_cylinder(radius=R_garm, height=height * 0.8, num_rings=12, num_segments=64)

        # Displace body vertices radially outward by +18mm -> R_burst = 0.19 + 0.018 = 0.208m (+8mm burst)
        for i, v in enumerate(b_verts):
            theta = math.atan2(v[1], v[0])
            if abs(theta) <= math.pi / 8.0 and abs(v[2]) <= 0.05:
                b_verts[i][0] *= (0.208 / 0.19)
                b_verts[i][1] *= (0.208 / 0.19)

        defects = evaluate_mesh_penetration(
            body_obj_name="Body",
            garment_obj_names=["Armor"],
            clearance_tolerance=0.0005,
            body_geo=(b_verts, b_faces),
            garment_geos={"Armor": (g_verts, g_faces)},
        )
        burst_defs = [d for d in defects if d.defect_type == "SKIN_BURST"]
        assert len(burst_defs) > 0
        assert burst_defs[0].severity == DefectSeverity.CRITICAL
        # Analytical burst depth = 0.208 - 0.200 = 8.0mm
        assert math.isclose(burst_defs[0].penetration_depth_mm, 8.0, abs_tol=0.2)


# ==============================================================================
# 4. HAIR GROOMING CURVE BOUNDARY STRESS TEST CLASS
# ==============================================================================

class TestHairGroomingCurveBoundaryStress:
    """Stress-tests hair grooming curve collision evaluation across lengths, zigzags, and thresholds."""

    @pytest.fixture
    def scalp_geometry(self):
        """High-resolution scalp cylinder (R=0.10m, segs=256)."""
        verts, faces = make_procedural_cylinder(radius=0.10, height=0.20, num_rings=16, num_segments=256, center_z=0.0)
        return verts, faces

    def test_splines_point_count_extremes(self, scalp_geometry):
        """Splines with 0, 1, 2, and 120 points execute cleanly without index errors."""
        splines = [
            {"points": []},  # 0 points
            {"points": [(0.102, 0.0, 0.0)]},  # 1 point
            {"points": [(0.102, 0.0, 0.0), (0.12, 0.0, 0.05)]},  # 2 points
            {"points": [(0.102 + i * 0.001, 0.0, i * 0.001) for i in range(120)]},  # 120 points
        ]
        defects = evaluate_hair_grooming_intersections(
            hair_obj_names=["Groom_Extreme_Lengths"],
            body_obj_name="Scalp",
            hair_splines={"Groom_Extreme_Lengths": splines},
            body_geo=scalp_geometry,
        )
        # All valid strands sit outside surface, so 0 defects
        assert len(defects) == 0

    def test_extreme_zigzag_curves_shaft_collision(self, scalp_geometry):
        """High-frequency zigzag curve oscillating through scalp surface is reliably caught."""
        zigzag_pts = []
        for i in range(60):
            # Alternates between R=0.11m (outside) and R=0.07m (inside scalp)
            rad = 0.11 if i % 2 == 0 else 0.07
            zigzag_pts.append((rad, 0.0, -0.05 + i * 0.002))

        splines = [{"points": zigzag_pts}]
        defects = evaluate_hair_grooming_intersections(
            hair_obj_names=["Groom_Zigzag"],
            body_obj_name="Scalp",
            hair_splines={"Groom_Zigzag": splines},
            body_geo=scalp_geometry,
        )
        assert len(defects) > 0
        shaft_def = next(d for d in defects if d.defect_type == "GROOMING_BODY_COLLISION")
        assert shaft_def.severity == DefectSeverity.CRITICAL
        assert shaft_def.penetration_count > 20

    @pytest.mark.parametrize("offset_mm, expect_submerged", [
        (-2.00, True),
        (-1.05, True),
        (-1.001, True),
        (-0.999, False),
        (-0.95, False),
        (0.00, False),
    ])
    def test_root_submerged_boundary_threshold_negative_1mm(self, scalp_geometry, offset_mm: float, expect_submerged: bool):
        """
        Roots positioned precisely on the submerged boundary threshold (-1.0mm).
        Deference deeper than -1.0mm must be flagged as GROOMING_ROOT_SUBMERGED.
        """
        r_root = 0.10 + (offset_mm / 1000.0)
        # Extend points radially outward so shaft does not collide
        splines = [{
            "points": [
                (r_root, 0.0, 0.0),
                (r_root + 0.02, 0.0, 0.01),
                (r_root + 0.04, 0.0, 0.02),
            ]
        }]
        defects = evaluate_hair_grooming_intersections(
            hair_obj_names=["Hair_Submerged_Test"],
            body_obj_name="Scalp",
            hair_splines={"Hair_Submerged_Test": splines},
            body_geo=scalp_geometry,
        )
        is_submerged = any(d.defect_type == "GROOMING_ROOT_SUBMERGED" for d in defects)
        assert is_submerged == expect_submerged, (
            f"Offset {offset_mm:+7.3f}mm: expected submerged={expect_submerged}, got {is_submerged}"
        )

    @pytest.mark.parametrize("offset_mm, expect_detached", [
        (2.00, False),
        (3.95, False),
        (3.999, False),
        (4.001, True),
        (4.05, True),
        (6.00, True),
    ])
    def test_root_floating_boundary_threshold_positive_4mm(self, scalp_geometry, offset_mm: float, expect_detached: bool):
        """
        Roots positioned precisely on the floating/detached threshold (+4.0mm).
        Distances beyond +4.0mm must be flagged as GROOMING_ROOT_DETACHED (GROOM_FLOAT_*).
        """
        r_root = 0.10 + (offset_mm / 1000.0)
        splines = [{
            "points": [
                (r_root, 0.0, 0.0),
                (r_root + 0.02, 0.0, 0.01),
                (r_root + 0.04, 0.0, 0.02),
            ]
        }]
        defects = evaluate_hair_grooming_intersections(
            hair_obj_names=["Hair_Floating_Test"],
            body_obj_name="Scalp",
            hair_splines={"Hair_Floating_Test": splines},
            body_geo=scalp_geometry,
        )
        is_detached = any(d.defect_type == "GROOMING_ROOT_DETACHED" for d in defects)
        assert is_detached == expect_detached, (
            f"Offset {offset_mm:+7.3f}mm: expected detached={expect_detached}, got {is_detached}"
        )

    def test_hair_garment_collision_detection(self, scalp_geometry):
        """Hair curve clipping through garment collar/shoulders is flagged as GROOMING_GARMENT_COLLISION."""
        # Garment cylinder collar positioned around neck z=-0.05
        g_verts, g_faces = make_procedural_cylinder(radius=0.12, height=0.06, num_rings=8, num_segments=64, center_z=-0.05)
        # Hair strand starting at scalp and piercing through collar
        strand = [
            (0.102, 0.0, 0.05),
            (0.110, 0.0, 0.0),
            (0.115, 0.0, -0.05),  # Pierces through collar at R=0.12 (inside collar by 5mm)
            (0.130, 0.0, -0.10),
        ]
        defects = evaluate_hair_grooming_intersections(
            hair_obj_names=["Hair_Long"],
            body_obj_name="Scalp",
            garment_obj_names=["Collar"],
            hair_splines={"Hair_Long": [{"points": strand}]},
            body_geo=scalp_geometry,
            garment_geos={"Collar": (g_verts, g_faces)},
        )
        garm_defs = [d for d in defects if d.defect_type == "GROOMING_GARMENT_COLLISION"]
        assert len(garm_defs) > 0
        assert "Collar" in garm_defs[0].affected_objects
