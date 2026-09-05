import bpy

def test_thin_feature_destruction():
    print("=== Testing Thin Feature Destruction under Voxel Remesh ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Create a creature base with a thin horn (radius=0.03, length=1.0) and thin claws (radius=0.015)
    # Head
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0))
    head = bpy.context.active_object
    
    # Horn
    bpy.ops.mesh.primitive_cone_add(radius1=0.04, radius2=0.001, depth=0.8, location=(0.2, 0, 0.7))
    horn = bpy.context.active_object
    
    # Claw / Spikes
    bpy.ops.mesh.primitive_cone_add(radius1=0.02, radius2=0.001, depth=0.4, location=(-0.2, 0, 0.6))
    claw = bpy.context.active_object
    
    # Join
    bpy.ops.object.select_all(action='DESELECT')
    head.select_set(True)
    horn.select_set(True)
    claw.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    creature = head
    creature.name = "CreatureWithHorns"
    
    initial_z_max = max(v.co.z for v in creature.data.vertices)
    print(f"Original high-poly Z_max (tip of horn): {initial_z_max:.4f}")
    
    # Apply Voxel Remesh with voxel_size = 0.1 (as recommended in Use-Case C fallback)
    creature.data.remesh_voxel_size = 0.1
    bpy.ops.object.voxel_remesh()
    
    remeshed_z_max = max(v.co.z for v in creature.data.vertices)
    print(f"Remeshed Z_max (voxel_size=0.1): {remeshed_z_max:.4f}")
    print(f"Tip loss: {initial_z_max - remeshed_z_max:.4f} ({(initial_z_max - remeshed_z_max)/initial_z_max * 100:.1f}%)")
    
    # Check claw presence: claw tip was at z = 0.8
    # Let's count vertices above z = 0.6 in original vs remeshed
    print(f"Vertices above z=0.6 in remeshed: {len([v for v in creature.data.vertices if v.co.z > 0.6])}")
    
    # Now decimate by 0.08 as recommended
    dec = creature.modifiers.new("Decimate", 'DECIMATE')
    dec.ratio = 0.08
    bpy.ops.object.modifier_apply(modifier="Decimate")
    final_z_max = max(v.co.z for v in creature.data.vertices)
    print(f"Final Z_max after decimate 0.08: {final_z_max:.4f}")
    print(f"Total silhouette tip loss: {initial_z_max - final_z_max:.4f} ({(initial_z_max - final_z_max)/initial_z_max * 100:.1f}%)")

test_thin_feature_destruction()
