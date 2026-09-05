import bpy
import sys
import traceback

def test_chimera_rig_generation():
    print("=== Testing Chimera Rig Generation (Wolf + Bird) ===")
    
    # 1. Reset scene and enable Rigify
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module='rigify')
    
    # Create test mesh
    bpy.ops.mesh.primitive_monkey_add(size=2.0, location=(0, 0, 1))
    creature = bpy.context.active_object
    creature.name = "FantasyDragon"
    
    # Add Wolf Metarig
    bpy.ops.object.armature_wolf_metarig_add()
    metarig = bpy.context.active_object
    metarig.name = "MetaRig_Chimera"
    print(f"Wolf metarig added. Bone count: {len(metarig.data.bones)}")
    
    # Add Bird Metarig
    bpy.ops.object.armature_bird_metarig_add()
    bird_meta = bpy.context.active_object
    bird_meta.name = "MetaRig_Bird"
    print(f"Bird metarig added. Bone count: {len(bird_meta.data.bones)}")
    
    # Join bird into metarig
    bpy.ops.object.select_all(action='DESELECT')
    bird_meta.select_set(True)
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.object.join()
    print(f"Joined metarig total bones: {len(metarig.data.bones)}")
    
    # Reparent wings as proposed in RESEARCH_BENCHMARK.md line 1029-1038
    bpy.ops.object.mode_set(mode='EDIT')
    eb = metarig.data.edit_bones
    spine_chest = eb.get("spine.002") or eb.get("spine")
    print(f"Spine chest bone: {spine_chest.name if spine_chest else None}")
    
    for side in ['L', 'R']:
        wing_shoulder = eb.get(f"shoulder.{side}")
        print(f"wing_shoulder {side}: {wing_shoulder}")
        if wing_shoulder and spine_chest:
            wing_shoulder.parent = spine_chest
            wing_shoulder.use_connect = False
            
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Check all bones in the joined metarig
    print("\n--- Inspecting bones in joined metarig ---")
    bone_names = [b.name for b in metarig.data.bones]
    print(f"Total bones: {len(bone_names)}")
    # Check for orphaned/duplicate bones from the bird metarig
    bird_artifacts = [b for b in bone_names if ".001" in b or "beak" in b or "pelvis" in b]
    print(f"Bird artifact bones in Wolf metarig: {bird_artifacts}")
    
    # Try Rigify Generate
    bpy.ops.object.select_all(action='DESELECT')
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.object.mode_set(mode='POSE')
    
    print("\nAttempting bpy.ops.pose.rigify_generate()...")
    try:
        gen_res = bpy.ops.pose.rigify_generate()
        print(f"rigify_generate result: {gen_res}")
        rig = bpy.data.objects.get("rig")
        print(f"Generated rig object: {rig}")
        if rig:
            print(f"Rig deform bone count: {len([b for b in rig.data.bones if b.name.startswith('DEF-')])}")
            print(f"Total rig bone count: {len(rig.data.bones)}")
    except Exception as e:
        print(f"rigify_generate FAILED with: {e}")
        traceback.print_exc()

test_chimera_rig_generation()
