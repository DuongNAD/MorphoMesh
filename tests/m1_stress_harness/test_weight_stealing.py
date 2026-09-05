import bpy

def test_weight_stealing():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module='rigify')
    
    # Create test dragon mesh
    bpy.ops.mesh.primitive_monkey_add(size=3.0, location=(0, 0, 0))
    creature = bpy.context.active_object
    creature.name = "FantasyDragon"
    
    bpy.ops.object.armature_wolf_metarig_add()
    metarig = bpy.context.active_object
    metarig.name = "MetaRig_Chimera"
    
    bpy.ops.object.armature_bird_metarig_add()
    bird_meta = bpy.context.active_object
    
    # Join
    bpy.ops.object.select_all(action='DESELECT')
    bird_meta.select_set(True)
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.object.join()
    
    # Reparent according to RESEARCH_BENCHMARK.md
    bpy.ops.object.mode_set(mode='EDIT')
    eb = metarig.data.edit_bones
    spine_chest = eb.get("spine.002") or eb.get("spine")
    for side in ['L', 'R']:
        wing_shoulder = eb.get(f"shoulder.{side}")
        if wing_shoulder and spine_chest:
            wing_shoulder.parent = spine_chest
            wing_shoulder.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Generate rig
    bpy.ops.object.select_all(action='DESELECT')
    metarig.select_set(True)
    bpy.context.view_layer.objects.active = metarig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.rigify_generate()
    
    # Find generated rig
    rig = [obj for obj in bpy.data.objects if obj.name.startswith("RIG-") or obj.name == "rig"][0]
    print(f"Located generated rig: {rig.name}")
    
    # Bind ARMATURE_AUTO
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    creature.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    
    # Check vertex groups for bird artifacts
    vg_names = [vg.name for vg in creature.vertex_groups]
    bird_vg = [vg for vg in vg_names if any(k in vg.lower() for k in ['beak', 'toe.001', 'shin.001', 'feather', 'wing.001'])]
    print(f"\nTotal vertex groups created on creature: {len(vg_names)}")
    print(f"Total bird artifact vertex groups: {len(bird_vg)}")
    print(f"Sample bird artifact vertex groups: {bird_vg[:15]}")
    
    # Check if vertices actually have non-zero weights in these artifact groups
    weights_stolen = 0
    for v in creature.data.vertices:
        for g in v.groups:
            group_name = creature.vertex_groups[g.group].name
            if group_name in bird_vg and g.weight > 0.01:
                weights_stolen += 1
                break
    print(f"Vertices with weights stolen by orphaned bird bones: {weights_stolen} / {len(creature.data.vertices)} ({weights_stolen / len(creature.data.vertices) * 100:.1f}%)")

test_weight_stealing()
