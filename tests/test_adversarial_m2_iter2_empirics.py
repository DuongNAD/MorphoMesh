"""
Milestone 2 Iteration 2 Adversarial Stress Harness.
Authored by challenger_human_m2_iter2_1.

Empirically validates:
1. Live mesh deformation in Blender 4.5.4 LTS when rotating bones:
   - Evaluates evaluated mesh deformation across 6 major deformers:
     DEF-forearm.L, DEF-forearm.R, DEF-shin.L, DEF-shin.R, DEF-upper_arm.L, DEF-thigh.L.
   - Asserts maximum vertex displacement is strictly > 0.05m.
2. Live shape key vertex displacement:
   - Evaluates all 52 Apple ARKit FACS blendshapes in Blender 4.5.4 LTS.
   - Asserts 100% of the 52 keys exist, have displaced vertices, zero NaNs, and displacement > 0.001m.
3. Dynamic finger partitioning under extreme shoulder widths and scales:
   - Tests extreme wrist_x = 0.60m, wrist_x = 0.20m, scale = 0.5, scale = 2.0.
   - Asserts 0 bleeding of finger vertices into palm (DEF-hand weight == 0 on fingers).
   - Asserts 0 bleeding of palm vertices into fingers (DEF-finger weight == 0 on palm).
   - Asserts all 5 digits receive vertices on both Left and Right hands.
4. Bilateral pre-bend angles verification under mirrored and distorted landmarks:
   - Tests severely inverted joint coordinates (elbows -Y, knees +Y).
   - Tests asymmetrical / mirrored distortions.
   - Asserts verify_prebends() returns True with both L and R strictly complying.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
from typing import Tuple

import pytest

from morphomesh.human_generator import HumanAnatomyConfig, generate_human_base_mesh
from morphomesh.human_rigging import (
    HumanRigConfig,
    calculate_anti_pinch_weights,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
)

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


# ==============================================================================
# 1. LIVE BLENDER 4.5.4 LTS MESH DEFORMATION EMPIRICAL TESTS
# ==============================================================================

class TestLiveBlenderBoneRotationDeformation:
    """Stress tests live mesh deformation inside Blender 4.5.4 LTS across multiple deformer bones."""

    @pytest.fixture(scope="class")
    def blender_exe(self):
        if not os.path.isfile(BLENDER_EXE):
            pytest.skip("Blender 4.5.4 LTS executable not found.")
        return BLENDER_EXE

    @pytest.mark.parametrize(
        "bone_name,euler_xyz,min_expected_disp",
        [
            ("DEF-forearm.L", (math.radians(45), 0, 0), 0.05),
            ("DEF-forearm.R", (math.radians(45), 0, 0), 0.05),
            ("DEF-shin.L", (math.radians(-45), 0, 0), 0.05),
            ("DEF-shin.R", (math.radians(-45), 0, 0), 0.05),
            ("DEF-upper_arm.L", (0, 0, math.radians(45)), 0.05),
            ("DEF-thigh.L", (math.radians(45), 0, 0), 0.05),
        ],
    )
    def test_live_bone_rotation_displacement_exceeds_threshold(
        self, blender_exe: str, bone_name: str, euler_xyz: Tuple[float, float, float], min_expected_disp: float
    ):
        """Verify that rotating bone_name by euler_xyz produces vertex displacement > 0.05m in Blender."""
        rx, ry, rz = euler_xyz
        py_script = f"""
import sys
sys.path.insert(0, r'E:\\tool\\mcp\\MorphoMesh\\src')
sys.path.append(r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')

import bpy, math, json
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script

mesh_name = 'Human_Base_Mesh'
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name))

obj = bpy.data.objects[mesh_name]
arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']

# Rest positions of all vertices
rest_coords = [list(v.co) for v in obj.data.vertices]

# Rotate target bone in Pose mode
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')

pbone = arm.pose.bones.get({repr(bone_name)})
assert pbone is not None, f"Bone '{repr(bone_name)}' not found in pose bones"

pbone.rotation_mode = 'XYZ'
pbone.rotation_euler = ({rx}, {ry}, {rz})

bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = obj.evaluated_get(depsgraph)
eval_mesh = eval_obj.to_mesh()

eval_coords = [list(v.co) for v in eval_mesh.vertices]
assert len(rest_coords) == len(eval_coords)

displacements = [
    math.sqrt(sum((a - b)**2 for a, b in zip(p0, p1)))
    for p0, p1 in zip(rest_coords, eval_coords)
]
max_disp = max(displacements)
moving_verts = sum(1 for d in displacements if d > 0.001)

print(json.dumps({{'bone': {repr(bone_name)}, 'max_disp': max_disp, 'moving_verts': moving_verts}}))
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(py_script)
            script_path = f.name

        try:
            cmd = [blender_exe, "--background", "--factory-startup", "--python", script_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            assert proc.returncode == 0, f"Blender failed:\n{proc.stderr}\n{proc.stdout}"

            # Parse JSON line
            json_line = None
            for line in proc.stdout.splitlines():
                if line.strip().startswith('{"bone":'):
                    json_line = line.strip()
                    break

            assert json_line is not None, f"No JSON result found in output:\n{proc.stdout}"
            data = json.loads(json_line)

            assert data["max_disp"] > min_expected_disp, (
                f"Bone {bone_name} produced insufficient displacement: {data['max_disp']:.6f}m "
                f"(expected > {min_expected_disp}m)"
            )
            assert data["moving_verts"] > 10, (
                f"Bone {bone_name} moved only {data['moving_verts']} vertices"
            )
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)


# ==============================================================================
# 2. LIVE BLENDER 4.5.4 LTS 52 APPLE ARKIT FACS BLENDSHAPES TEST
# ==============================================================================

class TestLiveBlenderARKit52Blendshapes:
    """Stress tests live shape key deltas inside Blender 4.5.4 LTS for all 52 ARKit keys."""

    @pytest.fixture(scope="class")
    def blender_exe(self):
        if not os.path.isfile(BLENDER_EXE):
            pytest.skip("Blender 4.5.4 LTS executable not found.")
        return BLENDER_EXE

    def test_all_52_arkit_keys_produce_non_zero_deltas_in_blender(self, blender_exe: str):
        """Verify in live Blender that all 52 ARKit keys have displaced vertices and zero NaNs."""
        py_script = """
import sys
sys.path.insert(0, r'E:\\tool\\mcp\\MorphoMesh\\src')
sys.path.append(r'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages')

import bpy, math, json
from morphomesh.human_generator import get_human_generation_script
from morphomesh.human_rigging import get_rigging_script, ARKIT_52_BLENDSHAPES

mesh_name = 'Human_Base_Mesh'
exec(get_human_generation_script(mesh_name))
exec(get_rigging_script(mesh_name))

obj = bpy.data.objects[mesh_name]
assert obj.data.shape_keys is not None, "Shape keys block is missing on mesh"
key_blocks = obj.data.shape_keys.key_blocks
basis = key_blocks['Basis']

results = {}
for k_name in ARKIT_52_BLENDSHAPES:
    if k_name not in key_blocks:
        results[k_name] = {'exists': False, 'max_disp': 0.0, 'displaced_verts': 0, 'has_nans': False}
        continue

    kb = key_blocks[k_name]
    disps = []
    has_nan = False
    for i in range(len(kb.data)):
        co_k = kb.data[i].co
        co_b = basis.data[i].co
        dx = co_k[0] - co_b[0]
        dy = co_k[1] - co_b[1]
        dz = co_k[2] - co_b[2]
        if math.isnan(dx) or math.isnan(dy) or math.isnan(dz):
            has_nan = True
        d = math.sqrt(dx*dx + dy*dy + dz*dz)
        disps.append(d)

    max_d = max(disps)
    num_disp = sum(1 for d in disps if d > 1e-5)
    results[k_name] = {
        'exists': True,
        'max_disp': max_d,
        'displaced_verts': num_disp,
        'has_nans': has_nan
    }

print("ARKit_REPORT:" + json.dumps(results))
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(py_script)
            script_path = f.name

        try:
            cmd = [blender_exe, "--background", "--factory-startup", "--python", script_path]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            assert proc.returncode == 0, f"Blender script failed:\n{proc.stderr}\n{proc.stdout}"

            line = [l for l in proc.stdout.splitlines() if l.startswith("ARKit_REPORT:")][0]
            report = json.loads(line.replace("ARKit_REPORT:", ""))

            assert len(report) == 52, f"Expected 52 ARKit keys in report, got {len(report)}"

            failed_keys = []
            for k_name, stats in report.items():
                if not stats["exists"]:
                    failed_keys.append(f"{k_name}: MISSING")
                elif stats["has_nans"]:
                    failed_keys.append(f"{k_name}: CONTAINS_NANS")
                elif stats["displaced_verts"] == 0:
                    failed_keys.append(f"{k_name}: ZERO_DISPLACED_VERTS")
                elif stats["max_disp"] < 0.001:
                    failed_keys.append(f"{k_name}: INSUFFICIENT_DISP_{stats['max_disp']:.6f}")

            assert not failed_keys, "ARKit blendshapes validation failures in Blender:\n" + "\n".join(failed_keys)
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)


# ==============================================================================
# 3. DYNAMIC FINGER PARTITIONING & PALM BLEEDING CHALLENGE
# ==============================================================================

class TestDynamicFingerPartitioningAndBleeding:
    """Stress tests finger partitioning and strictly verifies ZERO bleeding into palm."""

    @pytest.mark.parametrize(
        "desc,cfg,override_wrist_x",
        [
            ("Canonical_1.65m", HumanAnatomyConfig(height=1.65), None),
            ("Extreme_Broad_0.60m", HumanAnatomyConfig(shoulder_width=0.60, arm_span=2.5), 0.60),
            ("Extreme_Narrow_0.20m", HumanAnatomyConfig(shoulder_width=0.20, arm_span=1.0), 0.20),
            ("Min_Boundary_1.0m", HumanAnatomyConfig(height=1.00, head_ratio=5.0), None),
            ("Max_Boundary_2.5m", HumanAnatomyConfig(height=2.50, head_ratio=10.0), None),
        ],
    )
    def test_finger_palm_isolation_and_zero_bleeding(
        self, desc: str, cfg: HumanAnatomyConfig, override_wrist_x: float | None
    ):
        """
        Verify that:
        1. NO finger vertices receive DEF-hand weights (weight == 0.0).
        2. NO palm vertices receive DEF-thumb / DEF-finger weights (weight == 0.0).
        3. All 5 digits receive vertices on both Left and Right hands.
        4. Strict weight normalization (sum == 1.0) holds across all vertices.
        """
        mesh_res = generate_human_base_mesh(config=cfg)
        lm = dict(mesh_res.landmarks)
        if override_wrist_x is not None:
            lm["wrist_L"] = (override_wrist_x, lm["wrist_L"][1], lm["wrist_L"][2])
            lm["wrist_R"] = (-override_wrist_x, lm["wrist_R"][1], lm["wrist_R"][2])

        metarig = generate_rigify_human_metarig(landmarks=lm)
        weights = calculate_anti_pinch_weights(mesh_res.mesh, metarig, landmarks=lm)

        vgroups = mesh_res.vertex_groups

        for side in ["L", "R"]:
            fingers_vg = vgroups.get(f"fingers_{side}", [])
            hand_vg = vgroups.get(f"hand_{side}", [])
            # Isolate true palm vertices (hand group excluding finger phalanges)
            palm_verts = set(hand_vg) - set(fingers_vg)

            assert len(fingers_vg) > 0, f"{desc}: No vertices in fingers_{side}"
            assert len(palm_verts) > 0, f"{desc}: No palm vertices in hand_{side}"

            # 1. Zero bleeding of finger vertices into palm:
            # Check DEF-hand.{side} weight on all finger vertices is strictly 0.0
            for vi in fingers_vg:
                hand_w = weights.get_vertex_weight(vi, f"DEF-hand.{side}")
                assert hand_w == 0.0, (
                    f"{desc}: Bleeding! Finger vertex {vi} has DEF-hand.{side} weight = {hand_w:.4f}"
                )

            # 2. Zero bleeding of palm vertices into fingers:
            # Check finger deformer weights on all palm vertices is strictly 0.0
            finger_bone_names = [
                f"DEF-{d}.{ph:02d}.{side}"
                for d in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]
                for ph in range(1, 4)
            ]
            for vi in palm_verts:
                for fb in finger_bone_names:
                    fb_w = weights.get_vertex_weight(vi, fb)
                    assert fb_w == 0.0, (
                        f"{desc}: Bleeding! Palm vertex {vi} has {fb} weight = {fb_w:.4f}"
                    )

            # 3. Verify all 5 digits are assigned vertices:
            digits_count = {d: 0 for d in ["thumb", "f_index", "f_middle", "f_ring", "f_pinky"]}
            for vi in fingers_vg:
                for d in digits_count:
                    if weights.get_vertex_weight(vi, f"DEF-{d}.01.{side}") > 0:
                        digits_count[d] += 1
                        break

            for d, count in digits_count.items():
                assert count > 0, (
                    f"{desc}: Digit {d}.{side} collapsed to 0 vertices! Distribution: {digits_count}"
                )

        # 4. Strict weight normalization
        is_norm, total_checked, max_disc = weights.verify_normalization(tolerance=1e-4)
        assert is_norm is True, f"{desc}: Normalization failed, max discrepancy: {max_disc}"


# ==============================================================================
# 4. BILATERAL PRE-BEND ANGLES UNDER MIRRORED AND DISTORTED LANDMARKS
# ==============================================================================

class TestBilateralPrebendsAdversarial:
    """Stress tests bilateral pre-bend enforcement under severely distorted and mirrored landmarks."""

    def test_prebends_enforced_under_inverted_landmarks(self):
        """
        Adversarially inject inverted joints:
        - elbow_L_y = -0.20, elbow_R_y = -0.30 (elbows inverted forward)
        - knee_L_y = +0.20, knee_R_y = +0.35 (knees inverted backward)
        Verify that generate_rigify_human_metarig and verify_prebends enforce +Y on elbows and -Y on knees.
        """
        lm = get_default_human_landmarks()
        lm["elbow_L"] = (lm["elbow_L"][0], -0.20, lm["elbow_L"][2])
        lm["elbow_R"] = (lm["elbow_R"][0], -0.30, lm["elbow_R"][2])
        lm["knee_L"] = (lm["knee_L"][0], 0.20, lm["knee_L"][2])
        lm["knee_R"] = (lm["knee_R"][0], 0.35, lm["knee_R"][2])

        metarig = generate_rigify_human_metarig(landmarks=lm)
        ok, metrics = metarig.verify_prebends()

        assert ok is True, f"verify_prebends failed under inverted landmarks: {metrics}"
        assert metrics["elbow_L_y"] > 0.0, f"elbow_L_y not positive: {metrics['elbow_L_y']}"
        assert metrics["elbow_R_y"] > 0.0, f"elbow_R_y not positive: {metrics['elbow_R_y']}"
        assert metrics["knee_L_y"] < 0.0, f"knee_L_y not negative: {metrics['knee_L_y']}"
        assert metrics["knee_R_y"] < 0.0, f"knee_R_y not negative: {metrics['knee_R_y']}"

    def test_prebends_enforced_under_asymmetric_distortions(self):
        """
        Inject asymmetric distortion: Left side pristine, Right side severely distorted.
        Verify both sides are verified and strictly compliant.
        """
        lm = get_default_human_landmarks()
        lm["elbow_R"] = (lm["elbow_R"][0], -0.45, lm["elbow_R"][2])
        lm["knee_R"] = (lm["knee_R"][0], 0.50, lm["knee_R"][2])

        metarig = generate_rigify_human_metarig(landmarks=lm)
        ok, metrics = metarig.verify_prebends()

        assert ok is True, f"verify_prebends failed under asymmetric distortion: {metrics}"
        assert metrics["elbow_L_y"] > 0.0
        assert metrics["elbow_R_y"] > 0.0
        assert metrics["knee_L_y"] < 0.0
        assert metrics["knee_R_y"] < 0.0

    def test_prebends_custom_config_override_symmetrical(self):
        """
        Verify that custom prebend configuration overrides are applied symmetrically
        to both Left and Right limbs.
        """
        cfg = HumanRigConfig(elbow_prebend_y=0.035, knee_prebend_y=-0.045)
        lm = get_default_human_landmarks()

        metarig = generate_rigify_human_metarig(landmarks=lm, config=cfg)
        ok, metrics = metarig.verify_prebends()

        assert ok is True
        assert metrics["elbow_L_y"] >= 0.035
        assert metrics["elbow_R_y"] >= 0.035
        assert metrics["knee_L_y"] <= -0.045
        assert metrics["knee_R_y"] <= -0.045
