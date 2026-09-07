"""
Independent Reviewer Verification Script for Yu Nian An Master Blend.
Focusing on:
1. Master Scene Hierarchy & 7 Collections
2. PBR Materials & Fake Users (including Mat_Human_Lips)
3. Armature (163 DEF bones) & 52 ARKit FACS blendshapes with non-zero deltas
4. Bilateral Almond Eyelids (Mesh_Eyelid_Left and Mesh_Eyelid_Right) in 01_Body and rigged
5. Bodice Strap Subdivision & Clearance (intermediate quads over thoracic kyphosis, 0 BVH overlaps, clearance >= +4.0mm)
6. Camera Optics (Camera_FullBody 50mm, dist 5.5m, NDC Y in [0.05, 0.95]; Camera_Portrait_85mm 85mm)
"""

import math
import sys
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def run_independent_audit():
    print("=" * 80)
    print(">>> INDEPENDENT REVIEWER AUDIT: Yu_Nian_An_Master.blend <<<")
    print("=" * 80)

    results = {}
    failed_items = []

    # --------------------------------------------------------------------------
    # 1. Master Scene Hierarchy & Exactly 7 Collections
    # --------------------------------------------------------------------------
    print("\n--- [1] Scene Hierarchy & Collections ---")
    root_col = bpy.data.collections.get("Yu_Nian_An_Master")
    assert root_col is not None, "Root collection 'Yu_Nian_An_Master' not found!"

    expected_tiers = [
        "01_Body",
        "02_Hair",
        "03_Wardrobe",
        "04_Props",
        "05_Armature",
        "06_Lights_Camera",
    ]
    all_col_names = [c.name for c in bpy.data.collections]
    print(f"Collections in scene ({len(all_col_names)}): {all_col_names}")

    expected_all_7 = ["Yu_Nian_An_Master"] + expected_tiers
    # Check if exactly 7 collections are defined in character hierarchy
    col_count_match = len(all_col_names) == 7 and set(all_col_names) == set(expected_all_7)
    print(f"Exactly 7 expected collections present: {col_count_match}")
    if not col_count_match:
        failed_items.append(f"Collections mismatch: found {all_col_names}, expected {expected_all_7}")

    # Check child linkage under root
    child_names = [c.name for c in root_col.children]
    print(f"Child collections under Yu_Nian_An_Master: {child_names}")
    for exp in expected_tiers:
        if exp not in child_names:
            failed_items.append(f"Collection {exp} not linked under Yu_Nian_An_Master")

    # --------------------------------------------------------------------------
    # 2. PBR Materials & Fake Users (including Mat_Human_Lips)
    # --------------------------------------------------------------------------
    print("\n--- [2] PBR Materials & Fake Users ---")
    required_mats = [
        "Mat_Human_Skin_SSS",
        "Mat_Human_Eye_Outer_Cornea",
        "Mat_Human_Eye_Inner_Iris",
        "Mat_Human_Eye_Sclera",
        "Mat_Human_Hair",
        "Mat_Human_Lips",
        "Mat_Dress_WhiteSilk",
        "Mat_Dress_WaistBelt",
        "Mat_Sash_Satin",
        "Mat_Sandal_Leather",
        "Mat_Sandal_White",
        "Mat_Marionette_RedString",
        "Mat_Magic_Butterfly",
    ]
    for m_name in required_mats:
        m = bpy.data.materials.get(m_name)
        if not m:
            print(f"  MISSING MATERIAL: {m_name}")
            failed_items.append(f"Material {m_name} missing from bpy.data.materials")
        else:
            fu = m.use_fake_user
            print(f"  Material: {m_name:<30} | fake_user: {fu}")
            if not fu:
                failed_items.append(f"Material {m_name} does not have use_fake_user=True")

    # Verify Mat_Human_Lips properties
    m_lips = bpy.data.materials.get("Mat_Human_Lips")
    if m_lips and m_lips.node_tree:
        bsdf = m_lips.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            col = bsdf.inputs["Base Color"].default_value[:]
            rough = bsdf.inputs["Roughness"].default_value
            print(f"  Mat_Human_Lips Base Color: {col}, Roughness: {rough}")
            # Soft rose check
            if not (col[0] > 0.6 and col[1] < 0.5 and col[2] < 0.5):
                failed_items.append(f"Mat_Human_Lips color unexpected: {col}")

    # Check body polygon assignment to lips and scalp
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    assert body_obj is not None, "Yu_Nian_An_Body object not found!"

    lip_mat_slot = None
    hair_mat_slot = None
    for idx, slot in enumerate(body_obj.material_slots):
        if slot.material and slot.material.name == "Mat_Human_Lips":
            lip_mat_slot = idx
        if slot.material and slot.material.name == "Mat_Human_Hair":
            hair_mat_slot = idx

    print(f"  Body slot index for Mat_Human_Lips: {lip_mat_slot}")
    print(f"  Body slot index for Mat_Human_Hair: {hair_mat_slot}")

    lip_polys = [p.index for p in body_obj.data.polygons if p.material_index == lip_mat_slot] if lip_mat_slot is not None else []
    scalp_polys = [p.index for p in body_obj.data.polygons if p.material_index == hair_mat_slot] if hair_mat_slot is not None else []
    print(f"  Polygons assigned to Mat_Human_Lips: {len(lip_polys)} (indices: {lip_polys})")
    print(f"  Polygons assigned to Mat_Human_Hair (scalp dome): {len(scalp_polys)}")

    if len(lip_polys) == 0:
        failed_items.append("No polygons on Yu_Nian_An_Body assigned to Mat_Human_Lips")
    if len(scalp_polys) == 0:
        failed_items.append("No polygons on Yu_Nian_An_Body assigned to Mat_Human_Hair (scalp dome white hood)")

    # --------------------------------------------------------------------------
    # 3. Armature with 163 DEF bones and 52 FACS blendshapes
    # --------------------------------------------------------------------------
    print("\n--- [3] Armature (163 DEF bones) & 52 FACS Blendshapes ---")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify") or bpy.data.objects.get("rig")
    assert arm_obj is not None, "Armature object not found!"

    def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
    print(f"  DEF bones count: {len(def_bones)}")
    if len(def_bones) != 163:
        failed_items.append(f"DEF bones count is {len(def_bones)}, expected exactly 163")

    # Blendshapes on Yu_Nian_An_Body
    shape_keys = body_obj.data.shape_keys
    if not shape_keys:
        failed_items.append("Yu_Nian_An_Body has no shape keys")
    else:
        key_blocks = shape_keys.key_blocks
        arkit_keys = [k.name for k in key_blocks if k.name != "Basis"]
        print(f"  Total shape keys: {len(key_blocks)} (Basis + {len(arkit_keys)} FACS)")
        if len(arkit_keys) != 52:
            failed_items.append(f"FACS shape keys count is {len(arkit_keys)}, expected exactly 52")

        basis = key_blocks["Basis"]
        zero_delta_keys = []
        for k in arkit_keys:
            block = key_blocks[k]
            max_delta = max((v1.co - v0.co).length for v0, v1 in zip(basis.data, block.data))
            if max_delta < 1e-6:
                zero_delta_keys.append(k)

        print(f"  Shape keys with zero deltas: {len(zero_delta_keys)}")
        if zero_delta_keys:
            failed_items.append(f"Shape keys with zero deltas found: {zero_delta_keys}")

    # --------------------------------------------------------------------------
    # 4. Bilateral Almond Eyelids in 01_Body and Rigged
    # --------------------------------------------------------------------------
    print("\n--- [4] Bilateral Almond Eyelids ---")
    eyelid_left = bpy.data.objects.get("Mesh_Eyelid_Left")
    eyelid_right = bpy.data.objects.get("Mesh_Eyelid_Right")

    for el_name, el_obj in [("Mesh_Eyelid_Left", eyelid_left), ("Mesh_Eyelid_Right", eyelid_right)]:
        if not el_obj:
            failed_items.append(f"{el_name} not found!")
            continue

        # Check collection
        col_01 = bpy.data.collections.get("01_Body")
        in_col = el_obj.name in col_01.objects if col_01 else False
        print(f"  {el_name}: in 01_Body: {in_col}")
        if not in_col:
            failed_items.append(f"{el_name} is not in collection 01_Body")

        # Check parent
        print(f"  {el_name}: parent is {el_obj.parent.name if el_obj.parent else None}")
        if not el_obj.parent or el_obj.parent.name != "Yu_Nian_An_Body":
            failed_items.append(f"{el_name} parent is not Yu_Nian_An_Body")

        # Check armature modifier
        arm_mod = el_obj.modifiers.get("Armature")
        print(f"  {el_name}: armature modifier: {arm_mod is not None}, target: {arm_mod.object.name if arm_mod else None}")
        if not arm_mod or arm_mod.object != arm_obj:
            failed_items.append(f"{el_name} lacks valid Armature modifier pointing to rig")

        # Check vertex group DEF-head
        vg_head = el_obj.vertex_groups.get("DEF-head")
        has_vg_head = vg_head is not None
        print(f"  {el_name}: vertex group DEF-head: {has_vg_head}")
        if not has_vg_head:
            failed_items.append(f"{el_name} lacks DEF-head vertex group")
        else:
            # Check weights
            non_zero_weights = 0
            for v in el_obj.data.vertices:
                for g in v.groups:
                    if g.group == vg_head.index and g.weight > 0.0:
                        non_zero_weights += 1
            print(f"  {el_name}: vertices weighted to DEF-head: {non_zero_weights}/{len(el_obj.data.vertices)}")
            if non_zero_weights != len(el_obj.data.vertices):
                failed_items.append(f"{el_name} not 100% weighted to DEF-head")

        # Check geometry
        verts_cnt = len(el_obj.data.vertices)
        faces_cnt = len(el_obj.data.polygons)
        print(f"  {el_name}: {verts_cnt} vertices, {faces_cnt} faces")
        if verts_cnt == 0 or faces_cnt == 0:
            failed_items.append(f"{el_name} has empty geometry!")

    # --------------------------------------------------------------------------
    # 5. Bodice Strap Subdivision & Clearance
    # --------------------------------------------------------------------------
    print("\n--- [5] Bodice Strap Subdivision & Clearance ---")
    bodice_obj = bpy.data.objects.get("Mesh_Dress_Bodice")
    assert bodice_obj is not None, "Mesh_Dress_Bodice not found!"

    # Check rear strap subdivision vertices
    # Look at vertices where Y > 0.0, Z between 1.25 and 1.39
    bodice_verts_w = [bodice_obj.matrix_world @ v.co for v in bodice_obj.data.vertices]
    rear_strap_verts = [v for v in bodice_verts_w if v.y > 0.02 and 1.24 <= v.z <= 1.39]
    print(f"  Rear strap vertices (Y > 0.02, 1.24 <= Z <= 1.39): {len(rear_strap_verts)}")

    # Distinct Z levels in rear strap
    z_levels = sorted(list(set(round(v.z, 3) for v in rear_strap_verts)))
    print(f"  Distinct Z levels on rear strap: {z_levels}")
    if len(z_levels) < 3:
        failed_items.append(f"Rear shoulder strap lacks intermediate subdivision (only {len(z_levels)} Z levels: {z_levels})")

    # BVH Face Overlaps & Signed Clearance
    bm_body = bmesh.new()
    bm_body.from_object(body_obj, bpy.context.evaluated_depsgraph_get())
    bm_body.transform(body_obj.matrix_world)
    bvh_body = BVHTree.FromBMesh(bm_body)

    bm_bodice = bmesh.new()
    bm_bodice.from_object(bodice_obj, bpy.context.evaluated_depsgraph_get())
    bm_bodice.transform(bodice_obj.matrix_world)
    bvh_bodice = BVHTree.FromBMesh(bm_bodice)

    overlaps = bvh_body.overlap(bvh_bodice)
    overlap_count = len(overlaps)
    print(f"  BVH Face Overlaps between Body and Bodice: {overlap_count}")
    if overlap_count != 0:
        failed_items.append(f"Bodice has {overlap_count} BVH face overlaps with body!")

    # Signed distance from bodice vertices to body surface
    # Using find_nearest on body BVH
    min_dist_mm = 1e9
    avg_dist_mm = 0.0
    penetrations = 0

    for bv in bm_bodice.verts:
        loc, norm, face_idx, dist = bvh_body.find_nearest(bv.co)
        if loc is not None:
            # Check dot product with surface normal to confirm signed side
            diff = bv.co - loc
            sign = 1.0 if diff.dot(norm) >= 0.0 else -1.0
            signed_dist_mm = sign * dist * 1000.0
            if signed_dist_mm < 0.0:
                penetrations += 1
            if signed_dist_mm < min_dist_mm:
                min_dist_mm = signed_dist_mm
            avg_dist_mm += signed_dist_mm

    avg_dist_mm /= max(1, len(bm_bodice.verts))
    print(f"  Bodice Min Clearance: {min_dist_mm:.2f} mm (required >= +4.0 mm)")
    print(f"  Bodice Avg Clearance: {avg_dist_mm:.2f} mm")
    print(f"  Bodice Penetration Vertices: {penetrations}")

    if min_dist_mm < 4.0:
        failed_items.append(f"Bodice min clearance {min_dist_mm:.2f}mm is below +4.0mm requirement")
    if penetrations > 0:
        failed_items.append(f"Bodice has {penetrations} vertices penetrating body mesh")

    bm_body.free()
    bm_bodice.free()

    # --------------------------------------------------------------------------
    # 6. Camera Optics
    # --------------------------------------------------------------------------
    print("\n--- [6] Camera Optics & Framing ---")
    scene = bpy.context.scene

    # 6a. Camera_FullBody
    cam_full = bpy.data.objects.get("Camera_FullBody")
    assert cam_full is not None, "Camera_FullBody not found!"
    print(f"  Camera_FullBody lens: {cam_full.data.lens} mm, location: {cam_full.location[:]}")

    if abs(cam_full.data.lens - 50.0) > 0.1:
        failed_items.append(f"Camera_FullBody lens is {cam_full.data.lens}mm, expected 50.0mm")
    if abs(cam_full.location.y - (-5.5)) > 0.1:
        failed_items.append(f"Camera_FullBody distance Y is {cam_full.location.y}, expected -5.5m")

    # Project Yu Nian An vertices to NDC coordinates
    # Function to project 3D point to NDC (Normalized Device Coordinates)
    def world_to_ndc(camera, scene, point):
        co_cam = camera.matrix_world.inverted() @ point
        # Perspective projection
        focal_mm = camera.data.lens
        sensor_w = camera.data.sensor_width
        sensor_h = camera.data.sensor_height
        res_x = scene.render.resolution_x
        res_y = scene.render.resolution_y

        # Blender camera projection
        # Aspect ratio
        aspect = (res_x * scene.render.pixel_aspect_x) / (res_y * scene.render.pixel_aspect_y)
        fov_x = 2.0 * math.atan((sensor_w / 2.0) / focal_mm)
        fov_y = 2.0 * math.atan((sensor_h / 2.0) / focal_mm) if camera.data.sensor_fit == 'VERTICAL' else 2.0 * math.atan((sensor_w / 2.0 / aspect) / focal_mm)

        # In camera space: -Z is forward, +X is right, +Y is up
        z_dist = -co_cam.z
        if z_dist <= 0:
            return None
        ndc_x = 0.5 + (co_cam.x / (2.0 * z_dist * math.tan(fov_x / 2.0)))
        ndc_y = 0.5 + (co_cam.y / (2.0 * z_dist * math.tan(fov_y / 2.0)))
        return ndc_x, ndc_y

    body_world_verts = [body_obj.matrix_world @ v.co for v in body_obj.data.vertices]
    full_ndc_y = []
    for wv in body_world_verts:
        res = world_to_ndc(cam_full, scene, wv)
        if res is not None:
            full_ndc_y.append(res[1])

    min_ndc_y = min(full_ndc_y)
    max_ndc_y = max(full_ndc_y)
    print(f"  Yu Nian An projected into Camera_FullBody NDC Y: [{min_ndc_y:.4f}, {max_ndc_y:.4f}]")
    print(f"  Target bounds: [0.05, 0.95]")
    if min_ndc_y < 0.05 or max_ndc_y > 0.95:
        failed_items.append(f"Camera_FullBody NDC Y bounds [{min_ndc_y:.4f}, {max_ndc_y:.4f}] exceed [0.05, 0.95]")

    # 6b. Camera_Portrait_85mm
    cam_port = bpy.data.objects.get("Camera_Portrait_85mm")
    assert cam_port is not None, "Camera_Portrait_85mm not found!"
    print(f"  Camera_Portrait_85mm lens: {cam_port.data.lens} mm, location: {cam_port.location[:]}")

    if abs(cam_port.data.lens - 85.0) > 0.1:
        failed_items.append(f"Camera_Portrait_85mm lens is {cam_port.data.lens}mm, expected 85.0mm")

    # Project head vertices into portrait camera
    head_verts = [wv for wv in body_world_verts if wv.z >= 1.45]
    port_ndc_y = []
    for hv in head_verts:
        res = world_to_ndc(cam_port, scene, hv)
        if res is not None:
            port_ndc_y.append(res[1])

    min_head_y = min(port_ndc_y)
    max_head_y = max(port_ndc_y)
    print(f"  Head projected into Camera_Portrait_85mm NDC Y: [{min_head_y:.4f}, {max_head_y:.4f}]")
    # Head should be within frame (0.0 to 1.0) and nicely centered (e.g. within [0.20, 0.95])
    if min_head_y < 0.0 or max_head_y > 1.0:
        failed_items.append(f"Camera_Portrait_85mm crops head! NDC Y [{min_head_y:.4f}, {max_head_y:.4f}]")

    print("\n" + "=" * 80)
    if failed_items:
        print(f">>> AUDIT FAILED with {len(failed_items)} issues: <<<")
        for f in failed_items:
            print(f"  - FAIL: {f}")
        sys.exit(1)
    else:
        print(">>> ALL INDEPENDENT AUDIT CHECKS PASSED PERFECTLY! <<<")
        print("=" * 80)
        sys.exit(0)

if __name__ == "__main__":
    run_independent_audit()
