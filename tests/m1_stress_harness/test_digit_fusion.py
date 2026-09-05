import bpy

def test_digit_fusion():
    print("=== Testing Claws / Wing Digits Webbing / Bridging under Voxel Remesh ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # Create two separate claw fingers separated by 0.06 units
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=1.0, location=(-0.05, 0, 0.5))
    claw1 = bpy.context.active_object
    
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=1.0, location=(0.05, 0, 0.5))
    claw2 = bpy.context.active_object
    
    bpy.ops.object.select_all(action='DESELECT')
    claw1.select_set(True)
    claw2.select_set(True)
    bpy.context.view_layer.objects.active = claw1
    bpy.ops.object.join()
    claws = claw1
    
    # Check initial disconnected components
    # Initially 2 separate shells
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Original claw vertices: {len(claws.data.vertices)}")
    
    # Remesh with voxel_size = 0.1
    claws.data.remesh_voxel_size = 0.1
    bpy.ops.object.voxel_remesh()
    
    # Now check if they were fused into a single connected component
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    # Select one vertex
    import bmesh
    bm = bmesh.from_edit_mesh(claws.data)
    bm.verts.ensure_lookup_table()
    bm.verts[0].select = True
    bmesh.update_edit_mesh(claws.data)
    
    # Select linked
    bpy.ops.mesh.select_linked()
    selected_verts = len([v for v in bm.verts if v.select])
    total_verts = len(bm.verts)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Remeshed claw vertices: {total_verts}")
    print(f"Connected component vertices: {selected_verts}")
    if selected_verts == total_verts:
        print("CRITICAL: Claws were COMPLETELY FUSED into a single solid webbed block!")
    else:
        print("Claws remained separate.")

test_digit_fusion()
