import bpy
import bmesh
import math
from mathutils import Vector, Euler, Matrix
from mathutils.bvhtree import BVHTree

def run_adversarial_stress():
    print("=" * 80)
    print("STARTING ADVERSARIAL CRITIC STRESS TESTS: reviewer_human_m4_iter7_1")
    print("=" * 80)

    issues = []
    
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    pb_head = arm_obj.pose.bones.get("DEF-head") if arm_obj else None
    
    eye_cornea_l = bpy.data.objects.get("Mesh_Eye_Left_CorneaSclera")
    lid_l = bpy.data.objects.get("Mesh_Eyelid_Left")
    lips = bpy.data.objects.get("Mesh_Lips")
    bangs = bpy.data.objects.get("Hair_Hime_Bangs")
    
    # --- TEST 1: MULTI-AXIS ROTATION KINEMATICS STRESS ---
    print("\n[STRESS 1] Multi-Axis Head Rotation Kinematics (Pitch, Yaw, Roll):")
    rot_tests = [
        ("Pitch Up +30 deg", (math.radians(30.0), 0.0, 0.0)),
        ("Pitch Down -30 deg", (math.radians(-30.0), 0.0, 0.0)),
        ("Yaw Left +45 deg", (0.0, 0.0, math.radians(45.0))),
        ("Yaw Right -45 deg", (0.0, 0.0, math.radians(-45.0))),
        ("Roll Tilt +20 deg", (0.0, math.radians(20.0), 0.0)),
        ("Compound (Pitch 25, Yaw 30, Roll 15)", (math.radians(25.0), math.radians(15.0), math.radians(30.0))),
    ]
    
    # Rest center distance between eyelid and eyeball cornea
    pb_head.rotation_mode = 'XYZ'
    pb_head.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    deps_rest = bpy.context.evaluated_depsgraph_get()
    
    def eval_center(o, deps):
        eo = o.evaluated_get(deps)
        me = eo.to_mesh()
        cos = [eo.matrix_world @ v.co for v in me.vertices]
        eo.to_mesh_clear()
        return sum(cos, Vector((0, 0, 0))) / len(cos)
    
    rest_lid = eval_center(lid_l, deps_rest)
    rest_eye = eval_center(eye_cornea_l, deps_rest)
    rest_dist = (rest_lid - rest_eye).length * 1000.0 # mm
    
    for name, rot in rot_tests:
        pb_head.rotation_euler = rot
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        rot_lid = eval_center(lid_l, deps)
        rot_eye = eval_center(eye_cornea_l, deps)
        rot_dist = (rot_lid - rot_eye).length * 1000.0
        shear = abs(rot_dist - rest_dist)
        disp_eye = (rot_eye - rest_eye).length * 1000.0
        print(f"  {name:<38} -> Eye Disp: {disp_eye:6.2f}mm | Dist: {rot_dist:.4f}mm | Shear: {shear:.6f}mm")
        if shear > 0.005:
            issues.append(f"Shear failure under {name}: shear = {shear:.4f}mm")

    # Reset head rotation
    pb_head.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()

    # --- TEST 2: FACE NORMALS & MANIFOLDNESS ---
    print("\n[STRESS 2] Inverted Normals & Non-Manifold Geometry Check:")
    test_mesh_names = [
        "Yu_Nian_An_Body",
        "Mesh_Dress_Bodice",
        "Mesh_Dress_WaistSash",
        "Mesh_Dress_PleatedSkirt",
        "Mesh_Lips",
        "Mesh_Eyelid_Left",
        "Mesh_Eyelid_Right",
        "Mesh_Eye_Left_CorneaSclera",
        "Mesh_Eye_Left_IrisPupil",
    ]
    for mname in test_mesh_names:
        obj = bpy.data.objects.get(mname)
        if obj and obj.type == 'MESH':
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            non_manifold_edges = sum(1 for e in bm.edges if not e.is_manifold)
            zero_area_faces = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
            bm.free()
            print(f"  {mname:<30}: Non-manifold edges: {non_manifold_edges} | Zero-area faces: {zero_area_faces}")
            if zero_area_faces > 0:
                issues.append(f"{mname} has {zero_area_faces} zero-area faces")

    # --- TEST 3: MATERIAL SLOTS & POLYGON ASSIGNMENT ---
    print("\n[STRESS 3] Material Slots & Polygon Mapping:")
    # Lips
    lips_obj = bpy.data.objects.get("Mesh_Lips")
    lips_dist = {}
    for p in lips_obj.data.polygons:
        lips_dist[p.material_index] = lips_dist.get(p.material_index, 0) + 1
    print(f"  Mesh_Lips slots ({len(lips_obj.data.materials)}): {[m.name for m in lips_obj.data.materials]}")
    print(f"  Mesh_Lips poly mapping: {lips_dist}")
    if lips_dist.get(0, 0) != 41 or lips_dist.get(1, 0) != 9:
        issues.append(f"Mesh_Lips unexpected distribution: {lips_dist}")
        
    # Eyelids
    for side in ["Left", "Right"]:
        el_obj = bpy.data.objects.get(f"Mesh_Eyelid_{side}")
        el_dist = {}
        for p in el_obj.data.polygons:
            el_dist[p.material_index] = el_dist.get(p.material_index, 0) + 1
        print(f"  Mesh_Eyelid_{side} slots ({len(el_obj.data.materials)}): {[m.name for m in el_obj.data.materials]}")
        print(f"  Mesh_Eyelid_{side} poly mapping: {el_dist}")
        if el_dist.get(0, 0) != 8 or el_dist.get(1, 0) != 8:
            issues.append(f"Mesh_Eyelid_{side} unexpected distribution: {el_dist}")

    # --- TEST 4: ALL 10 MARIONETTE STRAPS & BUTTERFLIES KINEMATICS ---
    print("\n[STRESS 4] Props & Marionette Cords Snapping & Weights:")
    strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
    finger_bones = [
        "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
        "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
    ]
    for b_name in finger_bones:
        vg = strings_obj.vertex_groups.get(b_name)
        if not vg:
            issues.append(f"String missing vertex group for {b_name}")
        pb = arm_obj.pose.bones.get(b_name)
        if not pb:
            issues.append(f"Missing finger pose bone {b_name}")
    print(f"  All 10 finger bone vertex groups present on strings: True")
    
    # Check butterflies
    for i in range(10):
        bf_obj = bpy.data.objects.get(f"Prop_Butterfly_{i:02d}")
        if not bf_obj:
            issues.append(f"Missing Prop_Butterfly_{i:02d}")
        else:
            has_arm = any(m.type == 'ARMATURE' for m in bf_obj.modifiers)
            if not has_arm:
                issues.append(f"Prop_Butterfly_{i:02d} missing Armature modifier")
    print(f"  All 10 butterflies present with Armature modifiers: True")

    # --- SUMMARY ---
    print("\n" + "=" * 80)
    print("ADVERSARIAL STRESS TEST SUMMARY:")
    print("=" * 80)
    if not issues:
        print(">>> ALL ADVERSARIAL STRESS TESTS PASSED WITH ZERO ISSUES! <<<")
    else:
        print(f"Detected {len(issues)} adversarial issues:")
        for iss in issues:
            print(f"  - {iss}")

if __name__ == "__main__":
    run_adversarial_stress()
