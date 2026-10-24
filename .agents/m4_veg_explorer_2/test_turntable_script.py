import os
import sys
import math
import time
import bpy
import mathutils

def render_4_turntable_views():
    glb_path = r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\processed_palm\tropical\veg_tropical_palm_01\veg_tropical_palm_01.glb"
    out_dir = r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\test_turntable"
    os.makedirs(out_dir, exist_ok=True)

    # 1. Reset Scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # Use EEVEE Next or Cycles
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    if hasattr(scene, "eevee"):
        # Configure EEVEE Next sampling
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 32

    # 2. Import GLB
    bpy.ops.import_scene.gltf(filepath=glb_path)
    mesh_objs = [o for o in scene.objects if o.type == 'MESH']
    if not mesh_objs:
        raise RuntimeError("No mesh objects imported from GLB!")

    # Check orientation:
    for obj in mesh_objs:
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        min_y = min(c[1] for c in corners)
        max_y = max(c[1] for c in corners)
        min_z = min(c[2] for c in corners)
        max_z = max(c[2] for c in corners)
        # If height is lying on Y-axis (from post_processor Z export)
        if (max_y - min_y) > (max_z - min_z) * 1.5:
            rot = mathutils.Matrix.Rotation(-math.pi / 2.0, 4, 'X')
            obj.matrix_world = rot @ obj.matrix_world

    # 3. Ground contact shadow plane
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0, 0, 0))
    shadow_plane = bpy.context.active_object
    shadow_plane.name = "GroundShadowCatcher"
    if hasattr(shadow_plane, "is_shadow_catcher"):
        shadow_plane.is_shadow_catcher = True

    # 4. Botanical 3-Point Studio Lighting
    # Key Light (5500K warm daylight)
    key_light = bpy.data.lights.new(name="KeyLight", type='SUN')
    key_light.energy = 4.5
    key_light.color = (1.0, 0.95, 0.88)
    key_obj = bpy.data.objects.new(name="KeyLight", object_data=key_light)
    key_obj.rotation_euler = (math.radians(45.0), math.radians(15.0), math.radians(45.0))
    scene.collection.objects.link(key_obj)

    # Fill Light (6500K cool soft)
    fill_light = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_light.energy = 1.8
    fill_light.color = (0.88, 0.92, 1.0)
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_light)
    fill_obj.rotation_euler = (math.radians(45.0), math.radians(-20.0), math.radians(-110.0))
    scene.collection.objects.link(fill_obj)

    # Rim Backlight
    rim_light = bpy.data.lights.new(name="RimLight", type='SUN')
    rim_light.energy = 3.0
    rim_light.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new(name="RimLight", object_data=rim_light)
    rim_obj.rotation_euler = (math.radians(-50.0), math.radians(10.0), math.radians(180.0))
    scene.collection.objects.link(rim_obj)

    # 5. Calculate Bounding Box and Center
    all_corners = []
    for obj in mesh_objs:
        for c in obj.bound_box:
            all_corners.append(obj.matrix_world @ mathutils.Vector(c))

    min_x = min(c[0] for c in all_corners)
    max_x = max(c[0] for c in all_corners)
    min_y = min(c[1] for c in all_corners)
    max_y = max(c[1] for c in all_corners)
    min_z = min(c[2] for c in all_corners)
    max_z = max(c[2] for c in all_corners)

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0
    target_center = mathutils.Vector((center_x, center_y, center_z))

    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z
    radius = 0.5 * math.sqrt(dx * dx + dy * dy + dz * dz)
    radius = max(radius, 0.05)

    print(f"Computed bounding box: min=({min_x:.3f}, {min_y:.3f}, {min_z:.3f}), max=({max_x:.3f}, {max_y:.3f}, {max_z:.3f})")
    print(f"Target center: {target_center}, radius: {radius:.3f}m")

    # Optical framing distance (focal 50mm, 36mm sensor, 15% margin)
    half_fov = math.atan(36.0 / (2.0 * 50.0))
    dist = (radius / math.sin(half_fov)) * 1.15
    print(f"Framing distance: {dist:.3f}m")

    # 6. Setup Camera
    cam_data = bpy.data.cameras.new("InspectorCamera")
    cam_data.lens = 50.0
    cam_obj = bpy.data.objects.new("InspectorCamera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # 7. Render 4 standardized angles:
    angles = [
        ("turntable_01.png", 25.0, 45.0, "Hero 3/4 View"),
        ("turntable_02.png", 0.0, 0.0, "Front View"),
        ("turntable_03.png", 0.0, 90.0, "Side View"),
        ("turntable_04.png", 85.0, 0.0, "Top Crown View"),
    ]

    results = {}
    for filename, elev_deg, azim_deg, label in angles:
        elev = math.radians(elev_deg)
        azim = math.radians(azim_deg)

        # Position camera on sphere relative to target center
        px = center_x + dist * math.cos(elev) * math.sin(azim)
        py = center_y - dist * math.cos(elev) * math.cos(azim)
        pz = center_z + dist * math.sin(elev)
        cam_obj.location = (px, py, pz)

        # Point camera at target center
        direction = target_center - cam_obj.location
        cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        out_path = os.path.join(out_dir, filename)
        scene.render.filepath = out_path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        t_elapsed = time.time() - t0
        print(f"Rendered {label} ({filename}) in {t_elapsed:.3f}s -> size={os.path.getsize(out_path)} bytes")
        results[filename] = out_path

    print("All 4 views rendered successfully!")

if __name__ == "__main__":
    render_4_turntable_views()
