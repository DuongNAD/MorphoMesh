"""
Deep Empirical Challenger Stress Test Suite for Milestone 4 Iteration 3.
Audits:
1. Camera NDC bounds across all 5 cameras for Body, Wardrobe, Hair, and all combined assets.
2. BVH Signed Clearance and Face Overlaps (Bodice, Sash, Skirt vs Body).
3. Evaluated Hair Vertices and Modifiers.
4. Butterfly 3D Spatial Separation and Non-Origin distribution.
5. Live Rig Rotation Deformation and Proximal Cord Snapping.
6. Eye Visibility and Anterior Placement.
"""

import sys
import math
try:
    import bpy
    import bmesh
    import mathutils
    from bpy_extras.object_utils import world_to_camera_view
except ImportError:
    bpy = None
    bmesh = None
    mathutils = None
    world_to_camera_view = None

def deep_audit():
    print("=" * 80)
    print("CHALLENGER DEEP EMPIRICAL AUDIT: Yu_Nian_An_Master.blend")
    print("=" * 80)

    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    failures = []

    # =========================================================================
    # PART 1: CAMERA NDC BOUNDS ACROSS ALL 5 CAMERAS
    # =========================================================================
    print("\n>>> PART 1: CAMERA NDC BOUNDS AUDIT")
    target_cameras = [
        "Camera_FullBody",
        "Camera_Front",
        "Camera_ThreeQuarter",
        "Camera_Profile",
        "Camera_Back"
    ]

    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    assert body_obj is not None, "Yu_Nian_An_Body missing!"
    body_eval = body_obj.evaluated_get(depsgraph)
    body_mesh = body_eval.to_mesh()
    body_world_verts = [body_eval.matrix_world @ v.co for v in body_mesh.vertices]
    body_eval.to_mesh_clear()

    # Collect character objects: Body, Wardrobe, Hair
    char_obj_names = [
        "Yu_Nian_An_Body",
        "Mesh_Dress_Bodice",
        "Mesh_Dress_WaistSash",
        "Mesh_Dress_PleatedSkirt",
        "Mesh_Sandal_L",
        "Mesh_Sandal_R",
        "Hair_Hime_Bangs",
        "Hair_Hime_Sidelocks",
        "Hair_Scalp_Crown",
        "Hair_Back_Cascade",
        "Hair_Eyebrows",
        "Hair_Eyelashes"
    ]

    all_char_verts = []
    for name in char_obj_names:
        o = bpy.data.objects.get(name)
        if o:
            ev = o.evaluated_get(depsgraph)
            m = ev.to_mesh()
            all_char_verts.extend([ev.matrix_world @ v.co for v in m.vertices])
            ev.to_mesh_clear()

    print(f"Total evaluated character vertices sampled: {len(all_char_verts)}")

    for cam_name in target_cameras:
        cam_obj = bpy.data.objects.get(cam_name)
        if not cam_obj:
            failures.append(f"Camera '{cam_name}' missing from scene!")
            print(f"FAIL: {cam_name} missing!")
            continue

        lens = cam_obj.data.lens
        loc = cam_obj.matrix_world.translation

        # Body NDC
        body_ndc = [world_to_camera_view(scene, cam_obj, v) for v in body_world_verts]
        body_in_front = [c for c in body_ndc if c.z > 0]
        body_min_y = min(c.y for c in body_in_front)
        body_max_y = max(c.y for c in body_in_front)
        body_min_x = min(c.x for c in body_in_front)
        body_max_x = max(c.x for c in body_in_front)

        # Character All NDC
        char_ndc = [world_to_camera_view(scene, cam_obj, v) for v in all_char_verts]
        char_in_front = [c for c in char_ndc if c.z > 0]
        char_min_y = min(c.y for c in char_in_front)
        char_max_y = max(c.y for c in char_in_front)
        char_min_x = min(c.x for c in char_in_front)
        char_max_x = max(c.x for c in char_in_front)

        body_y_pass = (0.05 <= body_min_y and body_max_y <= 0.95)
        char_y_pass = (0.05 <= char_min_y and char_max_y <= 0.95)

        print(f"\n  Camera: {cam_name} (lens={lens:.1f}mm, loc=({loc.x:.2f}, {loc.y:.2f}, {loc.z:.2f}))")
        print(f"    Body NDC: Y=[{body_min_y:.4f}, {body_max_y:.4f}], X=[{body_min_x:.4f}, {body_max_x:.4f}] -> {'PASS' if body_y_pass else 'FAIL'}")
        print(f"    Char NDC: Y=[{char_min_y:.4f}, {char_max_y:.4f}], X=[{char_min_x:.4f}, {char_max_x:.4f}] -> {'PASS' if char_y_pass else 'FAIL'}")

        if not body_y_pass:
            failures.append(f"{cam_name}: Body NDC Y [{body_min_y:.4f}, {body_max_y:.4f}] outside [0.05, 0.95]")
        if not char_y_pass:
            failures.append(f"{cam_name}: Full Character NDC Y [{char_min_y:.4f}, {char_max_y:.4f}] outside [0.05, 0.95]")

    # =========================================================================
    # PART 2: GARMENT BVH CLEARANCE & FACE OVERLAP AUDIT
    # =========================================================================
    print("\n>>> PART 2: GARMENT BVH CLEARANCE & FACE OVERLAPS AUDIT")
    bm_body = bmesh.new()
    bm_body.from_mesh(body_obj.data)
    bm_body.transform(body_obj.matrix_world)
    body_bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

    dress_parts = ["Mesh_Dress_Bodice", "Mesh_Dress_WaistSash", "Mesh_Dress_PleatedSkirt"]
    for d_name in dress_parts:
        d_obj = bpy.data.objects.get(d_name)
        assert d_obj is not None, f"Missing {d_name}"

        # BVH overlap check
        bm_d = bmesh.new()
        bm_d.from_mesh(d_obj.data)
        bm_d.transform(d_obj.matrix_world)
        d_bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_d)

        overlaps = body_bvh.overlap(d_bvh)
        bm_d.free()

        # Vertex signed clearance
        d_verts = [d_obj.matrix_world @ v.co for v in d_obj.data.vertices]
        signed_dists = []
        penetrations = 0
        min_clearance = float('inf')

        for v in d_verts:
            loc, normal, idx, dist = body_bvh.find_nearest(v)
            if loc is not None:
                offset = v - loc
                dot = offset.dot(normal)
                s_dist = dist if dot >= 0 else -dist
                signed_dists.append(s_dist)
                if s_dist < min_clearance:
                    min_clearance = s_dist
                if dot < 0:
                    penetrations += 1

        avg_clearance = sum(signed_dists) / len(signed_dists)
        print(f"\n  Component: {d_name} ({len(d_verts)} verts)")
        print(f"    Min Signed Clearance: {min_clearance*1000:+.2f} mm")
        print(f"    Avg Signed Clearance: {avg_clearance*1000:+.2f} mm")
        print(f"    Penetrations: {penetrations} / {len(d_verts)}")
        print(f"    BVH Face Overlaps: {len(overlaps)}")

        # Bodice specifically requires >= +5.0mm and 0 penetrations
        if d_name == "Mesh_Dress_Bodice":
            if min_clearance < 0.005:
                failures.append(f"Mesh_Dress_Bodice min clearance {min_clearance*1000:.2f}mm < +5.0mm requirement!")
            if penetrations > 0:
                failures.append(f"Mesh_Dress_Bodice has {penetrations} penetrating vertices!")
        else:
            if min_clearance < 0.004:
                failures.append(f"{d_name} min clearance {min_clearance*1000:.2f}mm < +4.0mm requirement!")
            if penetrations > 0:
                failures.append(f"{d_name} has {penetrations} penetrating vertices!")

        if len(overlaps) > 0:
            failures.append(f"{d_name} has {len(overlaps)} face overlaps with body mesh!")

    bm_body.free()

    # =========================================================================
    # PART 3: HAIR EVALUATED VERTICES & MODIFIER AUDIT
    # =========================================================================
    print("\n>>> PART 3: HAIR EVALUATED VERTICES & MODIFIERS AUDIT")
    hair_names = [
        "Hair_Hime_Bangs",
        "Hair_Hime_Sidelocks",
        "Hair_Scalp_Crown",
        "Hair_Back_Cascade",
        "Hair_Eyebrows",
        "Hair_Eyelashes"
    ]
    total_hair_verts = 0
    for h_name in hair_names:
        h_obj = bpy.data.objects.get(h_name)
        assert h_obj is not None, f"Hair object {h_name} missing"
        ev = h_obj.evaluated_get(depsgraph)
        m = ev.to_mesh()
        v_c = len(m.vertices)
        f_c = len(m.polygons)
        total_hair_verts += v_c
        ev.to_mesh_clear()
        gn_mods = [mod.name for mod in h_obj.modifiers if mod.type == 'NODES']
        print(f"  {h_name:22}: {v_c:5d} verts, {f_c:5d} faces, GN mods: {gn_mods}")
        if v_c == 0:
            failures.append(f"Hair object {h_name} evaluated to 0 vertices!")

    print(f"\n  Total Hair Evaluated Vertices: {total_hair_verts}")
    if total_hair_verts <= 10000:
        failures.append(f"Total hair evaluated vertices {total_hair_verts} <= 10,000 threshold!")
    else:
        print(f"  Hair Vertices Check: PASS ({total_hair_verts} > 10,000)")

    # =========================================================================
    # PART 4: BUTTERFLY 3D SPATIAL SEPARATION & NON-ORIGIN
    # =========================================================================
    print("\n>>> PART 4: BUTTERFLY 3D SEPARATION AUDIT")
    butterflies = sorted(
        [o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")],
        key=lambda x: x.name
    )
    assert len(butterflies) == 10, f"Expected 10 butterflies, got {len(butterflies)}"

    bf_locs = [bf.matrix_world.translation.copy() for bf in butterflies]
    for idx, (bf, loc) in enumerate(zip(butterflies, bf_locs)):
        d_origin = loc.length
        print(f"  {bf.name}: loc=({loc.x:+.4f}, {loc.y:+.4f}, {loc.z:+.4f}), dist_origin={d_origin:.3f}m, Z>0.8m: {loc.z > 0.8}")
        if d_origin < 0.1:
            failures.append(f"{bf.name} is at origin ({d_origin:.3f}m)!")
        if loc.z <= 0.8:
            failures.append(f"{bf.name} Z={loc.z:.3f}m <= 0.8m!")

    min_pair_dist = float('inf')
    closest_pair = None
    for i in range(len(bf_locs)):
        for j in range(i + 1, len(bf_locs)):
            d = (bf_locs[i] - bf_locs[j]).length
            if d < min_pair_dist:
                min_pair_dist = d
                closest_pair = (butterflies[i].name, butterflies[j].name)

    print(f"  Minimum pairwise separation: {min_pair_dist*1000:.2f} mm between {closest_pair[0]} and {closest_pair[1]}")
    if min_pair_dist < 0.050:
        failures.append(f"Butterflies minimum pairwise distance {min_pair_dist*1000:.2f}mm < 50mm!")
    else:
        print(f"  Butterfly Separation Check: PASS ({min_pair_dist*1000:.2f}mm >= 50mm)")

    # =========================================================================
    # PART 5: RIG BONE ROTATION PROPAGATION & CORD PROXIMAL SNAPPING
    # =========================================================================
    print("\n>>> PART 5: RIG ROTATION PROPAGATION & CORD SNAPPING AUDIT")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
    assert arm_obj is not None, "Armature missing!"
    assert strings_obj is not None, "Strings missing!"

    finger_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R"
    ]

    # Verify proximal string snapping to bone tails
    print("\n  --- Proximal String Root to Bone Tail Alignment ---")
    for i, b_name in enumerate(finger_bones):
        bone = arm_obj.data.bones.get(b_name)
        assert bone is not None, f"Bone {b_name} missing!"
        bone_tail_world = arm_obj.matrix_world @ bone.tail_local
        # String i root vertex is vertex i*14
        string_root_world = strings_obj.matrix_world @ strings_obj.data.vertices[i * 14].co
        gap = (string_root_world - bone_tail_world).length * 1000.0  # mm
        print(f"  Cord {i:02d} -> {b_name:16}: gap = {gap:.4f} mm (tail={bone_tail_world.to_tuple(3)}, root={string_root_world.to_tuple(3)})")
        if gap >= 2.0:
            failures.append(f"Cord {i} proximal root is {gap:.2f}mm away from {b_name} tail (required < 2.0mm)!")

    # Verify rotation deformation
    print("\n  --- Bone Rotation Propagation ---")
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()

    eval_s_base = strings_obj.evaluated_get(deps)
    m_s_base = eval_s_base.to_mesh()
    base_s_coords = [eval_s_base.matrix_world @ v.co for v in m_s_base.vertices]
    eval_s_base.to_mesh_clear()

    for b_idx, b_name in enumerate(finger_bones):
        pb = arm_obj.pose.bones.get(b_name)
        assert pb is not None, f"Pose bone {b_name} missing!"
        orig_euler = pb.rotation_euler.copy()
        orig_mode = pb.rotation_mode

        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (math.radians(45.0), 0.0, math.radians(45.0))
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()

        eval_s_rot = strings_obj.evaluated_get(deps)
        m_s_rot = eval_s_rot.to_mesh()
        rot_s_coords = [eval_s_rot.matrix_world @ v.co for v in m_s_rot.vertices]
        eval_s_rot.to_mesh_clear()

        disp = max((r - b).length for r, b in zip(rot_s_coords, base_s_coords))

        target_bf = butterflies[b_idx % len(butterflies)]
        eval_bf = target_bf.evaluated_get(deps)
        m_bf = eval_bf.to_mesh()
        rot_bf_coords = [eval_bf.matrix_world @ v.co for v in m_bf.vertices]
        eval_bf.to_mesh_clear()

        # Compare with unrotated bf
        pb.rotation_euler = orig_euler
        pb.rotation_mode = orig_mode
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()

        eval_bf_orig = target_bf.evaluated_get(deps)
        m_bf_orig = eval_bf_orig.to_mesh()
        orig_bf_coords = [eval_bf_orig.matrix_world @ v.co for v in m_bf_orig.vertices]
        eval_bf_orig.to_mesh_clear()

        bf_disp = max((r - o).length for r, o in zip(rot_bf_coords, orig_bf_coords))

        print(f"  {b_name:16}: Max String Disp={disp*1000:6.2f} mm, Butterfly Disp={bf_disp*1000:6.2f} mm")
        if disp < 0.003:
            failures.append(f"Bone {b_name} rotation produced only {disp*1000:.2f}mm string displacement (< 3mm)!")
        if bf_disp < 0.003:
            failures.append(f"Bone {b_name} rotation produced only {bf_disp*1000:.2f}mm butterfly displacement (< 3mm)!")

    # =========================================================================
    # PART 6: EYE MESH ANTERIOR Y & FRONT CAMERA LINE OF SIGHT
    # =========================================================================
    print("\n>>> PART 6: EYE MESH ANTERIOR Y & LINE OF SIGHT AUDIT")
    eye_objs = [
        "Mesh_Eye_Left_CorneaSclera", "Mesh_Eye_Left_IrisPupil",
        "Mesh_Eye_Right_CorneaSclera", "Mesh_Eye_Right_IrisPupil"
    ]

    for e_name in eye_objs:
        e_obj = bpy.data.objects.get(e_name)
        assert e_obj is not None, f"Eye object {e_name} missing"
        ev = e_obj.evaluated_get(depsgraph)
        m = ev.to_mesh()
        world_verts = [ev.matrix_world @ v.co for v in m.vertices]
        ev.to_mesh_clear()

        min_y = min(v.y for v in world_verts)
        center = sum((v for v in world_verts), mathutils.Vector((0,0,0))) / len(world_verts)
        print(f"  {e_name:28}: anterior Y = {min_y:.5f}m, center = {center.to_tuple(3)}")
        if min_y < -0.135:
            failures.append(f"{e_name} anterior Y {min_y:.5f}m < -0.135m (buried)!")

    bm_b = bmesh.new()
    bm_b.from_mesh(body_obj.data)
    bm_b.transform(body_obj.matrix_world)
    bvh_b = mathutils.bvhtree.BVHTree.FromBMesh(bm_b)

    cam_front = bpy.data.objects.get("Camera_Front")
    for c_name in ["Mesh_Eye_Left_CorneaSclera", "Mesh_Eye_Right_CorneaSclera"]:
        c = bpy.data.objects.get(c_name)
        c_pos = c.matrix_world.translation
        cam_pos = cam_front.matrix_world.translation
        ray_dir = (c_pos - cam_pos).normalized()
        ray_len = (c_pos - cam_pos).length
        hit_loc, hit_norm, hit_idx, hit_dist = bvh_b.ray_cast(cam_pos, ray_dir, ray_len - 0.002)
        if hit_loc:
            print(f"  {c_name}: OCCLUDED by cranial mesh at {hit_loc.to_tuple(3)}")
            failures.append(f"{c_name} occluded from Camera_Front by body mesh!")
        else:
            print(f"  {c_name}: UNRESTRICTED LINE OF SIGHT from Camera_Front.")

    bm_b.free()

    # =========================================================================
    # SUMMARY & FINAL VERDICT
    # =========================================================================
    print("\n" + "=" * 80)
    print("CHALLENGER DEEP AUDIT SUMMARY")
    print("=" * 80)
    if failures:
        print(f"FAILURES ENCOUNTERED ({len(failures)}):")
        for f in failures:
            print(f"  - [DEFECT] {f}")
        print("\nFINAL CHALLENGER VERDICT: CHALLENGE")
        sys.exit(2)
    else:
        print("ALL EMPIRICAL TESTS PASSED SATISFACTORILY!")
        print("FINAL CHALLENGER VERDICT: CONFIRM (ROBUST)")
        sys.exit(0)

if __name__ == "__main__":
    deep_audit()
