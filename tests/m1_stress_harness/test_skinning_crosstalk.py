import bpy
import mathutils

def test_quadruped_skinning_crosstalk():
    print("=== Testing Quadruped Skinning Artifacts (Leg Crosstalk) ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module='rigify')
    
    # Create two parallel cylinders representing front left and right legs close together
    # Typical stance distance for a canine: ~15cm separation
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1.5, location=(-0.15, 0, 0.75))
    leg_l = bpy.context.active_object
    leg_l.name = "Leg_L"
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1.5, location=(0.15, 0, 0.75))
    leg_r = bpy.context.active_object
    leg_r.name = "Leg_R"
    
    # Join into single creature mesh
    bpy.ops.object.select_all(action='DESELECT')
    leg_l.select_set(True)
    leg_r.select_set(True)
    bpy.context.view_layer.objects.active = leg_l
    bpy.ops.object.join()
    creature = leg_l
    creature.name = "QuadrupedLegs"
    
    # Create a simple 2-bone armature (one for left leg, one for right leg)
    arm_data = bpy.data.armatures.new("ArmatureData")
    arm_obj = bpy.data.objects.new("Armature", arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    
    bpy.ops.object.mode_set(mode='EDIT')
    b_l = arm_data.edit_bones.new("Bone_L")
    b_l.head = (-0.15, 0, 0.0)
    b_l.tail = (-0.15, 0, 1.5)
    
    b_r = arm_data.edit_bones.new("Bone_R")
    b_r.head = (0.15, 0, 0.0)
    b_r.tail = (0.15, 0, 1.5)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Bind with ARMATURE_AUTO
    bpy.ops.object.select_all(action='DESELECT')
    creature.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    
    # Check for weight crosstalk: does Bone_L have non-zero weight on right leg vertices (x > 0)?
    right_leg_verts = [v for v in creature.data.vertices if v.co.x > 0]
    crosstalk_verts = 0
    vg_l_index = creature.vertex_groups["Bone_L"].index
    
    for v in right_leg_verts:
        for g in v.groups:
            if g.group == vg_l_index and g.weight > 0.05:
                crosstalk_verts += 1
                break
                
    print(f"Total vertices on Right Leg: {len(right_leg_verts)}")
    print(f"Right Leg vertices erroneously influenced by Bone_L (crosstalk > 0.05): {crosstalk_verts} ({crosstalk_verts/len(right_leg_verts)*100:.1f}%)")

test_quadruped_skinning_crosstalk()
