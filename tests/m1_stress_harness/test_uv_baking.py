import bpy
import numpy as np

def test_uv_and_normal_baking():
    print("=== Testing UV Unwrapping and Normal Baking Quality ===")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # High poly monkey
    bpy.ops.mesh.primitive_monkey_add(size=2.0)
    high_poly = bpy.context.active_object
    high_poly.name = "HighPoly"
    mod = high_poly.modifiers.new("Subsurf", 'SUBSURF')
    mod.levels = 3
    bpy.ops.object.modifier_apply(modifier="Subsurf")
    
    # Low poly monkey via Voxel Remesh + Decimate (as suggested in doc)
    bpy.ops.mesh.primitive_monkey_add(size=2.0)
    low_poly = bpy.context.active_object
    low_poly.name = "LowPoly"
    low_poly.data.remesh_voxel_size = 0.1
    bpy.ops.object.voxel_remesh()
    dec = low_poly.modifiers.new("Decimate", 'DECIMATE')
    dec.ratio = 0.08
    bpy.ops.object.modifier_apply(modifier="Decimate")
    
    # Check UVs before explicit unwrap
    uv_layer = low_poly.data.uv_layers.active
    print(f"Low poly UV layer present: {uv_layer is not None}")
    
    # Assign material with texture node as needed for Cycles bake
    mat = bpy.data.materials.new("LowPoly_Mat")
    mat.use_nodes = True
    low_poly.data.materials.append(mat)
    
    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    bake_img = bpy.data.images.new("Baked_Normal", width=1024, height=1024)
    tex_node.image = bake_img
    mat.node_tree.nodes.active = tex_node
    
    # Attempt bake without explicit UV unwrap
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'CPU'
    bpy.context.scene.cycles.bake_type = 'NORMAL'
    bpy.context.scene.render.bake.use_selected_to_active = True
    bpy.context.scene.render.bake.cage_extrusion = 0.05
    bpy.context.scene.render.bake.max_ray_distance = 0.1
    
    bpy.ops.object.select_all(action='DESELECT')
    high_poly.select_set(True)
    low_poly.select_set(True)
    bpy.context.view_layer.objects.active = low_poly
    
    print("\nAttempting bake without explicit Smart UV unwrap...")
    try:
        bpy.ops.object.bake(type='NORMAL')
        print("Bake completed without error.")
        # Check pixel variance in bake_img to see if it's distorted or blank
        pixels = np.array(bake_img.pixels[:])
        # In tangent normal maps, flat surface is (0.5, 0.5, 1.0) -> RGB (128, 128, 255)
        print(f"Image pixel count: {len(pixels)}, min: {pixels.min():.3f}, max: {pixels.max():.3f}, mean: {pixels.mean():.3f}")
    except Exception as e:
        print(f"Bake failed: {e}")
        
    # Now test silhouette destruction: compare volume and surface deviation
    # In creatures with thin horns/ears/spikes, what does Voxel Remesh + Decimate do?
    print("\n--- Silhouette Destruction Test on Thin Structures (Horns/Ears) ---")
    # Check ear tip position on HighPoly vs LowPoly
    high_z_max = max(v.co.z for v in high_poly.data.vertices)
    high_x_max = max(v.co.x for v in high_poly.data.vertices)
    low_z_max = max(v.co.z for v in low_poly.data.vertices)
    low_x_max = max(v.co.x for v in low_poly.data.vertices)
    
    print(f"HighPoly Bounds: X_max={high_x_max:.3f}, Z_max={high_z_max:.3f}")
    print(f"LowPoly Bounds:  X_max={low_x_max:.3f}, Z_max={low_z_max:.3f}")
    print(f"Shrinkage / Silhouette Loss: X={abs(high_x_max - low_x_max):.3f} ({(abs(high_x_max - low_x_max)/high_x_max)*100:.1f}%), Z={abs(high_z_max - low_z_max):.3f} ({(abs(high_z_max - low_z_max)/high_z_max)*100:.1f}%)")

test_uv_and_normal_baking()
