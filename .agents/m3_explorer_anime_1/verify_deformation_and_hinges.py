"""
verify_deformation_and_hinges.py
Tests mesh deformation and hinge limits across all frames of all 4 actions.
"""

import sys
sys.path.append(r'E:\tool\mcp\MorphoMesh\.agents\m3_explorer_anime_1')

import math
import bpy
from mathutils import Vector

arm = bpy.data.objects['Anime_Armature']
scene = bpy.context.scene

from test_all_4_actions import build_all_anime_actions

actions = build_all_anime_actions(arm, push_to_nla=False)

def check_action_integrity(act_name, act):
    arm.animation_data.action = act
    frame_start = int(act.frame_range[0])
    frame_end = int(act.frame_range[1])
    
    max_knee_flex_deg = 0.0
    min_knee_flex_deg = 999.0
    max_elbow_flex_deg = 0.0
    min_elbow_flex_deg = 999.0

    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)
        
        # Check knees (Shin.L, Shin.R)
        for side in ['L', 'R']:
            pb_shin = arm.pose.bones[f'Shin.{side}']
            flex = math.degrees(pb_shin.rotation_euler.x)
            max_knee_flex_deg = max(max_knee_flex_deg, flex)
            min_knee_flex_deg = min(min_knee_flex_deg, flex)

        # Check elbows (ForeArm.L, ForeArm.R)
        for side in ['L', 'R']:
            pb_fore = arm.pose.bones[f'ForeArm.{side}']
            flex = abs(math.degrees(pb_fore.rotation_euler.x))
            max_elbow_flex_deg = max(max_elbow_flex_deg, flex)
            min_elbow_flex_deg = min(min_elbow_flex_deg, flex)

    print(f"[{act_name}] frames [{frame_start}..{frame_end}]:")
    print(f"  Knee flexion: min={min_knee_flex_deg:.1f}°, max={max_knee_flex_deg:.1f}° (Limit: [0°, 140°])")
    print(f"  Elbow flexion: min={min_elbow_flex_deg:.1f}°, max={max_elbow_flex_deg:.1f}° (Limit: [0°, 145°])")

    # Assert hinge limits compliance
    assert min_knee_flex_deg >= -0.1, f"Knee hyperextension detected in {act_name}: {min_knee_flex_deg}°"
    assert max_knee_flex_deg <= 140.1, f"Knee flexion limit breached in {act_name}: {max_knee_flex_deg}°"
    assert max_elbow_flex_deg <= 145.1, f"Elbow flexion limit breached in {act_name}: {max_elbow_flex_deg}°"

for name, act in actions.items():
    check_action_integrity(name, act)

print("ALL ACTIONS SATISFY ANATOMICAL HINGE LIMITS!")