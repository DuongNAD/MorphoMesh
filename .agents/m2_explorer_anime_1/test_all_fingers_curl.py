import bpy
import math
from mathutils import Vector, Euler

import sys
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\src")
from morphomesh.human.mold_loader import extract_makehuman_joint_landmarks

lm = extract_makehuman_joint_landmarks(1.65)

bpy.ops.wm.read_factory_settings(use_empty=True)
arm_data = bpy.data.armatures.new("Anime_Armature")
arm_obj = bpy.data.objects.new("Anime_Armature", arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones

finger_keys = [
    ("Thumb", 1),
    ("Index", 2),
    ("Middle", 3),
    ("Ring", 4),
    ("Pinky", 5),
]
phalanges = ["01", "02", "03"]

for side in ["L", "R"]:
    side_prefix = "joint-l-" if side == "L" else "joint-r-"
    sign = 1.0 if side == "L" else -1.0

    b_hand = eb.new(f"Hand.{side}")
    b_hand.head = Vector(lm[f"{side_prefix}hand"])
    b_hand.tail = Vector(lm[f"{side_prefix}finger-3-1"])
    dorsal_normal = Vector((sign * -0.2, -0.6, 0.77)).normalized()
    b_hand.align_roll(dorsal_normal)

    for finger_name, f_idx in finger_keys:
        parent = b_hand
        pts = [lm[f"{side_prefix}finger-{f_idx}-{k}"] for k in range(1, 5)]

        p0, p1, p2, p3 = [Vector(p) for p in pts]
        v01 = (p1 - p0).normalized()
        v12 = (p2 - p1).normalized()
        v23 = (p3 - p2).normalized()

        hinge_axis = v01.cross(v12)
        if hinge_axis.length < 1e-4:
            hinge_axis = v12.cross(v23)
        if hinge_axis.length > 1e-4:
            hinge_axis.normalize()
            finger_up = hinge_axis.cross(v01).normalized()
            if finger_up.z < 0:
                finger_up = -finger_up
        else:
            finger_up = dorsal_normal

        # For Thumb, adjust up-vector to point outward/dorsal relative to thumb plane
        if finger_name == "Thumb":
            # Thumb anatomical orientation: dorsal is more anterior-up
            finger_up = Vector((sign * 0.5, -0.6, 0.6)).normalized()

        for i, ph in enumerate(phalanges):
            bname = f"{finger_name}.{ph}.{side}"
            b = eb.new(bname)
            b.head = Vector(pts[i])
            b.tail = Vector(pts[i+1])
            b.parent = parent
            b.use_connect = (i > 0)
            b.align_roll(finger_up)
            parent = b

bpy.ops.object.mode_set(mode='POSE')
pb = arm_obj.pose.bones

print("=== Testing Full 5-Finger Fist Curl (Left Hand) ===")
palm_l = Vector(lm["joint-l-hand-2"])
for finger_name, _ in finger_keys:
    d_rest = (Vector(lm[f"joint-l-finger-{_}-4"]) - palm_l).length
    for ph in phalanges:
        bname = f"{finger_name}.{ph}.L"
        pb[bname].rotation_mode = 'XYZ'
        curl_angle = 50.0 if finger_name != "Thumb" else 35.0
        pb[bname].rotation_euler = Euler((math.radians(curl_angle), 0, 0), 'XYZ')

bpy.context.view_layer.update()

for finger_name, _ in finger_keys:
    d_rest = (Vector(lm[f"joint-l-finger-{_}-4"]) - palm_l).length
    curled_tip = pb[f"{finger_name}.03.L"].tail
    d_curled = (curled_tip - palm_l).length
    print(f"  {finger_name:6s}: Rest dist={d_rest:.4f}m -> Curled dist={d_curled:.4f}m (diff: {d_rest - d_curled:+.4f}m)")
    assert d_curled < d_rest, f"{finger_name} failed to curl towards palm!"

print("=== Full Fist Curl Test PASSED for all 5 fingers! ===")

bpy.ops.object.mode_set(mode='OBJECT')
