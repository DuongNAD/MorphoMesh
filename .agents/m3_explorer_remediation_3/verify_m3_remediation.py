"""
verify_m3_remediation.py
Standalone Verification Script for Milestone 3 Remediation.
Author: m3_explorer_remediation_3

This script is to be executed by m3_worker_anime_1 (or CI/Auditor) after applying:
1. ForeArm flexion patch in anime_pipeline/animation/action_library.py
2. Skirt dynamic clearance patch in anime_pipeline/animation/spring_solver.py
3. Test assertion updates in tests/test_m3_animation_pipeline.py and tests/test_m3_challenger_adversarial.py
4. Re-baking deliverables output/anime_animated.blend and output/anime_animated.glb via generate_animated_character()

Validation Steps:
Step 1: Verify test_m3_challenger_adversarial.py (100% 7/7 passed in Blender 4.5.4 LTS)
Step 2: Verify test_m3_adversarial_secondary_and_clearance.py (100% 7/7 passed in uv pytest)
Step 3: Verify full test suite (100% passed in uv pytest tests/ -v)
Step 4: Live Blender audit on output/anime_animated.blend and output/anime_animated.glb
        - ForeArm local X flexion >= 0.0° and <= 145.0° (zero hyperextension)
        - Skirt-thigh 3D clearance >= 15.0mm across all frames
        - Skirt spoke bone pitch in [-15.0°, +65.0°]
        - GLB deliverable contains active non-zero forearm flexion across all 4 actions
"""

import os
import sys
import subprocess
from pathlib import Path

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe")
PROJECT_ROOT = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline").resolve()

def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def run_step_1_challenger_adversarial() -> bool:
    print_banner("STEP 1: Verifying test_m3_challenger_adversarial.py in Blender 4.5.4 LTS")
    if not BLENDER_EXE.exists():
        print(f"ERROR: Blender executable not found at {BLENDER_EXE}")
        return False
    
    cmd = [
        str(BLENDER_EXE),
        "-b",
        "--python-expr",
        "import sys, pytest; sys.exit(pytest.main(['tests/test_m3_challenger_adversarial.py', '-v']))"
    ]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)
    
    success = (proc.returncode == 0) and ("7 passed" in proc.stdout)
    print(f"STEP 1 RESULT: {'PASS' if success else 'FAIL'} (exit code {proc.returncode})")
    return success

def run_step_2_adversarial_secondary_and_clearance() -> bool:
    print_banner("STEP 2: Verifying test_m3_adversarial_secondary_and_clearance.py")
    cmd = ["uv", "run", "pytest", "tests/test_m3_adversarial_secondary_and_clearance.py", "-v"]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)
    
    success = (proc.returncode == 0) and ("failed" not in proc.stdout.lower() or "0 failed" in proc.stdout.lower())
    print(f"STEP 2 RESULT: {'PASS' if success else 'FAIL'} (exit code {proc.returncode})")
    return success

def run_step_3_full_pytest_suite() -> bool:
    print_banner("STEP 3: Verifying Full Canonical Pytest Suite (pytest tests/ -v)")
    cmd = ["uv", "run", "pytest", "tests/", "-v"]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)
    
    success = (proc.returncode == 0)
    print(f"STEP 3 RESULT: {'PASS' if success else 'FAIL'} (exit code {proc.returncode})")
    return success

def run_step_4_live_deliverables_audit() -> bool:
    print_banner("STEP 4: Live Deliverables Inspection (anime_animated.blend & anime_animated.glb)")
    py_code = """
import sys
sys.path.insert(0, '.')
import math
from pathlib import Path
import bpy
from tests.test_m3_adversarial_secondary_and_clearance import run_skirt_clearance_audit

blend_path = Path('output/anime_animated.blend').resolve()
glb_path = Path('output/anime_animated.glb').resolve()

assert blend_path.exists(), f'Missing {blend_path}'
assert glb_path.exists(), f'Missing {glb_path}'

# 1. Audit Skirt clearance and pitch compliance
rep = run_skirt_clearance_audit(blend_path)
print('SKIRT CLEARANCE AUDIT:')
print(f'  Min clearance: {rep[\"min_overall_clearance_mm\"]:.2f}mm (required >= 15.0mm)')
print(f'  Clearance violations: {rep[\"clearance_violations\"]}')
print(f'  Pitch violations: {rep[\"pitch_violations\"]}')
print(f'  Action clearances: {rep[\"action_clearances_mm\"]}')
assert rep['passed'], f'Skirt clearance audit failed: {rep}'

# 2. Audit ForeArm keyframes in blend
bpy.ops.wm.open_mainfile(filepath=str(blend_path))
arm = bpy.data.objects.get('Anime_Armature')
forearm_violations = 0
for act in bpy.data.actions:
    if not act.name.startswith('action_anime_'): continue
    arm.animation_data.action = act
    for f in range(int(act.frame_range[0]), int(act.frame_range[1]) + 1):
        bpy.context.scene.frame_set(f)
        for b in ['ForeArm.L', 'ForeArm.R']:
            rx = math.degrees(arm.pose.bones[b].rotation_euler.x)
            if rx < -0.01 or rx > 145.01:
                forearm_violations += 1
                print(f'VIOLATION: {act.name} {b} frame {f}: {rx:.2f}°')

print(f'ForeArm keyframe violations in blend: {forearm_violations}')
assert forearm_violations == 0, f'Found {forearm_violations} forearm limit violations'

# 3. Audit GLB baked animations
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb_path))
arm_objs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
assert len(arm_objs) > 0, 'No armature in GLB'
arm_glb = arm_objs[0]

print('GLB BAKED FOREARM ROTATIONS:')
for act in bpy.data.actions:
    arm_glb.animation_data.action = act
    for b in ['ForeArm.L', 'ForeArm.R']:
        pb = arm_glb.pose.bones.get(b)
        if not pb: continue
        angles = []
        for f in range(int(act.frame_range[0]), int(act.frame_range[1]) + 1):
            bpy.context.scene.frame_set(f)
            e = pb.rotation_quaternion.to_euler('XYZ') if pb.rotation_mode == 'QUATERNION' else pb.rotation_euler
            angles.append(abs(math.degrees(e.x)))
        print(f'  GLB {act.name} {b}: min={min(angles):.2f}°, max={max(angles):.2f}°')
        assert max(angles) > 10.0, f'GLB forearm frozen in {act.name} {b}: max={max(angles):.2f}°'

print('DELIVERABLES AUDIT: ALL CHECKS PASSED!')
"""
    cmd = [str(BLENDER_EXE), "-b", "--python-expr", py_code]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)
    
    success = (proc.returncode == 0) and ("DELIVERABLES AUDIT: ALL CHECKS PASSED!" in proc.stdout)
    print(f"STEP 4 RESULT: {'PASS' if success else 'FAIL'} (exit code {proc.returncode})")
    return success

def main():
    print_banner("MILESTONE 3 REMEDIATION STANDALONE VERIFICATION RUNNER")
    print(f"Project Directory: {PROJECT_ROOT}")
    print(f"Blender Executable: {BLENDER_EXE}")
    
    s1 = run_step_1_challenger_adversarial()
    s2 = run_step_2_adversarial_secondary_and_clearance()
    s3 = run_step_3_full_pytest_suite()
    s4 = run_step_4_live_deliverables_audit()
    
    print_banner("OVERALL VERIFICATION SUMMARY")
    print(f"  Step 1 (test_m3_challenger_adversarial.py):            {'PASS' if s1 else 'FAIL'}")
    print(f"  Step 2 (test_m3_adversarial_secondary_and_clearance): {'PASS' if s2 else 'FAIL'}")
    print(f"  Step 3 (Full Canonical Pytest Suite):                  {'PASS' if s3 else 'FAIL'}")
    print(f"  Step 4 (Live Deliverables Blend & GLB Audit):          {'PASS' if s4 else 'FAIL'}")
    
    overall = s1 and s2 and s3 and s4
    print("=" * 80)
    if overall:
        print("  VERDICT: 100% PASS - ALL REMEDIATION ACCEPTANCE CRITERIA SATISFIED!")
    else:
        print("  VERDICT: VERIFICATION FAILED - REVIEW FAILED STEPS ABOVE.")
    print("=" * 80)
    sys.exit(0 if overall else 1)

if __name__ == "__main__":
    main()
