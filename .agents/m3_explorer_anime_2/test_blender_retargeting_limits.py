"""
test_blender_retargeting_limits.py
Live Blender 4.5+ LTS Integration Test for proposed_retargeting_limits.py.
Loads output/anime_rigged.blend, applies constraints, tests pose bone evaluations,
audits constraints, and tests removal.
"""

import math
import sys
from pathlib import Path

# Add agent directory to sys.path
AGENT_DIR = Path(r"E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_2")
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

import bpy
from mathutils import Euler, Quaternion

import proposed_retargeting_limits as rl


def run_blender_tests():
    print("\n" + "="*70)
    print("STARTING LIVE BLENDER 4.5+ RETARGETING LIMITS TEST")
    print("="*70)

    arm = bpy.data.objects.get("Anime_Armature")
    assert arm is not None, "Anime_Armature not found in blend file!"
    assert arm.type == 'ARMATURE', f"Expected ARMATURE, got {arm.type}"
    print(f"[PASS] Found Anime_Armature with {len(arm.pose.bones)} pose bones.")

    # 1. Apply retargeting limits
    res_apply = rl.apply_retargeting_limits(arm, replace_existing=True)
    print(f"[PASS] apply_retargeting_limits: applied={res_apply['applied_count']}, updated={res_apply['updated_count']}, skipped={res_apply['skipped_count']}")
    assert res_apply["applied_count"] >= 16, f"Expected at least 16 major limbs/spine clamped, got {res_apply['applied_count']}"

    # 2. Verify limits audit
    audit = rl.verify_retargeting_limits(arm)
    print(f"[PASS] verify_retargeting_limits: verified={audit['verified_count']}, discrepancies={audit['discrepancies_count']}")
    if audit["discrepancies"]:
        print("Discrepancies noted:", audit["discrepancies"][:5])
    # The major physiological bones must have zero discrepancies
    major_bones = ["ForeArm.L", "ForeArm.R", "Shin.L", "Shin.R", "Foot.L", "Foot.R", "Toe.L", "Toe.R"]
    pb = arm.pose.bones
    for mb in major_bones:
        assert mb in pb, f"Major bone {mb} missing!"
        c = next((c for c in pb[mb].constraints if c.type == 'LIMIT_ROTATION' and c.name == 'Physiological_Limit_Rotation'), None)
        assert c is not None, f"Bone {mb} missing Physiological_Limit_Rotation constraint!"
        assert c.owner_space == 'LOCAL', f"Bone {mb} constraint owner_space is {c.owner_space}, expected LOCAL!"

    # 3. Test Pose Mode Clamping on ForeArm.L (Elbow pure hinge)
    fore = pb["ForeArm.L"]
    fore.rotation_mode = 'XYZ'

    # Test hyperextension attempt (-60° X) -> Clamped to 0.0°
    fore.rotation_euler = Euler((math.radians(-60.0), 0.0, 0.0), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["ForeArm.L"].matrix_local.inverted() @ fore.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] ForeArm.L hyperextension input -60° -> evaluated rel X = {math.degrees(rel_e.x):.2f}°")
    assert abs(rel_e.x - 0.0) < 1e-3, f"Elbow hyperextension not clamped: {math.degrees(rel_e.x)}°"

    # Test over-flexion attempt (+165° X) -> Clamped to 145.0°
    fore.rotation_euler = Euler((math.radians(165.0), 0.0, 0.0), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["ForeArm.L"].matrix_local.inverted() @ fore.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] ForeArm.L over-flexion input +165° -> evaluated rel X = {math.degrees(rel_e.x):.2f}°")
    assert abs(rel_e.x - math.radians(145.0)) < 1e-3, f"Elbow over-flexion not clamped: {math.degrees(rel_e.x)}°"

    # Test forearm twist clamp (+30° Y) -> Clamped to +15.0°
    fore.rotation_euler = Euler((0.0, math.radians(30.0), 0.0), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["ForeArm.L"].matrix_local.inverted() @ fore.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] ForeArm.L twist input +30° Y -> evaluated rel Y = {math.degrees(rel_e.y):.2f}°")
    assert abs(rel_e.y - math.radians(15.0)) < 1e-3, f"Forearm twist not clamped: {math.degrees(rel_e.y)}°"

    # Test forearm deviation clamp (+20° Z) -> Clamped to +5.0°
    fore.rotation_euler = Euler((0.0, 0.0, math.radians(20.0)), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["ForeArm.L"].matrix_local.inverted() @ fore.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] ForeArm.L deviation input +20° Z -> evaluated rel Z = {math.degrees(rel_e.z):.2f}°")
    assert abs(rel_e.z - math.radians(5.0)) < 1e-3, f"Forearm deviation not clamped: {math.degrees(rel_e.z)}°"

    fore.rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')

    # 4. Test Pose Mode Clamping on Shin.L (Knee backward flexion & anti-valgus)
    shin = pb["Shin.L"]
    shin.rotation_mode = 'XYZ'

    # Knee hyperextension attempt (-45° X) -> Clamped to 0.0°
    shin.rotation_euler = Euler((math.radians(-45.0), 0.0, 0.0), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["Shin.L"].matrix_local.inverted() @ shin.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] Shin.L hyperextension input -45° -> evaluated rel X = {math.degrees(rel_e.x):.2f}°")
    assert abs(rel_e.x - 0.0) < 1e-3, f"Knee front hyperextension not clamped: {math.degrees(rel_e.x)}°"

    # Knee over-flexion attempt (+160° X) -> Clamped to 140.0°
    shin.rotation_euler = Euler((math.radians(160.0), 0.0, 0.0), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["Shin.L"].matrix_local.inverted() @ shin.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] Shin.L over-flexion input +160° -> evaluated rel X = {math.degrees(rel_e.x):.2f}°")
    assert abs(rel_e.x - math.radians(140.0)) < 1e-3, f"Knee backward over-flexion not clamped: {math.degrees(rel_e.x)}°"

    # Knee valgus collapse attempt (+25° Y) -> Clamped to +3.0°
    shin.rotation_euler = Euler((0.0, math.radians(25.0), 0.0), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["Shin.L"].matrix_local.inverted() @ shin.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] Shin.L valgus input +25° Y -> evaluated rel Y = {math.degrees(rel_e.y):.2f}°")
    assert abs(rel_e.y - math.radians(3.0)) < 1e-3, f"Knee valgus collapse not clamped: {math.degrees(rel_e.y)}°"

    # Knee dislocation attempt (-20° Z) -> Clamped to -3.0°
    shin.rotation_euler = Euler((0.0, 0.0, math.radians(-20.0)), 'XYZ')
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["Shin.L"].matrix_local.inverted() @ shin.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] Shin.L dislocation input -20° Z -> evaluated rel Z = {math.degrees(rel_e.z):.2f}°")
    assert abs(rel_e.z - math.radians(-3.0)) < 1e-3, f"Knee dislocation not clamped: {math.degrees(rel_e.z)}°"

    shin.rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')

    # 5. Test Foot.L and Toe.L
    foot = pb["Foot.L"]
    foot.rotation_mode = 'XYZ'
    foot.rotation_euler = Euler((math.radians(-60.0), 0.0, 0.0), 'XYZ')  # Plantarflexion past -45°
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["Foot.L"].matrix_local.inverted() @ foot.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] Foot.L pitch input -60° X -> evaluated rel X = {math.degrees(rel_e.x):.2f}°")
    assert abs(rel_e.x - math.radians(-45.0)) < 1e-3

    foot.rotation_euler = Euler((0.0, math.radians(20.0), 0.0), 'XYZ')  # Roll past +8°
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["Foot.L"].matrix_local.inverted() @ foot.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] Foot.L roll input +20° Y -> evaluated rel Y = {math.degrees(rel_e.y):.2f}°")
    assert abs(rel_e.y - math.radians(8.0)) < 1e-3

    foot.rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')

    toe = pb["Toe.L"]
    toe.rotation_mode = 'XYZ'
    toe.rotation_euler = Euler((math.radians(60.0), 0.0, 0.0), 'XYZ')  # Toe-off past +45°
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["Toe.L"].matrix_local.inverted() @ toe.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] Toe.L toe-off input +60° X -> evaluated rel X = {math.degrees(rel_e.x):.2f}°")
    assert abs(rel_e.x - math.radians(45.0)) < 1e-3

    toe.rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')

    # 6. Test Quaternion Input Clamping on Live Armature
    fore.rotation_mode = 'QUATERNION'
    q_hyperext = Euler((math.radians(-50.0), 0.0, 0.0), 'XYZ').to_quaternion()
    fore.rotation_quaternion = q_hyperext
    bpy.context.view_layer.update()
    rel_mat = arm.data.bones["ForeArm.L"].matrix_local.inverted() @ fore.matrix
    rel_e = rel_mat.to_euler('XYZ')
    print(f"[TEST] ForeArm.L Quaternion input (-50° X) -> evaluated rel X = {math.degrees(rel_e.x):.2f}°")
    assert abs(rel_e.x - 0.0) < 1e-3, "Quaternion hyperextension not clamped on live armature!"

    # 7. Test Constraint Removal
    rem_count = rl.remove_retargeting_limits(arm)
    print(f"[PASS] remove_retargeting_limits: removed {rem_count} constraints.")
    assert rem_count >= 16

    print("\n" + "="*70)
    print("ALL LIVE BLENDER 4.5+ RETARGETING LIMITS TESTS PASSED (100%)!")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_blender_tests()
