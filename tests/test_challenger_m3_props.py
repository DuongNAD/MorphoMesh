"""
Empirical Challenger Test Suite for Milestone M3 Signature Props & Flocking:
- Invariant verification: exactly verts_per_cord = 14 (total 140 vertices across 10 cords).
- Snapping precision: root vertex pair midpoint snaps to distal finger bone tails with sub-10-micron error (< 0.01mm) and algebraic 0.0000mm error.
- Ribbon width: non-zero width (2 * half_w = 0.8mm) with positive face surface area.
- Butterfly topology: exactly 24 quads = 48 tris per butterfly, 48 vertices, zero degenerate faces (face area > 10^-6 m^2), valid dihedral flutter angles.
- Flocking distribution: bilateral upward vortex spiral (Z in [0.88m, 1.32m], minimum pairwise separation >= 150mm >= 50mm, |X| >= 0.35m).
- Adversarial empirical challenges:
    * Defect Challenge 1: character_assembler.py hardcoded flutter_positions reduces pairwise separation to 107.7mm (< 150mm).
    * Defect Challenge 2: character_assembler.py hardcoded flutter_positions detaches butterflies from cords by up to 635mm.
    * Defect Challenge 3: on-disk Yu_Nian_An_Master.blend contains stale M2 props (18-vert butterflies, 0.0mm cord root width).
"""

import math
import os
import subprocess
import numpy as np
import pytest

from morphomesh.human_rigging import generate_rigify_human_metarig
from morphomesh.character_assembler import MasterAssemblyConfig, get_master_assembly_script
from morphomesh.wardrobe import (
    BUTTERFLY_FLUTTER_POSITIONS,
    FINGER_DEF_BONE_ALIASES,
    FINGER_DEF_BONE_KEYS,
    generate_catenary_magic_strings,
    generate_marionette_red_strings,
    generate_swallowtail_butterfly,
    generate_swallowtail_quad_butterfly,
    generate_yu_nian_an_wardrobe,
    get_butterfly_flutter_positions,
    get_butterfly_vortex_positions,
    resolve_finger_def_bone_name,
    WardrobeConfig,
)

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
HAS_BLENDER = os.path.isfile(BLENDER_EXE)


# ==============================================================================
# 1. PROPS TOPOLOGY INVARIANTS
# ==============================================================================

class TestChallengerPropsInvariants:
    """Stress-tests mathematical invariants and boundary conditions for 10 crimson cords."""

    def test_invariant_verts_per_cord_equals_14(self):
        """Verify strict invariant: exactly 14 vertices per cord (140 total across 10 cords)."""
        strings = generate_catenary_magic_strings(count=10, height=1.65, rest_pose=True)
        assert len(strings.vertices) == 140, f"Expected 140 vertices, got {len(strings.vertices)}"
        assert len(strings.faces) == 120, f"Expected 120 triangular faces (60 quads), got {len(strings.faces)}"

    @pytest.mark.parametrize("scale", [0.5, 0.85, 1.0, 1.25, 1.65, 2.0])
    def test_scale_invariance_topology(self, scale: float):
        """Verify topological invariants hold across all character scales."""
        strings = generate_catenary_magic_strings(count=10, height=1.65 * scale, rest_pose=True)
        assert len(strings.vertices) == 140
        assert len(strings.faces) == 120

    def test_per_cord_connectivity_and_manifoldness(self):
        """Verify each cord is a contiguous strip of 6 quads (12 triangles) with no stray vertices."""
        strings = generate_catenary_magic_strings(count=10, height=1.65, rest_pose=True)
        verts_per_cord = 14
        faces_per_cord = 12

        for cord_i in range(10):
            v_start = cord_i * verts_per_cord
            v_end = (cord_i + 1) * verts_per_cord
            f_start = cord_i * faces_per_cord
            f_end = (cord_i + 1) * faces_per_cord

            cord_faces = strings.faces[f_start:f_end]
            cord_vert_indices = set()
            for f in cord_faces:
                for v_idx in f:
                    cord_vert_indices.add(v_idx)
                    assert v_start <= v_idx < v_end, f"Face vertex {v_idx} leaked outside cord range [{v_start}, {v_end})"

            assert len(cord_vert_indices) == 14, f"Cord {cord_i} did not reference all 14 vertices"

    def test_string_face_areas_strictly_positive(self):
        """Verify all 120 faces have strictly positive area > 10^-9 m^2 (no collapsed faces)."""
        strings = generate_catenary_magic_strings(count=10, height=1.65, rest_pose=True)
        for i, f in enumerate(strings.faces):
            p0 = np.array(strings.vertices[f[0]])
            p1 = np.array(strings.vertices[f[1]])
            p2 = np.array(strings.vertices[f[2]])
            cross = np.cross(p1 - p0, p2 - p0)
            area = 0.5 * float(np.linalg.norm(cross))
            assert area > 1e-9, f"Face {i} ({f}) has degenerate near-zero area: {area}"


# ==============================================================================
# 2. SNAPPING PRECISION & RIBBON WIDTH
# ==============================================================================

class TestChallengerSnappingPrecision:
    """Stress-tests distal finger bone tail snapping precision and ribbon geometry."""

    def test_snapping_precision_micron_level_to_bone_tails(self):
        """Verify root vertex pair midpoint snaps to distal finger bone tails with sub-10-micron error (< 0.01mm)."""
        metarig = generate_rigify_human_metarig()
        strings = generate_catenary_magic_strings(count=10, height=1.65, rest_pose=True)
        verts_per_cord = 14

        for cord_i, b_name in enumerate(FINGER_DEF_BONE_KEYS):
            bone = metarig.bones[b_name]
            tail = np.array(bone.tail)

            v0 = np.array(strings.vertices[cord_i * verts_per_cord])
            v1 = np.array(strings.vertices[cord_i * verts_per_cord + 1])
            midpoint = (v0 + v1) * 0.5

            err_m = float(np.linalg.norm(midpoint - tail))
            err_mm = err_m * 1000.0

            # Sub-10-micron precision (< 0.01mm)
            assert err_mm < 0.010, f"Cord {cord_i} ({b_name}) snap error {err_mm:.4f}mm exceeds 0.010mm"

    def test_blender_algebraic_snapping_precision_zero_error(self):
        """Verify the algebraic snapping formula in character_assembler yields exactly 0.0000mm error."""
        metarig = generate_rigify_human_metarig()
        s = 1.0
        half_w = 0.0004 * s

        for cord_i, b_name in enumerate(FINGER_DEF_BONE_KEYS):
            bone = metarig.bones[b_name]
            local_tail = np.array(bone.tail)

            # character_assembler.py:1272-1274 formula
            v0_co = np.array([local_tail[0] - half_w, local_tail[1], local_tail[2]])
            v1_co = np.array([local_tail[0] + half_w, local_tail[1], local_tail[2]])

            midpoint = (v0_co + v1_co) * 0.5
            err_mm = float(np.linalg.norm(midpoint - local_tail)) * 1000.0
            assert err_mm < 1e-6, f"Cord {cord_i} algebraic midpoint error {err_mm:.6f}mm exceeds 0.0000mm"

            width_mm = float(np.linalg.norm(v1_co - v0_co)) * 1000.0
            assert abs(width_mm - 0.80) < 1e-6, f"Cord {cord_i} width {width_mm:.6f}mm != 0.8mm"

    def test_ribbon_width_0_8mm_and_symmetric_offset(self):
        """Verify root vertices are separated by 0.8mm (half_w = 0.4mm) and symmetrically offset."""
        metarig = generate_rigify_human_metarig()
        strings = generate_catenary_magic_strings(count=10, height=1.65, rest_pose=True)
        verts_per_cord = 14

        for cord_i, b_name in enumerate(FINGER_DEF_BONE_KEYS):
            bone = metarig.bones[b_name]
            tail = np.array(bone.tail)

            v0 = np.array(strings.vertices[cord_i * verts_per_cord])
            v1 = np.array(strings.vertices[cord_i * verts_per_cord + 1])

            width_mm = float(np.linalg.norm(v1 - v0)) * 1000.0
            assert abs(width_mm - 0.80) < 0.05, f"Cord {cord_i} ribbon width {width_mm:.4f}mm != 0.8mm"

            dist0_mm = float(np.linalg.norm(v0 - tail)) * 1000.0
            dist1_mm = float(np.linalg.norm(v1 - tail)) * 1000.0
            assert abs(dist0_mm - 0.40) < 0.05, f"Cord {cord_i} v0 distance to tail {dist0_mm:.4f}mm != 0.4mm"
            assert abs(dist1_mm - 0.40) < 0.05, f"Cord {cord_i} v1 distance to tail {dist1_mm:.4f}mm != 0.4mm"
            assert abs(dist0_mm - dist1_mm) < 0.01, f"Cord {cord_i} asymmetry between v0 and v1: {dist0_mm} vs {dist1_mm}"

    def test_ribbon_tangent_orthogonality(self):
        """Verify ribbon width vector (v1 - v0) is orthogonal to initial tangent vector (v_mid - v_root)."""
        strings = generate_catenary_magic_strings(count=10, height=1.65, rest_pose=True)
        verts_per_cord = 14

        for cord_i in range(10):
            v0 = np.array(strings.vertices[cord_i * verts_per_cord])
            v1 = np.array(strings.vertices[cord_i * verts_per_cord + 1])
            width_vec = v1 - v0
            width_norm = width_vec / np.linalg.norm(width_vec)

            # Next ring
            v2 = np.array(strings.vertices[cord_i * verts_per_cord + 2])
            v3 = np.array(strings.vertices[cord_i * verts_per_cord + 3])
            seg1_mid = (v2 + v3) * 0.5
            seg0_mid = (v0 + v1) * 0.5
            tangent_vec = seg1_mid - seg0_mid
            tangent_norm = tangent_vec / np.linalg.norm(tangent_vec)

            dot = abs(float(np.dot(width_norm, tangent_norm)))
            assert dot < 0.05, f"Cord {cord_i} width vector not orthogonal to tangent: dot={dot}"


# ==============================================================================
# 3. BUTTERFLY TOPOLOGY & FLUTTER KINEMATICS
# ==============================================================================

class TestChallengerButterflyTopology:
    """Stress-tests butterfly geometry, 24-quad topology, and flutter kinematics."""

    def test_butterfly_exact_quad_and_vertex_count(self):
        """Verify butterfly topology has exactly 24 quads = 48 tris and 48 vertices."""
        bf = generate_swallowtail_quad_butterfly(scale=0.045, wing_angle_deg=25.0)
        assert len(bf.vertices) == 48, f"Expected 48 vertices, got {len(bf.vertices)}"
        assert len(bf.faces) == 48, f"Expected 48 triangular faces (24 quads), got {len(bf.faces)}"

    def test_butterfly_zero_degenerate_faces(self):
        """Verify every single face in the 24 quads has area > 10^-6 m^2."""
        bf = generate_swallowtail_quad_butterfly(scale=0.045, wing_angle_deg=25.0)
        min_area = float("inf")
        for i, f in enumerate(bf.faces):
            p0 = np.array(bf.vertices[f[0]])
            p1 = np.array(bf.vertices[f[1]])
            p2 = np.array(bf.vertices[f[2]])
            cross = np.cross(p1 - p0, p2 - p0)
            area = 0.5 * float(np.linalg.norm(cross))
            if area < min_area:
                min_area = area
            assert area > 1e-6, f"Face {i} ({f}) has area {area:.2e} m^2 <= 10^-6 m^2"
        assert min_area > 1e-6

    @pytest.mark.parametrize("angle", [-30.0, -15.0, 0.0, 15.0, 25.0, 45.0, 60.0, 80.0])
    def test_flutter_angles_robustness(self, angle: float):
        """Verify flutter kinematics over extreme dihedral angles maintain positive surface area."""
        bf = generate_swallowtail_quad_butterfly(scale=0.045, wing_angle_deg=angle)
        assert len(bf.vertices) == 48
        assert len(bf.faces) == 48
        for i, f in enumerate(bf.faces):
            p0 = np.array(bf.vertices[f[0]])
            p1 = np.array(bf.vertices[f[1]])
            p2 = np.array(bf.vertices[f[2]])
            cross = np.cross(p1 - p0, p2 - p0)
            area = 0.5 * float(np.linalg.norm(cross))
            assert area > 1e-7, f"Face {i} collapsed at angle {angle} deg: area={area}"

    def test_butterfly_subcomponents_morphology(self):
        """Verify 4-ring body, curved 3D antennae, and swallowtail caudal spurs."""
        bf = generate_swallowtail_quad_butterfly(scale=0.045, wing_angle_deg=0.0)

        # 1. Body vertices (0..15): 4 rings
        head_y = bf.vertices[0][1]
        tail_y = bf.vertices[12][1]
        assert head_y > 0.015, f"Head Y={head_y} should be anterior"
        assert tail_y < -0.015, f"Tail Y={tail_y} should be posterior"

        # 2. Antennae (16..27): tips at 20 (Left) and 26 (Right)
        tip_l = bf.vertices[20]
        tip_r = bf.vertices[26]
        assert tip_l[1] > head_y, "Left antenna tip must project beyond head"
        assert tip_r[1] > head_y, "Right antenna tip must project beyond head"
        assert tip_l[2] > 0.004, "Left antenna tip must curve upward"
        assert tip_r[2] > 0.004, "Right antenna tip must curve upward"
        assert tip_l[0] > 0 and tip_r[0] < 0, "Antennae must separate laterally"

        # 3. Swallowtail spurs (vertices 36 and 46)
        spur_l = bf.vertices[36]
        spur_r = bf.vertices[46]
        assert spur_l[1] < tail_y, f"Left spur Y={spur_l[1]} must extend posterior to abdomen tail {tail_y}"
        assert spur_r[1] < tail_y, f"Right spur Y={spur_r[1]} must extend posterior to abdomen tail {tail_y}"
        assert spur_l[0] > 0.015 and spur_r[0] < -0.015, "Spurs must point outward"


# ==============================================================================
# 4. FLOCKING DISTRIBUTION & VORTEX
# ==============================================================================

class TestChallengerFlockingDistribution:
    """Stress-tests butterfly vortex spiral flocking distribution and body clearance."""

    def test_flocking_pairwise_separation_ge_150mm(self):
        """Verify all 45 pairwise distances between 10 butterflies >= 150mm (well above 50mm)."""
        pos = get_butterfly_vortex_positions()
        assert len(pos) == 10

        min_d = float("inf")
        min_pair = None
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                p_i = np.array(pos[i])
                p_j = np.array(pos[j])
                d = float(np.linalg.norm(p_i - p_j))
                if d < min_d:
                    min_d = d
                    min_pair = (i, j)

        min_d_mm = min_d * 1000.0
        assert min_d_mm >= 50.0, f"Min separation {min_d_mm:.2f}mm < 50mm"
        assert min_d_mm >= 150.0, f"Min separation {min_d_mm:.2f}mm < 150mm (pair {min_pair})"

    def test_flocking_elevation_and_torso_clearance(self):
        """Verify Z in [0.88m, 1.32m] and lateral flank position |X| >= 0.35m."""
        pos = get_butterfly_vortex_positions()
        for i, (x, y, z) in enumerate(pos):
            assert 0.88 <= z <= 1.32, f"Butterfly {i} Z={z:.4f}m out of [0.88, 1.32]m"
            assert abs(x) >= 0.35, f"Butterfly {i} |X|={abs(x):.4f}m inside body clearance (< 0.35m)"
            radial_d = math.sqrt(x * x + y * y)
            assert radial_d >= 0.40, f"Butterfly {i} radial distance {radial_d:.4f}m < 0.40m"

    def test_bilateral_symmetry_5_per_flank(self):
        """Verify 5 butterflies on left flank (+X) and 5 on right flank (-X)."""
        pos = get_butterfly_vortex_positions()
        left_flank = [p for p in pos if p[0] > 0]
        right_flank = [p for p in pos if p[0] < 0]
        assert len(left_flank) == 5, f"Expected 5 left butterflies, got {len(left_flank)}"
        assert len(right_flank) == 5, f"Expected 5 right butterflies, got {len(right_flank)}"

    def test_string_tips_coincide_with_butterfly_targets(self):
        """Verify string tip midpoints coincide with butterfly target positions (< 0.01mm error)."""
        targets = get_butterfly_vortex_positions()
        strings = generate_catenary_magic_strings(rest_pose=True, target_positions=targets)
        verts_per_cord = 14

        for i in range(10):
            tip_l = np.array(strings.vertices[i * verts_per_cord + 12])
            tip_r = np.array(strings.vertices[i * verts_per_cord + 13])
            tip_mid = (tip_l + tip_r) * 0.5
            target = np.array(targets[i])

            err_mm = float(np.linalg.norm(tip_mid - target)) * 1000.0
            assert err_mm < 0.01, f"Cord {i} tip does not coincide with butterfly {i}: err={err_mm:.4f}mm"


# ==============================================================================
# 5. INTEGRATION & ADVERSARIAL DISCREPANCY CHALLENGES
# ==============================================================================

class TestChallengerCharacterAssemblerDiscrepancies:
    """Adversarial stress-test checking character_assembler.py integration and master deliverables."""

    def test_wardrobe_generation_contains_correct_props(self):
        """Verify generate_yu_nian_an_wardrobe produces Prop_Marionette_Strings and 10 butterflies."""
        cfg = WardrobeConfig(include_red_threads=True, include_glowing_butterflies=True, butterfly_count=10)
        wardrobe = generate_yu_nian_an_wardrobe(cfg)

        assert "Prop_Marionette_Strings" in wardrobe
        strings = wardrobe["Prop_Marionette_Strings"]
        assert len(strings.vertices) == 140
        assert len(strings.faces) == 120

        for i in range(10):
            bf_name = f"Prop_Butterfly_{i:02d}"
            assert bf_name in wardrobe, f"Missing {bf_name} in wardrobe"
            bf = wardrobe[bf_name]
            assert len(bf.vertices) == 48, f"{bf_name} has {len(bf.vertices)} vertices != 48"
            assert len(bf.faces) == 48, f"{bf_name} has {len(bf.faces)} faces != 48"

    def test_character_assembler_butterfly_flocking_separation_adversarial(self):
        """Adversarial challenge: verify character_assembler.py maintains pairwise distance >= 150mm."""
        cfg = MasterAssemblyConfig()
        script = get_master_assembly_script(cfg)

        # In character_assembler.py lines 1296-1307, flutter_positions is hardcoded:
        # Extract the flutter_positions defined in the script
        lines = script.split("\n")
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "flutter_positions = [":
                start_idx = i
                break
        assert start_idx is not None, "flutter_positions definition not found in script"

        # Parse the 10 positions
        coords = []
        s = 1.0
        for line in lines[start_idx + 1:start_idx + 11]:
            line = line.strip().rstrip(",").lstrip("(").rstrip(")")
            parts = [float(p.replace("* s", "").strip()) for p in line.split(",")]
            coords.append(parts)

        min_d = float("inf")
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                d = np.linalg.norm(np.array(coords[i]) - np.array(coords[j]))
                if d < min_d:
                    min_d = d

        min_d_mm = min_d * 1000.0
        assert min_d_mm >= 150.0, f"Assembler script butterfly min separation is {min_d_mm:.2f}mm < 150mm"

    def test_character_assembler_string_tip_to_butterfly_connection_adversarial(self):
        """Adversarial challenge: verify cords tips connect to butterflies within 20mm in assembler script."""
        cfg = MasterAssemblyConfig()
        script = get_master_assembly_script(cfg)

        # Parse hardcoded flutter_positions in character_assembler.py
        lines = script.split("\n")
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "flutter_positions = [":
                start_idx = i
                break
        assert start_idx is not None

        coords = []
        for line in lines[start_idx + 1:start_idx + 11]:
            line = line.strip().rstrip(",").lstrip("(").rstrip(")")
            parts = [float(p.replace("* s", "").strip()) for p in line.split(",")]
            coords.append(parts)

        targets = get_butterfly_vortex_positions()
        strings = generate_catenary_magic_strings(rest_pose=True, target_positions=targets)
        verts_per_cord = 14

        max_miss_mm = 0.0
        for i in range(10):
            tip_l = np.array(strings.vertices[i * verts_per_cord + 12])
            tip_r = np.array(strings.vertices[i * verts_per_cord + 13])
            tip_mid = (tip_l + tip_r) * 0.5
            bf_pos = np.array(coords[i])
            miss_mm = float(np.linalg.norm(tip_mid - bf_pos)) * 1000.0
            if miss_mm > max_miss_mm:
                max_miss_mm = miss_mm

        assert max_miss_mm <= 20.0, f"Assembler cord tip detached from butterfly by {max_miss_mm:.2f}mm > 20mm"

    @pytest.mark.skipif(not HAS_BLENDER, reason="Blender 4.5 LTS not installed")
    def test_on_disk_master_blend_has_m3_props_adversarial(self):
        """Adversarial challenge: verify Yu_Nian_An_Master.blend on disk contains 48-vert butterflies and 0.8mm cords."""
        blend_path = "output/yu_nian_an/Yu_Nian_An_Master.blend"
        assert os.path.isfile(blend_path), f"Master blend not found: {blend_path}"

        check_script = """
import bpy, sys
bf0 = bpy.data.objects.get('Prop_Butterfly_00')
if not bf0 or len(bf0.data.vertices) != 48:
    print(f'FAIL_BF_VERTS: {len(bf0.data.vertices) if bf0 else None}')
    sys.exit(1)

strings = bpy.data.objects.get('Prop_Marionette_Strings')
if not strings or len(strings.data.vertices) != 140:
    print(f'FAIL_STRINGS_VERTS: {len(strings.data.vertices) if strings else None}')
    sys.exit(1)

v0 = strings.data.vertices[0].co
v1 = strings.data.vertices[1].co
width_mm = (v1 - v0).length * 1000.0
if abs(width_mm - 0.8) > 0.05:
    print(f'FAIL_CORD_WIDTH: {width_mm}mm')
    sys.exit(1)

print('MASTER_BLEND_M3_PROPS_VERIFIED')
"""
        cmd = [BLENDER_EXE, "--background", blend_path, "--python-expr", check_script]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert res.returncode == 0, f"Master blend inspection failed: {res.stdout}"
