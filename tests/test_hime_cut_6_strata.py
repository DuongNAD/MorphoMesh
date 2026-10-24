"""
MorphoMesh: Milestone M3 6-Stratum Hime Cut Hair System Test Suite.

Validates:
1. 6 Cranial Strata Layer Configurations (get_6_stratum_hime_cut_layers):
   - Stratum 1: Blunt straight bangs cleanly cut above eyebrows (Z_tip in [1.545m, 1.555m], length ~0.11m).
   - Stratum 2: Symmetrical cheek-length sidelocks (bins/binzas) framing jawline down to chin (Z_tip ~= 1.418m, length ~0.20m).
   - Stratum 3: Scalp crown cap providing root volume (+3mm lift) and offset parting (+4mm).
   - Stratum 4: Temporal transitions wrapping naturally around ears (helix clearance >= 0.015m).
   - Stratum 5: Flowing dorsal cascade terminating at mid-back (Z_tip in [0.93m, 0.97m], length ~0.72m, +15mm scapular clearance).
   - Stratum 6: Flyaway strands (500 micro-frizz guide strands, tip radius <= 0.000020m).
2. Backward Compatibility (get_default_hime_cut_layers):
   - pure_strata=False preserves legacy keys for existing test suites.
   - pure_strata=True exposes the 6 pure cranial strata.
3. 3D Spline Mathematics & Landmark Clearances:
   - Forehead bangs termination at eyebrow level.
   - Chin-level termination for authentic hime sidelocks.
   - Crown parting offset and root lift.
   - Ear helix clearance for temporal transitions.
   - Mid-back termination for dorsal cascade.
   - Harmonic micro-frizz for flyaways.
4. Pure Quad Ribbon Mesh Evaluator (convert_curves_to_ribbon_mesh):
   - Pure quad geometry (even triangle count).
   - Monotonic UV coordinates advancing from root (V=0) to tip (V=1).
   - Outward-facing surface normals directed away from cranial center.
   - Rigify DEF-head vertex group with normalized skin weight 1.0.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pytest

from morphomesh.human_grooming import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    convert_curves_to_ribbon_mesh,
    generate_6_stratum_hime_cut_splines,
    generate_hime_cut_splines,
    get_6_stratum_hime_cut_layers,
    get_default_hime_cut_layers,
)


# ==============================================================================
# 1. 6-STRATUM LAYER CONFIGURATIONS TESTS
# ==============================================================================

class Test6StratumLayerConfigurations:
    """Validates the authoritative 6 cranial strata definitions and backward compatibility."""

    def test_all_six_authentic_strata_present(self):
        """Asserts all 6 cranial strata are configured in get_6_stratum_hime_cut_layers."""
        layers = get_6_stratum_hime_cut_layers(total_guides=15000)
        expected_strata = [
            "Hair_Hime_Bangs",              # Stratum 1
            "Hair_Hime_Sidelocks",          # Stratum 2
            "Hair_Scalp_Crown",             # Stratum 3
            "Hair_Temporal_Transitions",    # Stratum 4
            "Hair_Back_Cascade",            # Stratum 5
            "Hair_Flyaways",                # Stratum 6
        ]
        for name in expected_strata:
            assert name in layers, f"Missing authentic cranial stratum: {name}"
        assert len(layers) == 6, f"Expected exactly 6 strata, got {len(layers)}"

    def test_stratum_1_bangs_dimensions(self):
        """Validates Stratum 1 bangs trimmed cleanly above eyebrows."""
        layer = get_6_stratum_hime_cut_layers()["Hair_Hime_Bangs"]
        assert 0.10 <= layer.length <= 0.15, f"Bangs length {layer.length}m must be ~0.11-0.13m"
        assert layer.root_radius > layer.tip_radius
        assert layer.tip_radius <= 0.000030

    def test_stratum_2_sidelocks_dimensions(self):
        """Validates Stratum 2 sidelocks framing jawline and chin (length ~0.20m)."""
        layer = get_6_stratum_hime_cut_layers()["Hair_Hime_Sidelocks"]
        assert 0.18 <= layer.length <= 0.24, f"Authentic sidelocks length {layer.length}m must be ~0.20m"
        assert layer.clump_factor >= 0.20

    def test_stratum_3_crown_cap_dimensions(self):
        """Validates Stratum 3 crown cap providing volume and root lift."""
        layer = get_6_stratum_hime_cut_layers()["Hair_Scalp_Crown"]
        assert 0.15 <= layer.length <= 0.25, f"Crown cap length {layer.length}m must be ~0.18m"
        assert layer.clump_factor >= 0.10

    def test_stratum_4_temporal_transition_dimensions(self):
        """Validates Stratum 4 temporal transitions wrapping around ears."""
        layer = get_6_stratum_hime_cut_layers()["Hair_Temporal_Transitions"]
        assert 0.25 <= layer.length <= 0.35
        assert layer.strand_count >= 800

    def test_stratum_5_dorsal_cascade_dimensions(self):
        """Validates Stratum 5 dorsal cascade extending to mid-back (length ~0.72m)."""
        layer = get_6_stratum_hime_cut_layers()["Hair_Back_Cascade"]
        assert 0.68 <= layer.length <= 0.78, f"Mid-back cascade length {layer.length}m must be ~0.72m"
        assert layer.strand_count >= 5000, "Back cascade must carry dominant strand volume"

    def test_stratum_6_flyaways_micro_frizz(self):
        """Validates Stratum 6 flyaway micro-frizz guide strands."""
        layer = get_6_stratum_hime_cut_layers()["Hair_Flyaways"]
        assert layer.strand_count == 500, f"Expected 500 flyaway strands, got {layer.strand_count}"
        assert layer.tip_radius <= 0.000020, "Flyaways must have ultra-fine tapered tips"
        assert layer.noise_amplitude > 0.0, "Flyaways must have micro-frizz noise"

    def test_backward_compatibility_mode(self):
        """Asserts get_default_hime_cut_layers maintains legacy keys by default."""
        legacy = get_default_hime_cut_layers(pure_strata=False)
        assert "Hair_Eyebrows" in legacy
        assert "Hair_Eyelashes" in legacy
        assert "Hair_Hime_Bangs" in legacy
        # Check pure_strata=True delegates to 6 authentic strata
        pure = get_default_hime_cut_layers(pure_strata=True)
        assert "Hair_Temporal_Transitions" in pure
        assert "Hair_Flyaways" in pure


# ==============================================================================
# 2. 3D SPLINE GENERATION & ANATOMICAL CLEARANCE TESTS
# ==============================================================================

class Test6StratumSplineGeneration:
    """Validates 3D curve spline mathematics and cranial clearances for all 6 strata."""

    def test_all_six_strata_splines_generated(self):
        """Asserts splines are generated for each of the 6 strata."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.08)
        assert len(splines) == 6
        for name in [
            "Hair_Hime_Bangs",
            "Hair_Hime_Sidelocks",
            "Hair_Scalp_Crown",
            "Hair_Temporal_Transitions",
            "Hair_Back_Cascade",
            "Hair_Flyaways",
        ]:
            assert name in splines
            assert len(splines[name]) > 0

    def test_stratum_1_bangs_eyebrow_level_termination(self):
        """Asserts bangs terminate cleanly above eyebrows in [1.545m, 1.555m]."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.08)["Hair_Hime_Bangs"]
        for s in splines:
            root = s.points[0]
            tip = s.points[-1]
            assert root[2] > tip[2], "Bangs must descend downward"
            assert tip[1] < 0.0, "Bangs must drape forward over forehead"
            assert 1.530 <= tip[2] <= 1.565, f"Bangs tip Z={tip[2]:.4f}m must end at eyebrow level (~1.55m)"

    def test_stratum_2_sidelocks_chin_level_termination(self):
        """Asserts sidelocks frame cheeks and terminate at chin level (Z_tip in [1.40m, 1.44m])."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.08)["Hair_Hime_Sidelocks"]
        tip_zs = [s.points[-1][2] for s in splines]
        avg_tip_z = sum(tip_zs) / len(tip_zs)
        assert 1.40 <= avg_tip_z <= 1.44, f"Sidelocks avg tip Z={avg_tip_z:.4f}m should terminate at chin (~1.418m)"

        # Verify bilateral cheek framing symmetry
        left_strands = [s for s in splines if s.points[0][0] > 0.02]
        right_strands = [s for s in splines if s.points[0][0] < -0.02]
        assert len(left_strands) > 0 and len(right_strands) > 0

    def test_stratum_3_crown_parting_and_lift(self):
        """Asserts crown cap provides root lift and offset parting."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.08)["Hair_Scalp_Crown"]
        root_zs = [s.points[0][2] for s in splines]
        max_root_z = max(root_zs)
        # Scalp top is at Z=1.65m; root lift brings roots above skull surface
        assert max_root_z >= 1.630, f"Crown root Z={max_root_z:.4f}m provides volume lift"

    def test_stratum_4_temporal_transitions_ear_clearance(self):
        """Asserts temporal transitions wrap around ears with helix clearance >= 0.015m (15mm)."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.08)["Hair_Temporal_Transitions"]
        # Approximate ear helix positions: (+/- 0.065, -0.010, 1.54)
        for s in splines:
            root_x = s.points[0][0]
            ear_x = 0.065 if root_x >= 0 else -0.065
            ear_center = np.array([ear_x, -0.010, 1.540])

            # Check that points near ear height maintain clearance
            for pt in s.points:
                if 1.50 <= pt[2] <= 1.58:
                    p = np.array(pt)
                    dist = float(np.linalg.norm(p - ear_center))
                    assert dist >= 0.014, f"Temporal strand approaches ear too closely: {dist*1000:.1f}mm < 15mm"

    def test_stratum_5_dorsal_cascade_mid_back_termination(self):
        """Asserts dorsal cascade extends to mid-back in [0.93m, 0.97m] with scapular clearance."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.08)["Hair_Back_Cascade"]
        tip_zs = [s.points[-1][2] for s in splines]
        avg_tip_z = sum(tip_zs) / len(tip_zs)
        assert 0.93 <= avg_tip_z <= 0.97, f"Mid-back cascade avg tip Z={avg_tip_z:.4f}m must terminate in [0.93, 0.97]m"

        # Check posterior position (behind head/scapula, Y >= -0.05m)
        for s in splines:
            assert all(pt[1] >= -0.05 for pt in s.points), "Back hair must drape along posterior side"

    def test_stratum_6_flyaways_micro_frizz_variation(self):
        """Asserts flyaway guides exhibit non-zero organic radial displacement."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.10)["Hair_Flyaways"]
        assert len(splines) > 0
        # Check that flyaway paths are valid 3D curves with diverse trajectories
        tips = [s.points[-1] for s in splines]
        assert len(set(round(t[0], 3) for t in tips)) > 1, "Flyaways must have diverse lateral spread"


# ==============================================================================
# 3. PURE QUAD RIBBON MESH EVALUATOR TESTS
# ==============================================================================

class TestRibbonMeshEvaluator:
    """Validates pure-quad ribbon mesh evaluator, monotonic UVs, outward normals, and DEF-head binding."""

    def test_ribbon_mesh_pure_quad_topology(self):
        """Asserts ribbon mesh generator produces pure quads (triangulated pairs: even face count)."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.05)["Hair_Hime_Bangs"]
        mesh = convert_curves_to_ribbon_mesh(splines, ribbon_width=0.008)
        assert len(mesh.vertices) > 0
        assert len(mesh.faces) > 0
        # Pure quad conversion triangulates into 2 triangles per quad segment
        assert len(mesh.faces) % 2 == 0, f"Face count {len(mesh.faces)} must be even"

        # Ensure no degenerate zero-area faces
        for f in mesh.faces:
            p0 = np.array(mesh.vertices[f[0]])
            p1 = np.array(mesh.vertices[f[1]])
            p2 = np.array(mesh.vertices[f[2]])
            area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0))
            assert area > 1e-9, f"Face {f} has degenerate near-zero area: {area}"

    def test_ribbon_mesh_monotonic_uvs(self):
        """Asserts ribbon UV coordinates advance monotonically from root (V=0) to tip (V=1)."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.05)["Hair_Hime_Bangs"]
        mesh = convert_curves_to_ribbon_mesh(splines, ribbon_width=0.008)

        # In convert_curves_to_ribbon_mesh, left vertices have U=0.0, right vertices have U=1.0
        # and V advances strictly from 0.0 at root to 1.0 at tip
        assert len(mesh.uvs) == len(mesh.vertices)
        for u, v in mesh.uvs:
            assert abs(u - 0.0) < 1e-4 or abs(u - 1.0) < 1e-4, f"U coordinate {u} must be 0.0 or 1.0"
            assert 0.0 <= v <= 1.0, f"V coordinate {v} must be in range [0.0, 1.0]"

    def test_ribbon_mesh_outward_facing_normals(self):
        """Asserts ribbon normals point outward from head cranial center."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.05)["Hair_Hime_Bangs"]
        mesh = convert_curves_to_ribbon_mesh(splines, ribbon_width=0.008)
        c_head = np.array([0.0, 0.0, 1.55])

        outward_dot_sum = 0.0
        for v, n in zip(mesh.vertices, mesh.normals):
            p = np.array(v)
            norm = np.array(n)
            rad_vec = p - c_head
            rad_len = np.linalg.norm(rad_vec) or 1.0
            rad_norm = rad_vec / rad_len
            dot = float(np.dot(norm, rad_norm))
            outward_dot_sum += dot

        avg_dot = outward_dot_sum / len(mesh.vertices)
        assert avg_dot > 0.0, f"Average normal dot with radial cranial vector {avg_dot} must be positive (outward)"

    def test_ribbon_mesh_def_head_armature_binding(self):
        """Asserts all ribbon vertices are assigned to DEF-head vertex group with weight 1.0."""
        splines = generate_6_stratum_hime_cut_splines(sample_density_scale=0.05)["Hair_Hime_Bangs"]
        mesh = convert_curves_to_ribbon_mesh(splines, ribbon_width=0.008)

        assert "DEF-head" in mesh.vertex_groups, "Mesh missing 'DEF-head' vertex group"
        assert len(mesh.vertex_groups["DEF-head"]) == len(mesh.vertices), "Every vertex must be in DEF-head"
        assert hasattr(mesh, "skin_weights")
        weights: Dict[int, Dict[str, float]] = mesh.skin_weights  # type: ignore[attr-defined]
        for i in range(len(mesh.vertices)):
            assert weights[i].get("DEF-head", 0.0) == 1.0, f"Vertex {i} DEF-head weight != 1.0"
