"""
Comprehensive Adversarial Empirical Stress Test Harness for Milestone 4 Iteration 2.
Directly audits live Blender 4.5.4 LTS output/yu_nian_an/Yu_Nian_An_Master.blend.

Evaluates all 5 assignment requirements:
1. Evaluated hair geometry vertices across 6 layers (> 0).
2. Butterfly 3D non-origin and 3D spatial separation (Z > 0.8m).
3. Live finger DEF bone rotation deformation on strings and butterflies.
4. Dress-to-body clearance offset (>= +4mm with 0 penetration).
5. Eye mesh anterior Y (>= -0.135m) and front camera visibility.
"""

import sys
import math
try:
    import bpy
    import bmesh
    import mathutils
except ImportError:
    bpy = None
    bmesh = None
    mathutils = None

def run_empirical_adversarial_challenge():
    print("=" * 80)
    print("CHALLENGER DEEP EMPIRICAL STRESS AUDIT — BLENDER 4.5.4 LTS")
    print("=" * 80)

    audit_results = {
        "hair_layers": {},
        "butterflies": {},
        "rig_deformation": {},
        "dress_clearance": {},
        "eye_visibility": {},
        "verdict": "CHALLENGE",
        "failures": []
    }

    depsgraph = bpy.context.evaluated_depsgraph_get()

    # --------------------------------------------------------------------------
    # 1. HAIR CURVE LAYERS EVALUATED VERTICES CHECK
    # --------------------------------------------------------------------------
    print("\n--- [TEST 1] EVALUATED HAIR GEOMETRY AUDIT ---")
    hair_layers = [
        "Hair_Hime_Bangs",
        "Hair_Hime_Sidelocks",
        "Hair_Scalp_Crown",
        "Hair_Back_Cascade",
        "Hair_Eyebrows",
        "Hair_Eyelashes"
    ]

    all_hair_passed = True
    for h_name in hair_layers:
        obj = bpy.data.objects.get(h_name)
        if not obj:
            print(f"FAIL: Hair object '{h_name}' missing from bpy.data.objects!")
            audit_results["hair_layers"][h_name] = {"status": "MISSING"}
            all_hair_passed = False
            continue

        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        v_count = len(eval_mesh.vertices)
        f_count = len(eval_mesh.polygons)

        if v_count > 0:
            world_verts = [eval_obj.matrix_world @ v.co for v in eval_mesh.vertices]
            min_z = min(v.z for v in world_verts)
            max_z = max(v.z for v in world_verts)
            min_y = min(v.y for v in world_verts)
            max_y = max(v.y for v in world_verts)
            bbox_str = f"Z=[{min_z:.3f}m, {max_z:.3f}m], Y=[{min_y:.3f}m, {max_y:.3f}m]"
        else:
            bbox_str = "EMPTY"

        eval_obj.to_mesh_clear()
        gn_mods = [m.name for m in obj.modifiers if m.type == 'NODES']
        has_gn = len(gn_mods) > 0

        print(f"  Layer '{h_name}': {v_count} eval verts, {f_count} eval faces, GN={has_gn} ({gn_mods}), BBox: {bbox_str}")
        audit_results["hair_layers"][h_name] = {
            "eval_vertices": v_count,
            "eval_faces": f_count,
            "has_gn": has_gn,
            "bbox": bbox_str,
            "status": "PASS" if v_count > 0 else "FAIL"
        }
        if v_count <= 0:
            all_hair_passed = False

    if not all_hair_passed:
        audit_results["failures"].append("Hair geometry evaluation failed: one or more layers have 0 vertices.")
    print(f"Test 1 Result: {'PASS' if all_hair_passed else 'FAIL'}")

    # --------------------------------------------------------------------------
    # 2. BUTTERFLY 3D NON-ORIGIN & 3D SPATIAL SEPARATION CHECK
    # --------------------------------------------------------------------------
    print("\n--- [TEST 2] BUTTERFLY 3D NON-ORIGIN & SEPARATION AUDIT ---")
    bf_objs = sorted(
        [o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")],
        key=lambda x: x.name
    )
    print(f"Found {len(bf_objs)} butterfly objects: {[o.name for o in bf_objs]}")
    assert len(bf_objs) == 10, f"Expected exactly 10 butterflies, found {len(bf_objs)}"

    bf_positions = []
    all_butterflies_valid = True

    for bf in bf_objs:
        loc = bf.matrix_world.translation
        bf_positions.append((bf.name, loc.copy()))
        dist_from_origin = loc.length
        is_non_origin = dist_from_origin > 0.1
        is_above_08 = loc.z > 0.80

        print(f"  {bf.name}: Pos=({loc.x:+.4f}, {loc.y:+.4f}, {loc.z:+.4f}), DistToOrigin={dist_from_origin:.3f}m, Z>0.8: {is_above_08}")
        if not (is_non_origin and is_above_08):
            all_butterflies_valid = False

    pairwise_distances = []
    for i in range(len(bf_positions)):
        for j in range(i + 1, len(bf_positions)):
            name_i, pos_i = bf_positions[i]
            name_j, pos_j = bf_positions[j]
            dist = (pos_i - pos_j).length
            pairwise_distances.append((dist, name_i, name_j))

    pairwise_distances.sort(key=lambda x: x[0])
    min_dist, closest_pair_a, closest_pair_b = pairwise_distances[0]
    print(f"  Minimum Pairwise Distance: {min_dist*1000:.2f} mm between {closest_pair_a} and {closest_pair_b}")
    print(f"  Max Pairwise Distance: {pairwise_distances[-1][0]*1000:.2f} mm between {pairwise_distances[-1][1]} and {pairwise_distances[-1][2]}")

    is_sep_valid = (min_dist >= 0.050 and all_butterflies_valid)
    if not is_sep_valid:
        audit_results["failures"].append("Butterfly separation check failed.")
    print(f"Test 2 Result: {'PASS' if is_sep_valid else 'FAIL'}")

    # --------------------------------------------------------------------------
    # 3. LIVE BONE ROTATION ON FINGER DEF BONES (DEFORMATION PROPAGATION)
    # --------------------------------------------------------------------------
    print("\n--- [TEST 3] LIVE FINGER DEF BONE ROTATION DEFORMATION AUDIT ---")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")

    finger_def_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
    ]

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    eval_strings = strings_obj.evaluated_get(depsgraph)
    base_m = eval_strings.to_mesh()
    base_strings_coords = [eval_strings.matrix_world @ v.co for v in base_m.vertices]
    eval_strings.to_mesh_clear()

    base_bf_coords = {}
    for bf in bf_objs:
        bf_eval = bf.evaluated_get(depsgraph)
        bf_m = bf_eval.to_mesh()
        base_bf_coords[bf.name] = [bf_eval.matrix_world @ v.co for v in bf_m.vertices]
        bf_eval.to_mesh_clear()

    all_rotations_deformed = True
    for b_idx, b_name in enumerate(finger_def_bones):
        pbone = arm_obj.pose.bones.get(b_name)
        if not pbone:
            all_rotations_deformed = False
            continue

        orig_rot_mode = pbone.rotation_mode
        orig_rot_euler = pbone.rotation_euler.copy()
        orig_rot_quat = pbone.rotation_quaternion.copy()

        pbone.rotation_mode = 'XYZ'
        pbone.rotation_euler = (math.radians(60.0), 0.0, math.radians(30.0))

        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()

        eval_strings_rot = strings_obj.evaluated_get(depsgraph)
        m_rot = eval_strings_rot.to_mesh()
        rot_strings_coords = [eval_strings_rot.matrix_world @ v.co for v in m_rot.vertices]
        eval_strings_rot.to_mesh_clear()

        string_displacements = [
            (r - b).length for r, b in zip(rot_strings_coords, base_strings_coords)
        ]
        max_string_disp = max(string_displacements)

        target_bf = bf_objs[b_idx % len(bf_objs)]
        eval_bf_rot = target_bf.evaluated_get(depsgraph)
        bf_m_rot = eval_bf_rot.to_mesh()
        rot_bf_coords = [eval_bf_rot.matrix_world @ v.co for v in bf_m_rot.vertices]
        eval_bf_rot.to_mesh_clear()

        bf_displacements = [
            (r - b).length for r, b in zip(rot_bf_coords, base_bf_coords[target_bf.name])
        ]
        max_bf_disp = max(bf_displacements)

        is_string_deformed = max_string_disp >= 0.003
        is_bf_translated = max_bf_disp >= 0.003
        if not (is_string_deformed and is_bf_translated):
            all_rotations_deformed = False

        print(f"  Bone '{b_name}': String Max Disp={max_string_disp*1000:.2f} mm, Butterfly {target_bf.name} Max Disp={max_bf_disp*1000:.2f} mm -> {'PASS' if is_string_deformed and is_bf_translated else 'FAIL'}")

        pbone.rotation_euler = orig_rot_euler
        pbone.rotation_quaternion = orig_rot_quat
        pbone.rotation_mode = orig_rot_mode
        bpy.context.view_layer.update()

    if not all_rotations_deformed:
        audit_results["failures"].append("Finger bone rotation failed to propagate deformation to strings or butterflies.")
    print(f"Test 3 Result: {'PASS' if all_rotations_deformed else 'FAIL'}")

    # --------------------------------------------------------------------------
    # 4. DRESS-TO-BODY CLEARANCE OFFSET & ZERO PENETRATION CHECK
    # --------------------------------------------------------------------------
    print("\n--- [TEST 4] DRESS-TO-BODY CLEARANCE OFFSET AUDIT ---")
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    bm_body = bmesh.new()
    bm_body.from_mesh(body_obj.data)
    bm_body.transform(body_obj.matrix_world)
    body_bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

    dress_components = [
        "Mesh_Dress_Bodice",
        "Mesh_Dress_PleatedSkirt",
        "Mesh_Dress_WaistSash"
    ]

    all_clearance_passed = True
    for d_name in dress_components:
        d_obj = bpy.data.objects.get(d_name)
        d_verts = [d_obj.matrix_world @ v.co for v in d_obj.data.vertices]

        signed_distances = []
        penetrations = 0
        min_clearance = float('inf')

        for v in d_verts:
            loc, normal, idx, dist = body_bvh.find_nearest(v)
            if loc is not None:
                offset_vec = v - loc
                dot = offset_vec.dot(normal)
                signed_dist = dist if dot >= 0 else -dist
                signed_distances.append(signed_dist)

                if signed_dist < min_clearance:
                    min_clearance = signed_dist
                if dot < 0:
                    penetrations += 1

        avg_dist = sum(signed_distances) / len(signed_distances)
        passed = (min_clearance >= 0.004 and penetrations == 0)
        print(f"  {d_obj.name}: Min Signed Clearance = {min_clearance*1000:.2f} mm, Avg = {avg_dist*1000:.2f} mm, Penetrations = {penetrations} / {len(d_verts)} -> {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_clearance_passed = False
            audit_results["failures"].append(
                f"{d_obj.name} failed clearance offset: min_clearance={min_clearance*1000:.2f}mm (required >= +4.0mm), penetrations={penetrations}"
            )

    bm_body.free()
    print(f"Test 4 Result: {'PASS' if all_clearance_passed else 'FAIL'}")

    # --------------------------------------------------------------------------
    # 5. EYE MESH ANTERIOR Y COORDINATE & FRONT CAMERA VISIBILITY CHECK
    # --------------------------------------------------------------------------
    print("\n--- [TEST 5] EYE MESH ANTERIOR Y & FRONT CAMERA VISIBILITY AUDIT ---")
    eye_objs = [
        "Mesh_Eye_Left_CorneaSclera", "Mesh_Eye_Left_IrisPupil",
        "Mesh_Eye_Right_CorneaSclera", "Mesh_Eye_Right_IrisPupil"
    ]

    all_eyes_passed = True
    for e_name in eye_objs:
        e_obj = bpy.data.objects.get(e_name)
        eval_obj = e_obj.evaluated_get(depsgraph)
        m = eval_obj.to_mesh()
        world_verts = [eval_obj.matrix_world @ v.co for v in m.vertices]
        eval_obj.to_mesh_clear()

        min_y = min(v.y for v in world_verts)
        max_y = max(v.y for v in world_verts)
        center_y = sum(v.y for v in world_verts) / len(world_verts)
        center_z = sum(v.z for v in world_verts) / len(world_verts)
        center_x = sum(v.x for v in world_verts) / len(world_verts)

        is_valid = min_y >= -0.135
        print(f"  {e_name}: min_y={min_y:.5f}m, center=({center_x:+.4f}, {center_y:+.4f}, {center_z:+.4f}), min_y>=-0.135m: {is_valid}")
        if not is_valid:
            all_eyes_passed = False

    cam = bpy.data.objects.get("Camera_Front") or bpy.data.objects.get("Camera_Portrait_85mm")
    bm2 = bmesh.new()
    bm2.from_mesh(body_obj.data)
    bm2.transform(body_obj.matrix_world)
    bvh2 = mathutils.bvhtree.BVHTree.FromBMesh(bm2)

    for c_name in ["Mesh_Eye_Left_CorneaSclera", "Mesh_Eye_Right_CorneaSclera"]:
        c = bpy.data.objects.get(c_name)
        c_pos = c.matrix_world.translation
        cam_pos = cam.matrix_world.translation
        ray_dir = (c_pos - cam_pos).normalized()
        ray_len = (c_pos - cam_pos).length
        hit_loc, hit_norm, hit_idx, hit_dist = bvh2.ray_cast(cam_pos, ray_dir, ray_len - 0.002)
        if hit_loc:
            print(f"  Raycast to {c_name}: OCCLUDED by body at {hit_loc}")
            all_eyes_passed = False
        else:
            print(f"  Raycast to {c_name}: CLEAN LINE OF SIGHT! No cranial occlusion.")

    bm2.free()
    if not all_eyes_passed:
        audit_results["failures"].append("Eye anterior Y or front camera line of sight failed.")
    print(f"Test 5 Result: {'PASS' if all_eyes_passed else 'FAIL'}")

    # --------------------------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("EMPIRICAL AUDIT SUMMARY:")
    print(f"  Test 1 (Evaluated Hair Layers): {'PASS' if all_hair_passed else 'FAIL'}")
    print(f"  Test 2 (Butterfly 3D Separation): {'PASS' if is_sep_valid else 'FAIL'}")
    print(f"  Test 3 (Rig Bone Rotation Propagation): {'PASS' if all_rotations_deformed else 'FAIL'}")
    print(f"  Test 4 (Dress Clearance >= +4mm & 0 Pen): {'PASS' if all_clearance_passed else 'FAIL'}")
    print(f"  Test 5 (Eye Anterior Y & Visibility): {'PASS' if all_eyes_passed else 'FAIL'}")
    print("=" * 80)

    if audit_results["failures"]:
        print(f"\nCRITICAL ADVERSARIAL CHALLENGES DETECTED ({len(audit_results['failures'])}):")
        for f in audit_results["failures"]:
            print(f"  - [DEFECT] {f}")
        print("\nFINAL VERDICT: CHALLENGE")
        sys.exit(2)
    else:
        print("\nFINAL VERDICT: CONFIRM (ROBUST)")
        sys.exit(0)

if __name__ == '__main__':
    run_empirical_adversarial_challenge()