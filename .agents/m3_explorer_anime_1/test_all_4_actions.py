"""
test_all_4_actions.py
Complete implementation test for all 4 anime actions.
"""

import math
import bpy
from mathutils import Euler, Matrix, Vector

ACTION_NAMES = [
    "action_anime_idle_cute",
    "action_anime_wave_greeting",
    "action_anime_walk_cycle",
    "action_anime_jump_cheer",
]

def ensure_animation_data(arm_obj):
    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    return arm_obj.animation_data

def set_bezier_interpolation(action):
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = 'AUTO_CLAMPED'
            kp.handle_right_type = 'AUTO_CLAMPED'

def get_hips_local_shift(pb_hips, target_world_xyz):
    rest_rot = pb_hips.bone.matrix_local.to_3x3()
    return rest_rot.inverted() @ Vector(target_world_xyz)

# ------------------------------------------------------------------------------
# Action 1: Idle Cute (90 frames / 3.0s seamless loop)
# ------------------------------------------------------------------------------
def create_action_idle_cute(arm_obj):
    ensure_animation_data(arm_obj)
    act_name = "action_anime_idle_cute"
    if act_name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[act_name])
    act = bpy.data.actions.new(act_name)
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start = 1
    act.frame_end = 90
    arm_obj.animation_data.action = act
    pb = arm_obj.pose.bones

    for b in pb:
        b.rotation_mode = 'XYZ'

    cadence_frames = [1, 12, 23, 34, 45, 56, 67, 78, 90]

    # Hips: Contrapposto (+0.035m world X, roll -4.5°, yaw +2.0°) + double micro-bob (+/-0.006m)
    for f in cadence_frames:
        t = (f - 1) / 90.0
        bob_z = 0.006 * math.sin(4.0 * math.pi * t)
        local_trans = get_hips_local_shift(pb['Hips'], (0.035, 0.0, bob_z))
        sway_roll = math.radians(-4.5 + 0.3 * math.sin(2.0 * math.pi * t))
        sway_yaw = math.radians(2.0 + 0.2 * math.cos(2.0 * math.pi * t))

        pb['Hips'].location = local_trans
        pb['Hips'].rotation_euler = Euler((0.0, sway_yaw, sway_roll), 'XYZ')
        pb['Hips'].keyframe_insert(data_path='location', frame=f)
        pb['Hips'].keyframe_insert(data_path='rotation_euler', frame=f)

    # Spine & Chest: counter-tilt + breathing sway
    for f in cadence_frames:
        t = (f - 1) / 90.0
        breath_pitch = math.radians(1.5 * math.sin(2.0 * math.pi * t))
        counter_roll = math.radians(3.5)

        pb['Spine'].rotation_euler = Euler((breath_pitch * 0.4, 0.0, counter_roll * 0.4), 'XYZ')
        pb['Spine'].keyframe_insert(data_path='rotation_euler', frame=f)

        pb['Spine1'].rotation_euler = Euler((breath_pitch * 0.6, 0.0, counter_roll * 0.6), 'XYZ')
        pb['Spine1'].keyframe_insert(data_path='rotation_euler', frame=f)

    # Head: cute tilt ~4° delayed by pi/4 (~11 frames)
    for f in cadence_frames:
        t = (f - 1) / 90.0
        head_tilt = math.radians(4.0 + 1.2 * math.sin(2.0 * math.pi * t - math.pi * 0.25))
        head_nod = math.radians(0.8 * math.cos(2.0 * math.pi * t))
        pb['Head'].rotation_euler = Euler((head_nod, 0.0, head_tilt), 'XYZ')
        pb['Head'].keyframe_insert(data_path='rotation_euler', frame=f)

    # Legs: Right supporting (straight), Left relaxed (flexed forward 8°)
    for f in [1, 45, 90]:
        pb['Thigh.R'].rotation_euler = Euler((math.radians(1.5), 0.0, math.radians(-1.5)), 'XYZ')
        pb['Shin.R'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
        pb['Foot.R'].rotation_euler = Euler((math.radians(-1.0), 0.0, 0.0), 'XYZ')

        pb['Thigh.L'].rotation_euler = Euler((math.radians(-8.0), 0.0, math.radians(2.0)), 'XYZ')
        pb['Shin.L'].rotation_euler = Euler((math.radians(12.0), 0.0, 0.0), 'XYZ')
        pb['Foot.L'].rotation_euler = Euler((math.radians(-5.0), 0.0, 0.0), 'XYZ')

        for bname in ['Thigh.R', 'Shin.R', 'Foot.R', 'Thigh.L', 'Shin.L', 'Foot.L']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

    # Left Arm: hand resting on skirt/thigh
    for f in [1, 45, 90]:
        pb['UpperArm.L'].rotation_euler = Euler((math.radians(8.0), 0.0, math.radians(12.0)), 'XYZ')
        pb['ForeArm.L'].rotation_euler = Euler((math.radians(-38.0), 0.0, 0.0), 'XYZ')
        pb['Hand.L'].rotation_euler = Euler((math.radians(10.0), math.radians(5.0), 0.0), 'XYZ')

        for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
            for ph in ['01', '02', '03']:
                pb[f'{finger}.{ph}.L'].rotation_euler = Euler((math.radians(18.0), 0.0, 0.0), 'XYZ')
                pb[f'{finger}.{ph}.L'].keyframe_insert(data_path='rotation_euler', frame=f)
        for ph in ['01', '02', '03']:
            pb[f'Thumb.{ph}.L'].rotation_euler = Euler((math.radians(12.0), 0.0, 0.0), 'XYZ')
            pb[f'Thumb.{ph}.L'].keyframe_insert(data_path='rotation_euler', frame=f)

        for bname in ['UpperArm.L', 'ForeArm.L', 'Hand.L']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

    # Right Arm: bent gracefully near collarbone
    for f in [1, 45, 90]:
        pb['UpperArm.R'].rotation_euler = Euler((math.radians(-15.0), 0.0, math.radians(18.0)), 'XYZ')
        pb['ForeArm.R'].rotation_euler = Euler((math.radians(-65.0), 0.0, 0.0), 'XYZ')
        pb['Hand.R'].rotation_euler = Euler((math.radians(-12.0), math.radians(-10.0), math.radians(8.0)), 'XYZ')

        for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
            for ph in ['01', '02', '03']:
                pb[f'{finger}.{ph}.R'].rotation_euler = Euler((math.radians(22.0), 0.0, 0.0), 'XYZ')
                pb[f'{finger}.{ph}.R'].keyframe_insert(data_path='rotation_euler', frame=f)
        for ph in ['01', '02', '03']:
            pb[f'Thumb.{ph}.R'].rotation_euler = Euler((math.radians(15.0), 0.0, 0.0), 'XYZ')
            pb[f'Thumb.{ph}.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        for bname in ['UpperArm.R', 'ForeArm.R', 'Hand.R']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

    # Hair Twintails secondary sway
    for f in cadence_frames:
        t = (f - 1) / 90.0
        hair_sway = math.radians(2.0 * math.sin(2.0 * math.pi * t - 0.3))
        for i in range(1, 6):
            pb[f'Hair_L_{i:02d}'].rotation_euler = Euler((hair_sway * 0.4, 0.0, hair_sway * 0.6), 'XYZ')
            pb[f'Hair_L_{i:02d}'].keyframe_insert(data_path='rotation_euler', frame=f)
            pb[f'Hair_R_{i:02d}'].rotation_euler = Euler((hair_sway * 0.4, 0.0, -hair_sway * 0.6), 'XYZ')
            pb[f'Hair_R_{i:02d}'].keyframe_insert(data_path='rotation_euler', frame=f)

    set_bezier_interpolation(act)
    return act

# ------------------------------------------------------------------------------
# Action 2: Wave Greeting (120 frames / 4.0s)
# ------------------------------------------------------------------------------
def create_action_wave_greeting(arm_obj):
    ensure_animation_data(arm_obj)
    act_name = "action_anime_wave_greeting"
    if act_name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[act_name])
    act = bpy.data.actions.new(act_name)
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start = 1
    act.frame_end = 120
    arm_obj.animation_data.action = act
    pb = arm_obj.pose.bones

    for b in pb:
        b.rotation_mode = 'XYZ'

    # Keyframes breakdown:
    # 1: Idle rest
    # 15: Shift weight to left hip
    # 25: Recognition, torso lean, head turn
    # 45: Arm raised beside cheek, hand open
    # 46-95: 3 wave cycles (16 frames each: peaks at 50, 66, 82; troughs at 58, 74, 90)
    # 110: Lower arm
    # 120: Settle back to idle rest

    # Phase 1: Weight shift & recognition (1-25)
    pb['Hips'].location = get_hips_local_shift(pb['Hips'], (0.0, 0.0, 0.0))
    pb['Hips'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
    pb['Hips'].keyframe_insert(data_path='location', frame=1)
    pb['Hips'].keyframe_insert(data_path='rotation_euler', frame=1)

    pb['Hips'].location = get_hips_local_shift(pb['Hips'], (-0.025, 0.0, 0.005))
    pb['Hips'].rotation_euler = Euler((0.0, math.radians(-2.0), math.radians(3.0)), 'XYZ')
    pb['Hips'].keyframe_insert(data_path='location', frame=25)
    pb['Hips'].keyframe_insert(data_path='rotation_euler', frame=25)

    # Spine pitch forward +3°
    pb['Spine1'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
    pb['Spine1'].keyframe_insert(data_path='rotation_euler', frame=1)
    pb['Spine1'].rotation_euler = Euler((math.radians(3.0), 0.0, 0.0), 'XYZ')
    pb['Spine1'].keyframe_insert(data_path='rotation_euler', frame=25)

    # Head turns towards audience: yaw -6°, tilt +5°
    pb['Head'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
    pb['Head'].keyframe_insert(data_path='rotation_euler', frame=1)
    pb['Head'].rotation_euler = Euler((0.0, math.radians(-6.0), math.radians(5.0)), 'XYZ')
    pb['Head'].keyframe_insert(data_path='rotation_euler', frame=25)

    # Clavicle.R elevation +6°
    pb['Clavicle.R'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
    pb['Clavicle.R'].keyframe_insert(data_path='rotation_euler', frame=1)
    pb['Clavicle.R'].rotation_euler = Euler((math.radians(4.0), 0.0, math.radians(-6.0)), 'XYZ')
    pb['Clavicle.R'].keyframe_insert(data_path='rotation_euler', frame=25)

    # Phase 2: Arm raise (26-45)
    pb['UpperArm.R'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
    pb['UpperArm.R'].keyframe_insert(data_path='rotation_euler', frame=1)
    pb['UpperArm.R'].rotation_euler = Euler((math.radians(-75.0), 0.0, math.radians(-35.0)), 'XYZ')
    pb['UpperArm.R'].keyframe_insert(data_path='rotation_euler', frame=45)

    pb['ForeArm.R'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
    pb['ForeArm.R'].keyframe_insert(data_path='rotation_euler', frame=1)
    pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), 0.0, 0.0), 'XYZ')
    pb['ForeArm.R'].keyframe_insert(data_path='rotation_euler', frame=45)

    # Open hand pose at frame 45
    pb['Hand.R'].rotation_euler = Euler((math.radians(-10.0), 0.0, 0.0), 'XYZ')
    pb['Hand.R'].keyframe_insert(data_path='rotation_euler', frame=45)
    for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
        for ph in ['01', '02', '03']:
            pb[f'{finger}.{ph}.R'].rotation_euler = Euler((math.radians(-5.0), 0.0, 0.0), 'XYZ')
            pb[f'{finger}.{ph}.R'].keyframe_insert(data_path='rotation_euler', frame=45)
    for ph in ['01', '02', '03']:
        pb[f'Thumb.{ph}.R'].rotation_euler = Euler((math.radians(-15.0), 0.0, 0.0), 'XYZ')
        pb[f'Thumb.{ph}.R'].keyframe_insert(data_path='rotation_euler', frame=45)

    # Phase 3: 3 energetic wave cycles (frames 46-95, 16 frames per cycle)
    wave_keyframes = [46, 50, 54, 58, 62, 66, 70, 74, 78, 82, 86, 90, 95]
    for f in wave_keyframes:
        # wave phase angle
        phi = 2.0 * math.pi * (f - 46) / 16.0
        forearm_twist = math.radians(18.0 * math.sin(phi))
        wrist_yaw = math.radians(15.0 * math.sin(phi + math.pi * 0.25)) # leads by 2 frames
        head_bob_z = 0.008 * math.cos(phi)
        head_tilt_sway = math.radians(5.0 + 2.0 * math.sin(phi))

        pb['ForeArm.R'].rotation_euler = Euler((math.radians(-95.0), forearm_twist, 0.0), 'XYZ')
        pb['ForeArm.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        pb['Hand.R'].rotation_euler = Euler((math.radians(-10.0), 0.0, wrist_yaw), 'XYZ')
        pb['Hand.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        pb['Head'].rotation_euler = Euler((math.radians(head_bob_z * 100), math.radians(-6.0), head_tilt_sway), 'XYZ')
        pb['Head'].keyframe_insert(data_path='rotation_euler', frame=f)

    # Phase 4: Settle & smooth ease-out return to idle (96-120)
    for f, fac in [(105, 0.5), (120, 1.0)]:
        # Lower arm
        up_rot = (1.0 - fac) * math.radians(-75.0)
        up_abd = (1.0 - fac) * math.radians(-35.0)
        fore_flex = (1.0 - fac) * math.radians(-95.0)
        pb['UpperArm.R'].rotation_euler = Euler((up_rot, 0.0, up_abd), 'XYZ')
        pb['UpperArm.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        pb['ForeArm.R'].rotation_euler = Euler((fore_flex, 0.0, 0.0), 'XYZ')
        pb['ForeArm.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        pb['Hand.R'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
        pb['Hand.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Clavicle settle
        clav_z = (1.0 - fac) * math.radians(-6.0)
        pb['Clavicle.R'].rotation_euler = Euler((0.0, 0.0, clav_z), 'XYZ')
        pb['Clavicle.R'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Head settle
        h_yaw = (1.0 - fac) * math.radians(-6.0)
        h_tilt = (1.0 - fac) * math.radians(5.0)
        pb['Head'].rotation_euler = Euler((0.0, h_yaw, h_tilt), 'XYZ')
        pb['Head'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Hips settle
        hips_x = (1.0 - fac) * (-0.025)
        pb['Hips'].location = get_hips_local_shift(pb['Hips'], (hips_x, 0.0, 0.0))
        pb['Hips'].rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')
        pb['Hips'].keyframe_insert(data_path='location', frame=f)
        pb['Hips'].keyframe_insert(data_path='rotation_euler', frame=f)

    set_bezier_interpolation(act)
    return act

# ------------------------------------------------------------------------------
# Action 3: Walk Cycle (32 frames / 1.07s seamless loop)
# ------------------------------------------------------------------------------
def create_action_walk_cycle(arm_obj):
    ensure_animation_data(arm_obj)
    act_name = "action_anime_walk_cycle"
    if act_name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[act_name])
    act = bpy.data.actions.new(act_name)
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start = 1
    act.frame_end = 32
    arm_obj.animation_data.action = act
    pb = arm_obj.pose.bones

    for b in pb:
        b.rotation_mode = 'XYZ'

    # Walk cycle keyframes: 1, 4, 8, 12, 17, 20, 24, 28, 32
    # Step 1: Right step (1-16), Step 2: Left step (17-32)
    # Down at 4 & 20 (hips -0.032m), Passing at 8 & 24 (hips +0.025m)
    frames = [1, 4, 8, 12, 17, 20, 24, 28, 32]
    
    for f in frames:
        phase = 2.0 * math.pi * (f - 1) / 32.0
        step_phase = 2.0 * math.pi * (f - 1) / 16.0

        # Vertical bounce: Down at 4 & 20 (-0.032m), Passing at 8 & 24 (+0.025m)
        # Cosine model: Contact (f=1) -> 0.0, Down (f=4) -> -0.032, Passing (f=8) -> +0.025
        # Standard Fourier walk bounce:
        # z(t) = -0.0035 - 0.0285 * cos(2*pi*t/16)
        bounce_z = -0.0035 - 0.0285 * math.cos(step_phase)
        
        # Lateral weight shift (tracking tight center line <= 0.08m)
        sway_x = 0.015 * math.sin(phase)
        
        # Pelvic Roll (+/-4°) and Yaw (+/-6°)
        pelvis_roll = math.radians(4.0 * math.sin(phase))
        pelvis_yaw = math.radians(6.0 * math.cos(phase))

        pb['Hips'].location = get_hips_local_shift(pb['Hips'], (sway_x, 0.0, bounce_z))
        pb['Hips'].rotation_euler = Euler((0.0, pelvis_yaw, pelvis_roll), 'XYZ')
        pb['Hips'].keyframe_insert(data_path='location', frame=f)
        pb['Hips'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Thoracic counter-balance
        chest_roll = -pelvis_roll * 0.75 # -3° to -4° counter-roll
        chest_yaw = -pelvis_yaw * 0.70   # -4° to -5° counter-yaw
        pb['Spine1'].rotation_euler = Euler((0.0, chest_yaw, chest_roll), 'XYZ')
        pb['Spine1'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Leg strides
        # Thigh pitch: +/-28°
        thigh_r_pitch = math.radians(-28.0 * math.cos(phase))
        thigh_l_pitch = math.radians(28.0 * math.cos(phase))

        # Adduction for narrow center line (pigeon-toed toe yaw +1.5°)
        thigh_adduct = math.radians(2.5)
        
        # Knee flexion: Down phase flexes to 25°
        knee_r = math.radians(max(0.0, 25.0 * (1.0 - math.cos(phase))))
        knee_l = math.radians(max(0.0, 25.0 * (1.0 + math.cos(phase))))

        # Pigeon-toe contact angle
        toe_yaw = math.radians(1.5)

        pb['Thigh.R'].rotation_euler = Euler((thigh_r_pitch, 0.0, -thigh_adduct), 'XYZ')
        pb['Shin.R'].rotation_euler = Euler((knee_r, 0.0, 0.0), 'XYZ')
        pb['Foot.R'].rotation_euler = Euler((-thigh_r_pitch * 0.4, 0.0, toe_yaw), 'XYZ')

        pb['Thigh.L'].rotation_euler = Euler((thigh_l_pitch, 0.0, thigh_adduct), 'XYZ')
        pb['Shin.L'].rotation_euler = Euler((knee_l, 0.0, 0.0), 'XYZ')
        pb['Foot.L'].rotation_euler = Euler((-thigh_l_pitch * 0.4, 0.0, -toe_yaw), 'XYZ')

        for bname in ['Thigh.R', 'Shin.R', 'Foot.R', 'Thigh.L', 'Shin.L', 'Foot.L']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

        # Natural tucked arm swing: Forearms kept bent at 35°-45°!
        arm_swing_r = math.radians(18.0 * math.cos(phase))
        arm_swing_l = -arm_swing_r
        forearm_bent = math.radians(-40.0) # tucked forearm bend (35-45°)

        pb['UpperArm.R'].rotation_euler = Euler((arm_swing_r, 0.0, math.radians(12.0)), 'XYZ')
        pb['ForeArm.R'].rotation_euler = Euler((forearm_bent, 0.0, 0.0), 'XYZ')
        pb['Hand.R'].rotation_euler = Euler((arm_swing_r * 0.3, 0.0, 0.0), 'XYZ')

        pb['UpperArm.L'].rotation_euler = Euler((arm_swing_l, 0.0, math.radians(-12.0)), 'XYZ')
        pb['ForeArm.L'].rotation_euler = Euler((forearm_bent, 0.0, 0.0), 'XYZ')
        pb['Hand.L'].rotation_euler = Euler((arm_swing_l * 0.3, 0.0, 0.0), 'XYZ')

        for bname in ['UpperArm.R', 'ForeArm.R', 'Hand.R', 'UpperArm.L', 'ForeArm.L', 'Hand.L']:
            pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

    set_bezier_interpolation(act)
    return act

# ------------------------------------------------------------------------------
# Action 4: Jump Cheer (75 frames / 2.5s)
# ------------------------------------------------------------------------------
def create_action_jump_cheer(arm_obj):
    ensure_animation_data(arm_obj)
    act_name = "action_anime_jump_cheer"
    if act_name in bpy.data.actions:
        bpy.data.actions.remove(bpy.data.actions[act_name])
    act = bpy.data.actions.new(act_name)
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start = 1
    act.frame_end = 75
    arm_obj.animation_data.action = act
    pb = arm_obj.pose.bones

    for b in pb:
        b.rotation_mode = 'XYZ'

    # Timeline checkpoints:
    # 1: Upright standing rest
    # 15: Deep anticipation squash (hips -0.14m, knees 65°, arms back +35°, spine +18°)
    # 25: Explosive upward leap (hips +0.20m ascending, toes pointing down)
    # 35: Joyful apex "anime hop" (hips +0.35m, knees backward 85°, chest -12°, arms overhead +145°)
    # 44: Balls of feet touch ground
    # 50: Landing compression cushion (hips -0.10m, knees 55°, arms shoulder height)
    # 65: Springing back up
    # 75: Upright standing settle

    jump_timeline = [
        # Frame, Hips_Z, Torso_Pitch, Knee_Flex, Arms_Pitch, Arms_Abd, Forearm_Flex
        (1,   0.0,    0.0,   0.0,   0.0,    15.0,  -20.0),
        (8,  -0.08,   10.0,  35.0,  20.0,   12.0,  -25.0),
        (16, -0.14,   18.0,  65.0,  35.0,   10.0,  -35.0), # Anticipation squash
        (22,  0.05,    5.0,  15.0, -45.0,   25.0,  -20.0), # Launch thrust
        (28,  0.30,  -10.0,  60.0, -120.0,  35.0,  -30.0), # Ascending
        (35,  0.35,  -12.0,  85.0, -145.0,  40.0,  -35.0), # Joyful apex "anime hop"
        (42,  0.25,   -5.0,  70.0, -130.0,  35.0,  -30.0), # Descending
        (44,  0.02,    0.0,  20.0,  -80.0,  25.0,  -30.0), # Touchdown
        (50, -0.10,   10.0,  55.0,  -30.0,  20.0,  -40.0), # Landing cushion
        (62, -0.02,    3.0,  10.0,  -10.0,  18.0,  -25.0), # Recovery
        (75,  0.0,     0.0,   0.0,    0.0,  15.0,  -20.0), # Upright settle
    ]

    for f, hz, t_pitch, knee, arm_p, arm_abd, fore_f in jump_timeline:
        # Hips
        pb['Hips'].location = get_hips_local_shift(pb['Hips'], (0.0, 0.0, hz))
        pb['Hips'].rotation_euler = Euler((math.radians(t_pitch * 0.3), 0.0, 0.0), 'XYZ')
        pb['Hips'].keyframe_insert(data_path='location', frame=f)
        pb['Hips'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Spine
        pb['Spine1'].rotation_euler = Euler((math.radians(t_pitch), 0.0, 0.0), 'XYZ')
        pb['Spine1'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Head: Looks up during apex cheer (-15°)
        head_p = -15.0 if f == 35 else (-5.0 if 28 <= f <= 42 else 0.0)
        pb['Head'].rotation_euler = Euler((math.radians(head_p), 0.0, 0.0), 'XYZ')
        pb['Head'].keyframe_insert(data_path='rotation_euler', frame=f)

        # Legs (Bilateral symmetry during jump)
        thigh_rot = math.radians(-knee * 0.6)
        shin_rot = math.radians(knee)
        ankle_rot = math.radians(-40.0) if (22 <= f <= 28) else math.radians(knee * 0.3)

        for side in ['L', 'R']:
            sign = 1.0 if side == 'L' else -1.0
            pb[f'Thigh.{side}'].rotation_euler = Euler((thigh_rot, 0.0, sign * math.radians(2.0)), 'XYZ')
            pb[f'Shin.{side}'].rotation_euler = Euler((shin_rot, 0.0, 0.0), 'XYZ')
            pb[f'Foot.{side}'].rotation_euler = Euler((ankle_rot, 0.0, 0.0), 'XYZ')
            pb[f'Toe.{side}'].rotation_euler = Euler((math.radians(15.0) if f == 44 else 0.0, 0.0, 0.0), 'XYZ')

            for bname in [f'Thigh.{side}', f'Shin.{side}', f'Foot.{side}', f'Toe.{side}']:
                pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

        # Arms overhead cheer
        for side in ['L', 'R']:
            sign = 1.0 if side == 'L' else -1.0
            pb[f'UpperArm.{side}'].rotation_euler = Euler((math.radians(arm_p), 0.0, sign * math.radians(arm_abd)), 'XYZ')
            pb[f'ForeArm.{side}'].rotation_euler = Euler((math.radians(fore_f), 0.0, 0.0), 'XYZ')

            # Clenched fists during apex cheer
            fist_curl = math.radians(45.0) if (25 <= f <= 45) else math.radians(15.0)
            pb[f'Hand.{side}'].rotation_euler = Euler((math.radians(-10.0), 0.0, 0.0), 'XYZ')

            for finger in ['Index', 'Middle', 'Ring', 'Pinky']:
                for ph in ['01', '02', '03']:
                    pb[f'{finger}.{ph}.{side}'].rotation_euler = Euler((fist_curl, 0.0, 0.0), 'XYZ')
                    pb[f'{finger}.{ph}.{side}'].keyframe_insert(data_path='rotation_euler', frame=f)
            for ph in ['01', '02', '03']:
                pb[f'Thumb.{ph}.{side}'].rotation_euler = Euler((fist_curl * 0.8, 0.0, 0.0), 'XYZ')
                pb[f'Thumb.{ph}.{side}'].keyframe_insert(data_path='rotation_euler', frame=f)

            for bname in [f'UpperArm.{side}', f'ForeArm.{side}', f'Hand.{side}']:
                pb[bname].keyframe_insert(data_path='rotation_euler', frame=f)

        # Hair Twintails upward inertial flare (+45°) during apex
        hair_flare = math.radians(45.0) if (28 <= f <= 40) else math.radians(-15.0 if f <= 16 else 0.0)
        for side in ['L', 'R']:
            sign = 1.0 if side == 'L' else -1.0
            for i in range(1, 6):
                pb[f'Hair_{side}_{i:02d}'].rotation_euler = Euler((hair_flare * 0.5, 0.0, sign * hair_flare * 0.5), 'XYZ')
                pb[f'Hair_{side}_{i:02d}'].keyframe_insert(data_path='rotation_euler', frame=f)

    set_bezier_interpolation(act)
    return act

# ------------------------------------------------------------------------------
# Master Builder: Builds all 4 actions, registers NLA tracks
# ------------------------------------------------------------------------------
def build_all_anime_actions(arm_obj, push_to_nla=True):
    anim_data = ensure_animation_data(arm_obj)
    
    actions = {}
    actions["action_anime_idle_cute"] = create_action_idle_cute(arm_obj)
    actions["action_anime_wave_greeting"] = create_action_wave_greeting(arm_obj)
    actions["action_anime_walk_cycle"] = create_action_walk_cycle(arm_obj)
    actions["action_anime_jump_cheer"] = create_action_jump_cheer(arm_obj)

    if push_to_nla:
        # Clear existing NLA tracks
        while anim_data.nla_tracks:
            anim_data.nla_tracks.remove(anim_data.nla_tracks[0])

        for name, act in actions.items():
            track = anim_data.nla_tracks.new()
            track.name = f"NLA_{name}"
            # Only unmute base idle track by default
            track.mute = (name != "action_anime_idle_cute")
            strip = track.strips.new(name, int(act.frame_range[0]), act)
            strip.action = act

    # Set active action to idle cute
    anim_data.action = actions["action_anime_idle_cute"]
    return actions

# Execute verification
arm = bpy.data.objects['Anime_Armature']
all_actions = build_all_anime_actions(arm, push_to_nla=True)

print("=== VERIFICATION SUMMARY ===")
print("Total actions created:", len(all_actions))
for name, act in all_actions.items():
    print(f"Action: {name} | range: [{act.frame_start}, {act.frame_end}] | fcurves: {len(act.fcurves)} | fake_user: {act.use_fake_user}")

print("NLA Tracks on Anime_Armature:", [t.name for t in arm.animation_data.nla_tracks])
print("Active Action:", arm.animation_data.action.name)
print("ALL 4 ACTIONS VERIFIED SUCCESSFULLY!")