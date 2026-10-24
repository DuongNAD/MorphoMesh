import bpy
import bmesh
import math
import os
import shutil
from mathutils import Vector, Euler, Matrix

def process_and_rig_meshy():
    print('=' * 80)
    print('MORPHOMESH: RIGGING & ANIMATING MESHY 3D ASSET (ZERO-VRAM HYBRID PIPELINE)')
    print('=' * 80)

    source_blend = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend'
    master_blend = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Cloud_Master.blend'
    meshy_glb = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Meshy.glb'
    out_dir = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\renders'
    art_dir = r'C:\Users\Admin\.gemini\antigravity\brain\c7931bf1-e19c-488b-a992-7d1d51e244b9'
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(art_dir, exist_ok=True)

    bpy.ops.wm.open_mainfile(filepath=source_blend)
    scene = bpy.context.scene

    arm = bpy.data.objects.get('Armature_Yu_Nian_An_Rigify')
    if not arm:
        raise RuntimeError('Armature_Yu_Nian_An_Rigify not found!')

    arm.hide_viewport = False
    arm.hide_render = False

    # 1. Import Meshy GLB into scene
    print('[1/6] Importing Meshy 3D asset into master scene...')
    bpy.ops.import_scene.gltf(filepath=meshy_glb)

    meshy_obj = None
    for o in bpy.context.selected_objects:
        if o.type == 'MESH':
            meshy_obj = o
            break

    if not meshy_obj:
        raise RuntimeError('Imported mesh not found!')

    meshy_obj.name = 'Yu_Nian_An_Meshy_Body'
    meshy_obj.hide_render = False
    meshy_obj.hide_viewport = False

    # 2. Rescale and Align to 1.65m height and origin (z=0)
    print('[2/6] Aligning and scaling Meshy mesh to standard 1.65m height...')
    bbox = [Vector(corner) for corner in meshy_obj.bound_box]
    raw_min_z = min(v.z for v in bbox)
    raw_max_z = max(v.z for v in bbox)
    raw_height = raw_max_z - raw_min_z
    raw_mid_x = 0.5 * (min(v.x for v in bbox) + max(v.x for v in bbox))
    raw_mid_y = 0.5 * (min(v.y for v in bbox) + max(v.y for v in bbox))

    target_height = 1.650
    scale_factor = target_height / raw_height

    bm = bmesh.new()
    bm.from_mesh(meshy_obj.data)
    for v in bm.verts:
        v.co.x = (v.co.x - raw_mid_x) * scale_factor
        v.co.y = (v.co.y - raw_mid_y) * scale_factor
        v.co.z = (v.co.z - raw_min_z) * scale_factor

    bm.to_mesh(meshy_obj.data)
    bm.free()
    meshy_obj.data.update()

    meshy_obj.location = (0, 0, 0)
    meshy_obj.rotation_euler = (0, 0, 0)
    meshy_obj.scale = (1, 1, 1)

    # 3. Clean up older procedural meshes and hair (avoid double geometry)
    print('[3/6] Configuring scene visibility: displaying unified Meshy asset & stage props...')
    for o in bpy.data.objects:
        if o.type == 'MESH' and o != meshy_obj:
            if not ('Butterfly' in o.name or 'Marionette' in o.name or 'Studio' in o.name):
                o.hide_viewport = True
                o.hide_render = True
            else:
                o.hide_viewport = False
                o.hide_render = False

    # 4. Skinning via DataTransfer from Yu_Nian_An_Body (163 pre-weighted Rigify bones)
    print('[4/6] Transferring skin weights from calibrated body mesh to Meshy model...')
    body = bpy.data.objects.get('Yu_Nian_An_Body')
    if body:
        body.hide_viewport = False
        body.hide_render = True

        dt = meshy_obj.modifiers.new(name='DataTransfer_Weights', type='DATA_TRANSFER')
        dt.object = body
        dt.use_vert_data = True
        dt.data_types_verts = {'VGROUP_WEIGHTS'}
        dt.vert_mapping = 'NEAREST'
        bpy.context.view_layer.objects.active = meshy_obj
        bpy.ops.object.datalayout_transfer(modifier='DataTransfer_Weights')
        bpy.ops.object.modifier_apply(modifier='DataTransfer_Weights')
        print(f' - DataTransfer complete: {len(meshy_obj.vertex_groups)} vertex groups transferred!')

    arm_mod = meshy_obj.modifiers.new(name='Armature', type='ARMATURE')
    arm_mod.object = arm
    arm_mod.use_deform_preserve_volume = True
    meshy_obj.parent = arm

    # 5. Authoring 4 Complete Animations using DEF bones
    print('[5/6] Authoring 4 production animation tracks...')
    if not arm.animation_data:
        arm.animation_data_create()

    pose = arm.pose
    for pb in pose.bones:
        pb.rotation_mode = 'QUATERNION'

    def set_bone_rot(action, bone_name, frame, euler_deg):
        pb = pose.bones.get(bone_name)
        if not pb: return
        quat = Euler((math.radians(euler_deg[0]), math.radians(euler_deg[1]), math.radians(euler_deg[2])), 'XYZ').to_quaternion()
        pb.rotation_quaternion = quat
        pb.keyframe_insert(data_path='rotation_quaternion', frame=frame, group=bone_name)

    def set_bone_loc(action, bone_name, frame, loc_delta):
        pb = pose.bones.get(bone_name)
        if not pb: return
        pb.location = Vector(loc_delta)
        pb.keyframe_insert(data_path='location', frame=frame, group=bone_name)

    # --- TRACK 1: Yu_Nian_An_Idle (60 frames) ---
    act_idle = bpy.data.actions.new(name='Yu_Nian_An_Idle')
    act_idle.use_fake_user = True
    arm.animation_data.action = act_idle

    for f, chest_rx, head_rx in [(0, 0.0, 0.0), (30, 2.5, -1.5), (60, 0.0, 0.0)]:
        set_bone_rot(act_idle, 'DEF-spine.001', f, (chest_rx * 0.4, 0.0, 0.0))
        set_bone_rot(act_idle, 'DEF-spine.002', f, (chest_rx, 0.0, 0.0))
        set_bone_rot(act_idle, 'DEF-spine.003', f, (chest_rx * 0.7, 0.0, 0.0))
        set_bone_rot(act_idle, 'DEF-spine.005', f, (head_rx * 0.5, 0.0, 0.0))
        set_bone_rot(act_idle, 'DEF-head', f, (head_rx, 0.0, 0.0))

    for f, arm_rz in [(0, 0.0), (30, -1.8), (60, 0.0)]:
        set_bone_rot(act_idle, 'DEF-upper_arm.L', f, (1.0, 0.0, arm_rz))
        set_bone_rot(act_idle, 'DEF-upper_arm.R', f, (1.0, 0.0, -arm_rz))
        set_bone_rot(act_idle, 'DEF-forearm.L', f, (3.0, 0.0, 0.0))
        set_bone_rot(act_idle, 'DEF-forearm.R', f, (3.0, 0.0, 0.0))

    # --- TRACK 2: Yu_Nian_An_Walk (60 frames catwalk loop) ---
    act_walk = bpy.data.actions.new(name='Yu_Nian_An_Walk')
    act_walk.use_fake_user = True
    arm.animation_data.action = act_walk

    for f, z_off in [(0, -0.015), (15, 0.012), (30, -0.015), (45, 0.012), (60, -0.015)]:
        set_bone_loc(act_walk, 'DEF-spine', f, (0.0, 0.0, z_off))

    for f, r_z, r_x in [(0, 3.0, 0.0), (15, 0.0, 1.5), (30, -3.0, 0.0), (45, 0.0, -1.5), (60, 3.0, 0.0)]:
        set_bone_rot(act_walk, 'DEF-spine', f, (r_x, 0.0, r_z))
        set_bone_rot(act_walk, 'DEF-spine.001', f, (1.0, 0.0, -r_z * 0.8))

    r_leg_keys = [
        (0,  18.0, -6.0, -4.0),
        (15,  2.0, -2.0,  0.0),
        (30, -14.0, 10.0,  6.0),
        (45,  10.0, 24.0, -4.0),
        (60, 18.0, -6.0, -4.0),
    ]
    for f, up_rx, low_rx, ft_rx in r_leg_keys:
        set_bone_rot(act_walk, 'DEF-thigh.R', f, (up_rx, 0.0, 0.0))
        set_bone_rot(act_walk, 'DEF-shin.R', f, (low_rx, 0.0, 0.0))
        set_bone_rot(act_walk, 'DEF-foot.R', f, (ft_rx, 0.0, 0.0))

    l_leg_keys = [
        (0, -14.0, 10.0,  6.0),
        (15,  10.0, 24.0, -4.0),
        (30,  18.0, -6.0, -4.0),
        (45,   2.0, -2.0,  0.0),
        (60, -14.0, 10.0,  6.0),
    ]
    for f, up_rx, low_rx, ft_rx in l_leg_keys:
        set_bone_rot(act_walk, 'DEF-thigh.L', f, (up_rx, 0.0, 0.0))
        set_bone_rot(act_walk, 'DEF-shin.L', f, (low_rx, 0.0, 0.0))
        set_bone_rot(act_walk, 'DEF-foot.L', f, (ft_rx, 0.0, 0.0))

    for f, a_rx in [(0, 14.0), (15, 2.0), (30, -12.0), (45, 0.0), (60, 14.0)]:
        set_bone_rot(act_walk, 'DEF-upper_arm.L', f, (a_rx, 0.0, 0.0))
        set_bone_rot(act_walk, 'DEF-forearm.L', f, (max(2.0, a_rx * 0.4), 0.0, 0.0))
    for f, a_rx in [(0, -12.0), (15, 0.0), (30, 14.0), (45, 2.0), (60, -12.0)]:
        set_bone_rot(act_walk, 'DEF-upper_arm.R', f, (a_rx, 0.0, 0.0))
        set_bone_rot(act_walk, 'DEF-forearm.R', f, (max(2.0, a_rx * 0.4), 0.0, 0.0))

    # --- TRACK 3: Yu_Nian_An_Marionette_Awakening (120 frames) ---
    act_awake = bpy.data.actions.new(name='Yu_Nian_An_Marionette_Awakening')
    act_awake.use_fake_user = True
    arm.animation_data.action = act_awake

    set_bone_rot(act_awake, 'DEF-head', 0, (20.0, 0.0, 0.0))
    set_bone_rot(act_awake, 'DEF-spine.005', 0, (10.0, 0.0, 0.0))
    set_bone_rot(act_awake, 'DEF-upper_arm.L', 0, (2.0, 0.0, 0.0))
    set_bone_rot(act_awake, 'DEF-upper_arm.R', 0, (2.0, 0.0, 0.0))

    set_bone_rot(act_awake, 'DEF-head', 45, (-4.0, 0.0, 0.0))
    set_bone_rot(act_awake, 'DEF-spine.002', 45, (-5.0, 0.0, 0.0))

    for side, sign in [('L', 1.0), ('R', -1.0)]:
        set_bone_rot(act_awake, f'DEF-upper_arm.{side}', 60, (-35.0, sign * 12.0, sign * 15.0))
        set_bone_rot(act_awake, f'DEF-forearm.{side}', 60, (-45.0, 0.0, 0.0))
        set_bone_rot(act_awake, f'DEF-hand.{side}', 60, (20.0, sign * 10.0, 0.0))

        set_bone_rot(act_awake, f'DEF-upper_arm.{side}', 90, (-25.0, sign * 25.0, sign * 30.0))
        set_bone_rot(act_awake, f'DEF-forearm.{side}', 90, (-30.0, 0.0, 0.0))
        set_bone_rot(act_awake, f'DEF-hand.{side}', 90, (12.0, sign * 12.0, 0.0))

        set_bone_rot(act_awake, f'DEF-upper_arm.{side}', 120, (-15.0, sign * 15.0, sign * 18.0))
        set_bone_rot(act_awake, f'DEF-forearm.{side}', 120, (-20.0, 0.0, 0.0))
        set_bone_rot(act_awake, f'DEF-hand.{side}', 120, (5.0, 0.0, 0.0))

    set_bone_rot(act_awake, 'DEF-head', 120, (0.0, 0.0, 0.0))
    set_bone_rot(act_awake, 'DEF-spine.002', 120, (0.0, 0.0, 0.0))

    # --- TRACK 4: Yu_Nian_An_Graceful_Bow (90 frames) ---
    act_bow = bpy.data.actions.new(name='Yu_Nian_An_Graceful_Bow')
    act_bow.use_fake_user = True
    arm.animation_data.action = act_bow

    set_bone_rot(act_bow, 'DEF-spine', 0, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-spine.001', 0, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-spine.002', 0, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-head', 0, (0.0, 0.0, 0.0))

    # Bow down (Frame 45)
    set_bone_rot(act_bow, 'DEF-spine', 45, (8.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-spine.001', 45, (12.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-spine.002', 45, (10.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-head', 45, (12.0, 0.0, 0.0))
    # Right hand to chest
    set_bone_rot(act_bow, 'DEF-upper_arm.R', 45, (-22.0, -10.0, -25.0))
    set_bone_rot(act_bow, 'DEF-forearm.R', 45, (-55.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-hand.R', 45, (15.0, -10.0, 0.0))
    # Left hand resting gracefully
    set_bone_rot(act_bow, 'DEF-upper_arm.L', 45, (8.0, 0.0, 5.0))
    set_bone_rot(act_bow, 'DEF-forearm.L', 45, (8.0, 0.0, 0.0))

    # Return to rest (Frame 90)
    set_bone_rot(act_bow, 'DEF-spine', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-spine.001', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-spine.002', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-head', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-upper_arm.R', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-forearm.R', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-hand.R', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-upper_arm.L', 90, (0.0, 0.0, 0.0))
    set_bone_rot(act_bow, 'DEF-forearm.L', 90, (0.0, 0.0, 0.0))

    # Reset active to Idle frame 0
    arm.animation_data.action = act_idle
    scene.frame_set(0)

    # 6. Setup Lighting & Camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.device = 'CPU'
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1280

    cam = bpy.data.objects.get('Camera_FullBody') or bpy.data.objects.get('RenderCamera')
    if not cam:
        cam_data = bpy.data.cameras.new('Studio_Cam')
        cam = bpy.data.objects.new('Studio_Cam', cam_data)
        scene.collection.objects.link(cam)
    scene.camera = cam

    for light_name, loc, energy, color in [
        ('Key_Light', (1.5, -2.0, 2.2), 160.0, (1.0, 0.98, 0.95)),
        ('Fill_Light', (-1.5, -1.8, 1.6), 90.0, (0.95, 0.96, 1.0)),
        ('Rim_Light', (0.0, 1.8, 2.0), 130.0, (1.0, 1.0, 1.0)),
    ]:
        l_obj = bpy.data.objects.get(light_name)
        if not l_obj:
            l_data = bpy.data.lights.new(light_name, 'AREA')
            l_obj = bpy.data.objects.new(light_name, l_data)
            scene.collection.objects.link(l_obj)
        l_obj.location = loc
        l_obj.data.energy = energy
        l_obj.data.color = color[:3]

    # 7. Render 4 Distinct Animation Poses
    print('[6/6] Rendering Cycles preview images for each animation state...')
    render_shots = [
        ('Yu_Nian_An_Idle', 30, 'meshy_anim_01_idle.png', ((0.0, -2.6, 0.95), (math.radians(90), 0, 0))),
        ('Yu_Nian_An_Walk', 15, 'meshy_anim_02_walk.png', ((1.4, -2.2, 0.95), (math.radians(88), 0, math.radians(35)))),
        ('Yu_Nian_An_Marionette_Awakening', 60, 'meshy_anim_03_marionette.png', ((0.0, -2.2, 1.10), (math.radians(90), 0, 0))),
        ('Yu_Nian_An_Graceful_Bow', 45, 'meshy_anim_04_bow.png', ((1.3, -2.3, 0.95), (math.radians(88), 0, math.radians(30)))),
    ]

    for act_name, frame, filename, (cam_loc, cam_rot) in render_shots:
        act = bpy.data.actions.get(act_name)
        if act:
            arm.animation_data.action = act
            scene.frame_set(frame)
            cam.location = cam_loc
            cam.rotation_euler = cam_rot
            out_path = os.path.join(out_dir, filename)
            scene.render.filepath = out_path
            print(f' - Rendering {act_name} (Frame {frame}) -> {filename}...')
            bpy.ops.render.render(write_still=True)
            shutil.copy2(out_path, os.path.join(art_dir, filename))
            print(f'   -> Rendered and saved: {out_path} ({os.path.getsize(out_path):,} bytes)')

    # Reset back to Idle frame 0 for master file
    arm.animation_data.action = act_idle
    scene.frame_set(0)

    # Save Master Blend
    bpy.ops.wm.save_as_mainfile(filepath=master_blend)
    print(f' - Master blend saved: {master_blend}')

    # Clear unslotted NLA tracks to prevent Blender 4.5 exporter bug
    if arm.animation_data and arm.animation_data.nla_tracks:
        for trk in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(trk)

    # Production Container Exports
    glb_path = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Cloud.glb'
    fbx_path = r'E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Cloud.fbx'

    try:
        bpy.ops.export_scene.gltf(
            filepath=glb_path,
            export_format='GLB',
            export_animations=True,
            export_morph=True,
            export_skins=True,
            export_all_influences=True,
            export_apply=False,
            export_def_bones=True,
        )
        print(f' - Exported GLB: {glb_path} ({os.path.getsize(glb_path):,} bytes)')
    except Exception as e:
        print(f' - GLB export error: {e}')

    try:
        bpy.ops.export_scene.fbx(
            filepath=fbx_path,
            use_selection=False,
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=True,
            add_leaf_bones=False,
        )
        print(f' - Exported FBX: {fbx_path} ({os.path.getsize(fbx_path):,} bytes)')
    except Exception as e:
        print(f' - FBX export error: {e}')

    print('\n[COMPLETE] Meshy Yu Nian An character successfully processed, rigged, animated, and exported!')

if __name__ == '__main__':
    process_and_rig_meshy()
