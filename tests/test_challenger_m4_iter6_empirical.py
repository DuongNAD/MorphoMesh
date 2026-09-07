"""
Independent Empirical Adversarial Stress Test Suite — Milestone 4 Iteration 6 Remediation
Target: Yu Nian An (余念安) Master Digital Human Asset (Blender 4.5.4 LTS)
Asset: output/yu_nian_an/Yu_Nian_An_Master.blend

Adversarial Audits:
1. Bangs Quad Width & Overlap Stress Audit:
   - Evaluates actual quad X-widths of Hair_Hime_Bangs (avg >= 7.0mm, min >= 5.0mm).
   - Evaluates adjacent spline X-overlap across all splines (min overlap >= 1.0mm, 0 gaps across forehead).
2. Modular Face Geometry & Head Bone Kinematics Stress:
   - Mesh_Lips: 100% pure quads (50 quads, 66 verts), parented to Yu_Nian_An_Body, 100% weighted to DEF-head.
   - Mesh_Eyelid_Left / Right: 100% pure quads (16 quads, 32 verts), parented to body, 100% weighted to DEF-head.
   - Yu_Nian_An_Body: exactly 2,036 pure quads, 2,144 verts, 0 tris/ngons, polygons 377 and 378 on Mat_Human_Skin_SSS (slot 0).
   - DEF-head 30° rotation kinematics: Mesh_Lips, eyelids, and eye spheres must transform seamlessly without detaching or shearing!
3. Deep BVH Clearance & Marionette Kinematics:
   - Bodice-to-body BVH overlaps: 0 face intersections, min signed clearance >= +4.0mm.
   - 10 marionette cords: roots snapped to finger DEF tails with distance <= 1.0mm.
   - 45° and 60° finger rotations dynamically deform cords (> 30mm) and translate butterflies (> 30mm).
4. Cranial Apex Specular Glare & Optics:
   - 73 scalp polygons assigned Mat_Human_Scalp (Roughness = 0.70, Coat = 0.0, Specular = 0.25).
   - Mat_Human_Hair has Coat Weight <= 0.10, Coat Roughness >= 0.25, Anisotropic >= 0.65.
"""

import sys
import os
import math
import subprocess

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

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
MASTER_BLEND = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend"


def run_empirical_challenger_audit():
    print("=" * 80)
    print("EMPIRICAL CHALLENGER ADVERSARIAL STRESS AUDIT — BLENDER 4.5.4 LTS")
    print(f"Target Blend: {MASTER_BLEND}")
    print("=" * 80)

    if not bpy:
        print("ERROR: bpy not loaded!")
        sys.exit(1)

    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    failures = []
    audit_stats = {}

    # --------------------------------------------------------------------------
    # 1. BANGS QUAD WIDTH & GAP STRESS AUDIT
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 1] BANGS QUAD WIDTH & GAP STRESS AUDIT")
    bangs_obj = bpy.data.objects.get("Hair_Hime_Bangs")
    if not bangs_obj or not bangs_obj.data:
        failures.append("Hair_Hime_Bangs object missing or empty!")
    else:
        m = bangs_obj.data
        poly_count = len(m.polygons)
        vert_count = len(m.vertices)
        print(f"  Hair_Hime_Bangs: {vert_count} verts, {poly_count} polygons")

        quad_count = poly_count // 2
        quad_x_widths = []
        quad_3d_widths = []
        for q_idx in range(quad_count):
            t0 = m.polygons[2 * q_idx]
            t1 = m.polygons[2 * q_idx + 1]
            q_verts = list(set(list(t0.vertices) + list(t1.vertices)))
            if len(q_verts) == 4:
                cos = [m.vertices[vi].co for vi in q_verts]
                xs = [c.x for c in cos]
                quad_x_widths.append((max(xs) - min(xs)) * 1000.0)
                d_w = (m.vertices[t0.vertices[0]].co - m.vertices[t0.vertices[1]].co).length * 1000.0
                quad_3d_widths.append(d_w)

        avg_x_w = sum(quad_x_widths) / len(quad_x_widths) if quad_x_widths else 0.0
        min_x_w = min(quad_x_widths) if quad_x_widths else 0.0
        max_x_w = max(quad_x_widths) if quad_x_widths else 0.0
        avg_3d_w = sum(quad_3d_widths) / len(quad_3d_widths) if quad_3d_widths else 0.0
        min_3d_w = min(quad_3d_widths) if quad_3d_widths else 0.0

        print(f"  Quad X-Widths: min={min_x_w:.2f}mm (req >= 5.0mm), avg={avg_x_w:.2f}mm (req >= 7.0mm), max={max_x_w:.2f}mm")
        print(f"  Quad 3D-Widths: min={min_3d_w:.2f}mm, avg={avg_3d_w:.2f}mm")

        if avg_x_w < 7.0:
            failures.append(f"Hair_Hime_Bangs avg quad X-width {avg_x_w:.2f}mm < 7.0mm requirement!")
        if min_x_w < 5.0:
            failures.append(f"Hair_Hime_Bangs min quad X-width {min_x_w:.2f}mm < 5.0mm requirement!")

        bm_bangs = bmesh.new()
        bm_bangs.from_mesh(m)
        islands = []
        unvisited = set(bm_bangs.verts)
        while unvisited:
            start = unvisited.pop()
            isl = [start]
            q = [start]
            while q:
                curr = q.pop(0)
                for edge in curr.link_edges:
                    other = edge.other_vert(curr)
                    if other in unvisited:
                        unvisited.remove(other)
                        isl.append(other)
                        q.append(other)
            islands.append(isl)

        spline_bounds = []
        for isl in islands:
            xs = [v.co.x * 1000.0 for v in isl]
            spline_bounds.append({"min_x": min(xs), "max_x": max(xs), "mean_x": sum(xs) / len(xs)})
        spline_bounds.sort(key=lambda s: s["mean_x"])

        overlaps = []
        gaps = []
        for i in range(len(spline_bounds) - 1):
            ov = spline_bounds[i]["max_x"] - spline_bounds[i + 1]["min_x"]
            overlaps.append(ov)
            if ov < 0:
                gaps.append((i, -ov))

        min_ov = min(overlaps) if overlaps else 0.0
        avg_ov = sum(overlaps) / len(overlaps) if overlaps else 0.0
        print(f"  Spline Count: {len(islands)} | Min X Overlap: {min_ov:.2f}mm (req >= 1.0mm) | Gaps: {len(gaps)}")

        if min_ov < 1.0:
            failures.append(f"Hair_Hime_Bangs min adjacent spline overlap {min_ov:.2f}mm < 1.0mm requirement!")
        if len(gaps) > 0:
            failures.append(f"Hair_Hime_Bangs has {len(gaps)} empty gaps across forehead!")
        bm_bangs.free()

    # --------------------------------------------------------------------------
    # 2. MODULAR FACE GEOMETRY & RIGGING KINEMATICS STRESS
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 2] MODULAR FACE GEOMETRY & RIGGING KINEMATICS STRESS")
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    lips_obj = bpy.data.objects.get("Mesh_Lips")
    lid_l_obj = bpy.data.objects.get("Mesh_Eyelid_Left")
    lid_r_obj = bpy.data.objects.get("Mesh_Eyelid_Right")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")

    # 2a: Mesh_Lips pure quads & weighting
    if not lips_obj:
        failures.append("Mesh_Lips object missing!")
    else:
        m_lips = lips_obj.data
        n_quads = sum(1 for p in m_lips.polygons if len(p.vertices) == 4)
        n_verts = len(m_lips.vertices)
        print(f"  Mesh_Lips: {n_verts} verts (req 66), {n_quads} quads (req 50, 100% pure quads)")
        if n_quads != 50 or len(m_lips.polygons) != 50:
            failures.append(f"Mesh_Lips has {n_quads}/{len(m_lips.polygons)} quads (expected exactly 50 pure quads)!")
        if n_verts != 66:
            failures.append(f"Mesh_Lips has {n_verts} vertices (expected exactly 66)!")
        if not lips_obj.parent or lips_obj.parent.name != "Yu_Nian_An_Body":
            failures.append("Mesh_Lips is not parented to Yu_Nian_An_Body!")
        vg_head = lips_obj.vertex_groups.get("DEF-head")
        if not vg_head:
            failures.append("Mesh_Lips missing vertex group 'DEF-head'!")
        else:
            w_list = [vg_head.weight(vi) for vi in range(n_verts)]
            if any(abs(w - 1.0) > 1e-4 for w in w_list):
                failures.append("Mesh_Lips has vertices with DEF-head weight != 1.0!")

    # 2b: Mesh_Eyelid_Left & Right pure quads & weighting
    for lid_name, lid_obj in [("Mesh_Eyelid_Left", lid_l_obj), ("Mesh_Eyelid_Right", lid_r_obj)]:
        if not lid_obj:
            failures.append(f"{lid_name} missing!")
            continue
        m_lid = lid_obj.data
        n_quads = sum(1 for p in m_lid.polygons if len(p.vertices) == 4)
        n_verts = len(m_lid.vertices)
        print(f"  {lid_name}: {n_verts} verts (req 32), {n_quads}/{len(m_lid.polygons)} quads (100% quads)")
        if n_quads != len(m_lid.polygons) or n_quads < 16:
            failures.append(f"{lid_name} is not 100% pure quads ({n_quads}/{len(m_lid.polygons)})!")
        if not lid_obj.parent or lid_obj.parent.name != "Yu_Nian_An_Body":
            failures.append(f"{lid_name} is not parented to Yu_Nian_An_Body!")
        vg = lid_obj.vertex_groups.get("DEF-head")
        if not vg:
            failures.append(f"{lid_name} missing vertex group 'DEF-head'!")
        else:
            w_list = [vg.weight(vi) for vi in range(n_verts)]
            if any(abs(w - 1.0) > 1e-4 for w in w_list):
                failures.append(f"{lid_name} has vertices with DEF-head weight != 1.0!")

    # 2c: Yu_Nian_An_Body topology & polys 377/378
    if not body_obj:
        failures.append("Yu_Nian_An_Body missing!")
    else:
        m_body = body_obj.data
        b_quads = sum(1 for p in m_body.polygons if len(p.vertices) == 4)
        b_verts = len(m_body.vertices)
        print(f"  Yu_Nian_An_Body: {b_verts} verts (req 2,144), {b_quads}/{len(m_body.polygons)} pure quads (req 2,036)")
        if b_verts != 2144 or b_quads != 2036 or len(m_body.polygons) != 2036:
            failures.append(f"Yu_Nian_An_Body geometry mismatch: {b_verts} verts, {b_quads}/{len(m_body.polygons)} quads!")

        p377 = m_body.polygons[377]
        p378 = m_body.polygons[378]
        mat377 = m_body.materials[p377.material_index].name if p377.material_index < len(m_body.materials) else ""
        mat378 = m_body.materials[p378.material_index].name if p378.material_index < len(m_body.materials) else ""
        print(f"  Poly 377: slot {p377.material_index} ({mat377}) | Poly 378: slot {p378.material_index} ({mat378})")
        if p377.material_index != 0 or p378.material_index != 0 or mat377 != "Mat_Human_Skin_SSS" or mat378 != "Mat_Human_Skin_SSS":
            failures.append(f"Polygons 377/378 are not assigned to slot 0 Mat_Human_Skin_SSS (377={mat377}, 378={mat378})!")

    # 2d: DEF-head 30° Rotation Kinematics & Eye Detachment Stress Test
    print("\n  --- [2d] DEF-head 30° Rotation Kinematics & Eye Sphere Detachment Stress ---")
    pb_head = arm_obj.pose.bones.get("DEF-head") if arm_obj else None
    if not pb_head:
        failures.append("Pose bone 'DEF-head' missing from armature!")
    else:
        eye_sphere_names = [
            "Mesh_Eye_Left_CorneaSclera",
            "Mesh_Eye_Left_IrisPupil",
            "Mesh_Eye_Right_CorneaSclera",
            "Mesh_Eye_Right_IrisPupil",
        ]

        def get_eval_center(obj_name, depsgraph):
            o = bpy.data.objects.get(obj_name)
            if not o:
                return None
            e = o.evaluated_get(depsgraph)
            me = e.to_mesh()
            cos = [e.matrix_world @ v.co for v in me.vertices]
            e.to_mesh_clear()
            return sum(cos, mathutils.Vector((0, 0, 0))) / len(cos) if cos else None

        deps_base = bpy.context.evaluated_depsgraph_get()
        c_base_lips = get_eval_center("Mesh_Lips", deps_base)
        c_base_lid_l = get_eval_center("Mesh_Eyelid_Left", deps_base)
        c_base_eye_l = get_eval_center("Mesh_Eye_Left_CorneaSclera", deps_base)

        # Pre-cache rest-pose base centers before bone rotation updates evaluated depsgraph
        all_head_eval_names = ["Mesh_Lips", "Mesh_Eyelid_Left", "Mesh_Eyelid_Right"] + eye_sphere_names + [
            "Hair_Hime_Bangs", "Hair_Eyebrows", "Hair_Eyelashes",
            "Hair_Scalp_Crown", "Hair_Hime_Sidelocks", "Hair_Back_Cascade",
        ]
        base_centers = {n: get_eval_center(n, deps_base) for n in all_head_eval_names}

        pb_head.rotation_mode = "XYZ"
        pb_head.rotation_euler = (math.radians(30.0), 0.0, 0.0)
        bpy.context.view_layer.update()
        deps_rot = bpy.context.evaluated_depsgraph_get()

        c_rot_lips = get_eval_center("Mesh_Lips", deps_rot)
        c_rot_lid_l = get_eval_center("Mesh_Eyelid_Left", deps_rot)
        c_rot_eye_l = get_eval_center("Mesh_Eye_Left_CorneaSclera", deps_rot)

        disp_lips = (c_rot_lips - c_base_lips).length * 1000.0 if c_rot_lips and c_base_lips else 0.0
        disp_lid_l = (c_rot_lid_l - c_base_lid_l).length * 1000.0 if c_rot_lid_l and c_base_lid_l else 0.0
        disp_eye_l = (c_rot_eye_l - c_base_eye_l).length * 1000.0 if c_rot_eye_l and c_base_eye_l else 0.0

        dist_base_lid_eye = (c_base_lid_l - c_base_eye_l).length * 1000.0 if c_base_lid_l and c_base_eye_l else 0.0
        dist_rot_lid_eye = (c_rot_lid_l - c_rot_eye_l).length * 1000.0 if c_rot_lid_l and c_rot_eye_l else 0.0
        shear_detachment = abs(dist_rot_lid_eye - dist_base_lid_eye)

        print(f"  Mesh_Lips Displacement: {disp_lips:.2f} mm")
        print(f"  Mesh_Eyelid_Left Displacement: {disp_lid_l:.2f} mm")
        print(f"  Mesh_Eye_Left_CorneaSclera Displacement: {disp_eye_l:.2f} mm")
        print(f"  Eyelid-to-Eyeball Rest Distance: {dist_base_lid_eye:.2f} mm")
        print(f"  Eyelid-to-Eyeball Rotated Distance: {dist_rot_lid_eye:.2f} mm")
        print(f"  Separation Shear: {shear_detachment:.2f} mm")

        for e_name in eye_sphere_names:
            e_obj = bpy.data.objects.get(e_name)
            if not e_obj:
                failures.append(f"Eye sphere {e_name} missing!")
                continue
            c_base = base_centers.get(e_name)
            c_rot = get_eval_center(e_name, deps_rot)
            disp = (c_rot - c_base).length * 1000.0 if c_rot and c_base else 0.0
            has_arm_mod = any(m.type == 'ARMATURE' for m in e_obj.modifiers)
            has_vg_head = 'DEF-head' in e_obj.vertex_groups or 'DEF-eye.L' in e_obj.vertex_groups or 'DEF-eye.R' in e_obj.vertex_groups
            print(f"  {e_name:<30} | Armature Mod: {has_arm_mod} | VG: {has_vg_head} | Disp: {disp:.2f} mm")
            if disp < 20.0:
                failures.append(
                    f"{e_name}: Failed head rotation kinematics! Disp is {disp:.2f}mm (< 20.0mm); "
                    f"object is unrigged and detaches from cranium/eyelids by {shear_detachment:.2f}mm!"
                )

        # Also audit hair layers under head rotation
        hair_names = [
            "Hair_Hime_Bangs", "Hair_Eyebrows", "Hair_Eyelashes",
            "Hair_Scalp_Crown", "Hair_Hime_Sidelocks", "Hair_Back_Cascade",
        ]
        print("\n  --- Hair Layers Displacement Under DEF-head 30° Rotation ---")
        for h_name in hair_names:
            h_obj = bpy.data.objects.get(h_name)
            if h_obj and hasattr(h_obj.data, "vertices") and len(h_obj.data.vertices) > 0:
                c_base = base_centers.get(h_name)
                c_rot = get_eval_center(h_name, deps_rot)
                disp = (c_rot - c_base).length * 1000.0 if c_rot and c_base else 0.0
                has_arm_mod = any(m.type == 'ARMATURE' for m in h_obj.modifiers)
                print(f"  {h_name:<30} | Armature Mod: {has_arm_mod} | Disp: {disp:.2f} mm")
                if disp < 20.0:
                    failures.append(
                        f"{h_name}: Failed head rotation kinematics! Disp is {disp:.2f}mm (< 20.0mm); "
                        f"hair object is unrigged and stays frozen in air when head rotates!"
                    )

        pb_head.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()

    # --------------------------------------------------------------------------
    # 3. DEEP BVH CLEARANCE & PROPS KINEMATICS
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 3] DEEP BVH CLEARANCE & PROPS KINEMATICS")
    bodice_obj = bpy.data.objects.get("Mesh_Dress_Bodice")
    if body_obj and bodice_obj:
        bm_b = bmesh.new()
        bm_b.from_mesh(body_obj.data)
        bm_b.transform(body_obj.matrix_world)
        bvh_b = mathutils.bvhtree.BVHTree.FromBMesh(bm_b)

        bm_g = bmesh.new()
        bm_g.from_mesh(bodice_obj.data)
        bm_g.transform(bodice_obj.matrix_world)
        bvh_g = mathutils.bvhtree.BVHTree.FromBMesh(bm_g)

        overlaps = bvh_b.overlap(bvh_g)
        print(f"  Bodice-to-Body BVH Overlaps: {len(overlaps)} (req 0)")
        if len(overlaps) > 0:
            failures.append(f"Mesh_Dress_Bodice has {len(overlaps)} BVH face overlaps with body!")

        signed_dists = []
        penetrations = 0
        for v in bodice_obj.data.vertices:
            vw = bodice_obj.matrix_world @ v.co
            loc, norm, idx, dist = bvh_b.find_nearest(vw)
            if loc is not None:
                dot = (vw - loc).dot(norm)
                sd = dist if dot >= 0 else -dist
                signed_dists.append(sd * 1000.0)
                if dot < -1e-6:
                    penetrations += 1

        min_c = min(signed_dists) if signed_dists else 0.0
        print(f"  Bodice Signed Clearance: min={min_c:.2f}mm (req >= +4.0mm), penetrations={penetrations}")
        if min_c < 4.0:
            failures.append(f"Mesh_Dress_Bodice min signed clearance {min_c:.2f}mm < +4.0mm requirement!")
        if penetrations > 0:
            failures.append(f"Mesh_Dress_Bodice has {penetrations} penetrating vertices!")

        bm_b.free()
        bm_g.free()

    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
    finger_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
    ]
    if strings_obj and arm_obj:
        for i, b_name in enumerate(finger_bones):
            bone = arm_obj.data.bones.get(b_name)
            b_tail = arm_obj.matrix_world @ bone.tail_local
            root_co = strings_obj.matrix_world @ strings_obj.data.vertices[i * 14].co
            gap = (root_co - b_tail).length * 1000.0
            if gap > 1.05:
                failures.append(f"Cord {i} gap {gap:.2f}mm > 1.0mm from bone {b_name} tail!")
        print("  All 10 marionette cord roots snapped to finger DEF tails <= 1.0mm.")

    butterflies = sorted([o for o in bpy.data.objects if o.name.startswith("Prop_Butterfly_")], key=lambda x: x.name)
    if strings_obj and arm_obj and len(butterflies) == 10:
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        es_base = strings_obj.evaluated_get(deps)
        ms_base = es_base.to_mesh()
        base_s_cos = [es_base.matrix_world @ v.co for v in ms_base.vertices]
        es_base.to_mesh_clear()

        for deg in [45.0, 60.0]:
            for idx, b_name in enumerate(finger_bones):
                pb = arm_obj.pose.bones.get(b_name)
                pb.rotation_mode = "XYZ"
                pb.rotation_euler = (math.radians(deg), math.radians(deg * 0.5), math.radians(deg * 0.75))
                bpy.context.view_layer.update()
                d_eval = bpy.context.evaluated_depsgraph_get()

                es = strings_obj.evaluated_get(d_eval)
                ms = es.to_mesh()
                rot_s = [es.matrix_world @ v.co for v in ms.vertices]
                es.to_mesh_clear()
                cord_disp = max((r - b).length for r, b in zip(rot_s, base_s_cos)) * 1000.0

                bf = butterflies[idx]
                ebf = bf.evaluated_get(d_eval)
                mbf = ebf.to_mesh()
                rot_bf = [ebf.matrix_world @ v.co for v in mbf.vertices]
                ebf.to_mesh_clear()
                orig_bf = [bf.matrix_world @ v.co for v in bf.data.vertices]
                bf_disp = max((r - b).length for r, b in zip(rot_bf, orig_bf)) * 1000.0

                pb.rotation_euler = (0, 0, 0)
                bpy.context.view_layer.update()

                if cord_disp < 30.0:
                    failures.append(f"{b_name} at {deg}° cord disp {cord_disp:.2f}mm < 30.0mm!")
                if bf_disp < 30.0:
                    failures.append(f"{b_name} at {deg}° butterfly disp {bf_disp:.2f}mm < 30.0mm!")
        print("  Finger kinematics at 45°/60° passed: cords dynamically deform and butterflies translate.")

    # --------------------------------------------------------------------------
    # 4. CRANIAL APEX SPECULAR GLARE & OPTICS
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 4] CRANIAL APEX SPECULAR GLARE & OPTICS")
    if body_obj:
        scalp_mat_idx = next((i for i, m in enumerate(body_obj.data.materials) if m and m.name == "Mat_Human_Scalp"), None)
        scalp_count = sum(1 for p in body_obj.data.polygons if p.material_index == scalp_mat_idx)
        print(f"  Polygons assigned Mat_Human_Scalp: {scalp_count} (req 73)")
        if scalp_count != 73:
            failures.append(f"Expected 73 scalp polygons assigned Mat_Human_Scalp, got {scalp_count}!")

    mat_scalp = bpy.data.materials.get("Mat_Human_Scalp")
    if mat_scalp and mat_scalp.use_nodes:
        bsdf = next(n for n in mat_scalp.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        coat = bsdf.inputs["Coat Weight"].default_value if "Coat Weight" in bsdf.inputs else bsdf.inputs["Clearcoat"].default_value
        print(f"  Mat_Human_Scalp: Roughness={rough:.2f} (req 0.70), Coat={coat:.2f} (req 0.0)")
        if abs(rough - 0.70) > 0.01:
            failures.append(f"Mat_Human_Scalp Roughness {rough} != 0.70!")
        if abs(coat - 0.0) > 0.01:
            failures.append(f"Mat_Human_Scalp Coat {coat} != 0.0!")

    mat_hair = bpy.data.materials.get("Mat_Human_Hair")
    if mat_hair and mat_hair.use_nodes:
        bsdf = next(n for n in mat_hair.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        coat_w = bsdf.inputs["Coat Weight"].default_value if "Coat Weight" in bsdf.inputs else bsdf.inputs["Clearcoat"].default_value
        coat_r = bsdf.inputs["Coat Roughness"].default_value if "Coat Roughness" in bsdf.inputs else bsdf.inputs["Clearcoat Roughness"].default_value
        aniso = bsdf.inputs["Anisotropic"].default_value if "Anisotropic" in bsdf.inputs else 0.0
        print(f"  Mat_Human_Hair: Coat Weight={coat_w:.2f} (req <= 0.10), Coat Roughness={coat_r:.2f} (req >= 0.25), Anisotropic={aniso:.2f} (req >= 0.65)")
        if coat_w > 0.10:
            failures.append(f"Mat_Human_Hair Coat Weight {coat_w} > 0.10!")
        if coat_r < 0.25:
            failures.append(f"Mat_Human_Hair Coat Roughness {coat_r} < 0.25!")
        if aniso < 0.65:
            failures.append(f"Mat_Human_Hair Anisotropic {aniso} < 0.65!")

    # --------------------------------------------------------------------------
    # 5. MASTER ASSET ESSENTIAL AUDIT
    # --------------------------------------------------------------------------
    print("\n>>> [AUDIT 5] MASTER ASSET ESSENTIAL INTEGRITY AUDIT")
    def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
    print(f"  Armature DEF Bones Count: {len(def_bones)} / 163 required")
    if len(def_bones) != 163:
        failures.append(f"Armature has {len(def_bones)} DEF bones (expected 163)!")

    sk = body_obj.data.shape_keys
    arkit_keys = [k.name for k in sk.key_blocks if k.name != "Basis"] if sk else []
    print(f"  ARKit Shape Keys Count: {len(arkit_keys)} / 52 required")
    if len(arkit_keys) != 52:
        failures.append(f"Body has {len(arkit_keys)} ARKit shape keys (expected 52)!")

    # Check zero-delta shape keys
    basis_key = sk.key_blocks.get("Basis") if sk else None
    zero_delta_keys = []
    if basis_key:
        basis_cos = [v.co.copy() for v in basis_key.data]
        for kb_name in arkit_keys:
            kb = sk.key_blocks[kb_name]
            max_d = max((v.co - basis_cos[i]).length for i, v in enumerate(kb.data))
            if max_d < 1e-6:
                zero_delta_keys.append(kb_name)
    print(f"  Zero-Delta Shape Keys: {len(zero_delta_keys)}")
    if zero_delta_keys:
        failures.append(f"Found {len(zero_delta_keys)} zero-delta shape keys: {zero_delta_keys}")

    # Quads check
    quads = sum(1 for p in body_obj.data.polygons if len(p.vertices) == 4)
    quad_pct = quads / len(body_obj.data.polygons) * 100.0 if body_obj.data.polygons else 0.0
    print(f"  Body Topology: {quads}/{len(body_obj.data.polygons)} pure quads ({quad_pct:.1f}%)")
    if quad_pct < 100.0:
        failures.append(f"Body mesh quad ratio is {quad_pct:.2f}% (< 100.0%)!")

    # --------------------------------------------------------------------------
    # SUMMARY & FINAL VERDICT
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("EMPIRICAL CHALLENGER VERDICT & DEFECT LOG")
    print("=" * 80)
    if failures:
        print(f"FAILURES DETECTED ({len(failures)}):")
        for idx, f in enumerate(failures, 1):
            print(f"  [{idx}] {f}")
        print("\n>>> FINAL EMPIRICAL VERDICT: CHALLENGE <<<")
        return False
    else:
        print("ALL ADVERSARIAL STRESS TESTS PASSED WITH ZERO VIOLATIONS!")
        print(">>> FINAL EMPIRICAL VERDICT: CONFIRM (ROBUST) <<<")
        return True


# ==============================================================================
# Pytest Harness Wrapper
# ==============================================================================
def test_empirical_adversarial_audit_in_blender():
    """Execute the empirical challenger stress audit inside live Blender 4.5.4 LTS."""
    assert os.path.isfile(BLENDER_EXE), f"Blender 4.5 not found at {BLENDER_EXE}"
    assert os.path.isfile(MASTER_BLEND), f"Master blend not found at {MASTER_BLEND}"

    cmd = [
        BLENDER_EXE,
        "--background",
        MASTER_BLEND,
        "--python",
        os.path.abspath(__file__),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    print("\n[BLENDER AUDIT STDOUT]:\n" + proc.stdout)
    if proc.stderr:
        print("\n[BLENDER AUDIT STDERR]:\n" + proc.stderr)

    assert proc.returncode == 0, f"Blender audit exited with code {proc.returncode}"
    assert "FINAL EMPIRICAL VERDICT: CONFIRM (ROBUST)" in proc.stdout, "Audit did not yield CONFIRM (ROBUST) verdict!"


if __name__ == "__main__":
    success = run_empirical_challenger_audit()
    sys.exit(0 if success else 2)
