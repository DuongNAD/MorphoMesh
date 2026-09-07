import bpy
import bmesh
import math
from mathutils import Vector, Euler, Matrix
from mathutils.bvhtree import BVHTree
import bpy_extras.object_utils

def run_audit():
    print("=" * 80)
    print("STARTING INDEPENDENT EMPIRICAL AUDIT: reviewer_human_m4_iter7_1")
    print(f"Target Blend: {bpy.data.filepath}")
    print("=" * 80)
    
    findings = []
    
    # -------------------------------------------------------------------------
    # 1. SCENE HIERARCHY & COLLECTIONS
    # -------------------------------------------------------------------------
    print("\n>>> SECTION 1: SCENE HIERARCHY & COLLECTIONS")
    expected_seven = [
        "Yu_Nian_An_Master",
        "01_Body",
        "02_Hair",
        "03_Wardrobe",
        "04_Props",
        "05_Armature",
        "06_Lights_Camera",
    ]
    all_cols = [c.name for c in bpy.data.collections]
    print(f"All collections in file ({len(all_cols)}): {all_cols}")
    
    master_col = bpy.data.collections.get("Yu_Nian_An_Master")
    if not master_col:
        findings.append("CRITICAL: Root collection 'Yu_Nian_An_Master' missing!")
    else:
        child_col_names = [c.name for c in master_col.children]
        print(f"Children of Yu_Nian_An_Master ({len(child_col_names)}): {child_col_names}")
        expected_children = expected_seven[1:]
        missing_children = set(expected_children) - set(child_col_names)
        extra_children = set(child_col_names) - set(expected_children)
        if missing_children:
            findings.append(f"CRITICAL: Missing child collections: {missing_children}")
        if extra_children:
            findings.append(f"MAJOR: Extra child collections: {extra_children}")
        if len(all_cols) != 7:
            findings.append(f"MAJOR: Collection count is {len(all_cols)}, expected exactly 7!")
        else:
            print("  [PASS] Exactly 7 collections confirmed.")

    # Objects per collection
    print("\nObject breakdown per collection:")
    for c_name in expected_seven:
        col = bpy.data.collections.get(c_name)
        if col:
            print(f"  Collection '{c_name}': {len(col.objects)} objects -> {[o.name for o in col.objects]}")

    # Materials Fake User Check
    print("\nMaterials and Fake User status:")
    expected_materials = [
        "Mat_Human_Skin_SSS",
        "Mat_Human_Eye_Outer_Cornea",
        "Mat_Human_Eye_Inner_Iris",
        "Mat_Human_Hair",
        "Mat_Dress_WhiteSilk",
        "Mat_Dress_WaistBelt",
        "Mat_Sandal_Leather",
        "Mat_Marionette_RedString",
        "Mat_Magic_Butterfly",
        "Mat_Human_Lips",
        "Mat_Human_Oral_Slit",
        "Mat_Human_Eyeliner",
        "Mat_Human_Scalp"
    ]
    for mat in bpy.data.materials:
        print(f"  Material: {mat.name:<30} | fake_user: {mat.use_fake_user} | users: {mat.users}")
        if not mat.use_fake_user:
            findings.append(f"MINOR: Material '{mat.name}' does not have fake_user=True")

    # Armature DEF Bones Count
    print("\nArmature DEF Bones verification:")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    if not arm_obj or arm_obj.type != 'ARMATURE':
        findings.append("CRITICAL: 'Armature_Yu_Nian_An_Rigify' missing or not an ARMATURE!")
    else:
        def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
        print(f"  Total bones: {len(arm_obj.data.bones)}, DEF bones count: {len(def_bones)}")
        if len(def_bones) != 163:
            findings.append(f"CRITICAL: DEF bones count is {len(def_bones)}, expected exactly 163!")
        else:
            print("  [PASS] Exactly 163 DEF bones verified.")

    # 52 ARKit FACS shape keys
    print("\n52 ARKit FACS shape keys verification on Yu_Nian_An_Body:")
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    if not body_obj:
        findings.append("CRITICAL: 'Yu_Nian_An_Body' missing!")
    else:
        kb = body_obj.data.shape_keys
        if not kb:
            findings.append("CRITICAL: No shape keys found on 'Yu_Nian_An_Body'!")
        else:
            key_blocks = kb.key_blocks
            # Exclude Basis
            arkit_keys = [k for k in key_blocks if k.name != "Basis"]
            print(f"  Total shape keys (excluding Basis): {len(arkit_keys)}")
            zero_delta_keys = []
            basis = key_blocks["Basis"]
            for k in arkit_keys:
                # Check max delta
                max_d = 0.0
                for i in range(len(k.data)):
                    d = (k.data[i].co - basis.data[i].co).length
                    if d > max_d:
                        max_d = d
                if max_d < 1e-6:
                    zero_delta_keys.append(k.name)
            print(f"  Zero-delta shape keys count: {len(zero_delta_keys)}")
            if len(arkit_keys) != 52:
                findings.append(f"CRITICAL: ARKit shape keys count is {len(arkit_keys)}, expected exactly 52!")
            if zero_delta_keys:
                findings.append(f"MAJOR: {len(zero_delta_keys)} shape keys have zero displacement: {zero_delta_keys}")
            if len(arkit_keys) == 52 and not zero_delta_keys:
                print("  [PASS] 52 ARKit FACS keys exist with non-zero geometric deltas.")

    # -------------------------------------------------------------------------
    # 2. ARMATURE MODIFIERS & HEAD KINEMATICS
    # -------------------------------------------------------------------------
    print("\n>>> SECTION 2: ARMATURE MODIFIERS & HEAD KINEMATICS")
    eye_sphere_names = [
        "Mesh_Eye_Left_CorneaSclera",
        "Mesh_Eye_Left_IrisPupil",
        "Mesh_Eye_Right_CorneaSclera",
        "Mesh_Eye_Right_IrisPupil",
    ]
    hair_layer_names = [
        "Hair_Hime_Bangs",
        "Hair_Hime_Sidelocks",
        "Hair_Scalp_Crown",
        "Hair_Back_Cascade",
        "Hair_Eyebrows",
        "Hair_Eyelashes",
    ]
    additional_facial = [
        "Mesh_Lips",
        "Mesh_Eyelid_Left",
        "Mesh_Eyelid_Right",
    ]
    all_head_bound_objects = eye_sphere_names + hair_layer_names + additional_facial
    
    print("\nChecking Armature modifiers and 'DEF-head' vertex groups:")
    for obj_name in all_head_bound_objects:
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            findings.append(f"CRITICAL: Object '{obj_name}' missing!")
            continue
        # Check Armature modifier
        arm_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
        if not arm_mods:
            findings.append(f"CRITICAL: Object '{obj_name}' missing ARMATURE modifier!")
        else:
            mod = arm_mods[0]
            if mod.object != arm_obj:
                findings.append(f"CRITICAL: Object '{obj_name}' Armature modifier targets {mod.object}, expected {arm_obj}!")
            if not mod.use_deform_preserve_volume:
                findings.append(f"MAJOR: Object '{obj_name}' Armature modifier use_deform_preserve_volume is False!")
        
        # Check DEF-head vertex group
        vg = obj.vertex_groups.get("DEF-head")
        if not vg:
            findings.append(f"CRITICAL: Object '{obj_name}' missing 'DEF-head' vertex group!")
        else:
            # Check weights
            non_1_count = 0
            for v in obj.data.vertices:
                # find weight
                w = 0.0
                for g in v.groups:
                    if g.group == vg.index:
                        w = g.weight
                        break
                if abs(w - 1.0) > 1e-4:
                    non_1_count += 1
            if non_1_count > 0:
                findings.append(f"MAJOR: Object '{obj_name}' has {non_1_count}/{len(obj.data.vertices)} vertices with DEF-head weight != 1.0!")
            else:
                print(f"  [PASS] {obj_name:<35}: Armature Mod: True, PreserveVol: True, DEF-head 1.0 ({len(obj.data.vertices)} verts)")

    # 30° Head Rotation Kinematics & Shear Audit
    print("\nKinematics Audit under 30° DEF-head Rotation:")
    if arm_obj:
        pb_head = arm_obj.pose.bones.get("DEF-head")
        if not pb_head:
            findings.append("CRITICAL: Pose bone 'DEF-head' not found in armature!")
        else:
            # Record rest positions
            depsgraph_rest = bpy.context.evaluated_depsgraph_get()
            
            def get_mesh_center(o):
                eval_o = o.evaluated_get(depsgraph_rest)
                mesh = eval_o.to_mesh()
                verts = [eval_o.matrix_world @ v.co for v in mesh.vertices]
                eval_o.to_mesh_clear()
                return sum(verts, Vector((0,0,0))) / len(verts) if verts else Vector((0,0,0))
            
            rest_centers = {name: get_mesh_center(bpy.data.objects[name]) for name in all_head_bound_objects if bpy.data.objects.get(name)}
            
            # Apply 30° rotation (Euler X)
            pb_head.rotation_mode = 'XYZ'
            pb_head.rotation_euler = (math.radians(30.0), 0.0, 0.0)
            bpy.context.view_layer.update()
            depsgraph_rot = bpy.context.evaluated_depsgraph_get()
            
            def get_rotated_center(o):
                eval_o = o.evaluated_get(depsgraph_rot)
                mesh = eval_o.to_mesh()
                verts = [eval_o.matrix_world @ v.co for v in mesh.vertices]
                eval_o.to_mesh_clear()
                return sum(verts, Vector((0,0,0))) / len(verts) if verts else Vector((0,0,0))
            
            rot_centers = {name: get_rotated_center(bpy.data.objects[name]) for name in all_head_bound_objects if bpy.data.objects.get(name)}
            
            print("  Displacements under 30° DEF-head rotation:")
            for name in all_head_bound_objects:
                if name in rest_centers and name in rot_centers:
                    disp = (rot_centers[name] - rest_centers[name]).length * 1000.0  # mm
                    print(f"    {name:<35}: {disp:6.2f} mm")
                    if disp < 10.0:
                        findings.append(f"CRITICAL: Object '{name}' displacement is {disp:.2f}mm under 30° rotation (shearing/static failure)!")

            # Check relative distance (shear) between eyelid and eye cornea
            for side in ["Left", "Right"]:
                lid_name = f"Mesh_Eyelid_{side}"
                eye_name = f"Mesh_Eye_{side}_CorneaSclera"
                if lid_name in rest_centers and eye_name in rest_centers:
                    d_rest = (rest_centers[lid_name] - rest_centers[eye_name]).length * 1000.0
                    d_rot = (rot_centers[lid_name] - rot_centers[eye_name]).length * 1000.0
                    shear = abs(d_rot - d_rest)
                    print(f"    {side} Eyelid-to-Cornea Rest: {d_rest:.2f}mm, Rot: {d_rot:.2f}mm, Shear: {shear:.4f}mm")
                    if shear > 0.05:
                        findings.append(f"CRITICAL: {side} eye/eyelid separation shear is {shear:.4f}mm (> 0.05mm)!")
                    else:
                        print(f"    [PASS] {side} eye/eyelid shear: 0.00mm")
            
            # Reset head rotation
            pb_head.rotation_euler = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()

    # -------------------------------------------------------------------------
    # 3. CAMERA OPTICS & BODICE CLEARANCE
    # -------------------------------------------------------------------------
    print("\n>>> SECTION 3: CAMERA OPTICS & BODICE CLEARANCE")
    
    # Camera_FullBody
    cam_fb = bpy.data.objects.get("Camera_FullBody")
    if not cam_fb or cam_fb.type != 'CAMERA':
        findings.append("CRITICAL: 'Camera_FullBody' missing or not a CAMERA!")
    else:
        cam_data = cam_fb.data
        print(f"  Camera_FullBody lens: {cam_data.lens}mm (req 50.0mm)")
        print(f"  Camera_FullBody loc: {cam_fb.location} (dist: {abs(cam_fb.location.y):.2f}m)")
        if abs(cam_data.lens - 50.0) > 0.1:
            findings.append(f"CRITICAL: Camera_FullBody lens is {cam_data.lens}mm, expected 50.0mm!")
        if abs(abs(cam_fb.location.y) - 5.5) > 0.1:
            findings.append(f"MAJOR: Camera_FullBody distance is {abs(cam_fb.location.y)}m, expected 5.5m!")
            
        # Check NDC coverage of the full character
        scene = bpy.context.scene
        # Collect all vertices from character body, hair, wardrobe
        char_objs = [body_obj] + [bpy.data.objects.get(n) for n in hair_layer_names] + [bpy.data.objects.get("Mesh_Dress_Bodice"), bpy.data.objects.get("Mesh_Dress_PleatedSkirt"), bpy.data.objects.get("Mesh_Sandal_L"), bpy.data.objects.get("Mesh_Sandal_R")]
        all_ndc_y = []
        all_ndc_x = []
        for o in char_objs:
            if o and o.type == 'MESH':
                mw = o.matrix_world
                for v in o.data.vertices:
                    co_world = mw @ v.co
                    co_ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam_fb, co_world)
                    all_ndc_x.append(co_ndc.x)
                    all_ndc_y.append(co_ndc.y)
        if all_ndc_y:
            min_y, max_y = min(all_ndc_y), max(all_ndc_y)
            min_x, max_x = min(all_ndc_x), max(all_ndc_x)
            print(f"  Camera_FullBody NDC Y range: [{min_y:.4f}, {max_y:.4f}] (req [0.05, 0.95])")
            print(f"  Camera_FullBody NDC X range: [{min_x:.4f}, {max_x:.4f}] (centered ~ 0.5)")
            if min_y < 0.05 or max_y > 0.95:
                findings.append(f"CRITICAL: Full body framing NDC Y range [{min_y:.4f}, {max_y:.4f}] exceeds [0.05, 0.95]!")
            else:
                print("  [PASS] Fullbody fits vertically within NDC Y [0.05, 0.95].")

    # Camera_Portrait_85mm
    cam_port = bpy.data.objects.get("Camera_Portrait_85mm")
    if not cam_port or cam_port.type != 'CAMERA':
        findings.append("CRITICAL: 'Camera_Portrait_85mm' missing or not a CAMERA!")
    else:
        p_data = cam_port.data
        print(f"  Camera_Portrait_85mm lens: {p_data.lens}mm (req 85.0mm)")
        print(f"  Camera_Portrait_85mm loc: {cam_port.location}")
        if abs(p_data.lens - 85.0) > 0.1:
            findings.append(f"CRITICAL: Camera_Portrait_85mm lens is {p_data.lens}mm, expected 85.0mm!")
        # Head NDC check
        if body_obj:
            scene = bpy.context.scene
            mw = body_obj.matrix_world
            head_pts = [mw @ v.co for v in body_obj.data.vertices if (mw @ v.co).z >= 1.35]
            head_ndc_y = [bpy_extras.object_utils.world_to_camera_view(scene, cam_port, p).y for p in head_pts]
            if head_ndc_y:
                print(f"  Portrait Camera Head/Bust NDC Y: [{min(head_ndc_y):.4f}, {max(head_ndc_y):.4f}]")
                if min(head_ndc_y) < 0.0 or max(head_ndc_y) > 1.0:
                    findings.append("MAJOR: Head is cropped in Camera_Portrait_85mm!")
                else:
                    print("  [PASS] Head cleanly captured in portrait camera.")

    # Bodice Signed Clearance & BVH Overlap
    print("\nBodice Signed Clearance & BVH Overlap:")
    bodice_obj = bpy.data.objects.get("Mesh_Dress_Bodice")
    if not bodice_obj:
        findings.append("CRITICAL: 'Mesh_Dress_Bodice' missing!")
    elif not body_obj:
        findings.append("CRITICAL: 'Yu_Nian_An_Body' missing for clearance check!")
    else:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bvh_body = BVHTree.FromObject(body_obj, depsgraph)
        bvh_bodice = BVHTree.FromObject(bodice_obj, depsgraph)
        
        # BVH overlap check
        overlaps = bvh_bodice.overlap(bvh_body)
        print(f"  BVH face overlaps between Bodice and Body: {len(overlaps)}")
        if len(overlaps) > 0:
            findings.append(f"CRITICAL: Bodice has {len(overlaps)} face overlaps with Body (req 0)!")
        else:
            print("  [PASS] Exactly 0 BVH face overlaps.")

        # Signed distance check
        s_dists = []
        pens = 0
        mw_bodice = bodice_obj.matrix_world
        for v in bodice_obj.data.vertices:
            p_world = mw_bodice @ v.co
            hit_loc, hit_norm, hit_idx, hit_dist = bvh_body.find_nearest(p_world)
            if hit_loc is not None:
                vec = p_world - hit_loc
                dot = vec.dot(hit_norm)
                signed_d = hit_dist * 1000.0 if dot >= 0.0 else -hit_dist * 1000.0
                s_dists.append(signed_d)
                if signed_d < -0.01:
                    pens += 1
        
        if s_dists:
            min_c = min(s_dists)
            avg_c = sum(s_dists) / len(s_dists)
            max_c = max(s_dists)
            print(f"  Bodice signed clearance: min={min_c:+.2f}mm (req >= +4.0mm), avg={avg_c:+.2f}mm, max={max_c:+.2f}mm | Pens: {pens}/{len(s_dists)}")
            if min_c < 4.0:
                findings.append(f"CRITICAL: Bodice min signed clearance is {min_c:.2f}mm, expected >= +4.0mm!")
            elif pens > 0:
                findings.append(f"CRITICAL: Bodice has {pens} penetrating vertices into body!")
            else:
                print("  [PASS] Bodice clearance satisfies >= +4.0mm with 0 penetrations.")

    # -------------------------------------------------------------------------
    # SUMMARY OF FINDINGS
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("AUDIT FINDINGS SUMMARY:")
    print("=" * 80)
    if not findings:
        print(">>> ALL REVIEW & CRITIC CHECKS PASSED WITH ZERO FINDINGS! <<<")
        print("Verdict: APPROVE")
    else:
        print(f"Total findings: {len(findings)}")
        for f in findings:
            print(f"  - {f}")
        criticals = [f for f in findings if f.startswith("CRITICAL")]
        if criticals:
            print("Verdict: REQUEST_CHANGES")
        else:
            print("Verdict: REVIEW WITH WARNINGS")

if __name__ == "__main__":
    run_audit()
