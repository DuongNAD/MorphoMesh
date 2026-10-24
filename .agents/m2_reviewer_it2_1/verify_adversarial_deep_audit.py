import sys
import math
import json
from pathlib import Path
import bpy
import mathutils
from mathutils import Vector, Matrix, Euler

blend_path = Path("output/anime_rigged.blend").resolve()
assert blend_path.exists(), f"Blend file not found: {blend_path}"

bpy.ops.wm.open_mainfile(filepath=str(blend_path))

audit_results = {
    "transforms": {},
    "armature": {},
    "fingers": {},
    "twintails": {},
    "skirt": {},
    "twist_bones": {},
    "submesh_dqs": {},
    "errors": []
}

# -------------------------------------------------------------
# 1. Verify Submesh Object Transforms & Parenting
# -------------------------------------------------------------
arm_obj = bpy.data.objects.get("Anime_Armature")
if not arm_obj:
    audit_results["errors"].append("Anime_Armature not found in scene")
else:
    audit_results["armature"]["location"] = list(arm_obj.location)
    audit_results["armature"]["rotation_euler"] = [math.degrees(a) for a in arm_obj.rotation_euler]
    audit_results["armature"]["scale"] = list(arm_obj.scale)
    audit_results["armature"]["matrix_world"] = [list(row) for row in arm_obj.matrix_world]

expected_submeshes = [
    "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
    "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
]

for name in expected_submeshes:
    obj = bpy.data.objects.get(name)
    if not obj:
        audit_results["errors"].append(f"Submesh {name} missing from scene")
        continue

    rot_deg = [round(math.degrees(a), 4) for a in obj.rotation_euler]
    loc = [round(c, 4) for c in obj.location]
    scale = [round(s, 4) for s in obj.scale]
    parent_name = obj.parent.name if obj.parent else None

    # Check that parent is Anime_Armature
    is_child = (parent_name == "Anime_Armature")
    rot_zero = (all(abs(a) < 1e-4 for a in rot_deg))

    # Vertex bounds in world space
    v_world_zs = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
    min_z = min(v_world_zs) if v_world_zs else 0.0
    max_z = max(v_world_zs) if v_world_zs else 0.0

    audit_results["transforms"][name] = {
        "parent": parent_name,
        "is_child_of_armature": is_child,
        "rotation_euler_deg": rot_deg,
        "is_rotation_zero": rot_zero,
        "location": loc,
        "scale": scale,
        "min_world_z": round(min_z, 4),
        "max_world_z": round(max_z, 4),
        "vertex_count": len(obj.data.vertices)
    }

# -------------------------------------------------------------
# 2. Verify 78-Bone Hierarchy & Root Hips
# -------------------------------------------------------------
if arm_obj:
    bones = arm_obj.data.bones
    audit_results["armature"]["bone_count"] = len(bones)
    audit_results["armature"]["has_hips_root"] = ("Hips" in bones and bones["Hips"].parent is None)

    # Check all bones are connected to Hips directly or indirectly
    unconnected_bones = []
    for b in bones:
        curr = b
        visited = set()
        connected_to_hips = False
        while curr:
            if curr.name in visited:
                break
            visited.add(curr.name)
            if curr.name == "Hips":
                connected_to_hips = True
                break
            curr = curr.parent
        if not connected_to_hips:
            unconnected_bones.append(b.name)

    audit_results["armature"]["unconnected_bones"] = unconnected_bones
    audit_results["armature"]["all_connected_to_hips"] = (len(unconnected_bones) == 0)

    # Verify canonical spine
    spine_chain = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
    spine_intact = True
    for i in range(1, len(spine_chain)):
        b = bones.get(spine_chain[i])
        expected_parent = spine_chain[i-1]
        if not b or not b.parent or b.parent.name != expected_parent:
            spine_intact = False
            audit_results["errors"].append(f"Spine broken at {spine_chain[i]}")
    audit_results["armature"]["spine_chain_intact"] = spine_intact

# -------------------------------------------------------------
# 3. Verify Twintail Secondary Chains
# -------------------------------------------------------------
if arm_obj:
    head_bone = arm_obj.data.bones.get("Head")
    pb = arm_obj.pose.bones
    hair_l_parent_head = (bones.get("Hair_L_01") and bones["Hair_L_01"].parent.name == "Head")
    hair_r_parent_head = (bones.get("Hair_R_01") and bones["Hair_R_01"].parent.name == "Head")

    audit_results["twintails"]["hair_l_01_parent_head"] = hair_l_parent_head
    audit_results["twintails"]["hair_r_01_parent_head"] = hair_r_parent_head

    twintail_bones_valid = True
    for side in ["L", "R"]:
        for i in range(1, 6):
            bname = f"Hair_{side}_{i:02d}"
            if bname not in bones:
                twintail_bones_valid = False
                audit_results["errors"].append(f"Missing twintail bone {bname}")
                continue
            if i > 1:
                expected_p = f"Hair_{side}_{i-1:02d}"
                if not bones[bname].parent or bones[bname].parent.name != expected_p:
                    twintail_bones_valid = False
                    audit_results["errors"].append(f"{bname} not parented to {expected_p}")
            pbone = pb.get(bname)
            if not pbone:
                twintail_bones_valid = False
                continue
            stiff = pbone.get("spring_stiffness")
            damp = pbone.get("spring_damping")
            mass = pbone.get("spring_mass")
            if not (abs(stiff - 150.0) < 1e-3 and abs(damp - 12.0) < 1e-3 and abs(mass - 0.20) < 1e-3):
                twintail_bones_valid = False
                audit_results["errors"].append(f"Invalid spring props on {bname}: stiff={stiff}, damp={damp}, mass={mass}")

    audit_results["twintails"]["all_properties_calibrated"] = twintail_bones_valid

# -------------------------------------------------------------
# 4. Verify 30 Articulated Fingers (Curl, Torque, Floor Plunge)
# -------------------------------------------------------------
if arm_obj:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    pb = arm_obj.pose.bones

    finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
    phalanges = ["01", "02", "03"]

    finger_audit = {}
    all_curled_toward_palm = True
    all_monotonic = True
    any_floor_plunge = False

    for side in ["L", "R"]:
        sign = 1.0 if side == "L" else -1.0
        # Palm coordinate in world space
        palm_pt = Vector((sign * 0.43550, -0.18575, 1.01439))

        for f in finger_names:
            for p in phalanges:
                bname = f"{f}.{p}.{side}"
                pbone = pb.get(bname)
                if not pbone:
                    audit_results["errors"].append(f"Missing finger pose bone {bname}")
                    continue

                pbone.rotation_mode = 'XYZ'
                pbone.rotation_euler = (0.0, 0.0, 0.0)
                bpy.context.view_layer.update()

                rest_tail = arm_obj.matrix_world @ pbone.tail
                d_rest = (rest_tail - palm_pt).length
                rest_z = rest_tail.z

                # Rotate +30 deg (0.5236 rad)
                pbone.rotation_euler = (math.radians(30.0), 0.0, 0.0)
                bpy.context.view_layer.update()
                tail_30 = arm_obj.matrix_world @ pbone.tail
                d_30 = (tail_30 - palm_pt).length
                z_30 = tail_30.z

                # Rotate +60 deg (1.0472 rad)
                pbone.rotation_euler = (math.radians(60.0), 0.0, 0.0)
                bpy.context.view_layer.update()
                tail_60 = arm_obj.matrix_world @ pbone.tail
                d_60 = (tail_60 - palm_pt).length
                z_60 = tail_60.z

                # Reset
                pbone.rotation_euler = (0.0, 0.0, 0.0)
                bpy.context.view_layer.update()

                # Curled toward palm condition: d_60 < d_30 < d_rest
                curled = (d_30 < d_rest) and (d_60 < d_30)
                if not curled:
                    all_monotonic = False
                if d_30 >= d_rest:
                    all_curled_toward_palm = False

                # Floor plunge check: floor is at z=0, hand is at z~1.0. If tail.z drops below 0.5, that would be floor plunge
                if z_30 < 0.5 or z_60 < 0.5:
                    any_floor_plunge = True

                finger_audit[bname] = {
                    "d_rest": round(d_rest, 5),
                    "d_30": round(d_30, 5),
                    "d_60": round(d_60, 5),
                    "z_rest": round(rest_z, 5),
                    "z_60": round(z_60, 5),
                    "monotonic_curl": curled
                }

    audit_results["fingers"] = {
        "count": len(finger_audit),
        "all_curled_toward_palm": all_curled_toward_palm,
        "all_monotonic": all_monotonic,
        "floor_plunge_detected": any_floor_plunge
    }

    bpy.ops.object.mode_set(mode='OBJECT')

print("AUDIT_JSON_START")
print(json.dumps(audit_results, indent=2))
print("AUDIT_JSON_END")
