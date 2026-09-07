import bpy
import mathutils
import math
import json

print("=== DEEP BUTTERFLY & CAMERA AUDIT ===")

# 1. Butterflies
butterflies = [o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")]
print(f"Total butterflies: {len(butterflies)}")
for bf in sorted(butterflies, key=lambda x: x.name):
    loc = [round(v, 4) for v in bf.location]
    arm_mods = [m.type for m in bf.modifiers]
    vgs = [vg.name for vg in bf.vertex_groups]
    print(f"  {bf.name}: loc={loc}, mods={arm_mods}, vgs={vgs}")

# 2. Strings
strings = bpy.data.objects.get("Prop_Marionette_Strings")
if strings:
    str_mods = [m.type for m in strings.modifiers]
    str_vgs = [vg.name for vg in strings.vertex_groups]
    print(f"\nMarionette Strings: mods={str_mods}, vgs_count={len(str_vgs)}")
    print(f"  Vertex groups: {str_vgs}")
    z_coords = [v.co.z for v in strings.data.vertices]
    print(f"  Z bounds: [{min(z_coords):.4f}, {max(z_coords):.4f}]")

# 3. Camera Framing & Render Resolution
scene = bpy.context.scene
res_x = scene.render.resolution_x
res_y = scene.render.resolution_y
print(f"\nRender Resolution: {res_x} x {res_y} (Aspect: {res_x/res_y:.4f})")

body = bpy.data.objects.get("Yu_Nian_An_Body")
body_verts = [body.matrix_world @ v.co for v in body.data.vertices] if body else []
head_top_z = max(v.z for v in body_verts) if body_verts else 1.65
feet_bottom_z = min(v.z for v in body_verts) if body_verts else 0.0
print(f"Character Z range: [{feet_bottom_z:.4f}, {head_top_z:.4f}], Total height: {head_top_z - feet_bottom_z:.4f}m")

# Test camera projection for all cameras
from bpy_extras.object_utils import world_to_camera_view

cameras = [o for o in bpy.data.objects if o.type == 'CAMERA']
for cam in sorted(cameras, key=lambda x: x.name):
    print(f"\nCamera: {cam.name} (lens={cam.data.lens}mm, loc={[round(v,3) for v in cam.location]})")
    # Project character bounding box or vertices into camera NDC space (0 to 1)
    # in camera view: x in [0, 1] and y in [0, 1] means inside frame
    ndc_coords = [world_to_camera_view(scene, cam, v) for v in body_verts]
    min_x = min(co.x for co in ndc_coords)
    max_x = max(co.x for co in ndc_coords)
    min_y = min(co.y for co in ndc_coords)
    max_y = max(co.y for co in ndc_coords)
    min_depth = min(co.z for co in ndc_coords)
    max_depth = max(co.z for co in ndc_coords)
    
    print(f"  NDC X (horizontal): [{min_x:.4f}, {max_x:.4f}] (Inside: {0.0 <= min_x and max_x <= 1.0})")
    print(f"  NDC Y (vertical):   [{min_y:.4f}, {max_y:.4f}] (Inside: {0.0 <= min_y and max_y <= 1.0})")
    print(f"  Camera Depth (Z):   [{min_depth:.4f}, {max_depth:.4f}]")
    
    # Also check hair vertices in camera view
    hair_objs = [o for o in bpy.data.objects if o.name.startswith("Hair_")]
    all_hair_verts = []
    for ho in hair_objs:
        all_hair_verts.extend([ho.matrix_world @ v.co for v in ho.data.vertices])
    if all_hair_verts:
        hair_ndc = [world_to_camera_view(scene, cam, v) for v in all_hair_verts]
        h_min_y = min(co.y for co in hair_ndc)
        h_max_y = max(co.y for co in hair_ndc)
        print(f"  With Hair NDC Y:    [{min(min_y, h_min_y):.4f}, {max(max_y, h_max_y):.4f}] (Inside: {0.0 <= min(min_y, h_min_y) and max(max_y, h_max_y) <= 1.0})")

