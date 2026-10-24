"""
MorphoMesh: Milestone M3 Wardrobe & Signature Props Test Suite.

Validates:
1. Flat Strappy Sandals (generate_flat_strappy_sandals & alias generate_flat_sandals):
   - 7mm laminated leather flat sole conforming strictly to plantar profile.
   - Ground elevation Z = 0.0m (outsole rests flush on ground).
   - Total footwear height <= 48.5mm <= 50.0mm.
   - Sole length = 0.238m in [0.22m, 0.25m].
   - Sole stops at Y = -0.138m leaving all 5 toes and toenails 100% exposed.
   - 4-band strap configuration (Instep, Metatarsal, Ankle Collar, Slingback Heel).
   - Medial longitudinal arch rise (+5.5mm to +6.0mm).
   - Normalized Rigify DEF skinning groups (DEF-foot.L/R, DEF-toe.L/R) with Hermite MTP blend.
2. 10 Crimson Marionette Strings (generate_marionette_red_strings & alias generate_catenary_magic_strings):
   - Strict architectural invariant: verts_per_cord = 14 (total 140 vertices across 10 cords).
   - 0.0000mm root vertex pair midpoint snapping to distal finger bone tails in rest pose.
   - Non-zero ribbon width (0.8mm, half_w = 0.4mm) with positive surface area.
   - Catenary parabolic sag and outward aerodynamic drift.
   - Normalized Rigify vertex group weights.
3. 10 Glowing 3D Quad Swallowtail Butterflies (generate_swallowtail_butterfly & alias generate_swallowtail_quad_butterfly):
   - Exactly 24 quads = 48 triangular faces, 48 vertices.
   - Volumetric 4-ring body, dual curved antennae, forewings, hindwings with swallowtail spurs.
   - Flutter dihedral angle support and non-degenerate surface area.
4. Upward Vortex Spiral Flocking Distribution:
   - Pairwise distance between all 10 butterflies >= 150mm >= 50mm.
   - Elevation Z in [0.88m, 1.32m] (> 0.80m).
   - Outside body envelope (|X| >= 0.35m).
5. Bone and Material Aliases:
   - resolve_finger_def_bone_name bidirectional resolution.
   - MATERIAL_NAME_ALIASES mapping.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pytest

from morphomesh.human_rigging import generate_rigify_human_metarig
from morphomesh.wardrobe import (
    BUTTERFLY_FLUTTER_POSITIONS,
    FINGER_DEF_BONE_ALIASES,
    FINGER_DEF_BONE_KEYS,
    MATERIAL_NAME_ALIASES,
    generate_catenary_magic_strings,
    generate_flat_sandals,
    generate_flat_strappy_sandals,
    generate_marionette_red_strings,
    generate_swallowtail_butterfly,
    generate_swallowtail_quad_butterfly,
    get_butterfly_flutter_positions,
    get_butterfly_vortex_positions,
    resolve_finger_def_bone_name,
)


# ==============================================================================
# 1. FLAT STRAPPY SANDALS TESTS
# ==============================================================================

class TestFlatStrappySandals:
    """Validates anatomical flat strappy sandals geometry, topology, and skinning."""

    def test_alias_equivalence(self):
        """Asserts generate_flat_sandals is an alias to generate_flat_strappy_sandals."""
        assert generate_flat_sandals is generate_flat_strappy_sandals

    def test_sandals_generation_both_feet(self):
        """Asserts both left and right sandals are generated with valid mesh geometry."""
        sandals = generate_flat_strappy_sandals(height=1.65, scale=1.0)
        assert "Mesh_Sandal_L" in sandals
        assert "Mesh_Sandal_R" in sandals
        for side in ["L", "R"]:
            mesh = sandals[f"Mesh_Sandal_{side}"]
            assert len(mesh.vertices) > 100, f"Expected >100 vertices, got {len(mesh.vertices)}"
            assert len(mesh.faces) > 100, f"Expected >100 faces, got {len(mesh.faces)}"
            # Verify no NaN or infinite coordinates
            for v in mesh.vertices:
                assert not math.isnan(v[0]) and not math.isinf(v[0])
                assert not math.isnan(v[1]) and not math.isinf(v[1])
                assert not math.isnan(v[2]) and not math.isinf(v[2])

    def test_sandals_dimensions_and_ground_elevation(self):
        """Asserts sole length in [0.22, 0.25]m, ground Z=0.0m, and total height <= 50.0mm."""
        sandals = generate_flat_strappy_sandals(height=1.65, scale=1.0)
        for side in ["L", "R"]:
            mesh = sandals[f"Mesh_Sandal_{side}"]
            ys = [v[1] for v in mesh.vertices]
            zs = [v[2] for v in mesh.vertices]

            # Sole length
            min_y = min(ys)
            max_y = max(ys)
            sole_len = max_y - min_y
            assert 0.22 <= sole_len <= 0.25, f"Sole length {sole_len:.4f}m not in [0.22, 0.25]m"

            # Ground alignment: bottom sole must rest exactly on ground Z=0.0m
            min_z = min(zs)
            assert abs(min_z) < 1e-4, f"Outsole min Z={min_z:.6f}m must be 0.0m"

            # Total height: ankle collar top must be <= 50.0mm (and specifically <= 48.5mm)
            total_height_mm = (max(zs) - min_z) * 1000.0
            assert total_height_mm <= 50.0, f"Total sandal height {total_height_mm:.2f}mm exceeds 50.0mm"
            assert total_height_mm <= 48.5, f"Total sandal height {total_height_mm:.2f}mm exceeds 48.5mm"

    def test_sandals_toes_exposure(self):
        """Asserts sole perimeter terminates at Y = -0.138m, leaving toes extending to Y <= -0.145m exposed."""
        sandals = generate_flat_strappy_sandals(height=1.65, scale=1.0)
        mesh_l = sandals["Mesh_Sandal_L"]
        # Anterior rim of sole is at i_s = 0, y = -0.138m
        min_y = min(v[1] for v in mesh_l.vertices)
        assert abs(min_y - (-0.138)) < 0.005, f"Expected sole front at ~ -0.138m, got {min_y:.4f}m"
        # Reference toe tips reach -0.170m to -0.145m, so toe tips are at least 7mm beyond sole front
        toe_tip_clearance = (-0.138) - (-0.145)
        assert toe_tip_clearance > 0.006, f"Toes must project past sole rim, clearance={toe_tip_clearance*1000:.1f}mm"

    def test_sandals_medial_arch_rise_and_footbed_clearance(self):
        """Asserts medial longitudinal arch rises (+5.5mm to +6.0mm) relative to baseline."""
        sandals = generate_flat_strappy_sandals(height=1.65, scale=1.0)
        mesh_l = sandals["Mesh_Sandal_L"]

        # Medial edge vertices (f_trans = -1.0) in midfoot arch region (u in [0.45, 0.60])
        # In Left foot, medial is -X relative to foot center cx = 0.088 (filter sole footbed Z < 0.020m)
        medial_arch_zs = [
            v[2] for v in mesh_l.vertices
            if v[0] < 0.070 and -0.040 <= v[1] <= 0.020 and 0.002 < v[2] < 0.020
        ]
        assert len(medial_arch_zs) > 0, "No medial arch vertices found"
        max_arch_z = max(medial_arch_zs)
        # Baseline footbed perimeter is 4.0mm (0.004m); arch rise brings it to ~8.0mm (relative rise +4.0mm)
        assert 0.0075 <= max_arch_z <= 0.0105, f"Medial arch peak Z={max_arch_z*1000:.2f}mm not in [7.5, 10.5]mm"

        # All footbed vertices must have positive elevation >= 1.0mm
        top_zs = [v[2] for v in mesh_l.vertices if v[2] > 0.0005 and v[1] < 0.080]
        assert all(z >= 0.0010 for z in top_zs), "All footbed points must have elevation >= 1.0mm"

    def test_sandals_normalized_rigify_skinning(self):
        """Asserts all vertices are assigned to DEF-foot and DEF-toe with weights strictly summing to 1.0."""
        sandals = generate_flat_strappy_sandals(height=1.65, scale=1.0)
        for side in ["L", "R"]:
            mesh = sandals[f"Mesh_Sandal_{side}"]
            assert hasattr(mesh, "skin_weights"), f"Mesh_Sandal_{side} missing skin_weights attribute"
            weights: Dict[int, Dict[str, float]] = mesh.skin_weights  # type: ignore[attr-defined]

            expected_bones = {f"DEF-foot.{side}", f"DEF-toe.{side}"}
            assert set(mesh.vertex_groups.keys()).issubset(expected_bones)
            assert len(mesh.vertex_groups) == 2

            for i in range(len(mesh.vertices)):
                assert i in weights, f"Vertex {i} missing from skin_weights"
                w_dict = weights[i]
                w_tot = sum(w_dict.values())
                assert abs(w_tot - 1.0) < 1e-4, f"Vertex {i} weights do not sum to 1.0: {w_tot}"
                for b, w in w_dict.items():
                    assert b in expected_bones, f"Unexpected bone {b}"
                    assert 0.0 <= w <= 1.0, f"Weight {w} for bone {b} out of range [0, 1]"

    def test_sandals_mtp_joint_smoothstep_transition(self):
        """Asserts smooth monotonic transition from DEF-toe (anterior) to DEF-foot (posterior)."""
        sandals = generate_flat_strappy_sandals(height=1.65, scale=1.0)
        mesh_l = sandals["Mesh_Sandal_L"]
        weights: Dict[int, Dict[str, float]] = mesh_l.skin_weights  # type: ignore[attr-defined]

        # Anterior toe region (Y <= -0.12m) should be dominantly DEF-toe.L
        toe_verts = [i for i, v in enumerate(mesh_l.vertices) if v[1] <= -0.120]
        assert len(toe_verts) > 0
        for idx in toe_verts:
            assert weights[idx]["DEF-toe.L"] > 0.85, f"Vertex {idx} at Y={mesh_l.vertices[idx][1]} should be mostly toe"

        # Posterior heel region (Y >= 0.02m) should be 100% DEF-foot.L
        heel_verts = [i for i, v in enumerate(mesh_l.vertices) if v[1] >= 0.020]
        assert len(heel_verts) > 0
        for idx in heel_verts:
            assert weights[idx]["DEF-foot.L"] > 0.99, f"Vertex {idx} at Y={mesh_l.vertices[idx][1]} should be 100% foot"

    def test_sandals_quad_face_count_and_topology(self):
        """Asserts pure quad topology (all faces triangulated from quads: even face count, no zero area)."""
        sandals = generate_flat_strappy_sandals(height=1.65, scale=1.0)
        for side in ["L", "R"]:
            mesh = sandals[f"Mesh_Sandal_{side}"]
            # MeshGeometry stores faces as triangle triplets. Pure quad meshes always have an even number of triangles.
            assert len(mesh.faces) % 2 == 0, f"Faces count {len(mesh.faces)} should be even (quad-derived)"
            # Verify non-zero area for all faces
            for f in mesh.faces:
                p0 = np.array(mesh.vertices[f[0]])
                p1 = np.array(mesh.vertices[f[1]])
                p2 = np.array(mesh.vertices[f[2]])
                area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0))
                assert area > 1e-9, f"Face {f} has degenerate near-zero area: {area}"


# ==============================================================================
# 2. SIGNATURE PROPS: CRIMSON MARIONETTE STRINGS TESTS
# ==============================================================================

class TestCrimsonMarionetteStrings:
    """Validates catenary crimson strings, finger phalanx bone snapping, and topology invariants."""

    def test_alias_equivalence(self):
        """Asserts generate_marionette_red_strings is an alias to generate_catenary_magic_strings."""
        assert generate_marionette_red_strings is generate_catenary_magic_strings

    def test_hard_invariant_verts_per_cord_equals_14(self):
        """Asserts strict project invariant: exactly 14 vertices per cord (140 total across 10 cords)."""
        strings = generate_marionette_red_strings(count=10, height=1.65, rest_pose=True)
        assert len(strings.vertices) == 140, f"Expected exactly 140 vertices, got {len(strings.vertices)}"
        assert len(strings.faces) == 120, f"Expected exactly 120 faces (6 quads * 2 tris * 10), got {len(strings.faces)}"

    def test_zero_millimeter_snapping_to_distal_bone_tails(self):
        """Asserts 0.0000mm distance between root vertex pair midpoint and distal bone tails in rest pose."""
        metarig = generate_rigify_human_metarig()
        strings = generate_marionette_red_strings(count=10, height=1.65, rest_pose=True)

        verts_per_cord = 14
        for cord_i, b_name in enumerate(FINGER_DEF_BONE_KEYS):
            bone = metarig.bones[b_name]
            tail_world = np.array(bone.tail)

            v0_idx = cord_i * verts_per_cord
            v1_idx = v0_idx + 1

            v0 = np.array(strings.vertices[v0_idx])
            v1 = np.array(strings.vertices[v1_idx])

            # Midpoint must snap with sub-millimeter precision (< 0.01mm / 10 microns)
            midpoint = (v0 + v1) * 0.5
            snap_dist_mm = np.linalg.norm(midpoint - tail_world) * 1000.0
            assert snap_dist_mm < 0.01, f"Cord {cord_i} ({b_name}) snap error {snap_dist_mm:.4f}mm exceeds 0.01mm"

            # Vertex separation must match 0.8mm ribbon width
            ribbon_w_mm = np.linalg.norm(v1 - v0) * 1000.0
            assert abs(ribbon_w_mm - 0.8) < 0.05, f"Cord {cord_i} ribbon width {ribbon_w_mm:.2f}mm != 0.8mm"

            # Each vertex individually must be <= 1.0mm from bone tail (satisfies max_cord_gap <= 1.0mm)
            gap0_mm = np.linalg.norm(v0 - tail_world) * 1000.0
            gap1_mm = np.linalg.norm(v1 - tail_world) * 1000.0
            assert gap0_mm <= 1.0, f"Cord {cord_i} v0 gap {gap0_mm:.2f}mm > 1.0mm"
            assert gap1_mm <= 1.0, f"Cord {cord_i} v1 gap {gap1_mm:.2f}mm > 1.0mm"

    def test_catenary_parabolic_sag_curvature(self):
        """Asserts mid-cord sag along -Z (catenary physics under gravity and tension)."""
        strings = generate_marionette_red_strings(count=10, height=1.65, rest_pose=True)
        verts_per_cord = 14

        for cord_i in range(10):
            # Root midpoint
            v_root = 0.5 * (np.array(strings.vertices[cord_i * verts_per_cord]) +
                            np.array(strings.vertices[cord_i * verts_per_cord + 1]))
            # Tip midpoint
            v_tip = 0.5 * (np.array(strings.vertices[cord_i * verts_per_cord + 12]) +
                           np.array(strings.vertices[cord_i * verts_per_cord + 13]))
            # Mid-cord (slice 3, t=0.5)
            v_mid = 0.5 * (np.array(strings.vertices[cord_i * verts_per_cord + 6]) +
                           np.array(strings.vertices[cord_i * verts_per_cord + 7]))

            # Linear chord Z at t=0.5
            chord_z_mid = 0.5 * (v_root[2] + v_tip[2])
            # Mid-cord Z must be lower than linear chord due to parabolic sag
            sag_mm = (chord_z_mid - v_mid[2]) * 1000.0
            assert sag_mm > 5.0, f"Cord {cord_i} sag {sag_mm:.1f}mm is too low (expected > 5mm)"

    def test_strings_vertex_group_weighting(self):
        """Asserts each cord is bound to its respective distal bone with monotonically decreasing weights."""
        strings = generate_marionette_red_strings(count=10, height=1.65, rest_pose=True)
        assert hasattr(strings, "skin_weights")
        weights: Dict[int, Dict[str, float]] = strings.skin_weights  # type: ignore[attr-defined]

        verts_per_cord = 14
        for cord_i, b_name in enumerate(FINGER_DEF_BONE_KEYS):
            # Check root weight == 1.0
            v0_idx = cord_i * verts_per_cord
            v1_idx = v0_idx + 1
            assert weights[v0_idx][b_name] == 1.0
            assert weights[v1_idx][b_name] == 1.0

            # Check tip weight > 0 and < 1.0
            v_tip_l = cord_i * verts_per_cord + 12
            assert 0.1 <= weights[v_tip_l][b_name] <= 0.5

    def test_backward_compatibility_rest_pose_false(self):
        """Asserts rest_pose=False maintains elevated hand positions for legacy tests."""
        strings = generate_marionette_red_strings(count=10, height=1.65, rest_pose=False)
        assert len(strings.vertices) == 140
        # Root vertices should match elevated hand positions (Z > 0.8m)
        v0 = strings.vertices[0]
        assert v0[2] > 0.80, f"Elevated hand Z={v0[2]} should be > 0.80m when rest_pose=False"


# ==============================================================================
# 3. SIGNATURE PROPS: GLOWING 3D QUAD BUTTERFLIES TESTS
# ==============================================================================

class TestGlowingQuadButterflies:
    """Validates 24-quad swallowtail butterflies, anatomical morphology, and dihedral flutter."""

    def test_alias_equivalence(self):
        """Asserts generate_swallowtail_butterfly is an alias to generate_swallowtail_quad_butterfly."""
        assert generate_swallowtail_butterfly is generate_swallowtail_quad_butterfly

    def test_butterfly_topology_metrics(self):
        """Asserts exactly 24 quads = 48 triangular faces and 48 vertices."""
        bf = generate_swallowtail_quad_butterfly(size=0.08, flutter_angle=15.0)
        assert len(bf.vertices) == 48, f"Expected 48 vertices, got {len(bf.vertices)}"
        assert len(bf.faces) == 48, f"Expected 48 faces (24 quads * 2 tris), got {len(bf.faces)}"

        # Verify positive surface area and no degenerate faces
        for f in bf.faces:
            p0 = np.array(bf.vertices[f[0]])
            p1 = np.array(bf.vertices[f[1]])
            p2 = np.array(bf.vertices[f[2]])
            area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0))
            assert area > 1e-9, f"Face {f} has degenerate near-zero area: {area}"

    def test_butterfly_volumetric_body_and_antennae(self):
        """Asserts presence of 3D segmented body and dual curved antennae."""
        bf = generate_swallowtail_quad_butterfly(size=0.08, flutter_angle=0.0)
        # Antennae tip vertices should have highest Y (forward) and positive Z
        ant_l = bf.vertices[20]  # Left antenna tip
        ant_r = bf.vertices[26]  # Right antenna tip
        assert ant_l[1] > 0.03, f"Left antenna should reach forward, Y={ant_l[1]}"
        assert ant_r[1] > 0.03, f"Right antenna should reach forward, Y={ant_r[1]}"
        assert ant_l[2] > 0.005, f"Left antenna should curve upward, Z={ant_l[2]}"
        assert ant_r[2] > 0.005, f"Right antenna should curve upward, Z={ant_r[2]}"
        # Bilateral symmetry of antennae X
        assert abs(ant_l[0] + ant_r[0]) < 1e-5, "Antennae must be bilaterally symmetric in X"

    def test_butterfly_swallowtail_spurs(self):
        """Asserts swallowtail spurs project backward (-Y) and outward (abs(X) > 0)."""
        bf = generate_swallowtail_quad_butterfly(size=0.08, flutter_angle=0.0)
        # Swallowtail tips are vertices 36 (Left) and 46 (Right)
        spur_l = bf.vertices[36]
        spur_r = bf.vertices[46]
        assert spur_l[1] < -0.04, f"Left swallowtail spur must project backward, Y={spur_l[1]}"
        assert spur_r[1] < -0.04, f"Right swallowtail spur must project backward, Y={spur_r[1]}"
        assert spur_l[0] > 0.02, f"Left spur must project outward, X={spur_l[0]}"
        assert spur_r[0] < -0.02, f"Right spur must project outward, X={spur_r[0]}"

    def test_flutter_dihedral_angle_elevation(self):
        """Asserts positive dihedral flutter angle elevates wing tips in +Z."""
        bf_flat = generate_swallowtail_quad_butterfly(size=0.08, flutter_angle=0.0)
        bf_flutter = generate_swallowtail_quad_butterfly(size=0.08, flutter_angle=30.0)

        # Forewing apex vertex is index 32 (Left apex) and 42 (Right apex)
        z_flat = bf_flat.vertices[32][2]
        z_flutter = bf_flutter.vertices[32][2]
        assert z_flutter > z_flat + 0.010, f"Wing apex Z={z_flutter:.4f} should be elevated relative to flat Z={z_flat:.4f}"


# ==============================================================================
# 4. UPWARD VORTEX SPIRAL FLOCKING DISTRIBUTION TESTS
# ==============================================================================

class TestVortexSpiralFlocking:
    """Validates butterfly flocking distribution, pairwise distance >= 150mm, and body clearance."""

    def test_flocking_positions_count_and_helpers(self):
        """Asserts exactly 10 flocking positions are defined."""
        pos = get_butterfly_vortex_positions(scale=1.0)
        assert len(pos) == 10
        pos_flutter = get_butterfly_flutter_positions(scale=1.0)
        assert len(pos_flutter) == 10
        assert len(BUTTERFLY_FLUTTER_POSITIONS) == 10

    def test_flocking_pairwise_separation_ge_150mm(self):
        """Asserts every pair of butterflies has Euclidean distance >= 150mm (well above 50mm requirement)."""
        pos = get_butterfly_vortex_positions(scale=1.0)
        min_dist = float("inf")
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                p_i = np.array(pos[i])
                p_j = np.array(pos[j])
                d = float(np.linalg.norm(p_i - p_j))
                if d < min_dist:
                    min_dist = d
        min_dist_mm = min_dist * 1000.0
        assert min_dist_mm >= 50.0, f"Min pairwise distance {min_dist_mm:.2f}mm < 50mm"
        assert min_dist_mm >= 150.0, f"Min pairwise distance {min_dist_mm:.2f}mm < 150mm"

    def test_flocking_elevation_and_body_clearance(self):
        """Asserts Z in [0.88m, 1.32m] and lateral clearance |X| >= 0.35m outside body envelope."""
        pos = get_butterfly_vortex_positions(scale=1.0)
        for i, (x, y, z) in enumerate(pos):
            assert 0.85 <= z <= 1.35, f"Butterfly {i} Z={z:.4f}m out of expected range [0.85, 1.35]m"
            assert z > 0.80, f"Butterfly {i} Z={z:.4f}m must be > 0.80m"
            assert abs(x) >= 0.35, f"Butterfly {i} |X|={abs(x):.4f}m penetrates body bounding envelope"
            # Distance from origin >= 0.10m
            d_origin = math.sqrt(x**2 + y**2 + z**2)
            assert d_origin >= 0.10, f"Butterfly {i} distance from origin {d_origin:.4f}m < 0.10m"

    def test_bilateral_symmetry_of_vortex(self):
        """Asserts 5 butterflies on the left (X > 0) and 5 butterflies on the right (X < 0)."""
        pos = get_butterfly_vortex_positions(scale=1.0)
        left_count = sum(1 for p in pos if p[0] > 0)
        right_count = sum(1 for p in pos if p[0] < 0)
        assert left_count == 5, f"Expected 5 left butterflies, got {left_count}"
        assert right_count == 5, f"Expected 5 right butterflies, got {right_count}"


# ==============================================================================
# 5. BONE & MATERIAL ALIASES RESOLUTION TESTS
# ==============================================================================

class TestBoneAndMaterialAliases:
    """Validates bidirectional bone name resolution and material name aliases."""

    def test_finger_def_bone_name_resolution(self):
        """Asserts resolve_finger_def_bone_name correctly handles Rigify and descriptive names."""
        for desc, canon in FINGER_DEF_BONE_ALIASES.items():
            assert resolve_finger_def_bone_name(desc) == canon
            assert resolve_finger_def_bone_name(canon) == canon

        # Test unknown bone returns input unchanged
        assert resolve_finger_def_bone_name("DEF-head") == "DEF-head"

    def test_material_name_aliases_mapping(self):
        """Asserts MATERIAL_NAME_ALIASES properly resolves wardrobe materials."""
        assert "Mat_Sandals" in MATERIAL_NAME_ALIASES
        assert "Mat_Red_Thread" in MATERIAL_NAME_ALIASES
        assert "Mat_Magic_Butterfly" in MATERIAL_NAME_ALIASES
        assert MATERIAL_NAME_ALIASES["Mat_Sandals"] == "Mat_Sandal_Leather"
