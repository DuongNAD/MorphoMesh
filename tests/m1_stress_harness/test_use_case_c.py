import bpy
import os
import traceback

def test_use_case_c_baking():
    print("=== Testing Use-Case C: Normal Baking and Remeshing ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # 1. Create a detailed high-poly creature with sharp features (horns/ears)
    bpy.ops.mesh.primitive_monkey_add(size=2.0)
    high_poly = bpy.context.active_object
    high_poly.name = "Creature_HighPoly"
    mod = high_poly.modifiers.new("Subsurf", 'SUBSURF')
    mod.levels = 3
    bpy.ops.object.modifier_apply(modifier="Subsurf")
    print(f"High poly face count: {len(high_poly.data.polygons)}")
    
    # 2. Perform Option B: Voxel Remesh + Decimate as specified in line 1187
    print("\nExecuting Option B: Voxel Remesh (voxel_size=0.1) + Decimate (ratio=0.08)...")
    bpy.ops.mesh.primitive_monkey_add(size=2.0)
    low_poly = bpy.context.active_object
    low_poly.name = "Creature_LowPoly"
    
    # Voxel remesh
    low_poly.data.remesh_voxel_size = 0.1
    low_poly.data.remesh_mode = 'VOXEL'
    bpy.ops.object.voxel_remesh()
    print(f"Faces after Voxel Remesh: {len(low_poly.data.polygons)}")
    print(f"UV layers on low_poly after Voxel Remesh: {len(low_poly.data.uv_layers)}")
    
    # Decimate
    dec_mod = low_poly.modifiers.new("Decimate", 'DECIMATE')
    dec_mod.ratio = 0.08
    bpy.ops.object.modifier_apply(modifier="Decimate")
    print(f"Faces after Decimate: {len(low_poly.data.polygons)}")
    print(f"UV layers after Decimate: {len(low_poly.data.uv_layers)}")
    
    # 3. Now attempt bake_high_to_low_poly from RESEARCH_BENCHMARK.md line 1208
    output_path = "/tmp/test_bake_normal.png"
    print(f"\nAttempting bake_high_to_low_poly as written in line 1208...")
    
    try:
        high_obj = bpy.data.objects.get("Creature_HighPoly")
        low_obj = bpy.data.objects.get("Creature_LowPoly")
        
        # Configure Cycles for baking
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'CPU'
        bpy.context.scene.cycles.bake_type = 'NORMAL'
        bpy.context.scene.render.bake.use_selected_to_active = True
        bpy.context.scene.render.bake.cage_extrusion = 0.05
        bpy.context.scene.render.bake.max_ray_distance = 0.1
        
        # Setup bake target texture in low-poly material (line 1225)
        print(f"Checking low_obj.active_material: {low_obj.active_material}")
        mat = low_obj.active_material
        if mat is None:
            print("CRITICAL: low_obj.active_material is None! Let's see what line 1226 does:")
        tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        bake_img = bpy.data.images.new("Baked_Normal", width=512, height=512)
        tex_node.image = bake_img
        mat.node_tree.nodes.active = tex_node
        
        # Select High then Low Poly
        bpy.ops.object.select_all(action='DESELECT')
        high_obj.select_set(True)
        low_obj.select_set(True)
        bpy.context.view_layer.objects.active = low_obj
        
        # Execute Bake
        bpy.ops.object.bake(type='NORMAL')
        bake_img.filepath_raw = output_path
        bake_img.file_format = 'PNG'
        bake_img.save()
        print("Bake successful!")
    except Exception as e:
        print(f"Bake FAILED with exception: {e}")
        traceback.print_exc()

test_use_case_c_baking()
