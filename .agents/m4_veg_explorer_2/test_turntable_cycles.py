import os
import sys
import math
import time
import bpy
import mathutils

def render_palm_cycles():
    glb_path = r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\processed_palm\tropical\veg_tropical_palm_01\veg_tropical_palm_01.glb"
    out_dir = r"E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_2\test_turntable_cycles"
    os.makedirs(out_dir, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    # Configure Cycles
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.preview_samples = 12
    scene.cycles.use_denoising = True

    # Import GLB
    bpy.ops.import_scene.gltf(filepath=glb_path)
    mesh_objs = [o for o in scene.objects if o.type == 'MESH']

    # Auto-orient if necessary
    for obj in mesh_objs:
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        min_y = min(c[1] for c in corners)
        max_y = max(c[1] for c in corners)
        min_z = min(c[2] for c in corners)
        max_z = max(c[2] for c in corners)
        if (max_y - min_y) > (max_z - min_z) * 1.5:
            rot = mathutils.Matrix.Rotation(-math.pi / 2.0, 4, 'X')
            obj.matrix_world = rot @ obj.matrix_world

    # Recompute bounds
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
    spread = max(dx, dy)
    radius = 0.5 * math.sqrt(dx * dx + dy * dy + dz * dz)
    radius = max(radius, 0.05)

    # Shadow catcher plane at Z = min_z (0.000m)
    plane_size = max(spread * 3.5, 5.0)
    bpy.ops.mesh.primitive_plane_add(size=plane_size, location=(center_x, center_y, min_z))
    shadow_plane = bpy.context.active_object
    shadow_plane.name = "GroundShadowCatcher"
    shadow_plane.is_shadow_catcher = True

    # 3-Point Botanical Lighting
    # Key Light (5500K warm daylight)
    key_light = bpy.data.lights.new(name="KeyLight", type='SUN')
    key_light.energy = 4.0
    key_light.color = (1.0, 0.95, 0.88)
    key_obj = bpy.data.objects.new(name="KeyLight", object_data=key_light)
    key_obj.rotation_euler = (math.radians(45.0), math.radians(15.0), math.radians(45.0))
    scene.collection.objects.link(key_obj)

    # Fill Light (6500K cool soft)
    fill_light = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_light.energy = 1.5
    fill_light.color = (0.88, 0.92, 1.0)
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_light)
    fill_obj.rotation_euler = (math.radians(45.0), math.radians(-20.0), math.radians(-110.0))
    scene.collection.objects.link(fill_obj)

    # Rim Backlight
    rim_light = bpy.data.lights.new(name="RimLight", type='SUN')
    rim_light.energy = 2.5
    rim_light.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new(name="RimLight", object_data=rim_light)
    rim_obj.rotation_euler = (math.radians(-50.0), math.radians(10.0), math.radians(180.0))
    scene.collection.objects.link(rim_obj)

    # Framing camera
    cam_data = bpy.data.cameras.new("InspectorCamera")
    cam_data.lens = 50.0
    cam_obj = bpy.data.objects.new("InspectorCamera", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    half_fov = math.atan(36.0 / (2.0 * 50.0))
    dist = (radius / math.sin(half_fov)) * 1.15

    angles = [
        ("turntable_01.png", 25.0, 45.0, "Hero 3/4 View"),
        ("turntable_02.png", 0.0, 0.0, "Front View"),
        ("turntable_03.png", 0.0, 90.0, "Side View"),
        ("turntable_04.png", 85.0, 0.0, "Top Crown View"),
    ]

    for filename, elev_deg, azim_deg, label in angles:
        elev = math.radians(elev_deg)
        azim = math.radians(azim_deg)
        px = center_x + dist * math.cos(elev) * math.sin(azim)
        py = center_y - dist * math.cos(elev) * math.cos(azim)
        pz = center_z + dist * math.sin(elev)
        cam_obj.location = (px, py, pz)
        cam_obj.rotation_euler = (target_center - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()

        out_path = os.path.join(out_dir, filename)
        scene.render.filepath = out_path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"Cycles rendered {label} ({filename}) in {time.time() - t0:.3f}s")

if __name__ == "__main__":
    render_palm_cycles()
