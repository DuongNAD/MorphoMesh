"""
Independent Forensic Integrity Audit Script for Milestone 4 Iteration 7
Run inside Blender 4.5.4 LTS.
"""
import sys
import os
import math
import bpy
import bmesh
import mathutils
from mathutils.bvhtree import BVHTree

def run_forensic_audit():
    print("=" * 80)
    print("INDEPENDENT FORENSIC INTEGRITY AUDIT — BLENDER 4.5.4 LTS")
    print("Target file:", bpy.data.filepath)
    print("=" * 80)

    results = {}
    violations = []

    # 1. Check Root & Collections
    print("\n--- 1. Collection Hierarchy ---")
    root_col = bpy.data.collections.get("Yu_Nian_An_Master")
    if not root_col:
        violations.append("Missing root collection 'Yu_Nian_An_Master'")
    else:
        child_cols = [c.name for c in root_col.children]
        expected_cols = ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"]
        print("Root collection found. Children:", child_cols)
        for ec in expected_cols:
            if ec not in child_cols:
                violations.append(f"Missing collection {ec} in Yu_Nian_An_Master")

    # 2. Yu_Nian_An_Body Topology & Attributes
    print("\n--- 2. Yu_Nian_An_Body Topology & Data Integrity ---")
    body = bpy.data.objects.get("Yu_Nian_An_Body")
    if not body:
        violations.append("Missing object 'Yu_Nian_An_Body'")
    else:
        b_mesh = body.data
        n_verts = len(b_mesh.vertices)
        n_edges = len(b_mesh.edges)
        n_polys = len(b_mesh.polygons)
        quads = sum(1 for p in b_mesh.polygons if len(p.vertices) == 4)
        tris = sum(1 for p in b_mesh.polygons if len(p.vertices) == 3)
        ngons = sum(1 for p in b_mesh.polygons if len(p.vertices) > 4)
        quad_pct = (quads / n_polys * 100.0) if n_polys > 0 else 0.0

        print(f"Body Mesh: {n_verts} verts, {n_edges} edges, {n_polys} polygons")
        print(f"Quads: {quads} ({quad_pct:.2f}%), Tris: {tris}, Ngons: {ngons}")

        if quads != 2036 or n_polys != 2036 or tris != 0 or ngons != 0:
            violations.append(f"Yu_Nian_An_Body topology violation: {quads} quads, {tris} tris, {ngons} ngons (expected 2036 quads, 0 tris, 0 ngons)")
        if quad_pct != 100.0:
            violations.append(f"Yu_Nian_An_Body is not 100% pure quads: {quad_pct}%")

        # Check non-manifold or boundary edges using bmesh
        bm = bmesh.new()
        bm.from_mesh(b_mesh)
        boundary_edges = [e for e in bm.edges if e.is_boundary]
        non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
        print(f"Boundary edges: {len(boundary_edges)}, Non-manifold edges: {len(non_manifold_edges)}")
        if len(boundary_edges) > 0 or len(non_manifold_edges) > 0:
            violations.append(f"Body mesh non-manifold: {len(boundary_edges)} boundary edges, {len(non_manifold_edges)} non-manifold edges")
        bm.free()

        # Polygons 377 and 378 material assignment
        p377 = b_mesh.polygons[377]
        p378 = b_mesh.polygons[378]
        m377 = b_mesh.materials[p377.material_index].name if p377.material_index < len(b_mesh.materials) else "None"
        m378 = b_mesh.materials[p378.material_index].name if p378.material_index < len(b_mesh.materials) else "None"
        print(f"Polygon 377 material: slot {p377.material_index} ({m377})")
        print(f"Polygon 378 material: slot {p378.material_index} ({m378})")
        if p377.material_index != 0 or p378.material_index != 0 or m377 != "Mat_Human_Skin_SSS" or m378 != "Mat_Human_Skin_SSS":
            violations.append(f"Polygons 377/378 not on slot 0 Mat_Human_Skin_SSS: 377={m377}, 378={m378}")

        # Scalp polygons check
        scalp_slot = next((i for i, m in enumerate(b_mesh.materials) if m and m.name == "Mat_Human_Scalp"), None)
        scalp_polys = sum(1 for p in b_mesh.polygons if p.material_index == scalp_slot) if scalp_slot is not None else 0
        print(f"Scalp material slot: {scalp_slot}, Scalp polygons count: {scalp_polys}")
        if scalp_polys != 73:
            violations.append(f"Expected 73 scalp polygons assigned Mat_Human_Scalp, found {scalp_polys}")

    # 3. Shape Keys Analysis
    print("\n--- 3. Shape Keys Integrity Audit ---")
    if body and body.data.shape_keys:
        sk = body.data.shape_keys
        key_blocks = sk.key_blocks
        arkit_keys = [k for k in key_blocks if k.name != "Basis"]
        print(f"Total shape key blocks: {len(key_blocks)}, ARKit keys: {len(arkit_keys)} (expected 52)")
        if len(arkit_keys) != 52:
            violations.append(f"ARKit shape keys count {len(arkit_keys)} != 52")

        basis = key_blocks.get("Basis")
        if not basis:
            violations.append("Missing 'Basis' shape key block")
        else:
            basis_cos = [v.co.copy() for v in basis.data]
            zero_deltas = []
            key_stats = []
            for kb in arkit_keys:
                deltas = [(kb.data[i].co - basis_cos[i]).length for i in range(len(basis_cos))]
                max_d = max(deltas)
                avg_d = sum(deltas) / len(deltas)
                non_zero_verts = sum(1 for d in deltas if d > 1e-6)
                key_stats.append((kb.name, max_d * 1000.0, avg_d * 1000.0, non_zero_verts))
                if max_d < 1e-6:
                    zero_deltas.append(kb.name)

            print(f"Non-zero delta verification: {len(arkit_keys) - len(zero_deltas)} / {len(arkit_keys)} active")
            print("Sample shape keys deltas (max mm, avg mm, affected verts):")
            for ks in key_stats[:8]:
                print(f"  {ks[0]:<25}: max={ks[1]:.2f}mm, avg={ks[2]:.4f}mm, affected={ks[3]}")
            if zero_deltas:
                violations.append(f"Found {len(zero_deltas)} zero-delta ARKit shape keys: {zero_deltas}")
    else:
        violations.append("Yu_Nian_An_Body has no shape keys!")

    # 4. Mesh_Lips Deep Inspection
    print("\n--- 4. Mesh_Lips Forensic Inspection ---")
    lips = bpy.data.objects.get("Mesh_Lips")
    if not lips:
        violations.append("Missing object 'Mesh_Lips'")
    else:
        l_mesh = lips.data
        n_lverts = len(l_mesh.vertices)
        n_lpolys = len(l_mesh.polygons)
        l_quads = sum(1 for p in l_mesh.polygons if len(p.vertices) == 4)
        l_tris = sum(1 for p in l_mesh.polygons if len(p.vertices) == 3)
        l_ngons = sum(1 for p in l_mesh.polygons if len(p.vertices) > 4)
        print(f"Mesh_Lips: {n_lverts} vertices, {n_lpolys} polygons")
        print(f"Quads: {l_quads} ({l_quads/n_lpolys*100.0:.1f}%), Tris: {l_tris}, Ngons: {l_ngons}")
        if n_lverts != 66:
            violations.append(f"Mesh_Lips vertex count {n_lverts} != 66")
        if n_lpolys != 50 or l_quads != 50:
            violations.append(f"Mesh_Lips polygon count {l_quads} quads, {n_lpolys} total != 50 pure quads")
        if l_tris != 0 or l_ngons != 0:
            violations.append(f"Mesh_Lips contains non-quads: {l_tris} tris, {l_ngons} ngons")

        # Material distribution
        mat_dist = {}
        for p in l_mesh.polygons:
            mat_dist[p.material_index] = mat_dist.get(p.material_index, 0) + 1
        mat_names = [m.name for m in l_mesh.materials] if hasattr(l_mesh, "materials") else []
        print(f"Mesh_Lips materials: {mat_names}")
        print(f"Mesh_Lips polygon material distribution: {mat_dist}")
        if mat_names != ["Mat_Human_Lips", "Mat_Human_Oral_Slit"]:
            violations.append(f"Mesh_Lips material slots unexpected: {mat_names}")
        if mat_dist.get(0, 0) != 41:
            violations.append(f"Mesh_Lips slot 0 (Mat_Human_Lips) count {mat_dist.get(0, 0)} != 41")
        if mat_dist.get(1, 0) != 9:
            violations.append(f"Mesh_Lips slot 1 (Mat_Human_Oral_Slit) count {mat_dist.get(1, 0)} != 9")

        # Surface clearance via BVH
        deps = bpy.context.evaluated_depsgraph_get()
        bvh_body = BVHTree.FromObject(body, deps)
        signed_dists = []
        penetrations = 0
        for v in l_mesh.vertices:
            vw = lips.matrix_world @ v.co
            loc, norm, _, dist = bvh_body.find_nearest(vw)
            if loc is not None:
                dot = (vw - loc).dot(norm)
                sd = dist if dot >= 0 else -dist
                signed_dists.append(sd * 1000.0)
                if dot < -0.0001:
                    penetrations += 1

        min_c = min(signed_dists)
        avg_c = sum(signed_dists) / len(signed_dists)
        max_c = max(signed_dists)
        print(f"Mesh_Lips Surface Clearance: min={min_c:+.2f}mm, avg={avg_c:+.2f}mm, max={max_c:+.2f}mm")
        print(f"Penetrations (< -0.1mm): {penetrations} / {len(signed_dists)}")
        if penetrations > 0:
            violations.append(f"Mesh_Lips has {penetrations} vertices penetrating inside cranium (min={min_c:.2f}mm)")
        if min_c < 0.1:
            violations.append(f"Mesh_Lips min clearance {min_c:.2f}mm < +0.1mm")
        if max_c > 2.0:
            violations.append(f"Mesh_Lips max clearance {max_c:.2f}mm > +2.0mm (floating too far)")

    # 5. Eyelids Material Distribution
    print("\n--- 5. Eyelids Material Slots & Topology ---")
    for el_name in ["Mesh_Eyelid_Left", "Mesh_Eyelid_Right"]:
        el = bpy.data.objects.get(el_name)
        if not el:
            violations.append(f"Missing {el_name}")
            continue
        el_dist = {}
        for p in el.data.polygons:
            el_dist[p.material_index] = el_dist.get(p.material_index, 0) + 1
        mats = [m.name for m in el.data.materials]
        print(f"{el_name}: materials={mats}, poly dist={el_dist}, verts={len(el.data.vertices)}, polys={len(el.data.polygons)}")
        if el_dist.get(0, 0) != 8 or el_dist.get(1, 0) != 8:
            violations.append(f"{el_name} material distribution {el_dist} != {{0: 8, 1: 8}}")

    # 6. Armature Modifiers & Head Rotation Kinematics
    print("\n--- 6. Armature Modifiers & Kinematics Deformation ---")
    arm = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    if not arm:
        violations.append("Missing Armature_Yu_Nian_An_Rigify")
    else:
        def_bones = [b.name for b in arm.data.bones if b.name.startswith("DEF-")]
        print(f"DEF Bones Count: {len(def_bones)} (expected 163)")
        if len(def_bones) != 163:
            violations.append(f"Armature DEF bones count {len(def_bones)} != 163")

        all_head_bound = [
            "Mesh_Lips", "Mesh_Eyelid_Left", "Mesh_Eyelid_Right",
            "Mesh_Eye_Left_CorneaSclera", "Mesh_Eye_Left_IrisPupil",
            "Mesh_Eye_Right_CorneaSclera", "Mesh_Eye_Right_IrisPupil",
            "Hair_Hime_Bangs", "Hair_Eyebrows", "Hair_Eyelashes",
            "Hair_Scalp_Crown", "Hair_Hime_Sidelocks", "Hair_Back_Cascade",
        ]

        print("Checking Armature Modifiers and DEF-head vertex groups:")
        for name in all_head_bound:
            o = bpy.data.objects.get(name)
            if not o:
                violations.append(f"Object {name} missing for armature binding check")
                continue
            has_arm_mod = any(m.type == 'ARMATURE' and m.object == arm for m in o.modifiers)
            has_vg_head = 'DEF-head' in o.vertex_groups
            if not has_arm_mod:
                violations.append(f"{name} is missing Armature modifier targeting {arm.name}")
            if not has_vg_head:
                violations.append(f"{name} is missing 'DEF-head' vertex group")
            else:
                vg = o.vertex_groups['DEF-head']
                weights = [vg.weight(vi) for vi in range(len(o.data.vertices))]
                non_one = sum(1 for w in weights if abs(w - 1.0) > 1e-4)
                if non_one > 0:
                    violations.append(f"{name} has {non_one} vertices with DEF-head weight != 1.0")

        # Kinematic rotation test
        pb_head = arm.pose.bones.get("DEF-head")
        if pb_head:
            def get_eval_center(obj_name, deps):
                o = bpy.data.objects.get(obj_name)
                if not o: return None
                e = o.evaluated_get(deps)
                me = e.to_mesh()
                cos = [e.matrix_world @ v.co for v in me.vertices]
                e.to_mesh_clear()
                return sum(cos, mathutils.Vector((0, 0, 0))) / len(cos) if cos else None

            # Rest state
            pb_head.rotation_mode = 'XYZ'
            pb_head.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            deps_rest = bpy.context.evaluated_depsgraph_get()
            base_centers = {n: get_eval_center(n, deps_rest) for n in all_head_bound}

            # Rotate 30 degrees around X
            pb_head.rotation_euler = (math.radians(30.0), 0.0, 0.0)
            bpy.context.view_layer.update()
            deps_rot = bpy.context.evaluated_depsgraph_get()

            print("Kinematic displacement under 30° DEF-head rotation:")
            for n in all_head_bound:
                c_base = base_centers[n]
                c_rot = get_eval_center(n, deps_rot)
                disp = (c_rot - c_base).length * 1000.0 if c_rot and c_base else 0.0
                print(f"  {n:<32}: {disp:6.2f} mm")
                if disp < 20.0:
                    violations.append(f"{n} failed kinematics: displacement {disp:.2f}mm < 20.0mm (unbound/frozen)")

            # Check shear between eyelid and cornea
            c_lid_base = base_centers['Mesh_Eyelid_Left']
            c_eye_base = base_centers['Mesh_Eye_Left_CorneaSclera']
            c_lid_rot = get_eval_center('Mesh_Eyelid_Left', deps_rot)
            c_eye_rot = get_eval_center('Mesh_Eye_Left_CorneaSclera', deps_rot)
            dist_base = (c_lid_base - c_eye_base).length * 1000.0
            dist_rot = (c_lid_rot - c_eye_rot).length * 1000.0
            shear = abs(dist_rot - dist_base)
            print(f"Eyelid-to-Eyeball distance rest: {dist_base:.2f}mm, rotated: {dist_rot:.2f}mm, shear: {shear:.4f}mm")
            if shear > 0.01:
                violations.append(f"Separation shear between eyelid and eyeball {shear:.4f}mm > 0.01mm")

            # Reset pose
            pb_head.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()

    # 7. Wardrobe Clearance & Props
    print("\n--- 7. Wardrobe Clearance & Marionette Kinematics ---")
    bodice = bpy.data.objects.get("Mesh_Dress_Bodice")
    if body and bodice:
        bvh_body = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
        signed_dists = []
        pens = 0
        for v in bodice.data.vertices:
            vw = bodice.matrix_world @ v.co
            loc, norm, _, dist = bvh_body.find_nearest(vw)
            if loc is not None:
                dot = (vw - loc).dot(norm)
                sd = dist if dot >= 0 else -dist
                signed_dists.append(sd * 1000.0)
                if dot < -1e-6:
                    pens += 1
        min_bodice = min(signed_dists)
        print(f"Bodice signed clearance: min={min_bodice:.2f}mm, penetrations={pens}")
        if min_bodice < 4.0:
            violations.append(f"Bodice min clearance {min_bodice:.2f}mm < +4.0mm")
        if pens > 0:
            violations.append(f"Bodice has {pens} penetrating vertices")

    # Marionette Cords
    strings = bpy.data.objects.get("Prop_Marionette_Strings")
    finger_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
    ]
    if strings and arm:
        for i, b_name in enumerate(finger_bones):
            bone = arm.data.bones.get(b_name)
            b_tail = arm.matrix_world @ bone.tail_local
            root_co = strings.matrix_world @ strings.data.vertices[i * 14].co
            gap = (root_co - b_tail).length * 1000.0
            if gap > 1.05:
                violations.append(f"Cord {i} gap {gap:.2f}mm > 1.0mm from bone {b_name} tail")
        print("All 10 marionette cord roots verified against finger bone tails.")

    # 8. Summary & Verdict
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    if violations:
        print(f"VIOLATIONS FOUND ({len(violations)}):")
        for v in violations:
            print("  [FAIL]", v)
        print("\n>>> VERDICT: INTEGRITY VIOLATION <<<")
        return False
    else:
        print("ALL FORENSIC CHECKS PASSED EMPIRICALLY.")
        print(">>> VERDICT: CLEAN <<<")
        return True

if __name__ == "__main__":
    ok = run_forensic_audit()
    sys.exit(0 if ok else 1)
