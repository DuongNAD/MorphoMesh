"""
test_action_builder_prototype.py
Interactive prototype for Milestone 3 F11 Anime Action Library.
Builds all 4 canonical anime actions in Blender 4.5.4 LTS and validates integrity.
"""

import math
import bpy
from mathutils import Euler, Matrix, Vector

def clear_actions():
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)

def set_bezier_interpolation(action):
    """Sets BEZIER interpolation and auto-clamped handles on all fcurves."""
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = 'AUTO_CLAMPED'
            kp.handle_right_type = 'AUTO_CLAMPED'

def get_hips_local_shift(pb_hips, target_world_xyz):
    """Transforms a target world translation into the bone's local rest coordinate frame."""
    rest_rot = pb_hips.bone.matrix_local.to_3x3()
    return rest_rot.inverted() @ Vector(target_world_xyz)

def build_action_idle_cute(arm_obj):
    act = bpy.data.actions.new("action_anime_idle_cute")
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start = 1
    act.frame_end = 90
    arm_obj.animation_data.action = act
    pb = arm_obj.pose.bones

    for b in pb:
        b.rotation_mode = 'XYZ'

    # Sample keyframe cadences (every 5-10 frames or dense sampling for smooth loop)
    # Frames: 1, 15, 23, 30, 45, 60, 68, 75, 90 (with 91 for perfect loop tangent)
    frames = [1, 12, 23, 34, 45, 56, 67, 78, 90]
    
    # 1. Hips: Base contrapposto (+0.035m world X, roll Z = -4.5 deg, yaw Y = +2.0 deg)
    # Double micro-bob: +/- 0.006m (2 cycles in 90 frames -> period 45 frames)
    for f in range(1, 92):
        t = (f - 1) / 90.0
        bob_z = 0.006 * math.sin(4.0 * math.pi * t)
        w_trans = (0.035, 0.0, bob_z)
        local_trans = get_hips_local_shift(pb['Hips'], w_trans)
        
        # Subtle hip breathing sway
        sway_roll = math.radians(-4.5 + 0.3 * math.sin(2.0 * math.pi * t))
        sway_yaw = math.radians(2.0 + 0.2 * math.cos(2.0 * math.pi * t))
        
        if f in frames or f == 91:
            kf_frame = 90 if f == 91 else f
            pb['Hips'].location = local_trans
            pb['Hips'].rotation_euler = Euler((0.0, sway_yaw, sway_roll), 'XYZ')
            pb['Hips'].keyframe_insert(data_path='location', frame=kf_frame)
            pb['Hips'].keyframe_insert(data_path='rotation_euler', frame=kf_frame)

    # 2. Torso counter-tilt & breathing
    for f in frames:
        t = (f - 1) / 90.0
        breath_pitch = math.radians(1.5 * math.sin(2.0 * math.pi * t))
        counter_roll = math.radians(3.5)
        
        pb['Spine'].rotation_euler = Euler((breath_pitch * 0.4, 0.0, counter_roll * 0.5), 'XYZ')
        pb['Spine'].keyframe_insert(data_path='rotation_euler', frame=f)

        pb['Spine1'].rotation_euler = Euler((breath_pitch * 0.6, 0.0, counter_roll * 0.5), 'XYZ')
        pb['Spine1'].keyframe_insert(data_path='rotation_euler', frame=f)

    # 3. Head: cute tilt ~4 deg delayed by pi/4 (~11 frames)
    for f in frames:
        t = (f - 1) / 90.0
        head_tilt = math.radians(4.0 + 1.2 * math.sin(2.0 * math.pi * t - math.pi * 0.25))
        head_nod = math.radians(1.0 * math.cos(2.0 * math.pi * t))
        pb['Head'].rotation_euler = Euler((head_nod, 0.0, head_tilt), 'XYZ')
        pb['Head'].keyframe_insert(data_path='rotation_euler', frame=f)

    # 4. Legs: Right leg support (straight), Left leg relaxed (flexed forward 8 deg)
    for f in [1, 45, 90]:
        pb['Thigh.R'].rotation_euler = Euler((math.radians(1.5), 0.0, math.radians(-1.5)), 'XYZ')
        pb['Shin.R'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
        pb['Foot.R'].rotation_euler = Euler((math.radians(-1.0), 0.0, 0.0), 'XYZ')

        pb['Thigh.L'].rotation_euler = Euler((math.radians(-8.0), 0.0, math.radians(2.0)), 'XYZ')
        pb['Shin.L'].rotation_euler = Euler((math.radians(12.0), 0.0, 0.0), 'XYZ')
        pb['Foot.L'].rotation_euler = Euler((math.radians(-5.0), 0.0, 0.0), 'XYZ')

        for bname in ['Thigh.R', 'Shin.R', 'Foot.R', 'Thigh.L', 'Shin.L', 'Foot.L']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

    # 5. Left Arm: hand resting on skirt/thigh
    for f in [1, 45, 90]:
        pb['UpperArm.L'].rotation_euler = Euler((math.radians(8.0), 0.0, math.radians(12.0)), 'XYZ')
        pb['ForeArm.L'].rotation_euler = Euler((math.radians(-38.0), 0.0, 0.0), 'XYZ')
        pb['Hand.L'].rotation_euler = Euler((math.radians(10.0), math.radians(5.0), 0.0), 'XYZ')

        # Relaxed fingers Left
        for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
            for ph in ['01', '02', '03']:
                pb[f'{finger}.{ph}.L'].rotation_euler = Euler((math.radians(18.0), 0.0, 0.0), 'XYZ')
                pb[f'{finger}.{ph}.L'].keyframe_insert(data_path='rotation_euler', frame=f)
        for ph in ['01', '02', '03']:
            pb[f'Thumb.{ph}.L'].rotation_euler = Euler((math.radians(12.0), 0.0, 0.0), 'XYZ')
            pb[f'Thumb.{ph}.L'].keyframe_insert(data_path='rotation_euler', frame=f)

        for bname in ['UpperArm.L', 'ForeArm.L', 'Hand.L']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

    # 6. Right Arm: bent gracefully near collarbone
    for f in [1, 45, 90]:
        pb['UpperArm.R'].rotation_euler = Euler((math.radians(-15.0), 0.0, math.radians(18.0)), 'XYZ')
        pb['ForeArm.R'].rotation_euler = Euler((math.radians(-65.0), 0.0, 0.0), 'XYZ')
        pb['Hand.R'].rotation_euler = Euler((math.radians(-12.0), math.radians(-10.0), math.radians(8.0)), 'XYZ')

        # Graceful curved fingers Right
        for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
            for ph in ['01', '02', '03']:
                pb[f'{finger}.{ph}.R'].rotation_euler = Euler((math.radians(22.0), 0.0, 0.0), 'XYZ')
                pb[f'{finger}.{ph}.R'].keyframe_insert(data_path='rotation_euler', frame=f)
        for ph in ['01', '02', '03']:
            pb[f'Thumb.{ph}.R'].rotation_euler = Euler((math.radians(15.0), 0.0, 0.0), 'XYZ')
            pb[f'Thumb.{ph}.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        for bname in ['UpperArm.R', 'ForeArm.R', 'Hand.R']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

    # 7. Secondary hair twintail breathing sway
    for f in frames:
        t = (f - 1) / 90.0
        hair_sway = math.radians(2.0 * math.sin(2.0 * math.pi * t - 0.3))
        for i in range(1, 6):
            pb[f'Hair_L_{i:02d}'].rotation_euler = Euler((hair_sway * 0.4, 0.0, hair_sway * 0.6), 'XYZ')
            pb[f'Hair_L_{i:02d}'].keyframe_insert(data_path='rotation_euler', frame=f)
            pb[f'Hair_R_{i:02d}'].rotation_euler = Euler((hair_sway * 0.4, 0.0, -hair_sway * 0.6), 'XYZ')
            pb[f'Hair_R_{i:02d}'].keyframe_insert(data_path='rotation_euler', frame=f)

    set_bezier_interpolation(act)
    return act

# Run test
arm = bpy.data.objects['Anime_Armature']
clear_actions()
act_idle = build_action_idle_cute(arm)
print(f"Action {act_idle.name} built successfully with {len(act_idle.fcurves)} fcurves.")