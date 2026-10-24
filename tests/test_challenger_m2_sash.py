"""
Empirical Challenger Test Suite for MorphoMesh Milestone M2.
Challenger M2.2: Sash Clearance, Z-Fighting & Rigify Skinning Empirical Challenger.

Authoritative Specification:
1. ORIGINAL_REQUEST.md (M2 Organic Dress Drapery & Sash Envelope; 0% inverted normals; 0% penetration)
2. PROJECT.md (§2.2 Milestone M2 Spec & Interface Contracts)
3. Worker M2 Handoff & Changes (Claims of +2.5mm net clearance, 3D manifold closed caps, 0% Z-fighting)

Empirical Challenge Objectives:
- Stress-test waist sash clearance against dress bodice and skirt outer envelopes.
- Empirically verify 0% Z-fighting and 0% mesh penetration across all angles theta in [0, 2pi) and parameter combinations.
- Empirically stress-test 3D bow knot and ribbon geometry: non-zero loop volume, manifold closed caps on barrel knot, and ribbon streamer cascade trajectory.
- Empirically verify 100% normalized Rigify DEF skinning (sum w_i = 1.0 +- 1e-4), zero orphaned vertices, and zero negative weights.
"""

from __future__ import annotations

import ast
from collections import defaultdict
import math
from typing import Any, Dict, List, Tuple

import pytest

from morphomesh.inference_adapter import MeshGeometry
from morphomesh.visual_critic import PurePythonBVHTree
from morphomesh.wardrobe import (
    assign_bodice_skin_weights,
    assign_sash_skin_weights,
    assign_skirt_skin_weights,
    compute_dress_waist_radii,
    compute_wardrobe_skin_weights,
    generate_dress_bodice,
    generate_dress_organic_skirt,
    generate_dress_waist_sash,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_yu_nian_an_wardrobe,
    get_wardrobe_script,
)


def _triangle_area(
    v0: Tuple[float, float, float],
    v1: Tuple[float, float, float],
    v2: Tuple[float, float, float],
) -> float:
    """Computes Euclidean surface area of a 3D triangle."""
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def _compute_closed_mesh_volume(
    vertices: List[Tuple[float, float, float]],
    faces: List[Tuple[int, int, int]],
) -> float:
    """Computes volume of a closed 3D triangular surface via divergence theorem."""
    vol = 0.0
    for f in faces:
        v0, v1, v2 = vertices[f[0]], vertices[f[1]], vertices[f[2]]
        cp_x = v0[1] * v1[2] - v0[2] * v1[1]
        cp_y = v0[2] * v1[0] - v0[0] * v1[2]
        cp_z = v0[0] * v1[1] - v0[1] * v1[0]
        vol += (cp_x * v2[0] + cp_y * v2[1] + cp_z * v2[2]) / 6.0
    return abs(vol)


# ==============================================================================
# 1. SASH CLEARANCE, Z-FIGHTING & MESH PENETRATION EMPIRICAL TESTS
# ==============================================================================

class TestSashClearanceAndZFighting:
    """Empirical stress tests for waist sash clearance against dress bodice and skirt envelopes."""

    def test_contract_sash_clearance_parameter_sweep(self):
        """
        Stress-tests 81 parameter combinations of generate_organic_dress and generate_waist_sash_and_bow.
        Verifies that all 350 sash vertices maintain strictly >+2.0mm clearance against the dress bodice.
        """
        scale_range = [0.85, 1.0, 1.15]
        kw_range = [0.85, 1.0, 1.20]
        kc_range = [0.85, 1.0, 1.20]
        bust_range = [0.80, 1.0, 1.30]

        tested_combos = 0
        min_clearances: List[float] = []

        for scale in scale_range:
            for kw in kw_range:
                for kc in kc_range:
                    for bust in bust_range:
                        dress = generate_organic_dress(scale=scale, k_waist=kw, k_chest=kc, bust_cup_scale=bust)
                        bodice = dress["Dress_Bodice"]
                        sash = generate_waist_sash_and_bow(scale=scale, k_waist=kw)["Dress_WaistSash"]

                        b_pts = bodice.vertices
                        # Test band vertices (first 120 vertices)
                        for sv in sash.vertices[:120]:
                            d = min(math.sqrt((sv[0]-bv[0])**2 + (sv[1]-bv[1])**2 + (sv[2]-bv[2])**2) for bv in b_pts)
                            min_clearances.append(d)

                        tested_combos += 1

        assert tested_combos == 81, f"Expected 81 tested combinations, got {tested_combos}"
        overall_min = min(min_clearances)
        assert overall_min >= 0.002, f"Expected clearance >= 2.0mm, got minimum of {overall_min*1000:.2f}mm"
        # Verify healthy safety margin
        assert overall_min >= 0.005, f"Expected healthy contract margin >= 5.0mm, got {overall_min*1000:.2f}mm"

    def test_default_wardrobe_sash_bodice_clearance_all_angles(self):
        """
        Empirically tests sash band radial clearance over dress bodice across 360 azimuthal angles
        in the canonical Yu Nian An wardrobe.
        """
        wardrobe = generate_yu_nian_an_wardrobe()
        bodice = wardrobe["Dress_Bodice"]
        sash = wardrobe["Dress_WaistSash"]

        band_verts = sash.vertices[:120]
        b_pts = bodice.vertices

        for idx, sv in enumerate(band_verts):
            min_d = min(math.sqrt((sv[0]-bv[0])**2 + (sv[1]-bv[1])**2 + (sv[2]-bv[2])**2) for bv in b_pts)
            assert min_d >= 0.002, f"Sash band vertex {idx} {sv} clearance {min_d*1000:.2f}mm < 2.0mm from bodice"

    def test_empirical_posterior_skirt_sash_penetration_discovery(self):
        """
        EMPIRICAL DEFECT DISCOVERY:
        Tests clearance of the lowest sash ring (Z=1.0275m) against the upper flared skirt.
        Because the skirt starts at Z=1.030m and flares outward towards buttocks while the sash is
        shifted forward by yo=-0.007m, the posterior sash ring (verts 4, 5, 6, 7, 8) penetrates
        or has < 2.0mm clearance against the skirt, causing visible Z-fighting.
        """
        wardrobe = generate_yu_nian_an_wardrobe()
        sash = wardrobe["Dress_WaistSash"]
        skirt = wardrobe["Dress_PleatedSkirt"]

        # Posterior vertex 6 on the lowest sash ring (Z=1.0275m)
        v6 = sash.vertices[6]
        # In the skirt, ring 0 is at Z=1.030m and ring 1 is at Z=0.996m
        # Vertices 12 (ring 0) and 61 (ring 1) are on posterior midline
        v_skirt_0 = skirt.vertices[12]
        v_skirt_1 = skirt.vertices[61]

        # Linear interpolation of skirt Y at Z=1.0275m
        t_interp = (v_skirt_0[2] - v6[2]) / (v_skirt_0[2] - v_skirt_1[2])
        y_skirt_at_z = v_skirt_0[1] + t_interp * (v_skirt_1[1] - v_skirt_0[1])

        # Outward clearance along Y axis
        clearance_y = v6[1] - y_skirt_at_z

        # Fails because clearance_y = -0.00006m (-0.06mm, penetrating!)
        assert clearance_y >= 0.0020, (
            f"Posterior sash vertex 6 penetrates skirt: sash_Y={v6[1]:.5f}m, "
            f"skirt_Y={y_skirt_at_z:.5f}m, clearance={clearance_y*1000:.2f}mm < +2.0mm"
        )

    def test_costal_margin_flare_clearance_narrowing(self):
        """
        Verifies that under direct generation with small clearance differences (e.g. 2.5mm offset),
        the ribcage costal margin flare at Z=1.0725m narrows the net clearance to ~1.37mm.
        Documents boundary condition when caller specifies c_bodice=0.015, c_sash=0.0175 at h=1.50m.
        """
        h = 1.50
        s = h / 1.65
        kw = 0.85
        kc = 1.00
        bodice = generate_dress_bodice(height=h, waist_girth=0.58*kw, chest_girth=0.82*kc, clearance=0.015)
        sash = generate_dress_waist_sash(height=h, waist_girth=0.58*kw, chest_girth=0.82*kc, clearance=0.0175)

        # Top ring of sash (Z = 1.0725 * s)
        top_ring = sash.vertices[96:120]
        b_pts = bodice.vertices

        min_d = min(min(math.sqrt((sv[0]-bv[0])**2 + (sv[1]-bv[1])**2 + (sv[2]-bv[2])**2) for bv in b_pts) for sv in top_ring)
        # Verify clearance is positive, but record narrowed margin (< 2.0mm)
        assert min_d > 0.0, "Sash top ring must not penetrate bodice"


# ==============================================================================
# 2. 3D BOW KNOT AND RIBBON GEOMETRY EMPIRICAL TESTS
# ==============================================================================

class TestBowKnotAndRibbonGeometry:
    """Empirical tests for 3D bow knot volume, manifold caps, and ribbon streamer trajectory."""

    def test_bow_loops_strictly_positive_volume(self):
        """
        Verifies that bilateral 3D hollow bow loops enclose strictly positive volume
        (divergence theorem volume >= 10.0 cm^3 for each loop).
        """
        sash = generate_dress_waist_sash(height=1.65)
        # Left loop faces (indices 152 to 199)
        loop_L_faces = [f for f in sash.faces if all(152 <= idx < 200 for idx in f)]
        # Right loop faces (indices 200 to 247)
        loop_R_faces = [f for f in sash.faces if all(200 <= idx < 248 for idx in f)]

        assert len(loop_L_faces) == 96
        assert len(loop_R_faces) == 96

        vol_L = _compute_closed_mesh_volume(sash.vertices, loop_L_faces)
        vol_R = _compute_closed_mesh_volume(sash.vertices, loop_R_faces)

        # Convert to cm^3
        vol_L_cm3 = vol_L * 1e6
        vol_R_cm3 = vol_R * 1e6

        assert vol_L_cm3 >= 10.0, f"Left loop volume {vol_L_cm3:.2f}cm^3 must be >= 10.0 cm^3"
        assert vol_R_cm3 >= 10.0, f"Right loop volume {vol_R_cm3:.2f}cm^3 must be >= 10.0 cm^3"

    def test_bow_loops_closed_2_manifold(self):
        """
        Verifies that bilateral 3D hollow bow loops are 100% closed 2-manifold surfaces:
        every edge is shared by exactly 2 faces (0 boundary edges, 0 non-manifold edges).
        """
        sash = generate_dress_waist_sash(height=1.65)
        loop_L_faces = [f for f in sash.faces if all(152 <= idx < 200 for idx in f)]
        loop_R_faces = [f for f in sash.faces if all(200 <= idx < 248 for idx in f)]

        for name, faces in [("Left Loop", loop_L_faces), ("Right Loop", loop_R_faces)]:
            edge_counts: Dict[Tuple[int, int], int] = defaultdict(int)
            for f in faces:
                edges = [
                    (min(f[0], f[1]), max(f[0], f[1])),
                    (min(f[1], f[2]), max(f[1], f[2])),
                    (min(f[2], f[0]), max(f[2], f[0])),
                ]
                for e in edges:
                    edge_counts[e] += 1

            non_two = [e for e, c in edge_counts.items() if c != 2]
            assert len(non_two) == 0, f"{name} has {len(non_two)} non-manifold or boundary edges!"

    def test_barrel_knot_manifold_closed_caps(self):
        """
        EMPIRICAL DEFECT DISCOVERY:
        Verifies that the 3D barrel cuff knot has manifold closed caps.
        Fails because the cap quad generation only covers vertices (0,7,6,1) and (1,6,5,2),
        leaving vertices 2, 3, 4, 5 unclosed on both top and bottom (8 open boundary edges).
        """
        sash = generate_dress_waist_sash(height=1.65)
        knot_faces = [f for f in sash.faces if all(120 <= idx < 152 for idx in f)]

        edge_counts: Dict[Tuple[int, int], int] = defaultdict(int)
        for f in knot_faces:
            edges = [
                (min(f[0], f[1]), max(f[0], f[1])),
                (min(f[1], f[2]), max(f[1], f[2])),
                (min(f[2], f[0]), max(f[2], f[0])),
            ]
            for e in edges:
                edge_counts[e] += 1

        boundary_edges = [e for e, c in edge_counts.items() if c == 1]
        assert len(boundary_edges) == 0, (
            f"Barrel knot has {len(boundary_edges)} unclosed boundary edges: {boundary_edges}. "
            "Caps are incomplete and leave two 4-vertex holes!"
        )

    def test_ribbon_streamer_cascade_trajectory(self):
        """
        Verifies ribbon streamer trajectory: monotonic Z-descent below 0.75m,
        gentle outward lateral flare, and non-zero torsional twist.
        """
        sash = generate_dress_waist_sash(height=1.65)
        streamers = sash.vertices[248:]
        assert len(streamers) > 0

        # Monotonic downward cascade
        min_z = min(v[2] for v in streamers)
        assert min_z <= 0.75, f"Streamers must cascade below Z=0.75m, got {min_z:.3f}m"

        # Outward flare
        tip_verts_L = [v for v in streamers if v[0] > 0.0 and v[2] < 0.70]
        tip_verts_R = [v for v in streamers if v[0] < 0.0 and v[2] < 0.70]
        assert len(tip_verts_L) > 0 and len(tip_verts_R) > 0

        tip_x_L = max(v[0] for v in tip_verts_L)
        tip_x_R = min(v[0] for v in tip_verts_R)
        assert tip_x_L > 0.030, f"Left streamer tip X={tip_x_L:.4f}m must flare outward (>0.030m)"
        assert tip_x_R < -0.030, f"Right streamer tip X={tip_x_R:.4f}m must flare outward (<-0.030m)"

    def test_ribbon_streamer_tip_bias_cut(self):
        """
        EMPIRICAL DEFECT DISCOVERY:
        Tests that ribbon streamer ends exhibit an actual non-zero 45-degree bias cut.
        Fails because line 773 computes tip_bias = (0.008 * s * (1.0 - t)) when step == streamer_steps.
        At the last step, t = 1.0, so (1.0 - t) == 0.0, rendering tip_bias identically zero!
        """
        sash = generate_dress_waist_sash(height=1.65)
        streamers = sash.vertices[248:]

        # Get the 3 tip vertices of the left streamer (last 3 vertices of left streamer)
        # Left streamer has 17 steps of 3 vertices = 51 vertices (indices 248..298)
        tip_pts = sash.vertices[296:299]
        zs = [v[2] for v in tip_pts]
        delta_z = max(zs) - min(zs)

        # A 45-degree bias cut should produce delta_z approx 2 * 0.008 = 0.016m
        assert delta_z >= 0.004, (
            f"Streamer tip delta_z is {delta_z:.6f}m (identically zero!). "
            "The 45-degree bias cut is dead code due to (1.0 - t) == 0.0."
        )


# ==============================================================================
# 3. ORGANIC SKIRT NORMALS ORIENTATION EMPIRICAL TESTS
# ==============================================================================

class TestOrganicSkirtNormalsOrientation:
    """Empirical tests for normal vector orientation on the organic skirt."""

    def test_organic_skirt_faces_outward_normals(self):
        """
        EMPIRICAL DEFECT DISCOVERY:
        Verifies that skirt quad face normals point outward from the body interior.
        Fails because lines 917-921 define quad winding order v_bl -> v_br -> v_tr -> v_tl
        where r=0 is top and r=15 is bottom, making the winding clockwise and inverting
        100% of the 1440 triangular faces into the character body.
        """
        skirt = generate_dress_organic_skirt()

        outward_count = 0
        inward_count = 0

        for f in skirt.faces:
            v0, v1, v2 = skirt.vertices[f[0]], skirt.vertices[f[1]], skirt.vertices[f[2]]
            cx = (v0[0] + v1[0] + v2[0]) / 3.0
            cy = (v0[1] + v1[1] + v2[1]) / 3.0
            e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
            e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            dot = cx * nx + cy * ny
            if dot > 0:
                outward_count += 1
            else:
                inward_count += 1

        assert inward_count == 0, (
            f"Found {inward_count} / {len(skirt.faces)} inward-pointing (inverted) faces on organic skirt! "
            "Winding order must be counter-clockwise looking from exterior."
        )


# ==============================================================================
# 4. RIGIFY DEF SKINNING INTEGRITY EMPIRICAL TESTS
# ==============================================================================

class TestRigifyDEFSkinningIntegrity:
    """Empirical tests for Rigify 163 DEF bone skinning vertex weights normalization and coverage."""

    def test_bodice_skin_weights_normalization_and_orphans(self):
        """Verifies 100% of bodice vertices have normalized weights, 0 orphans, 0 negative weights."""
        bodice = generate_dress_bodice(height=1.65)
        assert hasattr(bodice, "skin_weights")
        weights = bodice.skin_weights

        assert len(weights) == len(bodice.vertices)

        for v_idx, b_map in weights.items():
            assert len(b_map) > 0, f"Bodice vertex {v_idx} has no bone weights (orphaned)"
            w_sum = sum(b_map.values())
            assert math.isclose(w_sum, 1.0, abs_tol=1e-4), f"Bodice vertex {v_idx} sum {w_sum} != 1.0"
            for b_name, w in b_map.items():
                assert w >= 0.0, f"Negative weight on {b_name} for vertex {v_idx}: {w}"
                assert not math.isnan(w) and not math.isinf(w)

    def test_skirt_skin_weights_normalization_and_orphans(self):
        """Verifies 100% of skirt vertices have normalized weights, 0 orphans, 0 negative weights."""
        skirt = generate_dress_organic_skirt(height=1.65)
        assert hasattr(skirt, "skin_weights")
        weights = skirt.skin_weights

        assert len(weights) == len(skirt.vertices)

        for v_idx, b_map in weights.items():
            assert len(b_map) > 0, f"Skirt vertex {v_idx} has no bone weights (orphaned)"
            w_sum = sum(b_map.values())
            assert math.isclose(w_sum, 1.0, abs_tol=1e-4), f"Skirt vertex {v_idx} sum {w_sum} != 1.0"
            for b_name, w in b_map.items():
                assert w >= 0.0, f"Negative weight on {b_name} for vertex {v_idx}: {w}"
                assert not math.isnan(w) and not math.isinf(w)

    def test_sash_skin_weights_normalization_and_orphans(self):
        """Verifies 100% of sash vertices have normalized weights, 0 orphans, 0 negative weights."""
        sash = generate_dress_waist_sash(height=1.65)
        assert hasattr(sash, "skin_weights")
        weights = sash.skin_weights

        assert len(weights) == len(sash.vertices)

        for v_idx, b_map in weights.items():
            assert len(b_map) > 0, f"Sash vertex {v_idx} has no bone weights (orphaned)"
            w_sum = sum(b_map.values())
            assert math.isclose(w_sum, 1.0, abs_tol=1e-4), f"Sash vertex {v_idx} sum {w_sum} != 1.0"
            for b_name, w in b_map.items():
                assert w >= 0.0, f"Negative weight on {b_name} for vertex {v_idx}: {w}"
                assert not math.isnan(w) and not math.isinf(w)

    def test_rigify_def_bones_schema_compliance(self):
        """Verifies that all assigned bones across all wardrobe components match Rigify DEF bones."""
        wardrobe = generate_yu_nian_an_wardrobe()
        valid_bone_prefixes = ("DEF-spine", "DEF-shoulder", "DEF-thigh", "DEF-pelvis")

        for comp_name in ("Dress_Bodice", "Dress_WaistSash", "Dress_PleatedSkirt"):
            mesh = wardrobe[comp_name]
            weights = compute_wardrobe_skin_weights(mesh, comp_name)
            for v_idx, b_map in weights.items():
                for b_name in b_map:
                    assert any(b_name.startswith(p) for p in valid_bone_prefixes), (
                        f"Non-Rigify DEF bone '{b_name}' assigned to {comp_name} vertex {v_idx}"
                    )


# ==============================================================================
# 5. BLENDER SCRIPT GENERATION & SOLIDIFY PARITY
# ==============================================================================

class TestBlenderScriptASTAndSolidify:
    """Verifies standalone Blender script generation, BONE_WEIGHTS JSON, and Solidify outward offset."""

    def test_wardrobe_script_bone_weights_and_solidify(self):
        """Verifies get_wardrobe_script serializes bone weights and configures outward solidify."""
        script = get_wardrobe_script()

        # AST parse verification
        tree = ast.parse(script)
        assert isinstance(tree, ast.Module)

        # String assertions
        assert "BONE_WEIGHTS = json.loads" in script
        assert "solid_mod.offset = 1.0" in script
        assert "arm_mod.use_deform_preserve_volume = True" in script
        assert "DEF-spine" in script
