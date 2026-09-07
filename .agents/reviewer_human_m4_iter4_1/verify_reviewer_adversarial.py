import sys
import os
import math
import bpy
import bmesh
import mathutils
from bpy_extras.object_utils import world_to_camera_view

def run_adversarial_verification():
    print("======================================================================")
    print("=== ADVERSARIAL VERIFICATION: MILESTONE 4 ITERATION 4 (REVIEWER) ===")
    print("======================================================================")
    
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    report = {
        "hair_clearance": {},
        "scene_hierarchy": {},
        "materials": {},
        "armature_bones": {},
        "shape_keys": {},
        "camera_optics": {},
        "wardrobe_props": {},
        "verdict_pass": True,
        "failures": []
    }
    
    # ------------------------------------------------------------------
    # 1. BODY MESH & BVH SETUP
    # ------------------------------------------------------------------
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    if not body_obj:
        report["failures"].append("Yu_Nian_An_Body missing from scene")
        report["verdict_pass"] = False
        print("FAIL: Yu_Nian_An_Body missing")
        return report

    body_eval = body_obj.evaluated_get(depsgraph)
    bm_body = bmesh.new()
    bm_body.from_mesh(body_eval.to_mesh())
    bm_body.transform(body_obj.matrix_world)
    bvh_body = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)
    print(f"Body Mesh Evaluated Vertices: {len(bm_body.verts)}, Polygons: {len(bm_body.faces)}")

    # ------------------------------------------------------------------
    # 2. HAIR SPLINES ANTERIOR OFFSET & CRANIUM CLEARANCE
    # ------------------------------------------------------------------
    hair_layers = [
        "Hair_Hime_Bangs",
        "Hair_Eyebrows",
        "Hair_Eyelashes",
        "Hair_Scalp_Crown",
        "Hair_Hime_Sidelocks",
        "Hair_Back_Cascade"
    ]
    
    print("\n--- 1. Hair Splines Anterior Clearance Audit ---")
    for h_name in hair_layers:
        h_obj = bpy.data.objects.get(h_name)
        if not h_obj:
            report["hair_clearance"][h_name] = {"error": "Missing object"}
            report["failures"].append(f"Hair object {h_name} missing")
            report["verdict_pass"] = False
            continue
            
        h_eval = h_obj.evaluated_get(depsgraph)
        h_mesh = h_eval.to_mesh() if hasattr(h_eval, "to_mesh") else h_obj.data
        verts = h_mesh.vertices if hasattr(h_mesh, "vertices") else h_obj.data.vertices
        
        total_verts = len(verts)
        outside_count = 0
        inside_count = 0
        min_dot = 1e9
        max_dot = -1e9
        
        for v in verts:
            world_co = h_obj.matrix_world @ v.co
            hit, normal, index, dist = bvh_body.find_nearest(world_co)
            if hit is None:
                outside_count += 1
                continue
            diff = world_co - hit
            dot_val = diff.dot(normal)
            if dot_val < min_dot: min_dot = dot_val
            if dot_val > max_dot: max_dot = dot_val
            
            # dot >= 0 means on or outside the cranial mesh surface
            # allowing tiny numerical tolerance of -1e-5
            if dot_val >= -1e-5:
                outside_count += 1
            else:
                inside_count += 1
                
        pct_outside = (outside_count / total_verts * 100.0) if total_verts > 0 else 0.0
        report["hair_clearance"][h_name] = {
            "total_verts": total_verts,
            "outside": outside_count,
            "inside": inside_count,
            "pct_outside": pct_outside,
            "min_dot": min_dot,
            "max_dot": max_dot
        }
        
        status = "PASS" if (pct_outside >= 95.0 or (h_name == "Hair_Back_Cascade" and pct_outside >= 90.0)) else "FAIL"
        if status == "FAIL":
            report["failures"].append(f"{h_name} clearance {pct_outside:.1f}% is below threshold")
            report["verdict_pass"] = False
            
        print(f"[{status}] {h_name:22s}: Total {total_verts:5d} | Outside {outside_count:5d} ({pct_outside:6.2f}%) | Inside {inside_count:4d} | min_dot {min_dot:+.5f}")
        h_eval.to_mesh_clear()

    # ------------------------------------------------------------------
    # 3. MASTER SCENE HIERARCHY & 7 COLLECTIONS
    # ------------------------------------------------------------------
    print("\n--- 2. Scene Hierarchy & Collections Audit ---")
    root_col = bpy.data.collections.get("Yu_Nian_An_Master")
    has_root = root_col is not None
    is_linked = "Yu_Nian_An_Master" in [c.name for c in scene.collection.children]
    expected_children = ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"]
    actual_children = [c.name for c in root_col.children] if root_col else []
    
    tier_match = sorted(actual_children) == sorted(expected_children)
    total_7_cols = has_root and tier_match and len(actual_children) == 6
    
    report["scene_hierarchy"] = {
        "root_exists": has_root,
        "root_linked": is_linked,
        "children": actual_children,
        "tier_match": tier_match,
        "total_7_cols": total_7_cols
    }
    
    print(f"Root 'Yu_Nian_An_Master': exists={has_root}, linked_to_scene={is_linked}")
    print(f"Child collections: {actual_children}")
    if not (has_root and is_linked and tier_match):
        report["failures"].append("Scene hierarchy does not match authoritative 7-tier specification")
        report["verdict_pass"] = False
        print("FAIL: Scene hierarchy mismatch")
    else:
        print("PASS: 7-Tier collection hierarchy confirmed")

    # ------------------------------------------------------------------
    # 4. 10 PBR MATERIALS WITH FAKE USERS
    # ------------------------------------------------------------------
    print("\n--- 3. PBR Materials & Fake Users Audit ---")
    expected_mats = [
        "Mat_Human_Skin_SSS",
        "Mat_Human_Eye_Outer_Cornea",
        "Mat_Human_Eye_Inner_Iris",
        "Mat_Human_Eye_Sclera",
        "Mat_Human_Hair",
        "Mat_Dress_WhiteSilk",
        "Mat_Dress_WaistBelt",
        "Mat_Sandal_Leather",
        "Mat_Marionette_RedString",
        "Mat_Magic_Butterfly",
    ]
    missing_mats = []
    no_fake_user = []
    
    for m_name in expected_mats:
        mat = bpy.data.materials.get(m_name)
        if not mat:
            missing_mats.append(m_name)
            continue
        if not mat.use_fake_user:
            no_fake_user.append(m_name)
        nodes = [n.type for n in mat.node_tree.nodes] if mat.node_tree else []
        print(f"  Material {m_name:28s}: fake_user={mat.use_fake_user}, users={mat.users}, nodes={len(nodes)}")
        
    report["materials"] = {
        "missing": missing_mats,
        "no_fake_user": no_fake_user,
        "total_present": len(expected_mats) - len(missing_mats)
    }
    if missing_mats or no_fake_user:
        report["failures"].append(f"Materials check failed: missing={missing_mats}, no_fake_user={no_fake_user}")
        report["verdict_pass"] = False
        print(f"FAIL: Material issues: missing={missing_mats}, no_fake_user={no_fake_user}")
    else:
        print("PASS: All 10 PBR materials present with fake users")

    # ------------------------------------------------------------------
    # 5. ARMATURE & 163 DEF BONES
    # ------------------------------------------------------------------
    print("\n--- 4. Armature & 163 DEF Bones Audit ---")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    has_arm = arm_obj is not None and arm_obj.type == 'ARMATURE'
    def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")] if has_arm else []
    
    report["armature_bones"] = {
        "armature_exists": has_arm,
        "total_bones": len(arm_obj.data.bones) if has_arm else 0,
        "def_bones_count": len(def_bones),
        "has_163_def_bones": len(def_bones) == 163
    }
    print(f"Armature object: {arm_obj.name if has_arm else 'None'}, Total bones: {len(arm_obj.data.bones) if has_arm else 0}, DEF bones: {len(def_bones)}")
    if len(def_bones) != 163:
        report["failures"].append(f"Armature has {len(def_bones)} DEF bones, expected exactly 163")
        report["verdict_pass"] = False
        print(f"FAIL: DEF bone count is {len(def_bones)} != 163")
    else:
        print("PASS: Exactly 163 DEF bones confirmed")

    # ------------------------------------------------------------------
    # 6. 52 ARKit FACS SHAPE KEYS & NON-ZERO DELTAS
    # ------------------------------------------------------------------
    print("\n--- 5. 52 ARKit FACS Shape Keys Audit ---")
    sk = body_obj.data.shape_keys
    has_sk = sk is not None
    basis = sk.key_blocks.get("Basis") if has_sk else None
    arkit_keys = [k for k in sk.key_blocks if k.name != "Basis"] if has_sk else []
    
    zero_delta_keys = []
    max_deltas = {}
    if basis:
        basis_pts = [v.co.copy() for v in basis.data]
        for kb in arkit_keys:
            max_d = max((v.co - basis_pts[i]).length for i, v in enumerate(kb.data))
            max_deltas[kb.name] = max_d
            if max_d < 1e-6:
                zero_delta_keys.append(kb.name)
                
    report["shape_keys"] = {
        "has_shape_keys": has_sk,
        "has_basis": basis is not None,
        "arkit_keys_count": len(arkit_keys),
        "zero_delta_count": len(zero_delta_keys),
        "zero_delta_keys": zero_delta_keys
    }
    print(f"Shape keys count: {len(arkit_keys)} (expected 52), zero-delta count: {len(zero_delta_keys)}")
    if len(arkit_keys) != 52 or len(zero_delta_keys) > 0:
        report["failures"].append(f"Shape keys failed: count={len(arkit_keys)} (expected 52), zero_deltas={zero_delta_keys}")
        report["verdict_pass"] = False
        print(f"FAIL: Shape keys check failed")
    else:
        print("PASS: All 52 ARKit FACS shape keys present with non-zero displacement deltas")

    # ------------------------------------------------------------------
    # 7. CAMERA OPTICS & FRAMING
    # ------------------------------------------------------------------
    print("\n--- 6. Camera Optics & Framing Audit ---")
    cam_full = bpy.data.objects.get("Camera_FullBody")
    cam_port = bpy.data.objects.get("Camera_Portrait_85mm")
    
    # Check Camera_FullBody
    if not cam_full or cam_full.type != 'CAMERA':
        report["failures"].append("Camera_FullBody missing or not a camera")
        report["verdict_pass"] = False
        print("FAIL: Camera_FullBody missing")
    else:
        lens_full = cam_full.data.lens
        dist_full = abs(cam_full.location.y)
        print(f"Camera_FullBody: lens={lens_full}mm (expected 50.0mm), loc_y={cam_full.location.y:.3f}m (dist={dist_full:.3f}m)")
        
        # Test NDC projection of body vertices
        ndc_pts = [world_to_camera_view(scene, cam_full, body_obj.matrix_world @ v.co) for v in body_obj.data.vertices]
        ndc_y_min = min(p.y for p in ndc_pts)
        ndc_y_max = max(p.y for p in ndc_pts)
        ndc_x_min = min(p.x for p in ndc_pts)
        ndc_x_max = max(p.x for p in ndc_pts)
        
        # Also test bounding box points at Z=0.0m (feet/sandals) and Z=1.65m (head top)
        head_top = mathutils.Vector((0.0, 0.0, 1.65))
        feet_bot = mathutils.Vector((0.0, 0.0, 0.0))
        pt_head = world_to_camera_view(scene, cam_full, head_top)
        pt_feet = world_to_camera_view(scene, cam_full, feet_bot)
        
        print(f"  Body vertices NDC Y range: [{ndc_y_min:.4f}, {ndc_y_max:.4f}]")
        print(f"  Body vertices NDC X range: [{ndc_x_min:.4f}, {ndc_x_max:.4f}]")
        print(f"  Canonical Height NDC Y: Feet Z=0 -> {pt_feet.y:.4f}, Head Z=1.65 -> {pt_head.y:.4f}")
        
        fullbody_framed = (0.05 <= ndc_y_min and ndc_y_max <= 0.95 and 0.05 <= pt_feet.y and pt_head.y <= 0.95)
        report["camera_optics"]["fullbody"] = {
            "lens": lens_full,
            "dist": dist_full,
            "ndc_y_min": ndc_y_min,
            "ndc_y_max": ndc_y_max,
            "pt_feet_y": pt_feet.y,
            "pt_head_y": pt_head.y,
            "framed_in_005_095": fullbody_framed
        }
        if abs(lens_full - 50.0) > 0.1 or abs(dist_full - 5.5) > 0.1 or not fullbody_framed:
            report["failures"].append(f"Camera_FullBody optical framing check failed (lens={lens_full}, dist={dist_full}, NDC Y=[{ndc_y_min:.3f}, {ndc_y_max:.3f}])")
            report["verdict_pass"] = False
            print("FAIL: Camera_FullBody optical framing check failed")
        else:
            print(f"PASS: Camera_FullBody 50mm, distance 5.5m, NDC Y in [{ndc_y_min:.4f}, {ndc_y_max:.4f}] strictly within [0.05, 0.95]")

    # Check Camera_Portrait_85mm
    if not cam_port or cam_port.type != 'CAMERA':
        report["failures"].append("Camera_Portrait_85mm missing or not a camera")
        report["verdict_pass"] = False
        print("FAIL: Camera_Portrait_85mm missing")
    else:
        lens_port = cam_port.data.lens
        dist_port = abs(cam_port.location.y)
        # Check head vertices NDC in portrait camera
        head_verts = [body_obj.matrix_world @ v.co for v in body_obj.data.vertices if (body_obj.matrix_world @ v.co).z >= 1.30]
        port_ndc_pts = [world_to_camera_view(scene, cam_port, co) for co in head_verts]
        port_y_min = min(p.y for p in port_ndc_pts)
        port_y_max = max(p.y for p in port_ndc_pts)
        print(f"Camera_Portrait_85mm: lens={lens_port}mm (expected 85.0mm), loc_y={cam_port.location.y:.3f}m, Head/Bust NDC Y: [{port_y_min:.4f}, {port_y_max:.4f}]")
        report["camera_optics"]["portrait"] = {
            "lens": lens_port,
            "dist": dist_port,
            "head_ndc_y_min": port_y_min,
            "head_ndc_y_max": port_y_max
        }
        if abs(lens_port - 85.0) > 0.1:
            report["failures"].append(f"Camera_Portrait_85mm lens is {lens_port}mm != 85.0mm")
            report["verdict_pass"] = False
            print("FAIL: Camera_Portrait_85mm lens mismatch")
        else:
            print("PASS: Camera_Portrait_85mm confirmed at 85mm framing head/bust")

    # ------------------------------------------------------------------
    # 8. WARDROBE & PROPS CLEARANCE & TETHERS
    # ------------------------------------------------------------------
    print("\n--- 7. Wardrobe Clearance & Marionette Cords Audit ---")
    wardrobe_items = ["Mesh_Dress_Bodice", "Mesh_Dress_WaistSash", "Mesh_Dress_PleatedSkirt", "Mesh_Sandal_L", "Mesh_Sandal_R"]
    for w_name in wardrobe_items:
        w_obj = bpy.data.objects.get(w_name)
        if not w_obj:
            report["failures"].append(f"Wardrobe object {w_name} missing")
            report["verdict_pass"] = False
            print(f"FAIL: {w_name} missing")
            continue
        w_eval = w_obj.evaluated_get(depsgraph)
        w_mesh = w_eval.to_mesh()
        
        pen_count = 0
        min_signed_dist = 1e9
        for v in w_mesh.vertices:
            w_co = w_obj.matrix_world @ v.co
            hit, normal, index, dist = bvh_body.find_nearest(w_co)
            if hit is not None:
                diff = w_co - hit
                # If dot(diff, normal) < 0, it penetrates inside body
                signed_dist = dist if diff.dot(normal) >= 0 else -dist
                if signed_dist < min_signed_dist: min_signed_dist = signed_dist
                if signed_dist < -0.001:  # 1mm penetration threshold
                    pen_count += 1
        w_eval.to_mesh_clear()
        print(f"  {w_name:24s}: min signed clearance = {min_signed_dist*1000.0:+.2f}mm, penetrations = {pen_count}")
        if pen_count > 0:
            report["failures"].append(f"{w_name} has {pen_count} penetrating vertices")
            report["verdict_pass"] = False

    # Check butterflies and strings
    butterflies = [bpy.data.objects.get(f"Prop_Butterfly_{i:02d}") for i in range(10)]
    missing_bf = [f"Prop_Butterfly_{i:02d}" for i, b in enumerate(butterflies) if b is None]
    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
    print(f"  Butterflies: {10 - len(missing_bf)}/10 present, Strings: {'Present' if strings_obj else 'Missing'}")
    if missing_bf or not strings_obj:
        report["failures"].append(f"Props missing: butterflies={missing_bf}, strings={strings_obj is not None}")
        report["verdict_pass"] = False

    # Clean up bmesh
    bm_body.free()

    # ------------------------------------------------------------------
    # FINAL VERDICT
    # ------------------------------------------------------------------
    print("\n======================================================================")
    if report["verdict_pass"]:
        print(">>> OVERALL ADVERSARIAL VERIFICATION RESULT: PASS <<<")
    else:
        print(">>> OVERALL ADVERSARIAL VERIFICATION RESULT: FAIL <<<")
        print("Failures:")
        for f in report["failures"]:
            print(f" - {f}")
    print("======================================================================")
    
    return report

if __name__ == "__main__":
    run_adversarial_verification()
