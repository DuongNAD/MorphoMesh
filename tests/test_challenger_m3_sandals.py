"""
MorphoMesh: Milestone M3 Adversarial Empirical Challenger Test Suite.
Challenger M3.1: Sandals Clearance, Height & Toes Exposure Empirical Challenger.

Empirically stress-tests procedural flat strappy sandals implementation in `src/morphomesh/wardrobe.py`:
1. Extreme character scaling (H in [1.50m, 1.80m]) and leg girth variations (k_leg in [0.8, 1.2]).
2. Total footwear height <= 50.0mm across all scales.
3. Sole length in [0.22m, 0.25m] and ground elevation Z = 0.0m.
4. 100% exposed toes and toenails: sole perimeter terminates at Y = -0.138m,
   big toe and pinky toe landmarks extend past sole with >= 7mm clearance.
5. Zero skin penetration: signed distance to underlying foot mesh >= +1.5mm.
6. Medial arch rise: top footbed elevates by > +3.5mm along medial border.
7. Normalized Rigify skinning: 100% of vertices have normalized weights sum w_i = 1.0 +- 1e-4 in DEF-foot and DEF-toe.
8. Topology: verify zero degenerate (zero-area) faces.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pytest

from morphomesh.human_generator import generate_human_base_mesh, HumanAnatomyConfig
from morphomesh.wardrobe import (
    generate_flat_sandals,
    generate_flat_strappy_sandals,
)
from morphomesh.visual_critic import PurePythonBVHTree


# ==============================================================================
# HELPER FUNCTIONS FOR EMPIRICAL EVALUATION
# ==============================================================================

def compute_signed_distance_to_foot(
    sandal_vertices: List[Tuple[float, float, float]],
    body_mesh,
    foot_vg_name: str = "foot_L",
) -> List[Tuple[int, float, Tuple[float, float, float], Tuple[float, float, float]]]:
    """Computes signed distance from each sandal vertex to the underlying foot mesh surface."""
    foot_v_indices = set(body_mesh.vertex_groups.get(foot_vg_name, []))
    if not foot_v_indices:
        return []
    foot_faces = [f for f in body_mesh.faces if any(v in foot_v_indices for v in f)]
    bvh = PurePythonBVHTree.FromPolygons(body_mesh.vertices, foot_faces)

    results = []
    for i, v in enumerate(sandal_vertices):
        loc, norm, idx, dist = bvh.find_nearest(v)
        if loc is not None:
            offset = np.array(v) - np.array(loc)
            dot = np.dot(offset, np.array(norm))
            # If dot >= 0, point is outside surface (positive clearance)
            # If dot < 0, point is inside foot (penetration)
            s_dist = dist if dot >= 0 else -dist
            results.append((i, s_dist, loc, norm))
    return results


# ==============================================================================
# TEST SUITE: CHALLENGER M3.1 EMPIRICAL SANDALS STRESS TESTS
# ==============================================================================

class TestChallengerM3SandalsEmpirical:
    """Adversarial stress-testing of flat strappy sandals against M3 specifications."""

    def test_sandals_ground_elevation_invariant(self):
        """Invariant: Outsole must rest flush on ground at Z = 0.0m across all scales."""
        for H in [1.50, 1.65, 1.80]:
            sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
            for side in ["L", "R"]:
                mesh = sandals[f"Mesh_Sandal_{side}"]
                zs = [v[2] for v in mesh.vertices]
                min_z = min(zs)
                assert abs(min_z) < 1e-4, f"Outsole min Z={min_z:.6f}m at H={H}m must be exactly 0.0m"

    def test_sandals_topology_and_zero_degenerate_faces(self):
        """Invariant: Zero degenerate (zero-area) faces across all scales and sides."""
        for H in [1.50, 1.65, 1.80]:
            sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
            for side in ["L", "R"]:
                mesh = sandals[f"Mesh_Sandal_{side}"]
                assert len(mesh.faces) > 0
                assert len(mesh.faces) % 2 == 0, "Expected pure quad-derived triangulation (even count)"
                for f_idx, f in enumerate(mesh.faces):
                    p0 = np.array(mesh.vertices[f[0]])
                    p1 = np.array(mesh.vertices[f[1]])
                    p2 = np.array(mesh.vertices[f[2]])
                    area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0))
                    assert area > 1e-9, f"Face {f_idx} ({f}) has degenerate zero area: {area} at H={H}m"

    def test_sandals_normalized_rigify_skinning_all_vertices(self):
        """Invariant: 100% of vertices must have normalized weights sum w_i = 1.0 +- 1e-4."""
        for H in [1.50, 1.65, 1.80]:
            sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
            for side in ["L", "R"]:
                mesh = sandals[f"Mesh_Sandal_{side}"]
                weights = mesh.skin_weights
                assert len(weights) == len(mesh.vertices)
                for i in range(len(mesh.vertices)):
                    w_dict = weights[i]
                    w_sum = sum(w_dict.values())
                    assert abs(w_sum - 1.0) <= 1e-4, f"Vertex {i} weights sum {w_sum} != 1.0"
                    for b_name in [f"DEF-foot.{side}", f"DEF-toe.{side}"]:
                        assert b_name in w_dict
                        assert 0.0 <= w_dict[b_name] <= 1.0

    def test_sandals_medial_arch_rise_greater_than_3_5mm(self):
        """Invariant: Medial longitudinal arch rises by > +3.5mm above baseline footbed."""
        for H in [1.50, 1.65, 1.80]:
            s = H / 1.65
            sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
            mesh_l = sandals["Mesh_Sandal_L"]
            # Medial edge vertices (f_trans = -1.0) in arch zone
            medial_arch_zs = [
                v[2] for v in mesh_l.vertices
                if v[0] < (0.088 * s - 0.015 * s) and -0.040 * s <= v[1] <= 0.020 * s and 0.002 * s < v[2] < 0.020 * s
            ]
            assert len(medial_arch_zs) > 0, f"No medial arch vertices found at H={H}m"
            max_arch_z = max(medial_arch_zs)
            baseline_z = 0.0040 * s
            rel_rise_mm = (max_arch_z - baseline_z) * 1000.0
            assert rel_rise_mm > 3.5, f"Medial arch relative rise {rel_rise_mm:.2f}mm <= 3.5mm at H={H}m"

    # --------------------------------------------------------------------------
    # ADVERSARIAL STRESS TESTS (HIGHLIGHTING DISCREPANCIES / DEFECTS)
    # --------------------------------------------------------------------------

    def test_sandals_height_bound_across_all_scales(self):
        """Stress Test: Total footwear height <= 50.0mm across all scales H in [1.50, 1.80]m.
        Catches scale dilation bug where height at H=1.80m expands to 52.66mm.
        """
        for H in [1.50, 1.65, 1.80]:
            sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
            for side in ["L", "R"]:
                mesh = sandals[f"Mesh_Sandal_{side}"]
                zs = [v[2] for v in mesh.vertices]
                total_height_mm = (max(zs) - min(zs)) * 1000.0
                assert total_height_mm <= 50.0, (
                    f"Scale dilation failure at H={H}m: total height {total_height_mm:.2f}mm exceeds 50.0mm limit"
                )

    def test_sandals_sole_length_bound_across_all_scales(self):
        """Stress Test: Sole length in [0.22, 0.25]m across extreme scaling H in [1.50, 1.80]m.
        Catches sole length expansion at H=1.80m (0.2676m > 0.25m).
        """
        for H in [1.50, 1.65, 1.80]:
            sandals = generate_flat_strappy_sandals(height=H, scale=1.0)
            mesh = sandals["Mesh_Sandal_L"]
            ys = [v[1] for v in mesh.vertices]
            sole_len = max(ys) - min(ys)
            assert 0.22 <= sole_len <= 0.25, (
                f"Sole length bounds failure at H={H}m: sole length {sole_len:.4f}m not in [0.22, 0.25]m"
            )

    def test_sandals_toes_and_toenails_exposure_and_clearance(self):
        """Stress Test: Big toe and pinky toe landmarks extend past sole with >= 7mm clearance.
        Catches discrepancy where big toe landmark clearance is 0.0mm and pinky toe is behind sole by 35mm.
        """
        cfg = HumanAnatomyConfig(height=1.65)
        res = generate_human_base_mesh(config=cfg)
        lms = res.landmarks
        sandals = generate_flat_strappy_sandals(foot_landmarks=lms, height=1.65, scale=1.0)
        mesh_l = sandals["Mesh_Sandal_L"]

        min_sandal_y = min(v[1] for v in mesh_l.vertices)
        assert abs(min_sandal_y - (-0.138)) < 0.005, f"Sole front {min_sandal_y:.4f}m expected at -0.138m"

        # Measure physical foot mesh toe tips in MakeHuman base mold
        foot_v_indices = set(res.mesh.vertex_groups.get("foot_L", []))
        foot_pts = [res.mesh.vertices[vi] for vi in foot_v_indices]
        tb_y = min(v[1] for v in foot_pts if v[0] < 0.08)
        t5_y = min(v[1] for v in foot_pts if v[0] > 0.11)
        big_toe_clearance_mm = (min_sandal_y - tb_y) * 1000.0
        assert big_toe_clearance_mm >= 7.0, (
            f"Big toe exposure clearance failure: clearance is {big_toe_clearance_mm:.2f}mm < 7.0mm"
        )

        pinky_toe_clearance_mm = (min_sandal_y - t5_y) * 1000.0
        assert pinky_toe_clearance_mm >= 7.0, (
            f"Pinky toe exposure clearance failure: clearance is {pinky_toe_clearance_mm:.2f}mm < 7.0mm"
        )

    def test_sandals_skin_clearance_buffer_canonical_scale(self):
        """Stress Test: Signed distance from all sandal vertices to foot skin >= +1.5mm at canonical scale.
        Catches sub-malleolar wrap vertex 206 skin penetration (-0.13mm).
        """
        cfg = HumanAnatomyConfig(height=1.65)
        res = generate_human_base_mesh(config=cfg)
        sandals = generate_flat_strappy_sandals(foot_landmarks=res.landmarks, height=1.65, scale=1.0)

        dists = compute_signed_distance_to_foot(sandals["Mesh_Sandal_L"].vertices[170:], res.mesh, "foot_L")
        min_signed_dist = min(d[1] for d in dists)
        penetrations = [d for d in dists if d[1] < 0.0]
        sub_buffer = [d for d in dists if d[1] < 0.0015]

        assert min_signed_dist >= 0.0015, (
            f"Skin penetration / buffer failure: min signed distance is {min_signed_dist*1000:.3f}mm < +1.5mm. "
            f"Penetrating vertices count: {len(penetrations)}, below buffer: {len(sub_buffer)}."
        )

    def test_sandals_skin_clearance_under_leg_girth_variations(self):
        """Stress Test: Zero skin penetration under leg variations (k_leg in [0.8, 1.2]).
        Catches lack of k_leg parameter propagation causing up to -7.64mm strap skin penetration.
        """
        for kl in [0.8, 1.2]:
            leg_len = 0.88 * kl
            cfg = HumanAnatomyConfig(height=1.65, leg_length=leg_len)
            res = generate_human_base_mesh(config=cfg)
            sandals = generate_flat_strappy_sandals(foot_landmarks=res.landmarks, height=1.65, scale=1.0, k_leg=kl)

            dists = compute_signed_distance_to_foot(sandals["Mesh_Sandal_L"].vertices[170:], res.mesh, "foot_L")
            min_dist = min(d[1] for d in dists)
            assert min_dist >= 0.0015, (
                f"Leg variation clearance failure at k_leg={kl}: min signed clearance is {min_dist*1000:.2f}mm < +1.5mm"
            )
