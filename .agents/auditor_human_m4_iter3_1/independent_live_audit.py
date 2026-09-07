"""
Independent Forensic Live Audit Script for Milestone 4 Iteration 3 Deliverables.
Executed via Blender 4.5.4 LTS in background mode against Yu_Nian_An_Master.blend.
"""

import math
import sys
import bpy
import bmesh
import mathutils
from bpy_extras.object_utils import world_to_camera_view

print("=" * 80)
print("STARTING INDEPENDENT FORENSIC AUDIT OF YU_NIAN_AN_MASTER.BLEND")
print("=" * 80)

# ----------------------------------------------------------------------
# 1. SCENE OBJECT INVENTORY & 7-TIER COLLECTION HIERARCHY
# ----------------------------------------------------------------------
print("\n--- 1. SCENE COLLECTIONS & OBJECTS ---")
root_col = bpy.data.collections.get("Yu_Nian_An_Master")
print(f"Root collection 'Yu_Nian_An_Master' present: {root_col is not None}")
if root_col:
    child_names = [c.name for c in root_col.children]
    print(f"Child collections: {child_names}")
    expected_tiers = ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"]
    for t in expected_tiers:
        print(f"  Tier '{t}': {'PASS' if t in child_names else 'FAIL'}")

# ----------------------------------------------------------------------
# 2. CAMERA CALIBRATION & OPTICAL FRAMING (NDC BOUNDS & PIXEL AUDIT)
# ----------------------------------------------------------------------
print("\n--- 2. CAMERA CALIBRATION & OPTICAL FRAMING ---")
scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
res_x = scene.render.resolution_x
res_y = scene.render.resolution_y
aspect = res_x / res_y
print(f"Render Resolution: {res_x} x {res_y} (aspect {aspect:.4f})")

body = bpy.data.objects.get("Yu_Nian_An_Body")
if body is None:
    print("FATAL: Yu_Nian_An_Body object missing!")
    sys.exit(1)

body_verts = [body.matrix_world @ v.co for v in body.data.vertices]
body_z_min = min(v.z for v in body_verts)
body_z_max = max(v.z for v in body_verts)
print(f"Body Mesh Z range: [{body_z_min:.5f}m, {body_z_max:.5f}m], Height: {body_z_max - body_z_min:.5f}m")

# Also include hair and dress if present
all_char_verts = list(body_verts)
for obj_name in ["Mesh_Dress_Bodice", "Mesh_Dress_WaistSash", "Mesh_Dress_PleatedSkirt", "Sandals_Flat_L", "Sandals_Flat_R"]:
    o = bpy.data.objects.get(obj_name)
    if o and o.data and hasattr(o.data, "vertices"):
        all_char_verts.extend([o.matrix_world @ v.co for v in o.data.vertices])

cams_to_test = [
    "Camera_FullBody",
    "Camera_Front",
    "Camera_ThreeQuarter",
    "Camera_Profile",
    "Camera_Back",
    "Camera_Portrait_85mm",
]

camera_results = {}
for c_name in cams_to_test:
    cam_obj = bpy.data.objects.get(c_name)
    if not cam_obj:
        print(f"Camera '{c_name}': MISSING")
        camera_results[c_name] = {"missing": True}
        continue

    lens = cam_obj.data.lens
    loc = [round(x, 4) for x in cam_obj.location]
    sensor_w = cam_obj.data.sensor_width
    sensor_h = cam_obj.data.sensor_height

    # Compute NDC coordinates for all character vertices
    ndc_points = []
    for v in all_char_verts:
        p = world_to_camera_view(scene, cam_obj, v)
        if p.z > 0:  # in front of camera
            ndc_points.append(p)

    if not ndc_points:
        print(f"Camera '{c_name}': lens={lens}mm, NO VERTICES IN FRONT OF CAMERA!")
        continue

    min_x = min(p.x for p in ndc_points)
    max_x = max(p.x for p in ndc_points)
    min_y = min(p.y for p in ndc_points)
    max_y = max(p.y for p in ndc_points)

    camera_results[c_name] = {
        "lens": lens,
        "loc": loc,
        "sensor_w": sensor_w,
        "sensor_h": sensor_h,
        "ndc_x": (round(min_x, 4), round(max_x, 4)),
        "ndc_y": (round(min_y, 4), round(max_y, 4)),
    }

    # For full body cameras: check strict NDC Y in [0.05, 0.95]
    if c_name != "Camera_Portrait_85mm":
        is_50mm = (lens == 50.0)
        in_y_bounds = (min_y >= 0.05 and max_y <= 0.95)
        status = "PASS" if (is_50mm and in_y_bounds) else "FAIL"
        print(f"Camera '{c_name}': lens={lens}mm, loc={loc}, NDC X=[{min_x:.4f}, {max_x:.4f}], NDC Y=[{min_y:.4f}, {max_y:.4f}] => {status}")
        if not is_50mm:
            print(f"   VIOLATION: Expected lens 50.0mm, got {lens}mm")
        if min_y < 0.05:
            print(f"   VIOLATION: Foot margin below 0.05 (got {min_y:.4f})")
        if max_y > 0.95:
            print(f"   VIOLATION: Head decapitation risk / margin above 0.95 (got {max_y:.4f})")
    else:
        print(f"Camera '{c_name}' (Portrait): lens={lens}mm, loc={loc}, NDC X=[{min_x:.4f}, {max_x:.4f}], NDC Y=[{min_y:.4f}, {max_y:.4f}]")

# ----------------------------------------------------------------------
# 3. LIVE RENDER OF CAMERA_FULLBODY & BORDER PIXEL DECAPITATION CHECK
# ----------------------------------------------------------------------
print("\n--- 3. LIVE RENDER & BORDER PIXEL AUDIT ---")
render_out_path = r"E:\tool\mcp\MorphoMesh\.agents\auditor_human_m4_iter3_1\independent_fullbody_render.png"
cam_fb = bpy.data.objects.get("Camera_FullBody")
if cam_fb:
    scene.camera = cam_fb
    scene.render.filepath = render_out_path
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    print(f"Rendering test image from Camera_FullBody to {render_out_path}...")
    bpy.ops.render.render(write_still=True)
    print("Render complete. Inspecting pixels...")

    img = bpy.data.images.load(render_out_path)
    pixels = list(img.pixels)
    w, h = img.size[0], img.size[1]
    print(f"Loaded render image: {w} x {h}, channels: 4")

    # Check top 5 rows and bottom 5 rows for non-background alpha or luminance
    top_pixels_found = False
    for y in range(h - 5, h):
        for x in range(w):
            alpha = pixels[(y * w + x) * 4 + 3]
            r = pixels[(y * w + x) * 4 + 0]
            g = pixels[(y * w + x) * 4 + 1]
            b = pixels[(y * w + x) * 4 + 2]
            # In EEVEE_NEXT with background world or transparent, check if character pixel
            if (r + g + b) > 0.15 or alpha > 0.1:
                # Scene background might have slight gray, let's check background color
                pass

    # Let's inspect rows from top down to find first non-background geometry
    # Get world background color at corner (0, h-1)
    bg_r = pixels[((h - 1) * w + 0) * 4 + 0]
    bg_g = pixels[((h - 1) * w + 0) * 4 + 1]
    bg_b = pixels[((h - 1) * w + 0) * 4 + 2]
    print(f"Background sample at (0, {h-1}): R={bg_r:.4f}, G={bg_g:.4f}, B={bg_b:.4f}")

    def is_diff_from_bg(x, y):
        idx = (y * w + x) * 4
        r = pixels[idx]
        g = pixels[idx + 1]
        b = pixels[idx + 2]
        diff = abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)
        return diff > 0.08

    # Scan from top (h-1 down to 0)
    top_geom_y = None
    for y in range(h - 1, -1, -1):
        if any(is_diff_from_bg(x, y) for x in range(w)):
            top_geom_y = y
            break

    # Scan from bottom (0 up to h-1)
    bot_geom_y = None
    for y in range(h):
        if any(is_diff_from_bg(x, y) for x in range(w)):
            bot_geom_y = y
            break

    print(f"Top-most geometry row: Y={top_geom_y} (margin above: {h - 1 - top_geom_y} px = {(h - 1 - top_geom_y)/h*100:.2f}%)")
    print(f"Bottom-most geometry row: Y={bot_geom_y} (margin below: {bot_geom_y} px = {bot_geom_y/h*100:.2f}%)")
    if top_geom_y == h - 1:
        print("FAIL: Head / top edge decapitation detected (geometry touches row h-1)!")
    elif top_geom_y is not None:
        print(f"PASS: Zero head decapitation! Generous top headroom: {h - 1 - top_geom_y} pixels.")

    if bot_geom_y == 0:
        print("FAIL: Foot / bottom edge amputation detected (geometry touches row 0)!")
    elif bot_geom_y is not None:
        print(f"PASS: Zero foot amputation! Generous bottom margin: {bot_geom_y} pixels.")

# ----------------------------------------------------------------------
# 4. MARIONETTE STRINGS SNAPPING & RIG KINEMATICS AUDIT
# ----------------------------------------------------------------------
print("\n--- 4. MARIONETTE STRINGS SNAPPING TO FINGER DEF BONES ---")
arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
str_obj = bpy.data.objects.get("Prop_Marionette_Strings")

if not arm_obj or not str_obj:
    print(f"FATAL: Armature ({arm_obj is not None}) or Strings ({str_obj is not None}) missing!")
else:
    finger_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
    ]
    verts_per_cord = 14
    max_cord_dist = 0.0

    print("Finger Bone Tails vs String Proximal Roots:")
    for cord_i, b_name in enumerate(finger_bones):
        bone = arm_obj.data.bones.get(b_name)
        if not bone:
            print(f"  Cord {cord_i}: Bone '{b_name}' NOT FOUND in armature!")
            continue

        tail_world = arm_obj.matrix_world @ bone.tail_local
        v0_idx = cord_i * verts_per_cord
        v1_idx = v0_idx + 1

        if v1_idx >= len(str_obj.data.vertices):
            print(f"  Cord {cord_i}: Vertex index out of range!")
            continue

        v0_world = str_obj.matrix_world @ str_obj.data.vertices[v0_idx].co
        v1_world = str_obj.matrix_world @ str_obj.data.vertices[v1_idx].co
        root_center = (v0_world + v1_world) * 0.5
        dist = (root_center - tail_world).length
        dist_mm = dist * 1000.0
        if dist > max_cord_dist:
            max_cord_dist = dist

        status = "PASS" if dist < 0.002 else ("WARNING" if dist < 0.005 else "FAIL")
        print(f"  Cord {cord_i:02d} ({b_name}): dist={dist_mm:.4f}mm, bone_tail=({tail_world.x:.4f}, {tail_world.y:.4f}, {tail_world.z:.4f}), root=({root_center.x:.4f}, {root_center.y:.4f}, {root_center.z:.4f}) => {status}")

    print(f"Max String-to-Bone Root Distance: {max_cord_dist * 1000:.4f}mm (Threshold: < 2.0mm)")
    if max_cord_dist < 0.002:
        print("PASS: All 10 marionette strings snap with sub-2.0mm accuracy (0 floating gap)!")
    else:
        print("FAIL: String root distance exceeds 2.0mm specification!")

    # Check vertex groups on strings
    vg_names = [vg.name for vg in str_obj.vertex_groups]
    print(f"Strings vertex groups count: {len(vg_names)}")
    missing_vgs = [b for b in finger_bones if b not in vg_names]
    print(f"Missing finger VGs: {missing_vgs if missing_vgs else 'NONE (All 10 present)'}")

    # Check Armature modifier on strings
    arm_mods = [m for m in str_obj.modifiers if m.type == 'ARMATURE']
    print(f"Armature modifier present on strings: {len(arm_mods) > 0}")
    if arm_mods:
        print(f"  Target object: {arm_mods[0].object.name if arm_mods[0].object else 'None'}")
        print(f"  Preserve volume: {arm_mods[0].use_deform_preserve_volume}")

# ----------------------------------------------------------------------
# 5. WARDROBE SIGNED NORMAL CLEARANCE & ZERO PENETRATION AUDIT
# ----------------------------------------------------------------------
print("\n--- 5. WARDROBE SIGNED NORMAL CLEARANCE & PENETRATION AUDIT ---")
bm_body = bmesh.new()
bm_body.from_mesh(body.data)
bm_body.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

wardrobe_parts = [
    ("Mesh_Dress_Bodice", 0.004),
    ("Mesh_Dress_WaistSash", 0.004),
    ("Mesh_Dress_PleatedSkirt", 0.004),
]

for part_name, thresh in wardrobe_parts:
    obj = bpy.data.objects.get(part_name)
    if not obj:
        print(f"Garment '{part_name}': MISSING")
        continue

    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    total_verts = len(verts)
    min_signed = float('inf')
    max_signed = float('-inf')
    sum_signed = 0.0
    penetrations = 0
    pen_depth_max = 0.0

    for v in verts:
        loc, normal, _, dist = bvh.find_nearest(v)
        if loc is not None:
            # Vector from nearest body surface point to garment vertex
            diff = v - loc
            dot = diff.dot(normal)
            # If dot >= 0, vertex is outside/on body surface (+dist)
            # If dot < 0, vertex is inside body surface (-dist)
            signed = dist if dot >= 0 else -dist
            sum_signed += signed
            if signed < min_signed:
                min_signed = signed
            if signed > max_signed:
                max_signed = signed
            if dot < 0:
                penetrations += 1
                if -signed > pen_depth_max:
                    pen_depth_max = -signed

    avg_signed = sum_signed / max(1, total_verts)
    status = "PASS" if (penetrations == 0 and min_signed >= thresh) else "FAIL"
    print(f"Garment '{part_name}':")
    print(f"  Vertices: {total_verts}")
    print(f"  Min Signed Clearance: {min_signed * 1000:.2f}mm (Spec: >= +{thresh*1000:.1f}mm)")
    print(f"  Avg Signed Clearance: {avg_signed * 1000:.2f}mm")
    print(f"  Max Signed Clearance: {max_signed * 1000:.2f}mm")
    print(f"  Penetrations: {penetrations} / {total_verts} ({penetrations/total_verts*100:.1f}%)")
    if penetrations > 0:
        print(f"  Max Penetration Depth: {pen_depth_max * 1000:.2f}mm")
    print(f"  => VERDICT: {status}")

# ----------------------------------------------------------------------
# 6. SKELETON 163 DEF BONES & 52 ARKIT SHAPE KEYS
# ----------------------------------------------------------------------
print("\n--- 6. SKELETON 163 DEF BONES & 52 FACS SHAPE KEYS ---")
if arm_obj:
    def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
    print(f"Total DEF bones: {len(def_bones)} (Spec: 163)")
    print(f"  => 163 DEF Bones Status: {'PASS' if len(def_bones) == 163 else 'FAIL'}")

if body.data.shape_keys:
    sk = body.data.shape_keys
    basis = sk.key_blocks.get("Basis")
    non_basis = [kb for kb in sk.key_blocks if kb.name != "Basis"]
    print(f"Total non-basis shape keys: {len(non_basis)} (Spec: 52 ARKit)")
    zero_delta = []
    if basis:
        basis_cos = [v.co.copy() for v in basis.data]
        for kb in non_basis:
            max_d = max((v.co - basis_cos[i]).length for i, v in enumerate(kb.data))
            if max_d < 1e-6:
                zero_delta.append(kb.name)
    print(f"  Zero-delta dummy shape keys: {len(zero_delta)} ({zero_delta if zero_delta else 'NONE'})")
    print(f"  => 52 ARKit FACS Status: {'PASS' if len(non_basis) == 52 and len(zero_delta) == 0 else 'FAIL'}")

# ----------------------------------------------------------------------
# 7. HAIR EVALUATED STRATA & BUTTERFLIES
# ----------------------------------------------------------------------
print("\n--- 7. HAIR EVALUATION & BUTTERFLIES ---")
hair_obj = bpy.data.objects.get("Hair_Curves_Yu_Nian_An")
if hair_obj:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_hair = hair_obj.evaluated_get(depsgraph)
    eval_verts = len(eval_hair.data.vertices) if eval_hair.data and hasattr(eval_hair.data, "vertices") else 0
    print(f"Hair evaluated vertices: {eval_verts} across GN modifiers")
    print(f"  => Hair Evaluation Status: {'PASS' if eval_verts > 1000 else 'FAIL'}")

butterflies = [o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")]
print(f"Total butterflies: {len(butterflies)} (Spec: 10)")
butterflies_at_origin = [b.name for b in butterflies if b.location.length < 0.01]
print(f"Butterflies at (0, 0, 0): {len(butterflies_at_origin)} ({butterflies_at_origin if butterflies_at_origin else 'NONE'})")
b_z_min = min((b.location.z for b in butterflies), default=0.0)
b_z_max = max((b.location.z for b in butterflies), default=0.0)
print(f"Butterflies elevation Z: [{b_z_min:.2f}m, {b_z_max:.2f}m]")
print(f"  => Butterflies Status: {'PASS' if len(butterflies) == 10 and len(butterflies_at_origin) == 0 else 'FAIL'}")

print("\n" + "=" * 80)
print("INDEPENDENT FORENSIC AUDIT FINISHED")
print("=" * 80)
