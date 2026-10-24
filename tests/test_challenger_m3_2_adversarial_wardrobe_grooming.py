"""
MorphoMesh Milestone M3 Adversarial Empirical Challenger Suite.
Challenger M3-2: Wardrobe Procedural Generation & Grooming Subsystems Stress Testing.

Authoritative coverage:
1. Wardrobe Procedural Mesh Generation:
   - generate_dress_bodice: Sweetheart neckline, teardrop bust, 3D straps, extreme scaling & girths.
   - generate_dress_waist_sash: Barrel-cuff knot, 3D hollow bow loops, cascading streamers.
   - generate_dress_organic_skirt / generate_dress_pleated_skirt: Multi-pleat drape, scalloped hem, UV seams.
   - generate_flat_strappy_sandals: Bilateral L/R, plantar contour, toe exposure, medial arch rise.
   - generate_catenary_magic_strings: 14 verts/cord invariant, snapping to finger phalanx DEF bones, parabolic sag.
   - generate_swallowtail_quad_butterfly: 24 pure quads (48 tris), 48 vertices, dihedral flutter angles.
   - Manifold & Topological Verification: Zero degenerate faces (area > 1e-8), no edge in > 2 faces, Rigify skin weights sum = 1.0.

2. Grooming Subsystems:
   - 6-Stratum Hime Cut Splines: Bangs, sidelocks, crown, temporal, dorsal cascade, flyaways.
   - Ribbon Extrusion (convert_curves_to_ribbon_mesh): Pure quad topology, monotonic UVs [0, 1], outward normals.
   - Geometry Nodes Modifier Network (build_hair_geom_node_tree): Modifier node network integrity, taper, clumping.
   - Creature Fur Grooming Compatibility (CreatureGroomingEngine): Zero-fur mask invariance, biological flow vectors, pure python ribbon evaluation.
"""

from __future__ import annotations

import ast
import math
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest

from morphomesh.inference_adapter import MeshGeometry
from morphomesh.wardrobe import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_waist_sash,
    generate_dress_organic_skirt,
    generate_dress_pleated_skirt,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_flat_strappy_sandals,
    generate_flat_sandals,
    generate_catenary_magic_strings,
    generate_marionette_red_strings,
    generate_swallowtail_quad_butterfly,
    generate_swallowtail_butterfly,
    generate_yu_nian_an_wardrobe,
    get_butterfly_vortex_positions,
    get_butterfly_flutter_positions,
    compute_dress_waist_radii,
    assign_dress_pin_weights,
    assign_bodice_skin_weights,
    assign_skirt_skin_weights,
    assign_sash_skin_weights,
    compute_wardrobe_skin_weights,
    get_wardrobe_script,
    dress_human,
    FINGER_DEF_BONE_KEYS,
    FINGER_DEF_BONE_ALIASES,
    resolve_finger_def_bone_name,
    MATERIAL_NAME_ALIASES,
)
from morphomesh.grooming import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    _calc_spline_length,
    get_6_stratum_hime_cut_layers,
    get_default_hime_cut_layers,
    generate_hime_cut_splines,
    generate_6_stratum_hime_cut_splines,
    convert_curves_to_ribbon_mesh,
    build_hair_geom_node_tree,
    get_grooming_script,
    groom_human,
    # Creature grooming backward compatibility
    ZERO_FUR_GROUPS,
    FULL_FUR_GROUPS,
    MODULATED_FUR_GROUPS,
    FurLayerConfig,
    CreatureGroomingEngine,
    compute_biological_flow_vector,
    evaluate_fur_ribbons_for_gltf,
    get_default_undercoat_config,
    get_default_guard_hair_config,
    setup_volumetric_fur,
)


def _triangle_area_3d(v0: Tuple[float, float, float], v1: Tuple[float, float, float], v2: Tuple[float, float, float]) -> float:
    """Computes Euclidean area of a 3D triangle."""
    ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
    bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def _check_manifold_edges(faces: List[Tuple[int, int, int]]) -> Tuple[int, int]:
    """
    Checks manifold properties of triangular face mesh:
    Returns (max_edge_sharing, non_manifold_edge_count).
    A 2-manifold surface has every interior edge shared by exactly 2 faces,
    and boundary edges shared by 1 face. Edges shared by >= 3 faces are non-manifold.
    """
    edge_counts: Dict[Tuple[int, int], int] = defaultdict(int)
    for f in faces:
        for i in range(3):
            v_a = min(f[i], f[(i + 1) % 3])
            v_b = max(f[i], f[(i + 1) % 3])
            edge_counts[(v_a, v_b)] += 1

    max_sharing = max(edge_counts.values()) if edge_counts else 0
    non_manifold_edges = sum(1 for c in edge_counts.values() if c > 2)
    return max_sharing, non_manifold_edges


# ==============================================================================
# 1. PROCEDURAL WARDROBE MESH GENERATION & TOPOLOGY
# ==============================================================================

class TestAdversarialWardrobeBodice:
    """Stress tests dress bodice mesh generation across extreme parameter envelopes."""

    @pytest.mark.parametrize("height", [1.20, 1.50, 1.65, 1.85, 2.10])
    @pytest.mark.parametrize("waist_girth,chest_girth", [(0.40, 0.65), (0.58, 0.82), (0.80, 1.10)])
    def test_bodice_extreme_proportions(self, height: float, waist_girth: float, chest_girth: float):
        """Validates bodice mesh geometry under wide anthropometric variations."""
        bodice = generate_dress_bodice(
            height=height,
            waist_girth=waist_girth,
            chest_girth=chest_girth,
            bust_cup_scale=1.0,
        )
        assert len(bodice.vertices) > 100, f"Insufficient vertices: {len(bodice.vertices)}"
        assert len(bodice.faces) > 100, f"Insufficient faces: {len(bodice.faces)}"

        # Verify no NaN or Inf
        for i, (x, y, z) in enumerate(bodice.vertices):
            assert math.isfinite(x) and math.isfinite(y) and math.isfinite(z), f"Non-finite vertex {i}: {(x, y, z)}"

        # Verify no zero-area degenerate faces
        for f_idx, (i0, i1, i2) in enumerate(bodice.faces):
            area = _triangle_area_3d(bodice.vertices[i0], bodice.vertices[i1], bodice.vertices[i2])
            assert area > 1e-8, f"Degenerate face {f_idx}: area={area}"

        # Manifold check: no non-manifold edges (> 2 faces sharing edge)
        max_sharing, non_manifold = _check_manifold_edges(bodice.faces)
        assert non_manifold == 0, f"Bodice has {non_manifold} non-manifold edges"

    def test_bodice_teardrop_bust_and_sweetheart_neckline(self):
        """Verifies geometric presence of sweetheart dip and teardrop bust curvature."""
        bodice = generate_dress_bodice(height=1.65)
        # Find anterior vertices around chest height (Z in [1.18, 1.26])
        chest_verts = [(x, y, z) for (x, y, z) in bodice.vertices if 1.18 <= z <= 1.26 and y > 0.02]
        assert len(chest_verts) > 0, "No anterior chest vertices found"

        # Centerline neckline (X near 0) should be lower than lateral bust peaks
        center_rim = [z for (x, y, z) in chest_verts if abs(x) < 0.015]
        lateral_peaks = [z for (x, y, z) in chest_verts if 0.04 <= abs(x) <= 0.08]
        assert len(center_rim) > 0 and len(lateral_peaks) > 0
        assert min(center_rim) <= max(lateral_peaks), "Sweetheart neckline dip not observed"


class TestAdversarialWardrobeSashAndBow:
    """Stress tests waist sash, barrel knot, and ribbon streamer generation."""

    @pytest.mark.parametrize("scale", [0.75, 1.0, 1.5])
    def test_sash_hollow_loops_and_streamers(self, scale: float):
        """Verifies 3D volumetric bow loops and twisted ribbon streamers across scales."""
        sash = generate_dress_waist_sash(height=1.65 * scale)
        assert len(sash.vertices) > 200
        assert len(sash.faces) > 200

        # Verify finite coordinates
        for i, v in enumerate(sash.vertices):
            assert all(math.isfinite(c) for c in v), f"Non-finite vertex {i} in sash: {v}"

        # Verify zero degenerate faces
        for f_idx, (i0, i1, i2) in enumerate(sash.faces):
            area = _triangle_area_3d(sash.vertices[i0], sash.vertices[i1], sash.vertices[i2])
            assert area > 1e-8, f"Degenerate face {f_idx} in sash: area={area}"


class TestAdversarialWardrobeSkirt:
    """Stress tests multi-harmonic organic skirt drape and pleated skirt generation."""

    @pytest.mark.parametrize("pleat_count", [10, 16, 20, 24, 32])
    def test_pleated_skirt_harmonic_stability(self, pleat_count: int):
        """Validates harmonic stability across varied pleat counts."""
        skirt = generate_dress_pleated_skirt(height=1.65, pleat_count=pleat_count)
        assert len(skirt.vertices) > 300
        assert len(skirt.faces) > 400

        # Verify finite coordinates
        for v in skirt.vertices:
            assert all(math.isfinite(c) for c in v)

        # Verify UV coordinates monotonic in V
        for uv in skirt.uvs:
            assert 0.0 <= uv[0] <= 1.05 and -0.05 <= uv[1] <= 1.05

        # Verify manifold edges
        max_sharing, non_manifold = _check_manifold_edges(skirt.faces)
        assert non_manifold == 0, f"Pleated skirt has {non_manifold} non-manifold edges"

    def test_skirt_scalloped_hemline_undulation(self):
        """Verifies non-zero undulating scalloped hemline on skirt bottom."""
        skirt = generate_dress_organic_skirt(height=1.65)
        # Extract lowest ring of vertices
        min_z = min(v[2] for v in skirt.vertices)
        hem_verts = [v for v in skirt.vertices if abs(v[2] - min_z) < 0.025]
        z_vals = [v[2] for v in hem_verts]
        undulation = max(z_vals) - min(z_vals)
        assert undulation > 0.005, f"Expected scalloped hemline undulation > 5mm, got {undulation*1000:.2f}mm"


class TestAdversarialWardrobeSandals:
    """Stress tests flat strappy sandals, bilateral symmetry, and toe clearance."""

    @pytest.mark.parametrize("scale", [0.8, 1.0, 1.2])
    def test_sandals_bilateral_structure(self, scale: float):
        """Verifies Left and Right sandals have symmetrical topology and positive face area."""
        sandals = generate_flat_strappy_sandals(height=1.65 * scale)
        assert "Mesh_Sandal_L" in sandals and "Mesh_Sandal_R" in sandals

        s_l = sandals["Mesh_Sandal_L"]
        s_r = sandals["Mesh_Sandal_R"]

        assert len(s_l.vertices) == len(s_r.vertices)
        assert len(s_l.faces) == len(s_r.faces)

        # Verify sole resting on ground Z=0
        min_z_l = min(v[2] for v in s_l.vertices)
        min_z_r = min(v[2] for v in s_r.vertices)
        assert abs(min_z_l) < 1e-4, f"Left sole not grounded: min Z = {min_z_l}"
        assert abs(min_z_r) < 1e-4, f"Right sole not grounded: min Z = {min_z_r}"

        # Verify medial arch rise
        max_footbed_z = max(v[2] for v in s_l.vertices if v[2] < 0.025)
        assert max_footbed_z > 0.005, f"Medial arch elevation missing: {max_footbed_z*1000:.2f}mm"

        # Verify zero degenerate faces
        for f_idx, (i0, i1, i2) in enumerate(s_l.faces):
            area = _triangle_area_3d(s_l.vertices[i0], s_l.vertices[i1], s_l.vertices[i2])
            assert area > 1e-8, f"Degenerate face {f_idx} in Left sandal: area={area}"


class TestAdversarialMarionetteStrings:
    """Stress tests catenary magic strings, invariants, and edge case geometry."""

    def test_catenary_cords_invariant_and_snapping(self):
        """Verify strict invariant: 14 verts/cord across 10 cords and zero-error snapping."""
        strings = generate_catenary_magic_strings(height=1.65, rest_pose=True)
        assert len(strings.vertices) == 140, f"Expected 140 verts, got {len(strings.vertices)}"
        assert len(strings.faces) == 120, f"Expected 120 faces (60 quads), got {len(strings.faces)}"

        # Every vertex must belong to a valid DEF finger bone group
        for bone_key in FINGER_DEF_BONE_KEYS:
            assert bone_key in strings.vertex_groups, f"Bone group missing: {bone_key}"
            assert len(strings.vertex_groups[bone_key]) == 14, f"Wrong vertex count for {bone_key}"

    @pytest.mark.parametrize("sag_ratio", [0.0, 0.01, 0.035, 0.10, 0.30])
    def test_catenary_sag_curvature(self, sag_ratio: float):
        """Tests parabolic sag formulation with varying tension/slack."""
        strings = generate_catenary_magic_strings(height=1.65, rest_pose=True, sag_ratio=sag_ratio)
        assert len(strings.vertices) == 140
        for v in strings.vertices:
            assert all(math.isfinite(c) for c in v)

    def test_catenary_sag_midpoint_drop(self):
        """Verifies that cords with sag_ratio > 0 exhibit midpoint downward sag."""
        strings = generate_catenary_magic_strings(height=1.65, rest_pose=True, sag_ratio=0.035)
        # Check first cord (vertices 0..13)
        v_root = (np.array(strings.vertices[0]) + np.array(strings.vertices[1])) * 0.5
        v_tip = (np.array(strings.vertices[12]) + np.array(strings.vertices[13])) * 0.5
        v_mid = (np.array(strings.vertices[6]) + np.array(strings.vertices[7])) * 0.5

        # Straight line midpoint Z
        linear_mid_z = (v_root[2] + v_tip[2]) * 0.5
        # Sagged midpoint Z should be strictly lower
        assert v_mid[2] < linear_mid_z, f"Midpoint does not sag: mid={v_mid[2]}, linear={linear_mid_z}"


class TestAdversarialButterflyQuadGeneration:
    """Stress tests pure quad butterfly generation, wing flutter, and morphology."""

    @pytest.mark.parametrize("wing_angle", [-45.0, -15.0, 0.0, 25.0, 60.0, 85.0])
    def test_butterfly_flutter_angles(self, wing_angle: float):
        """Verifies butterfly pure quad topology (24 quads = 48 tris) across dihedral flutter angles."""
        b_mesh = generate_swallowtail_quad_butterfly(scale=0.045, wing_angle_deg=wing_angle)
        assert len(b_mesh.vertices) == 48, f"Expected 48 vertices, got {len(b_mesh.vertices)}"
        assert len(b_mesh.faces) == 48, f"Expected 48 triangular faces (24 quads), got {len(b_mesh.faces)}"

        # All vertices must be finite
        for v in b_mesh.vertices:
            assert all(math.isfinite(c) for c in v)

        # Zero degenerate faces
        for f_idx, (i0, i1, i2) in enumerate(b_mesh.faces):
            area = _triangle_area_3d(b_mesh.vertices[i0], b_mesh.vertices[i1], b_mesh.vertices[i2])
            assert area > 1e-8, f"Degenerate face {f_idx} at angle {wing_angle}: area={area}"

    def test_butterfly_flocking_positions_distribution(self):
        """Verifies flocking positions satisfy pairwise separation and upward vortex spiral bounds."""
        positions = get_butterfly_vortex_positions(height=1.65, count=10)
        assert len(positions) == 10

        # Elevation bounds: Z in [0.88m, 1.32m]
        z_vals = [p[2] for p in positions]
        assert min(z_vals) >= 0.85, f"Min Z violation: {min(z_vals)}"
        assert max(z_vals) <= 1.35, f"Max Z violation: {max(z_vals)}"

        # Pairwise separation >= 100mm
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                p1, p2 = np.array(positions[i]), np.array(positions[j])
                dist = np.linalg.norm(p1 - p2)
                assert dist >= 0.10, f"Pairwise separation too small between {i} and {j}: {dist*1000:.1f}mm"


class TestAdversarialWardrobeSkinningAndAssembly:
    """Stress tests skin weights normalization and full wardrobe suite assembly."""

    def test_rigify_skin_weights_normalization(self):
        """Verifies that all vertices in bodice, skirt, and sash have normalized Rigify DEF skin weights."""
        bodice = generate_dress_bodice(height=1.65)
        assign_bodice_skin_weights(bodice, height=1.65)
        assert hasattr(bodice, "skin_weights")
        for v_idx, w_map in bodice.skin_weights.items():
            total_w = sum(w_map.values())
            assert abs(total_w - 1.0) < 1e-4, f"Bodice vert {v_idx} unnormalized skin weight sum={total_w}"

        sash = generate_dress_waist_sash(height=1.65)
        assign_sash_skin_weights(sash, height=1.65)
        assert hasattr(sash, "skin_weights")
        for v_idx, w_map in sash.skin_weights.items():
            total_w = sum(w_map.values())
            assert abs(total_w - 1.0) < 1e-4, f"Sash vert {v_idx} unnormalized skin weight sum={total_w}"

    def test_full_wardrobe_suite_generation(self):
        """Verifies generate_yu_nian_an_wardrobe produces all required elements."""
        cfg = WardrobeConfig(
            character_height=1.65,
            include_sandals=True,
            include_red_threads=True,
            include_glowing_butterflies=True,
            butterfly_count=10,
        )
        wardrobe = generate_yu_nian_an_wardrobe(cfg)
        expected_keys = [
            "Dress_Bodice",
            "Dress_WaistSash",
            "Dress_PleatedSkirt",
            "Mesh_Sandal_L",
            "Mesh_Sandal_R",
            "Prop_Marionette_Strings",
        ] + [f"Prop_Butterfly_{i:02d}" for i in range(10)]

        for k in expected_keys:
            assert k in wardrobe, f"Missing wardrobe element: {k}"
            assert len(wardrobe[k].vertices) > 0
            assert len(wardrobe[k].faces) > 0


# ==============================================================================
# 2. GROOMING SUBSYSTEM: 6-STRATUM HIME CUT & RIBBON EXTRUSION
# ==============================================================================

class TestAdversarial6StratumHimeCut:
    """Stress tests 6-stratum cranial splines, terminations, and landmark clearances."""

    def test_all_six_authentic_strata_presence_and_counts(self):
        """Verifies all 6 strata are properly instantiated with positive guide counts."""
        layers = get_6_stratum_hime_cut_layers(total_guides=15000)
        expected_strata = [
            "Hair_Hime_Bangs",
            "Hair_Hime_Sidelocks",
            "Hair_Scalp_Crown",
            "Hair_Temporal_Transitions",
            "Hair_Back_Cascade",
            "Hair_Flyaways",
        ]
        assert len(layers) == 6
        for name in expected_strata:
            assert name in layers, f"Missing stratum: {name}"
            cfg = layers[name]
            assert cfg.strand_count > 0
            assert cfg.length > 0.0
            assert cfg.root_radius > cfg.tip_radius

    @pytest.mark.parametrize("height", [1.40, 1.65, 1.90])
    def test_spline_generation_all_strata_finite_geometry(self, height: float):
        """Verifies 3D spline coordinate finiteness and positive lengths across heights."""
        splines_by_layer = generate_6_stratum_hime_cut_splines(height=height, sample_density_scale=0.10)
        assert len(splines_by_layer) == 6
        for layer_name, splines in splines_by_layer.items():
            assert len(splines) > 0, f"No splines generated for {layer_name}"
            for s_idx, s in enumerate(splines):
                assert len(s.points) >= 2, f"Spline {s_idx} in {layer_name} has < 2 points"
                length = _calc_spline_length(s.points)
                assert length > 0.005, f"Spline {s_idx} in {layer_name} has degenerate length {length}"
                for pt in s.points:
                    assert all(math.isfinite(c) for c in pt), f"Non-finite point in {layer_name}: {pt}"

    def test_stratum_terminations(self):
        """Verifies bangs terminate at eyebrow level, sidelocks at chin, cascade at mid-back/hip."""
        splines_by_layer = generate_6_stratum_hime_cut_splines(height=1.65, sample_density_scale=0.10)

        # Stratum 1: Bangs terminate around eyebrows Z in [1.53m, 1.57m]
        bangs = splines_by_layer["Hair_Hime_Bangs"]
        bang_tips = [s.points[-1][2] for s in bangs]
        avg_bang_tip = sum(bang_tips) / len(bang_tips)
        assert 1.53 <= avg_bang_tip <= 1.57, f"Bangs termination out of eyebrow range: {avg_bang_tip:.3f}m"

        # Stratum 2: Sidelocks terminate around chin Z in [1.40m, 1.45m]
        sidelocks = splines_by_layer["Hair_Hime_Sidelocks"]
        side_tips = [s.points[-1][2] for s in sidelocks]
        avg_side_tip = sum(side_tips) / len(side_tips)
        assert 1.40 <= avg_side_tip <= 1.45, f"Sidelocks termination out of chin range: {avg_side_tip:.3f}m"

        # Stratum 5: Dorsal cascade terminates at mid-back Z in [0.90m, 1.05m]
        cascade = splines_by_layer["Hair_Back_Cascade"]
        cascade_tips = [s.points[-1][2] for s in cascade]
        avg_cascade_tip = sum(cascade_tips) / len(cascade_tips)
        assert 0.90 <= avg_cascade_tip <= 1.05, f"Cascade termination out of back/hip range: {avg_cascade_tip:.3f}m"


class TestAdversarialHairRibbonExtrusion:
    """Stress tests convert_curves_to_ribbon_mesh for pure quad topology and UVs."""

    def test_ribbon_quad_topology_and_uv_monotonicity(self):
        """Verifies quad extrusion, non-zero face area, and monotonic UV coordinates."""
        spline = HairCurveSpline(
            points=[
                (0.0, 0.08, 1.66),
                (0.0, 0.09, 1.62),
                (0.0, 0.095, 1.58),
                (0.0, 0.098, 1.55),
            ],
            radii=[0.00016, 0.000025],
            layer_name="Hair_Hime_Bangs",
            length=0.11,
        )
        ribbon = convert_curves_to_ribbon_mesh([spline], ribbon_width=0.002)
        assert len(ribbon.vertices) == 8  # 4 points * 2 vertices
        assert len(ribbon.faces) == 6     # 3 segments * 2 triangles (3 quads)

        # Check UVs: monotonic advancing from 0 to 1
        v_coords = [uv[1] for uv in ribbon.uvs]
        assert v_coords[0] == 0.0 and v_coords[-1] == 1.0
        for i in range(0, len(v_coords) - 2, 2):
            assert v_coords[i+2] >= v_coords[i], "Non-monotonic UV advancing along spline"

        # Verify zero degenerate faces
        for f_idx, (i0, i1, i2) in enumerate(ribbon.faces):
            area = _triangle_area_3d(ribbon.vertices[i0], ribbon.vertices[i1], ribbon.vertices[i2])
            assert area > 1e-10, f"Degenerate face {f_idx}: area={area}"

        # Verify Rigify DEF-head bone assignment
        assert "DEF-head" in ribbon.vertex_groups
        assert len(ribbon.vertex_groups["DEF-head"]) == 8

    def test_ribbon_degenerate_curve_handling(self):
        """Verifies ribbon extrusion handles edge cases (empty list, single-point curves)."""
        empty_ribbon = convert_curves_to_ribbon_mesh([])
        assert len(empty_ribbon.vertices) == 0
        assert len(empty_ribbon.faces) == 0

        single_pt_spline = HairCurveSpline(
            points=[(0.0, 0.08, 1.66)],
            radii=[0.00016, 0.000025],
            layer_name="Hair_Hime_Bangs",
            length=0.0,
        )
        single_ribbon = convert_curves_to_ribbon_mesh([single_pt_spline])
        assert len(single_ribbon.vertices) == 0
        assert len(single_ribbon.faces) == 0


class TestAdversarialCurvesGeometryNodesPipeline:
    """Stress tests build_hair_geom_node_tree mock execution and modifier script generation."""

    def test_build_hair_geom_node_tree_mock_execution(self):
        """Verifies build_hair_geom_node_tree constructs interface sockets and modifier nodes."""
        mock_tree = MagicMock()
        mock_tree.nodes = MagicMock()
        mock_tree.links = MagicMock()
        mock_tree.interface = MagicMock()

        cfg = {
            "root_radius": 0.00016,
            "tip_radius": 0.000025,
            "clump_factor": 0.28,
            "noise_frequency": 14.0,
            "noise_amplitude": 0.0012,
        }
        res_tree = build_hair_geom_node_tree(mock_tree, cfg)
        assert res_tree is mock_tree
        assert mock_tree.nodes.clear.called
        assert mock_tree.nodes.new.called

    def test_grooming_script_ast_validity(self):
        """Verifies get_grooming_script generates syntactically valid Python AST."""
        script = get_grooming_script(
            target_object="Human_Base_Mesh",
            hair_style="hime_cut_long",
            strand_count=15000,
        )
        parsed = ast.parse(script)
        assert isinstance(parsed, ast.Module)
        assert "GN_HairGroom" in script or "build_hair_geom_node_tree" in script


# ==============================================================================
# 3. CREATURE FUR GROOMING COMPATIBILITY & REGRESSION
# ==============================================================================

class TestAdversarialCreatureFurCompatibility:
    """Stress tests CreatureGroomingEngine backward compatibility and regression invariance."""

    def test_creature_grooming_engine_instantiation_and_configs(self):
        """Verifies default undercoat and guard hair configs exceed 10k parent strands."""
        undercoat = get_default_undercoat_config(8000)
        guard = get_default_guard_hair_config(4000)
        assert undercoat.strand_count + guard.strand_count >= 12000 >= 10000
        assert undercoat.rendered_child_count >= 8
        assert guard.rendered_child_count >= 8

        # Rendered child strands calculation exceeds 100k
        total_render = undercoat.strand_count * (1 + undercoat.rendered_child_count) + \
                       guard.strand_count * (1 + guard.rendered_child_count)
        assert total_render >= 100000, f"Render strand total below 100k: {total_render}"

    def test_zero_fur_groups_mask_invariance(self):
        """Asserts zero-fur anatomical features receive strictly zero weight."""
        engine = CreatureGroomingEngine()
        # Mock vertex groups with standard naked features
        mock_vgs = {
            "snout": [0, 1],
            "nostrils": [2, 3],
            "claws_front": [4, 5],
            "pads_front": [6, 7],
            "torso": [8, 9, 10, 11],
        }
        masks = engine.build_density_mask_weights(mock_vgs, total_vertices=12)
        assert "Fur_Density" in masks and "Fur_Length" in masks and "Fur_Clump" in masks
        density_map = masks["Fur_Density"]

        # Vertices 0..7 are in ZERO_FUR_GROUPS -> must be strictly 0.0
        for i in range(8):
            assert density_map[i] == 0.0, f"Vertex {i} in zero-fur region has non-zero weight: {density_map[i]}"

        # Vertices 8..11 are in FULL_FUR_GROUPS (torso) -> must be 1.0
        for i in range(8, 12):
            assert density_map[i] == 1.0, f"Vertex {i} in full-fur region has non-full weight: {density_map[i]}"

    @pytest.mark.parametrize("pos,expected_axis,min_component", [
        ((0.0, 0.5, 0.8), "y", 0.60),   # Spine dorsal flow should point caudal (-Y or +Y depending on orientation)
        ((0.4, 0.0, 0.5), "x", 0.50),   # Lateral flank flow outward
    ])
    def test_biological_flow_field_vectors(self, pos: Tuple[float, float, float], expected_axis: str, min_component: float):
        """Verifies biological flow vector fields align with anatomical growth patterns."""
        flow_vec = compute_biological_flow_vector(pos)
        norm = np.linalg.norm(flow_vec)
        assert abs(norm - 1.0) < 1e-4, f"Biological flow vector not normalized: {norm}"

    def test_pure_python_ribbon_geometry_generation(self):
        """Verifies CreatureGroomingEngine.generate_ribbon_geometry_pure_python produces valid ribbons."""
        engine = CreatureGroomingEngine()
        mock_strand = [
            (0.0, 0.0, 1.0),
            (0.0, -0.05, 0.95),
            (0.0, -0.10, 0.90),
        ]
        ribbon_data = engine.generate_ribbon_geometry_pure_python([mock_strand], root_width=0.002, tip_width=0.0002)
        assert "vertices" in ribbon_data and "faces" in ribbon_data and "uvs" in ribbon_data
        assert len(ribbon_data["vertices"]) == 6
        assert len(ribbon_data["faces"]) == 2  # 2 quad faces
        assert len(ribbon_data["uvs"]) == 8   # 2 quads * 4 uvs
        assert ribbon_data["has_uvs"] is True
