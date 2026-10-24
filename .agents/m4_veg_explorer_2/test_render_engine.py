import sys
import time
import os
import bpy

def run_test():
    glb_path = r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\output\tropical\veg_tropical_palm_01\veg_tropical_palm_01.glb"
    out_dir = r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\test_renders"
    os.makedirs(out_dir, exist_ok=True)

    # 1. Reset scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    scene = bpy.context.scene
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # 2. Import GLB
    t0 = time.time()
    bpy.ops.import_scene.gltf(filepath=glb_path)
    print(f"Import GLB took: {time.time() - t0:.3f}s")
    
    imported_mesh_objs = [o for o in scene.objects if o.type == 'MESH']
    print(f"Imported {len(imported_mesh_objs)} mesh objects")
    for obj in imported_mesh_objs:
        print(f" - {obj.name}: {len(obj.data.vertices)} vertices, {len(obj.data.polygons)} polygons")
        for slot in obj.material_slots:
            if slot.material:
                mat = slot.material
                print(f"   Material '{mat.name}': blend_method={getattr(mat, 'blend_method', 'N/A')}")
                if hasattr(mat, "surface_render_method"):
                    print(f"   surface_render_method={mat.surface_render_method}")

    # 3. Setup Camera & Framing
    cam_data = bpy.data.cameras.new("InspectorCamera")
    cam_data.lens = 50.0
    cam_obj = bpy.data.objects.new("InspectorCamera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # 4. Botanical Lighting
    # Key light (5500K daylight)
    key_light_data = bpy.data.lights.new(name="KeyLight", type='SUN')
    key_light_data.energy = 4.0
    key_light_data.color = (1.0, 0.96, 0.90)  # ~5500K warm daylight
    key_obj = bpy.data.objects.new(name="KeyLight", object_data=key_light_data)
    key_obj.rotation_euler = (0.785, 0.35, 0.6)  # ~45 deg down, angled
    scene.collection.objects.link(key_obj)

    # Fill light (6500K soft cool)
    fill_light_data = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_light_data.energy = 1.5
    fill_light_data.color = (0.90, 0.94, 1.0)  # ~6500K cool fill
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_light_data)
    fill_obj.rotation_euler = (0.8, -0.4, -2.0)
    scene.collection.objects.link(fill_obj)

    # Rim light
    rim_light_data = bpy.data.lights.new(name="RimLight", type='SUN')
    rim_light_data.energy = 2.5
    rim_light_data.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new(name="RimLight", object_data=rim_light_data)
    rim_obj.rotation_euler = (-1.0, 0.2, 3.14)
    scene.collection.objects.link(rim_obj)

    import mathutils
    all_verts = []
    for o in imported_mesh_objs:
        for corner in o.bound_box:
            world_co = o.matrix_world @ mathutils.Vector(corner)
            all_verts.append(world_co)

    min_x = min(v[0] for v in all_verts)
    max_x = max(v[0] for v in all_verts)
    min_y = min(v[1] for v in all_verts)
    max_y = max(v[1] for v in all_verts)
    min_z = min(v[2] for v in all_verts)
    max_z = max(v[2] for v in all_verts)

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0
    radius = 0.5 * ((max_x - min_x)**2 + (max_y - min_y)**2 + (max_z - min_z)**2)**0.5

    print(f"Bounds: min=({min_x:.3f}, {min_y:.3f}, {min_z:.3f}), max=({max_x:.3f}, {max_y:.3f}, {max_z:.3f})")
    print(f"Center=({center_x:.3f}, {center_y:.3f}, {center_z:.3f}), radius={radius:.3f}")

    # Distance
    import math
    half_fov = math.atan(36.0 / (2.0 * 50.0))
    dist = (radius / math.sin(half_fov)) * 1.15
    print(f"Framing dist: {dist:.3f}")

    # Hero 3/4: elevation 25 deg, azimuth 45 deg
    elev = math.radians(25.0)
    azim = math.radians(45.0)
    cam_x = center_x + dist * math.cos(elev) * math.sin(azim)
    cam_y = center_y - dist * math.cos(elev) * math.cos(azim)
    cam_z = center_z + dist * math.sin(elev)

    cam_obj.location = (cam_x, cam_y, cam_z)

    # Track to center
    direction = mathutils.Vector((center_x - cam_x, center_y - cam_y, center_z - cam_z))
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    # Test rendering with Cycles vs EEVEE Next
    for engine in ["BLENDER_EEVEE_NEXT", "CYCLES"]:
        scene.render.engine = engine
        if engine == "CYCLES":
            scene.cycles.samples = 32
            scene.cycles.device = 'CPU'  # safe CPU default
        output_file = os.path.join(out_dir, f"test_{engine.lower()}.png")
        scene.render.filepath = output_file
        t_render = time.time()
        bpy.ops.render.render(write_still=True)
        render_time = time.time() - t_render
        print(f"Render engine {engine} finished in {render_time:.3f}s -> {output_file} (exists={os.path.exists(output_file)}, size={os.path.getsize(output_file)} bytes)")

if __name__ == "__main__":
    run_test()
