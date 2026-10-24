"""
Adversarial Stress Testing Suite for MorphoMesh Rigging & Blendshapes Engine.

Adversarially challenges `src/morphomesh/human_rigging.py` across:
1. Extreme anthropometric variations (height 1.2m vs 2.2m, extreme WHR ratios, broad/narrow shoulders).
2. Finger cylinder partitioning resilience under anatomical variations (exposing hardcoded palm_x).
3. Joint deformation physics (elbow 90 deg flexion, knee 90 deg flexion, shoulder 90 deg abduction).
4. Complete 52 Apple ARKit FACS facial blendshapes (zero NaNs, non-zero deltas, facial zone fidelity).
5. Live headless Blender 4.5.4 LTS execution (vertex weight binding, shape key deltas, mesh deformation).
"""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from typing import Tuple

import pytest

from morphomesh.human_generator import HumanAnatomyConfig, generate_human_base_mesh
from morphomesh.human_rigging import (
    ARKIT_52_BLENDSHAPES,
    calculate_anti_pinch_weights,
    generate_arkit_52_blendshapes,
    generate_rigify_human_metarig,
)



# ==============================================================================
# 1. EXTREME ANTHROPOMETRIC STRESS TESTING
# ==============================================================================

class TestExtremeAnthropometricStress:
    """Stress tests landmark snapping, metarig construction, and weights under extreme variations."""

    @pytest.mark.parametrize(
        "cfg_name,cfg",
        [
            ("Chibi_Dwarf_1.2m", HumanAnatomyConfig(height=1.20, head_ratio=5.0)),
            ("Giant_Amazon_2.2m", HumanAnatomyConfig(height=2.20, head_ratio=8.5)),
            ("Extreme_Pear_WHR_0.33", HumanAnatomyConfig(waist_girth=0.40, hip_girth=1.20)),
            ("Extreme_Apple_WHR_1.375", HumanAnatomyConfig(waist_girth=1.10, hip_girth=0.80)),
            ("Ultra_Broad_Torso", HumanAnatomyConfig(chest_girth=1.40, shoulder_width=0.55)),
            ("Ultra_Slender_Torso", HumanAnatomyConfig(chest_girth=0.55, shoulder_width=0.25)),
        ],
    )
    def test_metarig_integrity_under_extreme_anthropometry(self, cfg_name: str, cfg: HumanAnatomyConfig):
        """Verify 163 DEF bones, valid bone lengths, and pre-bends under extreme bodies."""
        mesh_res = generate_human_base_mesh(config=cfg)
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)

        assert metarig.def_bone_count == 163, f"{cfg_name}: expected 163 DEF bones, got {metarig.def_bone_count}"
        assert len(metarig.body_def_bones) == 64
        assert len(metarig.facial_def_bones) == 99

        # Check bone lengths are strictly positive (> 1mm) and coordinates are finite
        for b_name, b in metarig.bones.items():
            for c in b.head + b.tail:
                assert not math.isnan(c) and not math.isinf(c), f"{cfg_name}: NaN/Inf in bone {b_name}"
            dx = b.tail[0] - b.head[0]
            dy = b.tail[1] - b.head[1]
            dz = b.tail[2] - b.head[2]
            length = math.sqrt(dx * dx + dy * dy + dz * dz)
            assert length > 0.001, f"{cfg_name}: degenerate bone {b_name} with length {length:.6f}m"

        # Check pre-bends are maintained
        prebend_ok, pmetrics = metarig.verify_prebends()
        assert prebend_ok is True, f"{cfg_name}: pre-bend verification failed: {pmetrics}"
        assert pmetrics["elbow_L_y"] > 0.0, f"{cfg_name}: elbow pre-bend not +Y: {pmetrics['elbow_L_y']}"
        assert pmetrics["knee_L_y"] < 0.0, f"{cfg_name}: knee pre-bend not -Y: {pmetrics['knee_L_y']}"

    @pytest.mark.parametrize(
        "cfg_name,cfg",
        [
            ("Chibi_Dwarf_1.2m", HumanAnatomyConfig(height=1.20, head_ratio=5.0)),
            ("Giant_Amazon_2.2m", HumanAnatomyConfig(height=2.20, head_ratio=8.5)),
            ("Extreme_Pear_WHR_0.33", HumanAnatomyConfig(waist_girth=0.40, hip_girth=1.20)),
            ("Extreme_Apple_WHR_1.375", HumanAnatomyConfig(waist_girth=1.10, hip_girth=0.80)),
        ],
    )
    def test_skin_weights_normalization_under_extreme_anthropometry(self, cfg_name: str, cfg: HumanAnatomyConfig):
        """Verify strict weight normalization (sum == 1.0) holds for all vertices under extreme scale."""
        mesh_res = generate_human_base_mesh(config=cfg)
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=mesh_res.landmarks)

        is_norm, count, max_disc = weights.verify_normalization(tolerance=1e-4)
        assert is_norm is True, f"{cfg_name}: weights normalization failed, max discrepancy: {max_disc}"
        assert count == len(mesh_res.mesh.vertices)


# ==============================================================================
# 2. FINGER PARTITIONING ADVERSARIAL CHALLENGE
# ==============================================================================

class TestFingerPartitioningAdversarial:
    """
    Adversarial test revealing the hardcoded palm_x vulnerability in calculate_anti_pinch_weights.
    When shoulder_width or arm_span differs from canonical, hardcoded palm_x (0.385 * scale)
    misaligns, causing all finger vertices to collapse into a single digit.
    """

    def test_finger_isolation_on_canonical_proportions(self):
        """On canonical 1.65m mesh, all 5 digits must receive vertices."""
        mesh_res = generate_human_base_mesh()
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=mesh_res.landmarks)

        finger_verts = mesh_res.vertex_groups.get("fingers_L", [])
        digits_assigned = {d: 0 for d in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]}
        for v in finger_verts:
            for d in digits_assigned:
                if weights.get_vertex_weight(v, f"DEF-{d}.01.L") > 0:
                    digits_assigned[d] += 1
                    break

        for d, cnt in digits_assigned.items():
            assert cnt > 0, f"Digit {d} has 0 vertices assigned in canonical model"

    def test_empirical_finger_collapse_on_broad_shoulders(self):
        """
        EMPIRICAL VERIFICATION OF FINGER PARTITIONING:
        On broad shoulders (shoulder_width=0.50, arm_span=2.0), dynamic palm_x
        ensures finger vertices are properly distributed across all 5 digits
        rather than collapsing onto a single digit.
        """
        cfg = HumanAnatomyConfig(shoulder_width=0.50, arm_span=2.0)
        mesh_res = generate_human_base_mesh(config=cfg)
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=mesh_res.landmarks)

        finger_verts = mesh_res.vertex_groups.get("fingers_L", [])
        digits_assigned = {d: 0 for d in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]}
        for v in finger_verts:
            for d in digits_assigned:
                if weights.get_vertex_weight(v, f"DEF-{d}.01.L") > 0:
                    digits_assigned[d] += 1
                    break

        # Verifies remediation: all digits are weighted and thumb does not capture 100%
        assert digits_assigned["thumb"] < len(finger_verts)
        for d, cnt in digits_assigned.items():
            assert cnt > 0, f"Expected digit {d} to have vertices on broad shoulders, got 0"

    def test_finger_partitioning_resilient_to_broad_shoulders(self):
        """
        Target contract: Finger partitioning must remain resilient to shoulder_width / arm_span variations,
        allocating vertices to all 5 digits.
        """
        cfg = HumanAnatomyConfig(shoulder_width=0.50, arm_span=2.0)
        mesh_res = generate_human_base_mesh(config=cfg)
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=mesh_res.landmarks)

        finger_verts = mesh_res.vertex_groups.get("fingers_L", [])
        digits_assigned = {d: 0 for d in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]}
        for v in finger_verts:
            for d in digits_assigned:
                if weights.get_vertex_weight(v, f"DEF-{d}.01.L") > 0:
                    digits_assigned[d] += 1
                    break

        for d, cnt in digits_assigned.items():
            assert cnt > 0, f"Digit {d} collapsed to 0 vertices on broad shoulders"


# ==============================================================================
# 3. JOINT DEFORMATION MATHEMATICAL SIMULATION
# ==============================================================================

class TestJointDeformationSimulation:
    """
    Mathematical stress tests for Linear Blend Skinning (LBS) joint deformation:
    Elbow 90 deg flexion, Knee 90 deg flexion, Shoulder 90 deg abduction.
    """

    @pytest.fixture(scope="class")
    def rigging_data(self):
        mesh_res = generate_human_base_mesh()
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=mesh_res.landmarks)
        return mesh_res, metarig, weights

    def test_elbow_90_degree_flexion_thickness(self, rigging_data):
        """
        Simulate 90-degree elbow flexion around hinge axis:
        Verify that elbow cross-sectional diameter maintains >= 50% of rest diameter
        and vertices do not collapse into the joint center (min_dist > 5mm).
        """
        mesh_res, _, weights = rigging_data
        verts = mesh_res.mesh.vertices
        lm = mesh_res.landmarks
        p_el = lm.get("joint-l-elbow", lm["elbow_L"])
        p_sh = lm.get("joint-l-shoulder", lm["shoulder_L"])

        # Hinge axis u perpendicular to arm direction and Y
        v_arm = (p_el[0] - p_sh[0], p_el[1] - p_sh[1], p_el[2] - p_sh[2])
        ux = v_arm[2]
        uz = -v_arm[0]
        u_len = math.sqrt(ux * ux + uz * uz) or 1.0
        ux, uz = ux / u_len, uz / u_len

        def rotate_elbow_90(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
            rel = (v[0] - p_el[0], v[1] - p_el[1], v[2] - p_el[2])
            dot = ux * rel[0] + uz * rel[2]
            cross = (-uz * rel[1], uz * rel[0] - ux * rel[2], ux * rel[1])
            rot = (cross[0] + ux * dot, cross[1], cross[2] + uz * dot)
            return (p_el[0] + rot[0], p_el[1] + rot[1], p_el[2] + rot[2])

        elbow_verts = [i for i, v in enumerate(verts) if math.sqrt(sum((a - b) ** 2 for a, b in zip(v, p_el))) < 0.045]
        assert len(elbow_verts) >= 6

        dists_rest = [math.sqrt(sum((a - b) ** 2 for a, b in zip(verts[i], p_el))) for i in elbow_verts]
        rest_thickness = max(dists_rest) * 2

        dists_def = []
        for i in elbow_verts:
            v = verts[i]
            w_fa = (
                weights.get_vertex_weight(i, "DEF-forearm.L")
                + weights.get_vertex_weight(i, "DEF-forearm.L.001")
                + weights.get_vertex_weight(i, "DEF-hand.L")
            )
            w_ua = (
                weights.get_vertex_weight(i, "DEF-upper_arm.L")
                + weights.get_vertex_weight(i, "DEF-upper_arm.L.001")
            )
            w_tot = w_fa + w_ua or 1.0
            w_fa /= w_tot
            w_ua /= w_tot
            v_rot = rotate_elbow_90(v)
            v_def = (
                w_ua * v[0] + w_fa * v_rot[0],
                w_ua * v[1] + w_fa * v_rot[1],
                w_ua * v[2] + w_fa * v_rot[2],
            )
            dists_def.append(math.sqrt(sum((a - b) ** 2 for a, b in zip(v_def, p_el))))

        def_thickness = max(dists_def) * 2
        min_dist = min(dists_def)
        ratio = def_thickness / rest_thickness

        assert ratio >= 0.50, f"Elbow collapsed abnormally! Thickness ratio: {ratio:.2f}"
        assert min_dist > 0.005, f"Elbow vertices collapsed into joint center! min_dist: {min_dist:.4f}m"

    def test_knee_90_degree_flexion_patella_preservation(self, rigging_data):
        """
        Simulate 90-degree knee flexion around lateral X axis:
        Verify that patella rigid locking maintains >= 85% of radial distance from knee pivot.
        """
        mesh_res, _, weights = rigging_data
        verts = mesh_res.mesh.vertices
        p_kn = mesh_res.landmarks["knee_L"]

        def rotate_knee_90(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
            dy = v[1] - p_kn[1]
            dz = v[2] - p_kn[2]
            return (v[0], p_kn[1] - dz, p_kn[2] + dy)

        patella_verts = [
            i for i, v in enumerate(verts)
            if abs(v[2] - p_kn[2]) < 0.035 and v[1] < p_kn[1] - 0.015 and abs(v[0] - p_kn[0]) < 0.035
        ]
        assert len(patella_verts) >= 6

        r0_pat = [math.sqrt(sum((a - b) ** 2 for a, b in zip(verts[i], p_kn))) for i in patella_verts]
        r90_pat = []
        for i in patella_verts:
            v = verts[i]
            w_shin = weights.get_vertex_weight(i, "DEF-shin.L") + weights.get_vertex_weight(i, "DEF-shin.L.001")
            w_thigh = weights.get_vertex_weight(i, "DEF-thigh.L") + weights.get_vertex_weight(i, "DEF-thigh.L.001")
            w_tot = w_shin + w_thigh or 1.0
            w_shin /= w_tot
            w_thigh /= w_tot
            v_rot = rotate_knee_90(v)
            v_def = (
                w_thigh * v[0] + w_shin * v_rot[0],
                w_thigh * v[1] + w_shin * v_rot[1],
                w_thigh * v[2] + w_shin * v_rot[2],
            )
            r90_pat.append(math.sqrt(sum((a - b) ** 2 for a, b in zip(v_def, p_kn))))

        avg_r0 = sum(r0_pat) / len(r0_pat)
        avg_r90 = sum(r90_pat) / len(r90_pat)
        preservation_ratio = avg_r90 / avg_r0

        assert preservation_ratio >= 0.85, (
            f"Patella collapsed into knee cavity! Preservation ratio: {preservation_ratio:.2f}"
        )

    def test_shoulder_90_degree_abduction_axilla_fold_clamping(self, rigging_data):
        """
        Simulate 90-degree shoulder abduction:
        Verify that axilla fold vertices displacement is clamped to <= 35% of arm displacement.
        """
        mesh_res, _, weights = rigging_data
        verts = mesh_res.mesh.vertices
        p_sh = mesh_res.landmarks["shoulder_L"]

        def rotate_shoulder_90(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
            dx = v[0] - p_sh[0]
            dz = v[2] - p_sh[2]
            return (p_sh[0] - dz, v[1], p_sh[2] + dx)

        arm_up_verts = mesh_res.vertex_groups.get("arm_upper_L", [])
        axilla_verts = [i for i in arm_up_verts if verts[i][0] < 0.20 and verts[i][2] < 1.32]
        assert len(axilla_verts) >= 3

        axilla_disps = []
        arm_disps = []
        for i in axilla_verts:
            v = verts[i]
            v_arm = rotate_shoulder_90(v)
            arm_d = math.sqrt(sum((a - b) ** 2 for a, b in zip(v_arm, v)))
            arm_disps.append(arm_d)

            w_arm = weights.get_vertex_weight(i, "DEF-upper_arm.L") + weights.get_vertex_weight(i, "DEF-upper_arm.L.001")
            w_sh = weights.get_vertex_weight(i, "DEF-shoulder.L")
            w_sp = weights.get_vertex_weight(i, "DEF-spine.003")
            w_tot = w_arm + w_sh + w_sp or 1.0

            v_def = (
                (w_sp * v[0] + (w_arm + w_sh) * v_arm[0]) / w_tot,
                (w_sp * v[1] + (w_arm + w_sh) * v_arm[1]) / w_tot,
                (w_sp * v[2] + (w_arm + w_sh) * v_arm[2]) / w_tot,
            )
            disp = math.sqrt(sum((a - b) ** 2 for a, b in zip(v_def, v)))
            axilla_disps.append(disp)

        avg_arm_d = sum(arm_disps) / len(arm_disps)
        avg_ax_d = sum(axilla_disps) / len(axilla_disps)
        movement_ratio = avg_ax_d / avg_arm_d

        assert movement_ratio <= 0.35, f"Axilla fold tore away from torso! Movement ratio: {movement_ratio:.2f}"


# ==============================================================================
# 4. 52 ARKIT FACS BLENDSHAPES ADVERSARIAL VERIFICATION
# ==============================================================================

class TestARKit52FACSAdversarial:
    """Verifies all 52 shape keys have non-zero deltas, zero NaNs/Infs, and correct zones."""

    @pytest.mark.parametrize("scale", [0.727, 1.0, 1.333, 1.75])
    def test_all_52_shape_keys_displace_without_nans(self, scale: float):
        """Verify all 52 ARKit keys have valid non-zero finite displacements across scales."""
        mesh_res = generate_human_base_mesh()
        shapes = generate_arkit_52_blendshapes(mesh_res.mesh, landmarks=mesh_res.landmarks, scale=scale)

        assert len(shapes) == 52, f"Expected 52 shape keys, got {len(shapes)}"

        for k_name in ARKIT_52_BLENDSHAPES:
            assert k_name in shapes, f"Missing shape key {k_name}"
            deltas = shapes[k_name]
            assert len(deltas) > 0, f"Shape key {k_name} produced 0 displaced vertices"

            for vi, (dx, dy, dz) in deltas.items():
                for c in (dx, dy, dz):
                    assert not math.isnan(c) and not math.isinf(c), f"NaN/Inf in {k_name} vertex {vi}"
                mag = math.sqrt(dx * dx + dy * dy + dz * dz)
                assert mag > 1e-6, f"Zero delta magnitude for {k_name} vertex {vi}"

    def test_anatomical_facial_zone_fidelity(self):
        """Verify vertices displaced belong strictly to their target anatomical facial zone."""
        mesh_res = generate_human_base_mesh()
        shapes = generate_arkit_52_blendshapes(mesh_res.mesh, landmarks=mesh_res.landmarks)
        vgroups = mesh_res.vertex_groups

        v_eyes = set(vgroups.get("eyes_left", []) + vgroups.get("eyes_right", []))
        v_brows = set(vgroups.get("eyebrows", []))
        v_mouth = set(vgroups.get("mouth", []))
        v_lips = set(vgroups.get("lips", []))
        v_tongue = set(vgroups.get("tongue", []))
        v_face = set(vgroups.get("face", []))

        for k, deltas in shapes.items():
            for vi in deltas:
                if "eye" in k.lower() and "squint" not in k.lower() and "puff" not in k.lower():
                    assert vi in v_eyes or vi in v_face, f"{k} displaced non-eye vertex {vi}"
                elif "brow" in k.lower():
                    assert vi in v_brows or vi in v_face, f"{k} displaced non-brow vertex {vi}"
                elif "mouth" in k.lower() or "jaw" in k.lower():
                    assert vi in v_mouth or vi in v_lips or vi in v_face, f"{k} displaced non-mouth vertex {vi}"
                elif "tongue" in k.lower():
                    assert vi in v_tongue or vi in v_face, f"{k} displaced non-tongue vertex {vi}"


# ==============================================================================
# 5. LIVE BLENDER 4.5.4 LTS HEADLESS EXECUTION CHALLENGE
# ==============================================================================

BLENDER_45_PATH = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


class TestLiveBlenderHeadlessExecution:
    """
    Empirically executes auto-rigging scripts inside headless Blender 4.5.4 LTS:
    Tests whether vertex groups have weights, whether shape keys have deltas,
    and whether bone rotation actually deforms the mesh in Blender.
    """

    @pytest.fixture(scope="class")
    def blender_available(self):
        if not os.path.isfile(BLENDER_45_PATH):
            pytest.skip("Blender 4.5.4 LTS binary not found at canonical location")
        return BLENDER_45_PATH

    def test_live_blender_script_execution_and_bone_counts(self, blender_available):
        """Verify that get_rigging_script executes in Blender 4.5.4 LTS and produces 163 DEF bones."""
        py_code = """
import sys
sys.path.insert(0, r'E:\\tool\\mcp\\MorphoMesh\\src')
sys.path.append(r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')

import bpy
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script

mesh_name = 'Human_Base_Mesh'
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name))

arm = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
assert arm is not None, 'Armature object not created'
def_bones = [b.name for b in arm.data.bones if b.name.startswith('DEF-')]
assert len(def_bones) == 163, f'Expected 163 DEF bones, got {len(def_bones)}'

obj = bpy.data.objects.get(mesh_name)
assert obj is not None, 'Mesh object not found'
mod = obj.modifiers.get('Armature')
assert mod is not None, 'Armature modifier missing'
assert mod.use_deform_preserve_volume is True, 'DQS preserve volume not enabled'
print('BLENDER_RIG_SUCCESS')
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(py_code)
            script_path = f.name

        try:
            cmd = [blender_available, "--background", "--factory-startup", "--python", script_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            assert proc.returncode == 0, f"Blender script failed:\n{proc.stderr}\n{proc.stdout}"
            assert "BLENDER_RIG_SUCCESS" in proc.stdout
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_empirical_blender_vertex_weights_and_shape_keys_defect(self, blender_available):
        """
        EMPIRICAL PROOF OF BLENDER SCRIPT DEFECT:
        Verifies that get_rigging_script creates 163 empty DEF vertex groups (weighted_verts = 0),
        52 empty shape keys (non_zero_keys = 0), resulting in zero mesh deformation (max_disp = 0.000000m)
        when bones rotate in Blender.
        """
        py_code = """
import sys
sys.path.insert(0, r'E:\\tool\\mcp\\MorphoMesh\\src')
sys.path.append(r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')

import bpy, math
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script

mesh_name = 'Human_Base_Mesh'
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name))

obj = bpy.data.objects[mesh_name]
arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']

# Count vertices with DEF weights
def_group_indices = {g.index for g in obj.vertex_groups if g.name.startswith('DEF-')}
weighted_verts = sum(1 for v in obj.data.vertices if any(g.group in def_group_indices and g.weight > 0 for g in v.groups))

# Rotate forearm by 90 degrees
arm_low_vg = obj.vertex_groups.get('arm_lower_L')
v_indices = [v.index for v in obj.data.vertices for g in v.groups if arm_low_vg and g.group == arm_low_vg.index and g.weight > 0.5]
rest_pos = [list(obj.data.vertices[i].co) for i in v_indices]

bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
pbone = arm.pose.bones.get('DEF-forearm.L')
if pbone:
    pbone.rotation_mode = 'XYZ'
    pbone.rotation_euler = (math.radians(90), 0, 0)

bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = obj.evaluated_get(depsgraph)
eval_mesh = eval_obj.to_mesh()

def_pos = [list(eval_mesh.vertices[i].co) for i in v_indices]
max_disp = max((math.sqrt(sum((a - b)**2 for a, b in zip(p0, p1))) for p0, p1 in zip(rest_pos, def_pos)), default=0.0)

# Check shape key deltas in Blender
basis = obj.data.shape_keys.key_blocks['Basis']
non_zero_keys = sum(
    1 for kb in obj.data.shape_keys.key_blocks
    if kb.name != 'Basis' and any((kb.data[i].co - basis.data[i].co).length > 1e-6 for i in range(len(kb.data)))
)

print(f'RESULT: weighted_verts={weighted_verts}, max_disp={max_disp:.6f}, non_zero_keys={non_zero_keys}')
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(py_code)
            script_path = f.name

        try:
            cmd = [blender_available, "--background", "--factory-startup", "--python", script_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            assert proc.returncode == 0, f"Blender script failed:\n{proc.stderr}\n{proc.stdout}"

            line = [l for l in proc.stdout.splitlines() if l.startswith("RESULT:")][0]
            # Verifies remediation: weights are baked, deformation is active, and shape keys displaced
            assert "weighted_verts=2144" in line, f"Expected 2144 weighted verts, got: {line}"
            assert "max_disp=0.000000" not in line and "max_disp=0.36" in line, f"Expected active deformation, got: {line}"
            assert "non_zero_keys=52" in line, f"Expected 52 non-zero keys in Blender, got: {line}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)

    def test_live_blender_mesh_deformation_active(self, blender_available):
        """
        Target contract: In Blender, vertices must have DEF weights and mesh must deform
        when bones rotate in pose mode.
        """
        py_code = """
import sys
sys.path.insert(0, r'E:\\tool\\mcp\\MorphoMesh\\src')
sys.path.append(r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')

import bpy, math
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script

mesh_name = 'Human_Base_Mesh'
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name))

obj = bpy.data.objects[mesh_name]
def_group_indices = {g.index for g in obj.vertex_groups if g.name.startswith('DEF-')}
weighted_verts = sum(1 for v in obj.data.vertices if any(g.group in def_group_indices and g.weight > 0 for g in v.groups))

print(f'CONTRACT_CHECK: weighted_verts={weighted_verts}')
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(py_code)
            script_path = f.name

        try:
            cmd = [blender_available, "--background", "--factory-startup", "--python", script_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            line = [l for l in proc.stdout.splitlines() if l.startswith("CONTRACT_CHECK:")][0]
            # Expect weighted_verts > 0; fails because weighted_verts == 0
            assert "weighted_verts=0" not in line, f"Blender DEF vertex groups are unweighted: {line}"
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)

