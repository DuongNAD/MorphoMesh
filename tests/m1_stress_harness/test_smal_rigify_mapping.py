import bpy
import mathutils

def inspect_rigify_wolf_vs_smal():
    print("=== Comparing Rigify Wolf Metarig vs SMAL ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module='rigify')
    
    bpy.ops.object.armature_wolf_metarig_add()
    wolf = bpy.context.active_object
    
    bones = wolf.data.bones
    print(f"Wolf metarig total bones: {len(bones)}")
    
    # Generate Rigify rig to see deformation bones
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.rigify_generate()
    rig = [o for o in bpy.data.objects if o.name.startswith("RIG-") or o.name == "rig"][0]
    
    def_bones = [b.name for b in rig.data.bones if b.name.startswith("DEF-")]
    print(f"Wolf generated DEF-* bones: {len(def_bones)}")
    print(f"Sample DEF-* bones: {def_bones[:20]}")
    
    # Standard SMAL 35 joints
    smal_joints = [
        "root", "left_hip", "right_hip", "spine1", "left_knee", "right_knee", "spine2",
        "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot", "neck1",
        "left_collar", "right_collar", "neck2", "left_shoulder", "right_shoulder",
        "head", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
        "left_hand", "right_hand", "tail1", "tail2", "tail3", "tail4", "tail5",
        "tail6", "jaw", "left_ear", "right_ear", "nose"
    ]
    print(f"SMAL joint count: {len(smal_joints)}")
    
    # Check matching names
    matched = 0
    for j in smal_joints:
        matching_def = [b for b in def_bones if j in b.lower()]
        if matching_def:
            matched += 1
    print(f"Direct name matches between SMAL joints and Rigify DEF-* bones: {matched}/{len(smal_joints)}")

inspect_rigify_wolf_vs_smal()
