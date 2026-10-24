"""
Empirical Challenger Test Suite for Rigify 163 DEF Rig & Skinning Deformation.
Author: challenger_m1_deformation_volume
Milestone: M1 (Medical-Grade Human Anatomy & Rigify 163 DEF Rigging)

Empirically stress-tests the Rigify 163 DEF rig and skinning deformation
produced by src/morphomesh/human_rigging.py and src/morphomesh/human_generator.py:
1. Strict 163 DEF bone invariant (64 body DEF + 99 facial DEF) across all poses.
2. Mesh volume preservation ratio rho_V = V_posed / V_0 >= 0.92 under 90-degree
   thigh, knee, ankle, and toe flexion (individual and combined).
3. Patella vertex displacement relative to shin bone <= 2.0mm during 90-degree knee flexion.
4. Malleoli vertex displacement relative to lower leg <= 1.5mm during 30-degree foot rotation/flexion.
5. Zero NaN or Infinite vertex coordinates across extreme poses.

Can be executed via:
1. uv run pytest tests/test_empiric_m1_rigging.py -v
2. & 'C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe' --background --factory-startup --python tests/test_empiric_m1_rigging.py
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

# Ensure paths for both standard Python and embedded Blender Python
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
sys.path.append(r"E:\tool\mcp\MorphoMesh\.venv\Lib\site-packages")
sys.path.append(r"C:\Users\Admin\AppData\Local\Programs\Python\Python311\Lib\site-packages")

try:
    import pytest
except ImportError:
    pytest = None

from morphomesh.human_generator import HumanAnatomyConfig, generate_human_base_mesh
from morphomesh.human_rigging import (
    ALL_163_DEF_BONES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    HumanRigConfig,
    calculate_anti_pinch_weights,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
)

BLENDER_45_PATH = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


# ==============================================================================
# 1. STRICT 163 DEF BONE INVARIANT (64 BODY + 99 FACIAL)
# ==============================================================================

class TestEmpiricalRigifyBoneHierarchy:
    """Empirical verification of the strict 163 DEF bone invariant across all poses."""

    def test_strict_163_def_bone_invariant(self):
        """Assert exactly 163 DEF bones (64 body DEF + 99 facial DEF) with strict uniqueness."""
        metarig = generate_rigify_human_metarig()

        assert metarig.def_bone_count == 163, f"Expected 163 DEF bones, got {metarig.def_bone_count}"
        assert len(metarig.body_def_bones) == 64, f"Expected 64 body DEF bones, got {len(metarig.body_def_bones)}"
        assert len(metarig.facial_def_bones) == 99, f"Expected 99 facial DEF bones, got {len(metarig.facial_def_bones)}"
        assert len(metarig.total_def_bones) == 163

        # Uniqueness and prefix validation
        assert len(set(ALL_163_DEF_BONES)) == 163, "Bone names must be strictly unique"
        assert set(BODY_DEF_BONES).isdisjoint(set(FACIAL_DEF_BONES)), "Body and facial sets must be disjoint"
        for b_name in ALL_163_DEF_BONES:
            assert b_name.startswith("DEF-"), f"Deformer bone {b_name} must have 'DEF-' prefix"

    def test_bone_lengths_and_prebends_non_degenerate(self):
        """Assert all 163 DEF bones have non-degenerate lengths (> 1mm) and verified IK pre-bends."""
        mesh_res = generate_human_base_mesh()
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)

        for b_name, b in metarig.bones.items():
            assert b.length > 0.001, f"Bone {b_name} has degenerate length {b.length:.6f}m"
            for coord in b.head + b.tail:
                assert not math.isnan(coord) and not math.isinf(coord), f"NaN/Inf in bone {b_name} coordinates"

        # Pre-bends for Rigify IK solvers (elbow +Y, knee -Y)
        ok, metrics = metarig.verify_prebends()
        assert ok is True, f"Pre-bends verification failed: {metrics}"
        assert metrics["elbow_L_y"] > 0.0, f"Left elbow pre-bend must be > 0 (+Y), got {metrics['elbow_L_y']}"
        assert metrics["knee_L_y"] < 0.0, f"Left knee pre-bend must be < 0 (-Y), got {metrics['knee_L_y']}"


# ==============================================================================
# 2. PURE PYTHON MATHEMATICAL MESH VOLUME & LBS SIMULATION
# ==============================================================================

def compute_mesh_signed_volume(vertices: List[Tuple[float, float, float]], faces: List[List[int]]) -> float:
    """Computes signed enclosed volume of a watertight 3D mesh via divergence theorem."""
    total_vol = 0.0
    for f in faces:
        if len(f) == 3:
            v1 = vertices[f[0]]
            v2 = vertices[f[1]]
            v3 = vertices[f[2]]
            cross = (v2[1] * v3[2] - v2[2] * v3[1], v2[2] * v3[0] - v2[0] * v3[2], v2[0] * v3[1] - v2[1] * v3[0])
            total_vol += (v1[0] * cross[0] + v1[1] * cross[1] + v1[2] * cross[2]) / 6.0
        elif len(f) == 4:
            v1 = vertices[f[0]]
            v2 = vertices[f[1]]
            v3 = vertices[f[2]]
            v4 = vertices[f[3]]
            c1 = (v2[1] * v3[2] - v2[2] * v3[1], v2[2] * v3[0] - v2[0] * v3[2], v2[0] * v3[1] - v2[1] * v3[0])
            total_vol += (v1[0] * c1[0] + v1[1] * c1[1] + v1[2] * c1[2]) / 6.0
            c2 = (v3[1] * v4[2] - v3[2] * v4[1], v3[2] * v4[0] - v3[0] * v4[2], v3[0] * v4[1] - v3[1] * v4[0])
            total_vol += (v1[0] * c2[0] + v1[1] * c2[1] + v1[2] * c2[2]) / 6.0
    return abs(total_vol)


class TestPurePythonMathematicalVolume:
    """Pure-Python empirical test of rest mesh volume and skinning weight integrity."""

    def test_canonical_rest_mesh_volume(self):
        """Verify baseline rest mesh volume V_0 is biologically reasonable (~0.050 m^3 = 50 liters)."""
        mesh_res = generate_human_base_mesh()
        v0 = compute_mesh_signed_volume(mesh_res.mesh.vertices, mesh_res.mesh.faces)
        # 50 liters is standard for ~1.65m female body
        assert 0.040 <= v0 <= 0.065, f"Rest mesh volume V_0={v0:.6f}m^3 is outside physiological range (40-65L)"

    def test_skin_weights_strict_normalization(self):
        """Verify anti-pinch skin weights sum strictly to 1.0 (discrepancy < 1e-4) for all vertices."""
        mesh_res = generate_human_base_mesh()
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, mesh_res.landmarks)

        is_norm, count, max_disc = weights.verify_normalization(tolerance=1e-4)
        assert is_norm is True, f"Weights normalization failed with max discrepancy {max_disc}"
        assert count == len(mesh_res.mesh.vertices)

    def test_plantar_arch_and_toenail_weight_isolation(self):
        """
        Verify plantar arch and toenail vertex groups have strict weight isolation:
        - Arch vertices: 100% DEF-foot (0% DEF-shin) to prevent arch flattening and tibia pinning.
        - Toenail vertices: 100% DEF-toe to prevent nail distortion during toe flexion.
        """
        mesh_res = generate_human_base_mesh()
        vg = mesh_res.vertex_groups
        metarig = generate_rigify_human_metarig(landmarks=mesh_res.landmarks)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, mesh_res.landmarks)

        assert "plantar_arch_L" in vg and len(vg["plantar_arch_L"]) in (40, 51, 52)
        assert "plantar_arch_R" in vg and len(vg["plantar_arch_R"]) in (40, 51, 52)

        for side in ["L", "R"]:
            arch_verts = vg[f"plantar_arch_{side}"]
            shin_bone = f"DEF-shin.{side}.001"
            foot_bone = f"DEF-foot.{side}"

            shin_w = [weights.weights[vi].get(shin_bone, 0.0) for vi in arch_verts]
            foot_w = [weights.weights[vi].get(foot_bone, 0.0) for vi in arch_verts]

            assert max(shin_w) < 1e-6, f"Plantar arch {side} vertices have shin weight bleed (max={max(shin_w)})"
            assert min(foot_w) > 0.999, f"Plantar arch {side} vertices must have 100% DEF-foot weight (min={min(foot_w)})"

        # Toenails isolation
        for side in ["L", "R"]:
            tn_key = f"toenails_{side}"
            if tn_key in vg:
                toe_bone = f"DEF-toe.{side}"
                toe_w = [weights.weights[vi].get(toe_bone, 0.0) for vi in vg[tn_key]]
                assert min(toe_w) > 0.999, f"Toenails {side} must have 100% DEF-toe weight"


# ==============================================================================
# 3. LIVE BLENDER HEADLESS DEPSGRAPH VERIFICATION HARNESS
# ==============================================================================

class TestLiveBlenderDeformationEmpirics:
    """
    Empirically executes headless Blender 4.5.4 LTS to evaluate the evaluated depsgraph mesh:
    - Volume ratio rho_V >= 0.92 under 90-degree thigh, knee, ankle, and toe flexion
    - Patella vertex displacement relative to shin bone <= 2.0mm during 90-degree knee flexion
    - Malleoli vertex displacement relative to lower leg <= 1.5mm during 30-degree foot rotation/flexion
    - Zero NaN or Infinite vertex coordinates under extreme poses
    - Strict 163 DEF bone invariant across all poses
    """

    @pytest.fixture(scope="class")
    def blender_bin(self) -> str:
        if not os.path.isfile(BLENDER_45_PATH):
            pytest.skip(f"Blender binary not found at {BLENDER_45_PATH}")
        return BLENDER_45_PATH

    def test_live_blender_empirical_metrics(self, blender_bin: str):
        """
        Runs comprehensive deformation and volume analysis in live Blender depsgraph:
        Extracts structured JSON metrics report and asserts all pass criteria.
        """
        py_harness = """
import sys
sys.path.insert(0, r'E:\\tool\\mcp\\MorphoMesh\\src')
sys.path.append(r'E:\\tool\\mcp\\MorphoMesh\\.venv\\Lib\\site-packages')
sys.path.append(r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')

import bpy
import bmesh
import json
import math

from morphomesh.human_generator import generate_human_base_mesh, get_human_generation_script
from morphomesh.human_rigging import get_rigging_script

mesh_name = 'Human_Base_Mesh'
mesh_res = generate_human_base_mesh()
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name, landmarks=mesh_res.landmarks))

obj = bpy.data.objects[mesh_name]
arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']

# 1. Check 163 DEF Bone Invariant
def_bones = [b.name for b in arm.data.bones if b.name.startswith('DEF-')]
body_def = [b for b in def_bones if not any(x in b for x in ['brow', 'cheek', 'chin', 'ear', 'forehead', 'jaw', 'lid', 'lip', 'nose', 'temple', 'tongue'])]
# Precise categorization
facial_prefixes = ['DEF-brow.', 'DEF-cheek.', 'DEF-chin.', 'DEF-ear.', 'DEF-forehead.', 'DEF-jaw.', 'DEF-lid.', 'DEF-lip.', 'DEF-nose.', 'DEF-temple.', 'DEF-tongue.']
facial_def_list = [b for b in def_bones if any(b.startswith(p) for p in facial_prefixes)]
body_def_list = [b for b in def_bones if b not in facial_def_list]

bone_report = {
    'total_def_bones': len(def_bones),
    'body_def_bones': len(body_def_list),
    'facial_def_bones': len(facial_def_list),
}

# 2. Baseline Rest Mesh Volume V_0
bm0 = bmesh.new()
bm0.from_mesh(obj.data)
v0 = bm0.calc_volume()
bm0.free()

def get_evaluated_volume_and_coords():
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(dg)
    eval_mesh = eval_obj.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    vol = bm.calc_volume()
    bm.free()
    coords = [v.co.copy() for v in eval_mesh.vertices]
    eval_obj.to_mesh_clear()
    return vol, coords

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

def reset_all_pose_bones():
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()

reset_all_pose_bones()

# 3. Flexion Volume Ratios
volume_metrics = {'v0': v0}

# 3a. Thigh 90-deg flexion
reset_all_pose_bones()
thigh = arm.pose.bones['DEF-thigh.L']
thigh.rotation_euler = (math.radians(-90), 0, 0)
v_thigh, _ = get_evaluated_volume_and_coords()
volume_metrics['thigh_90_vol'] = v_thigh
volume_metrics['thigh_90_ratio'] = v_thigh / v0

# 3b. Knee 90-deg flexion
reset_all_pose_bones()
knee = arm.pose.bones['DEF-shin.L']
knee.rotation_euler = (math.radians(90), 0, 0)
v_knee, _ = get_evaluated_volume_and_coords()
volume_metrics['knee_90_vol'] = v_knee
volume_metrics['knee_90_ratio'] = v_knee / v0

# 3c. Ankle 90-deg flexion
reset_all_pose_bones()
ankle = arm.pose.bones['DEF-foot.L']
ankle.rotation_euler = (math.radians(-90), 0, 0)
v_ankle, _ = get_evaluated_volume_and_coords()
volume_metrics['ankle_90_vol'] = v_ankle
volume_metrics['ankle_90_ratio'] = v_ankle / v0

# 3d. Toe 90-deg flexion
reset_all_pose_bones()
toe = arm.pose.bones['DEF-toe.L']
toe.rotation_euler = (math.radians(90), 0, 0)
v_toe, _ = get_evaluated_volume_and_coords()
volume_metrics['toe_90_vol'] = v_toe
volume_metrics['toe_90_ratio'] = v_toe / v0

# 3e. Combined 90-deg flexion (Thigh + Knee + Ankle + Toe)
reset_all_pose_bones()
thigh.rotation_euler = (math.radians(-90), 0, 0)
knee.rotation_euler = (math.radians(90), 0, 0)
ankle.rotation_euler = (math.radians(-90), 0, 0)
toe.rotation_euler = (math.radians(90), 0, 0)
v_comb, _ = get_evaluated_volume_and_coords()
volume_metrics['combined_90_vol'] = v_comb
volume_metrics['combined_90_ratio'] = v_comb / v0

# 4. Patella Vertex Displacement Relative to Shin Bone
reset_all_pose_bones()
coords_rest = [v.co.copy() for v in obj.data.vertices]
patella_verts = [
    i for i, v in enumerate(coords_rest)
    if abs(v[0] - 0.100) < 0.035 and abs(v[2] - 0.470) < 0.035 and v[1] < -0.025
]

shin_pb = arm.pose.bones['DEF-shin.L']
shin_rest_mat_inv = shin_pb.matrix.inverted()
local_rest_patella = [shin_rest_mat_inv @ coords_rest[i] for i in patella_verts]

# Rotate knee 90 degrees
knee.rotation_euler = (math.radians(90), 0, 0)
_, eval_coords_knee = get_evaluated_volume_and_coords()
shin_posed_mat_inv = shin_pb.matrix.inverted()
local_posed_patella = [shin_posed_mat_inv @ eval_coords_knee[i] for i in patella_verts]

patella_disps_mm = [
    (p_pos - p_rst).length * 1000.0
    for p_rst, p_pos in zip(local_rest_patella, local_posed_patella)
]
patella_metrics = {
    'count': len(patella_verts),
    'max_disp_mm': max(patella_disps_mm),
    'mean_disp_mm': sum(patella_disps_mm) / len(patella_disps_mm),
}

# 5. Malleoli Vertex Displacement Relative to Lower Leg (30-deg Foot Rotation/Flexion)
reset_all_pose_bones()
# Medial and lateral malleoli apex vertices on Left and Right
malleoli_metrics = {}
for side in ['L', 'R']:
    sign = 1.0 if side == 'L' else -1.0
    ring = [i for i, c in enumerate(coords_rest) if abs(c[2] - 0.082) < 0.002 and (c[0] * sign) > 0.03]
    med_apex = min(ring, key=lambda i: coords_rest[i][0] * sign)
    lat_apex = max(ring, key=lambda i: coords_rest[i][0] * sign)
    malleoli_verts = [med_apex, lat_apex]

    shin1_pb = arm.pose.bones[f'DEF-shin.{side}.001']
    foot_pb = arm.pose.bones[f'DEF-foot.{side}']

    shin1_rest_mat_inv = shin1_pb.matrix.inverted()
    local_rest_malleoli = [shin1_rest_mat_inv @ coords_rest[i] for i in malleoli_verts]

    # Rotate foot 30 degrees (flexion +30 deg)
    foot_pb.rotation_euler = (math.radians(30), 0, 0)
    _, eval_coords_foot = get_evaluated_volume_and_coords()

    shin1_posed_mat_inv = shin1_pb.matrix.inverted()
    local_posed_malleoli = [shin1_posed_mat_inv @ eval_coords_foot[i] for i in malleoli_verts]

    mal_disps_mm = [
        (p_pos - p_rst).length * 1000.0
        for p_rst, p_pos in zip(local_rest_malleoli, local_posed_malleoli)
    ]
    malleoli_metrics[f'side_{side}'] = {
        'vertices': malleoli_verts,
        'max_disp_mm': max(mal_disps_mm),
        'mean_disp_mm': sum(mal_disps_mm) / len(mal_disps_mm),
    }

# 6. Zero NaN/Inf under Extreme Poses
reset_all_pose_bones()
extreme_poses = [
    # Crouch / Acute flexion
    {'DEF-thigh.L': (-2.09, 0, 0), 'DEF-shin.L': (2.35, 0, 0), 'DEF-foot.L': (-0.78, 0, 0)},
    # Hyper-extension and twist
    {'DEF-thigh.R': (1.05, 0, 0.52), 'DEF-shin.R': (-0.35, 0, 0), 'DEF-spine.002': (0, 0.78, 0.52)},
    # Full arm overhead and abduction
    {'DEF-upper_arm.L': (0, 0, 2.09), 'DEF-forearm.L': (0, 1.57, 0)},
]

extreme_coords_count = 0
nan_count = 0
inf_count = 0

for pose_dict in extreme_poses:
    reset_all_pose_bones()
    for b_name, rot in pose_dict.items():
        pb = arm.pose.bones.get(b_name)
        if pb:
            pb.rotation_euler = rot
    _, eval_coords_ext = get_evaluated_volume_and_coords()
    extreme_coords_count += len(eval_coords_ext)
    for c in eval_coords_ext:
        for val in (c[0], c[1], c[2]):
            if math.isnan(val):
                nan_count += 1
            if math.isinf(val):
                inf_count += 1

extreme_metrics = {
    'total_evaluated_vertices': extreme_coords_count,
    'nan_count': nan_count,
    'inf_count': inf_count,
}

full_report = {
    'bone_invariant': bone_report,
    'volume': volume_metrics,
    'patella': patella_metrics,
    'malleoli': malleoli_metrics,
    'extreme_poses': extreme_metrics,
}

print('EMPIRICAL_REPORT_JSON_START')
print(json.dumps(full_report))
print('EMPIRICAL_REPORT_JSON_END')
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(py_harness)
            script_path = f.name

        try:
            cmd = [blender_bin, "--background", "--factory-startup", "--python", script_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            assert proc.returncode == 0, f"Blender execution failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

            assert "EMPIRICAL_REPORT_JSON_START" in proc.stdout
            raw_json = proc.stdout.split("EMPIRICAL_REPORT_JSON_START")[1].split("EMPIRICAL_REPORT_JSON_END")[0].strip()
            data = json.loads(raw_json)

            # 1. Assert Strict 163 DEF Bone Invariant
            b_info = data["bone_invariant"]
            assert b_info["total_def_bones"] == 163, f"Expected 163 DEF bones, got {b_info['total_def_bones']}"
            assert b_info["body_def_bones"] == 64, f"Expected 64 body DEF bones, got {b_info['body_def_bones']}"
            assert b_info["facial_def_bones"] == 99, f"Expected 99 facial DEF bones, got {b_info['facial_def_bones']}"

            # 2. Assert Volume Preservation Ratios >= 0.92
            vol = data["volume"]
            assert vol["thigh_90_ratio"] >= 0.92, f"Thigh 90-deg volume ratio {vol['thigh_90_ratio']:.4f} < 0.92"
            assert vol["knee_90_ratio"] >= 0.92, f"Knee 90-deg volume ratio {vol['knee_90_ratio']:.4f} < 0.92"
            assert vol["ankle_90_ratio"] >= 0.92, f"Ankle 90-deg volume ratio {vol['ankle_90_ratio']:.4f} < 0.92"
            assert vol["toe_90_ratio"] >= 0.92, f"Toe 90-deg volume ratio {vol['toe_90_ratio']:.4f} < 0.92"
            assert vol["combined_90_ratio"] >= 0.92, f"Combined 90-deg volume ratio {vol['combined_90_ratio']:.4f} < 0.92"

            # 3. Assert Patella Displacement Relative to Shin Bone <= 2.0 mm
            pat = data["patella"]
            assert pat["count"] > 0, "No patella vertices detected"
            assert pat["max_disp_mm"] <= 2.0, (
                f"Patella max relative displacement {pat['max_disp_mm']:.3f}mm exceeds 2.0mm limit"
            )

            # 4. Assert Malleoli Displacement Relative to Lower Leg <= 1.5 mm
            mal = data["malleoli"]
            for side in ["L", "R"]:
                s_data = mal[f"side_{side}"]
                assert s_data["max_disp_mm"] <= 1.5, (
                    f"Side {side} malleoli displacement {s_data['max_disp_mm']:.3f}mm exceeds 1.5mm limit"
                )

            # 5. Assert Zero NaN / Inf under Extreme Poses
            ext = data["extreme_poses"]
            assert ext["nan_count"] == 0, f"Detected {ext['nan_count']} NaN coordinates under extreme poses"
            assert ext["inf_count"] == 0, f"Detected {ext['inf_count']} Inf coordinates under extreme poses"
            assert ext["total_evaluated_vertices"] > 0

        finally:
            if os.path.exists(script_path):
                os.remove(script_path)


# ==============================================================================
# 4. STANDALONE BLENDER EXECUTION ENTRYPOINT
# ==============================================================================

def run_standalone_blender_audit():
    """Directly executes empirical audit inside Blender without requiring pytest."""
    import bpy
    import bmesh

    print("\n=======================================================")
    print("=== EMPIRICAL CHALLENGER: DIRECT IN-BLENDER AUDIT ===")
    print("=======================================================")

    mesh_name = "Human_Base_Mesh"
    mesh_res = generate_human_base_mesh()
    from morphomesh.human_generator import get_human_generation_script
    from morphomesh.human_rigging import get_rigging_script

    exec(get_human_generation_script(mesh_name), globals())
    exec(get_rigging_script(mesh_name, landmarks=mesh_res.landmarks), globals())

    obj = bpy.data.objects[mesh_name]
    arm = bpy.data.objects["Armature_Yu_Nian_An_Rigify"]

    # 1. 163 DEF Bones Invariant
    def_bones = [b.name for b in arm.data.bones if b.name.startswith("DEF-")]
    facial_prefixes = ['DEF-brow.', 'DEF-cheek.', 'DEF-chin.', 'DEF-ear.', 'DEF-forehead.', 'DEF-jaw.', 'DEF-lid.', 'DEF-lip.', 'DEF-nose.', 'DEF-temple.', 'DEF-tongue.']
    facial_def = [b for b in def_bones if any(b.startswith(p) for p in facial_prefixes)]
    body_def = [b for b in def_bones if b not in facial_def]

    print(f"DEF Bones: {len(def_bones)} total (64 body: {len(body_def)}, 99 facial: {len(facial_def)})")
    assert len(def_bones) == 163, f"Expected 163 DEF bones, got {len(def_bones)}"
    assert len(body_def) == 64, f"Expected 64 body DEF bones, got {len(body_def)}"
    assert len(facial_def) == 99, f"Expected 99 facial DEF bones, got {len(facial_def)}"

    # 2. Volume preservation under flexion
    bm0 = bmesh.new()
    bm0.from_mesh(obj.data)
    v0 = bm0.calc_volume()
    bm0.free()
    print(f"Rest Mesh Volume V_0: {v0:.6f} m^3")

    def get_evaluated_mesh_data():
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(dg)
        eval_mesh = eval_obj.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        vol = bm.calc_volume()
        bm.free()
        coords = [v.co.copy() for v in eval_mesh.vertices]
        eval_obj.to_mesh_clear()
        return vol, coords

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')

    def reset_pose():
        for pb in arm.pose.bones:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()

    # Thigh 90
    reset_pose()
    arm.pose.bones['DEF-thigh.L'].rotation_euler = (math.radians(-90), 0, 0)
    v_thigh, _ = get_evaluated_mesh_data()
    rho_thigh = v_thigh / v0
    print(f"Thigh 90-deg Flexion: vol={v_thigh:.6f} m^3, rho_V={rho_thigh:.4f} (>=0.92: {'PASS' if rho_thigh >= 0.92 else 'FAIL'})")
    assert rho_thigh >= 0.92

    # Knee 90
    reset_pose()
    arm.pose.bones['DEF-shin.L'].rotation_euler = (math.radians(90), 0, 0)
    v_knee, _ = get_evaluated_mesh_data()
    rho_knee = v_knee / v0
    print(f"Knee 90-deg Flexion:  vol={v_knee:.6f} m^3, rho_V={rho_knee:.4f} (>=0.92: {'PASS' if rho_knee >= 0.92 else 'FAIL'})")
    assert rho_knee >= 0.92

    # Ankle 90
    reset_pose()
    arm.pose.bones['DEF-foot.L'].rotation_euler = (math.radians(-90), 0, 0)
    v_ankle, _ = get_evaluated_mesh_data()
    rho_ankle = v_ankle / v0
    print(f"Ankle 90-deg Flexion: vol={v_ankle:.6f} m^3, rho_V={rho_ankle:.4f} (>=0.92: {'PASS' if rho_ankle >= 0.92 else 'FAIL'})")
    assert rho_ankle >= 0.92

    # Toe 90
    reset_pose()
    arm.pose.bones['DEF-toe.L'].rotation_euler = (math.radians(90), 0, 0)
    v_toe, _ = get_evaluated_mesh_data()
    rho_toe = v_toe / v0
    print(f"Toe 90-deg Flexion:   vol={v_toe:.6f} m^3, rho_V={rho_toe:.4f} (>=0.92: {'PASS' if rho_toe >= 0.92 else 'FAIL'})")
    assert rho_toe >= 0.92

    # Combined 90
    reset_pose()
    arm.pose.bones['DEF-thigh.L'].rotation_euler = (math.radians(-90), 0, 0)
    arm.pose.bones['DEF-shin.L'].rotation_euler = (math.radians(90), 0, 0)
    arm.pose.bones['DEF-foot.L'].rotation_euler = (math.radians(-90), 0, 0)
    arm.pose.bones['DEF-toe.L'].rotation_euler = (math.radians(90), 0, 0)
    v_comb, _ = get_evaluated_mesh_data()
    rho_comb = v_comb / v0
    print(f"Combined 4-Joint Flexion: vol={v_comb:.6f} m^3, rho_V={rho_comb:.4f} (>=0.92: {'PASS' if rho_comb >= 0.92 else 'FAIL'})")
    assert rho_comb >= 0.92

    # 3. Patella displacement relative to shin bone
    reset_pose()
    coords_rest = [v.co.copy() for v in obj.data.vertices]
    patella_verts = [
        i for i, v in enumerate(coords_rest)
        if abs(v[0] - 0.100) < 0.035 and abs(v[2] - 0.470) < 0.035 and v[1] < -0.025
    ]
    shin_pb = arm.pose.bones['DEF-shin.L']
    shin_rest_inv = shin_pb.matrix.inverted()
    local_rest_patella = [shin_rest_inv @ coords_rest[i] for i in patella_verts]

    arm.pose.bones['DEF-shin.L'].rotation_euler = (math.radians(90), 0, 0)
    _, eval_coords_knee = get_evaluated_mesh_data()
    shin_posed_inv = shin_pb.matrix.inverted()
    local_posed_patella = [shin_posed_inv @ eval_coords_knee[i] for i in patella_verts]

    pat_disps_mm = [(p_pos - p_rst).length * 1000.0 for p_rst, p_pos in zip(local_rest_patella, local_posed_patella)]
    max_pat_disp = max(pat_disps_mm)
    print(f"Patella Relative Disp: max={max_pat_disp:.3f} mm, mean={sum(pat_disps_mm)/len(pat_disps_mm):.3f} mm (<=2.0mm: {'PASS' if max_pat_disp <= 2.0 else 'FAIL'})")
    assert max_pat_disp <= 2.0

    # 4. Malleoli displacement relative to lower leg
    reset_pose()
    for side in ['L', 'R']:
        sign = 1.0 if side == 'L' else -1.0
        ring = [i for i, c in enumerate(coords_rest) if abs(c[2] - 0.082) < 0.002 and (c[0] * sign) > 0.03]
        med_apex = min(ring, key=lambda i: coords_rest[i][0] * sign)
        lat_apex = max(ring, key=lambda i: coords_rest[i][0] * sign)
        mal_verts = [med_apex, lat_apex]

        shin1_pb = arm.pose.bones[f'DEF-shin.{side}.001']
        foot_pb = arm.pose.bones[f'DEF-foot.{side}']
        shin1_rest_inv = shin1_pb.matrix.inverted()
        local_rest_mal = [shin1_rest_inv @ coords_rest[i] for i in mal_verts]

        foot_pb.rotation_euler = (math.radians(30), 0, 0)
        _, eval_coords_foot = get_evaluated_mesh_data()
        shin1_posed_inv = shin1_pb.matrix.inverted()
        local_posed_mal = [shin1_posed_inv @ eval_coords_foot[i] for i in mal_verts]

        mal_disps_mm = [(p_pos - p_rst).length * 1000.0 for p_rst, p_pos in zip(local_rest_mal, local_posed_mal)]
        max_mal_disp = max(mal_disps_mm)
        print(f"Malleoli Side {side} Disp: max={max_mal_disp:.3f} mm, mean={sum(mal_disps_mm)/len(mal_disps_mm):.3f} mm (<=1.5mm: {'PASS' if max_mal_disp <= 1.5 else 'FAIL'})")
        assert max_mal_disp <= 1.5
        reset_pose()

    # 5. Extreme Poses NaN/Inf Check
    extreme_poses = [
        {'DEF-thigh.L': (-2.09, 0, 0), 'DEF-shin.L': (2.35, 0, 0), 'DEF-foot.L': (-0.78, 0, 0)},
        {'DEF-thigh.R': (1.05, 0, 0.52), 'DEF-shin.R': (-0.35, 0, 0), 'DEF-spine.002': (0, 0.78, 0.52)},
        {'DEF-upper_arm.L': (0, 0, 2.09), 'DEF-forearm.L': (0, 1.57, 0)},
    ]
    nan_count = 0
    inf_count = 0
    total_evaluated = 0
    for p_dict in extreme_poses:
        reset_pose()
        for b_name, rot in p_dict.items():
            pb = arm.pose.bones.get(b_name)
            if pb: pb.rotation_euler = rot
        _, eval_coords_ext = get_evaluated_mesh_data()
        total_evaluated += len(eval_coords_ext)
        for c in eval_coords_ext:
            for val in (c[0], c[1], c[2]):
                if math.isnan(val): nan_count += 1
                if math.isinf(val): inf_count += 1

    print(f"Extreme Poses ({len(extreme_poses)} poses, {total_evaluated} vertices): NaNs={nan_count}, Infs={inf_count} (PASS: {nan_count == 0 and inf_count == 0})")
    assert nan_count == 0 and inf_count == 0

    print("\n>>> ALL DIRECT IN-BLENDER EMPIRICAL ASSERTS PASSED! <<<")



if __name__ == "__main__":
    if "bpy" in sys.modules:
        run_standalone_blender_audit()
    elif pytest is not None:
        sys.exit(pytest.main([__file__, "-v"]))
    else:
        print("Neither bpy nor pytest available in runner environment.")
