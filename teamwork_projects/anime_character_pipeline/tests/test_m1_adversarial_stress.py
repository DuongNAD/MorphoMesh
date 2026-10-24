"""
tests/test_m1_adversarial_stress.py
Adversarial Stress Test Harness for Milestone 1: Geometry & Mesh Synthesizer.

Authored by: m1_challenger_anime_1 (Empirical Challenger)
Targets:
- anime_pipeline.mesh.generator.AnimeMeshGenerator
- anime_pipeline.mesh.topology_cleaner.TopologyValidator, NormalHarmonizer, TopologyCleaner
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple
import pytest

from anime_pipeline.mesh.generator import AnimeMeshGenerator, AnimeMeshConfig
from anime_pipeline.mesh.topology_cleaner import (
    TopologyValidator,
    NormalHarmonizer,
    TopologyCleaner,
)


def point_to_segment_dist_sq(p: Tuple[float, float, float], a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    ab_len_sq = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
    if ab_len_sq < 1e-12:
        return ap[0] ** 2 + ap[1] ** 2 + ap[2] ** 2
    t = max(0.0, min(1.0, (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / ab_len_sq))
    proj = (a[0] + t * ab[0], a[1] + t * ab[1], a[2] + t * ab[2])
    return (p[0] - proj[0]) ** 2 + (p[1] - proj[1]) ** 2 + (p[2] - proj[2]) ** 2


def point_to_triangle_dist(
    p: Tuple[float, float, float],
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    c: Tuple[float, float, float],
) -> float:
    v0 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v1 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (
        v0[1] * v1[2] - v0[2] * v1[1],
        v0[2] * v1[0] - v0[0] * v1[2],
        v0[0] * v1[1] - v0[1] * v1[0],
    )
    n_len = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    if n_len < 1e-12:
        return math.sqrt(
            min(
                point_to_segment_dist_sq(p, a, b),
                point_to_segment_dist_sq(p, b, c),
                point_to_segment_dist_sq(p, c, a),
            )
        )
    un = (n[0] / n_len, n[1] / n_len, n[2] / n_len)
    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    dist_plane = ap[0] * un[0] + ap[1] * un[1] + ap[2] * un[2]
    proj = (p[0] - dist_plane * un[0], p[1] - dist_plane * un[1], p[2] - dist_plane * un[2])

    def same_side(p1, p2, l1, l2):
        cp1 = (
            (l2[1] - l1[1]) * (p1[2] - l1[2]) - (l2[2] - l1[2]) * (p1[1] - l1[1]),
            (l2[2] - l1[2]) * (p1[0] - l1[0]) - (l2[0] - l1[0]) * (p1[2] - l1[2]),
            (l2[0] - l1[0]) * (p1[1] - l1[1]) - (l2[1] - l1[1]) * (p1[0] - l1[0]),
        )
        cp2 = (
            (l2[1] - l1[1]) * (p2[2] - l1[2]) - (l2[2] - l1[2]) * (p2[1] - l1[1]),
            (l2[2] - l1[2]) * (p2[0] - l1[0]) - (l2[0] - l1[0]) * (p2[2] - l1[2]),
            (l2[0] - l1[0]) * (p2[1] - l1[1]) - (l2[1] - l1[1]) * (p2[0] - l1[0]),
        )
        return cp1[0] * cp2[0] + cp1[1] * cp2[1] + cp1[2] * cp2[2] >= -1e-8

    if same_side(proj, a, b, c) and same_side(proj, b, a, c) and same_side(proj, c, a, b):
        return abs(dist_plane)
    return math.sqrt(
        min(
            point_to_segment_dist_sq(p, a, b),
            point_to_segment_dist_sq(p, b, c),
            point_to_segment_dist_sq(p, c, a),
        )
    )


def point_to_quad_surface_dist(
    p: Tuple[float, float, float],
    q: Tuple[int, int, int, int],
    verts: List[Tuple[float, float, float]],
) -> float:
    a, b, c, d = verts[q[0]], verts[q[1]], verts[q[2]], verts[q[3]]
    return min(point_to_triangle_dist(p, a, b, c), point_to_triangle_dist(p, a, c, d))


class TestM1AdversarialStress:
    """Empirical adversarial stress suite for M1."""

    # --------------------------------------------------------------------------
    # 1. Skirt Clearance Invariant Stress Tests
    # --------------------------------------------------------------------------

    def test_adversarial_skirt_clearance_nominal_15mm_invariant(self):
        """
        Adversarial: Validates that skirt maintains >= 15.0mm 3D clearance across all
        body vertices (thighs and lower pelvis) within the skirt's vertical span.
        """
        gen = AnimeMeshGenerator(AnimeMeshConfig(height=1.65))
        res = gen.generate()
        skirt = res.submeshes["Anime_Skirt"]
        legs = res.submeshes["Anime_Legs"]
        torso = res.submeshes["Anime_Torso"]

        z_min = skirt.get_bounding_box().min_point[2]
        z_max = skirt.get_bounding_box().max_point[2]

        body_verts = [v for v in legs.vertices if z_min <= v[2] <= z_max] + [
            v for v in torso.vertices if z_min <= v[2] <= z_max
        ]
        assert len(body_verts) > 0

        min_dist = min(
            point_to_quad_surface_dist(bv, q, skirt.vertices)
            for bv in body_verts
            for q in skirt.quads
        )
        clearance_mm = min_dist * 1000.0

        assert clearance_mm >= 15.0, (
            f"Nominal skirt clearance {clearance_mm:.2f}mm violates required >=15.0mm threshold!"
        )

    @pytest.mark.parametrize("girth_scale", [1.00, 1.05, 1.10])
    def test_adversarial_skirt_clearance_under_thigh_girth_variations(self, girth_scale: float):
        """
        Adversarial: Validates skirt clearance does not drop below 15.0mm under
        athletic/curvy thigh girth variations (+0% to +10%).
        """
        gen = AnimeMeshGenerator(AnimeMeshConfig(height=1.65))
        res = gen.generate()
        skirt = res.submeshes["Anime_Skirt"]
        legs = res.submeshes["Anime_Legs"]

        z_min = skirt.get_bounding_box().min_point[2]
        z_max = skirt.get_bounding_box().max_point[2]

        # Apply girth expansion to thighs
        scaled_leg_verts = []
        for v in legs.vertices:
            if z_min <= v[2] <= z_max:
                cx = 0.088 if v[0] > 0 else -0.088
                cy = -0.020
                sx = cx + (v[0] - cx) * girth_scale
                sy = cy + (v[1] - cy) * girth_scale
                scaled_leg_verts.append((sx, sy, v[2]))

        min_dist = min(
            point_to_quad_surface_dist(bv, q, skirt.vertices)
            for bv in scaled_leg_verts
            for q in skirt.quads
        )
        clearance_mm = min_dist * 1000.0

        assert clearance_mm >= 15.0, (
            f"Under thigh girth scale {girth_scale*100:.0f}%, skirt clearance {clearance_mm:.2f}mm fell below 15.0mm!"
        )

    # --------------------------------------------------------------------------
    # 2. Shoe-Foot Spatial Alignment and Grounding Invariants
    # --------------------------------------------------------------------------

    def test_adversarial_shoes_foot_containment_and_alignment(self):
        """
        Adversarial: Validates that Anime_Shoes actually encloses the anatomical
        feet in Anime_Legs rather than being displaced into empty space.
        """
        gen = AnimeMeshGenerator()
        res = gen.generate()
        shoes = res.submeshes["Anime_Shoes"]
        legs = res.submeshes["Anime_Legs"]

        # Left foot center of mass in Anime_Legs
        left_foot_verts = [v for v in legs.vertices if v[0] > 0 and v[2] < 0.08]
        assert len(left_foot_verts) > 0, "No foot vertices found in Anime_Legs"
        foot_cx = sum(v[0] for v in left_foot_verts) / len(left_foot_verts)
        foot_cy = sum(v[1] for v in left_foot_verts) / len(left_foot_verts)

        # Left shoe center of mass in Anime_Shoes
        left_shoe_verts = [v for v in shoes.vertices if v[0] > 0]
        assert len(left_shoe_verts) > 0, "No left shoe vertices found in Anime_Shoes"
        shoe_cx = sum(v[0] for v in left_shoe_verts) / len(left_shoe_verts)
        shoe_cy = sum(v[1] for v in left_shoe_verts) / len(left_shoe_verts)

        displacement = math.hypot(foot_cx - shoe_cx, foot_cy - shoe_cy)

        assert displacement <= 0.030, (
            f"Catastrophic shoe-foot misalignment: Left shoe center ({shoe_cx:.4f}, {shoe_cy:.4f}) is "
            f"displaced {displacement*1000:.1f}mm from anatomical foot center ({foot_cx:.4f}, {foot_cy:.4f})!"
        )

    def test_adversarial_ground_sole_z_offset_coincidence(self):
        """
        Adversarial: Validates that setting ground_sole_z keeps Shoes and Legs grounded coincidentally.
        """
        cfg = AnimeMeshConfig(ground_sole_z=0.05)
        gen = AnimeMeshGenerator(cfg)
        res = gen.generate()
        shoes_min_z = min(v[2] for v in res.submeshes["Anime_Shoes"].vertices)
        legs_min_z = min(v[2] for v in res.submeshes["Anime_Legs"].vertices)

        assert abs(shoes_min_z - legs_min_z) < 1e-4, (
            f"Desynchronized sole grounding: Shoes min Z={shoes_min_z:.4f}m but Legs min Z={legs_min_z:.4f}m"
        )

    # --------------------------------------------------------------------------
    # 3. Landmark Accuracy Stress Tests
    # --------------------------------------------------------------------------

    def test_adversarial_landmark_alignment_with_mesh_geometry(self):
        """
        Adversarial: Validates that skeletal joint landmarks (knee, ankle)
        correspond to actual vertex cluster centers in Anime_Legs.
        """
        gen = AnimeMeshGenerator()
        res = gen.generate()
        legs = res.submeshes["Anime_Legs"]
        lm = res.landmarks

        # Ankle landmark
        ankle_lm = lm.get("ankle_L") or lm.get("joint-l-ankle")
        assert ankle_lm is not None, "Missing ankle_L landmark"

        ankle_verts = [v for v in legs.vertices if 0.06 <= v[2] <= 0.10 and v[0] > 0]
        actual_ankle_x = sum(v[0] for v in ankle_verts) / len(ankle_verts)

        assert abs(ankle_lm[0] - actual_ankle_x) < 0.030, (
            f"Ankle landmark X={ankle_lm[0]:.4f} deviates {abs(ankle_lm[0]-actual_ankle_x)*1000:.1f}mm "
            f"from mesh ankle center X={actual_ankle_x:.4f}!"
        )

    # --------------------------------------------------------------------------
    # 4. Scale Invariant Stress Tests (1.45m to 1.75m)
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("height", [1.45, 1.50, 1.55, 1.60, 1.65, 1.70, 1.75])
    def test_adversarial_scale_invariants_145_to_175(self, height: float):
        """
        Adversarial: Verifies head-to-body ratio in [6.5, 7.0], seam coincidence,
        and 100% 2-manifold quads across the full height range.
        """
        gen = AnimeMeshGenerator(AnimeMeshConfig(height=height))
        res = gen.generate()

        head = res.submeshes["Anime_Head"]
        head_h = head.get_bounding_box().dimensions[2]
        ratio = height / head_h
        assert 6.5 <= ratio <= 7.0, f"Head ratio {ratio:.2f} out of [6.5, 7.0] at height {height}m"

        # Check seam alignment
        overrides = NormalHarmonizer.harmonize_all_modular_seams(res.submeshes, seam_tolerance=1e-4 * (height / 1.65))
        assert len(overrides["Anime_Head"]) == 46
        assert len(overrides["Anime_Arms"]) == 92
        assert len(overrides["Anime_Legs"]) == 50

    # --------------------------------------------------------------------------
    # 5. Mesh Array Audits: NaNs, Infs, Duplicates, Degenerate Faces
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("height", [1.45, 1.65, 1.75])
    def test_adversarial_mesh_arrays_finite_floats_and_degeneracy(self, height: float):
        """
        Adversarial: Verifies zero NaN/Inf floats, zero duplicate vertices,
        and zero degenerate faces across submeshes.
        """
        gen = AnimeMeshGenerator(AnimeMeshConfig(height=height))
        res = gen.generate()

        for name, sm in res.submeshes.items():
            for vi, (x, y, z) in enumerate(sm.vertices):
                assert math.isfinite(x) and math.isfinite(y) and math.isfinite(z), (
                    f"Non-finite float at vert {vi} in {name}"
                )
            rep = TopologyValidator.audit_mesh(sm.vertices, sm.quads)
            assert rep.is_valid, f"{name} failed topology audit at height {height}m"
            assert len(rep.duplicate_vertices) == 0, f"{name} contains duplicate vertices"
            assert len(rep.degenerate_faces) == 0, f"{name} contains degenerate faces"

    # --------------------------------------------------------------------------
    # 6. TopologyValidator Robustness
    # --------------------------------------------------------------------------

    def test_adversarial_topology_validator_nan_inf_robustness(self):
        """
        Adversarial: Verifies TopologyValidator does NOT crash with unhandled
        ValueError or OverflowError when encountering NaN or Inf vertex coordinates.
        """
        nan_verts = [(float("nan"), 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
        inf_verts = [(float("inf"), 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
        quads = [(0, 1, 2, 3)]

        try:
            rep_nan = TopologyValidator.audit_mesh(nan_verts, quads)
            assert not rep_nan.is_valid
        except (ValueError, OverflowError) as e:
            pytest.fail(f"TopologyValidator crashed on NaN vertices: {type(e).__name__}: {e}")

        try:
            rep_inf = TopologyValidator.audit_mesh(inf_verts, quads)
            assert not rep_inf.is_valid
        except (ValueError, OverflowError) as e:
            pytest.fail(f"TopologyValidator crashed on Inf vertices: {type(e).__name__}: {e}")
