import sys
import os

try:
    import bpy
except ImportError:
    bpy = None

if bpy is None:
    try:
        import pytest
        pytest.skip("bpy module not available (must run inside Blender)", allow_module_level=True)
    except Exception:
        sys.exit(0)

def run_inspection():
    print("=== DEEP LIVE BLENDER INSPECTION OF Yu_Nian_An_Master.blend ===")
    results = {}
    
    # 1. COLLECTIONS
    all_col_names = [c.name for c in bpy.data.collections]
    print(f"Total Collections in bpy.data: {len(all_col_names)}: {all_col_names}")
    
    root_col = bpy.data.collections.get("Yu_Nian_An_Master")
    results["root_col_exists"] = root_col is not None
    
    expected_tiers = ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"]
    child_col_names = [c.name for c in root_col.children] if root_col else []
    print(f"Child collections under Yu_Nian_An_Master: {child_col_names}")
    results["all_tiers_present"] = set(expected_tiers).issubset(set(child_col_names))
    results["exact_tiers_match"] = sorted(child_col_names) == sorted(expected_tiers)
    
    # Check scene collection links
    scene_children = [c.name for c in bpy.context.scene.collection.children]
    print(f"Collections directly linked to Scene Collection: {scene_children}")
    results["root_linked_to_scene"] = "Yu_Nian_An_Master" in scene_children
    
    # Check objects per collection
    objects_per_tier = {}
    for t in expected_tiers:
        col = bpy.data.collections.get(t)
        objects_per_tier[t] = [o.name for o in col.objects] if col else []
        print(f"[{t}] Objects ({len(objects_per_tier[t])}): {objects_per_tier[t]}")
        
    # Check orphaned objects
    all_objs = list(bpy.data.objects)
    print(f"Total Objects in scene: {len(all_objs)}")
    
    # 2. MATERIALS
    expected_materials = [
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
    all_mat_names = [m.name for m in bpy.data.materials]
    print(f"Total Materials in bpy.data: {len(all_mat_names)}: {all_mat_names}")
    missing_mats = [m for m in expected_materials if m not in all_mat_names]
    results["all_10_materials_present"] = len(missing_mats) == 0
    results["missing_materials"] = missing_mats
    
    for m_name in expected_materials:
        mat = bpy.data.materials.get(m_name)
        if mat:
            print(f"Material {m_name}: use_nodes={mat.use_nodes}, use_fake_user={mat.use_fake_user}, users={mat.users}")
            
    # 3. ARMATURE & 163 DEF BONES
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    results["armature_exists"] = arm_obj is not None
    if arm_obj and arm_obj.type == 'ARMATURE':
        total_bones = len(arm_obj.data.bones)
        def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
        print(f"Armature: total_bones={total_bones}, def_bones={len(def_bones)}")
        results["def_bones_count"] = len(def_bones)
        results["has_163_def_bones"] = len(def_bones) == 163
        
        # Check fingers
        expected_finger_bones = [
            "DEF-thumb.01.L", "DEF-thumb.02.L", "DEF-thumb.03.L",
            "DEF-f_index.01.L", "DEF-f_index.02.L", "DEF-f_index.03.L",
            "DEF-f_middle.01.L", "DEF-f_middle.02.L", "DEF-f_middle.03.L",
            "DEF-f_ring.01.L", "DEF-f_ring.02.L", "DEF-f_ring.03.L",
            "DEF-f_pinky.01.L", "DEF-f_pinky.02.L", "DEF-f_pinky.03.L",
            "DEF-thumb.01.R", "DEF-thumb.02.R", "DEF-thumb.03.R",
            "DEF-f_index.01.R", "DEF-f_index.02.R", "DEF-f_index.03.R",
            "DEF-f_middle.01.R", "DEF-f_middle.02.R", "DEF-f_middle.03.R",
            "DEF-f_ring.01.R", "DEF-f_ring.02.R", "DEF-f_ring.03.R",
            "DEF-f_pinky.01.R", "DEF-f_pinky.02.R", "DEF-f_pinky.03.R",
        ]
        missing_finger_bones = [b for b in expected_finger_bones if b not in def_bones]
        results["finger_bones_intact"] = len(missing_finger_bones) == 0
        if missing_finger_bones:
            print(f"Missing finger bones: {missing_finger_bones}")
    else:
        results["has_163_def_bones"] = False
        
    # 4. 52 ARKit FACS SHAPE KEYS ON BODY MESH
    body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
    results["body_exists"] = body_obj is not None
    if body_obj and body_obj.type == 'MESH':
        results["body_poly_count"] = len(body_obj.data.polygons)
        results["body_vert_count"] = len(body_obj.data.vertices)
        quads = sum(1 for p in body_obj.data.polygons if len(p.vertices) == 4)
        print(f"Body Mesh: verts={len(body_obj.data.vertices)}, polys={len(body_obj.data.polygons)}, quads={quads} ({quads/len(body_obj.data.polygons)*100:.1f}%)")
        
        sk = body_obj.data.shape_keys
        if sk:
            key_blocks = list(sk.key_blocks)
            print(f"Total shape key blocks: {len(key_blocks)}")
            basis_key = sk.key_blocks.get("Basis")
            results["has_basis_key"] = basis_key is not None
            
            arkit_keys = [k.name for k in key_blocks if k.name != "Basis"]
            print(f"Non-basis shape keys: {len(arkit_keys)}")
            results["arkit_shape_keys_count"] = len(arkit_keys)
            results["has_52_arkit_keys"] = len(arkit_keys) == 52
            
            # Check displacement delta for each key
            zero_delta_keys = []
            basis_cos = [v.co.copy() for v in basis_key.data]
            for kb in arkit_keys:
                kb_obj = sk.key_blocks[kb]
                max_disp = 0.0
                for i, v in enumerate(kb_obj.data):
                    disp = (v.co - basis_cos[i]).length
                    if disp > max_disp:
                        max_disp = disp
                if max_disp < 1e-6:
                    zero_delta_keys.append(kb)
            print(f"Shape keys with zero vertex displacement: {len(zero_delta_keys)}: {zero_delta_keys}")
            results["zero_delta_shape_keys"] = zero_delta_keys
            results["all_shape_keys_have_deltas"] = len(zero_delta_keys) == 0
        else:
            results["has_52_arkit_keys"] = False
            results["all_shape_keys_have_deltas"] = False
            
        # 5. ARMATURE MODIFIER ON BODY & WARDROBE
        body_arm_mod = next((m for m in body_obj.modifiers if m.type == 'ARMATURE'), None)
        results["body_has_armature_mod"] = body_arm_mod is not None
        if body_arm_mod:
            results["body_armature_target"] = body_arm_mod.object.name if body_arm_mod.object else None
            results["body_preserve_volume"] = body_arm_mod.use_deform_preserve_volume
            print(f"Body Armature modifier: target={results['body_armature_target']}, preserve_volume={results['body_preserve_volume']}")
            
        # Check vertex groups on body
        vgroup_names = [vg.name for vg in body_obj.vertex_groups]
        print(f"Body Vertex Groups count: {len(vgroup_names)}")
        results["body_vertex_groups_count"] = len(vgroup_names)
        
        # Check wardrobe armature modifiers
        wardrobe_objs = [o for o in bpy.data.objects if any(w in o.name for w in ["Dress", "Sandal"])]
        wardrobe_mods = {}
        for wo in wardrobe_objs:
            arm_m = next((m for m in wo.modifiers if m.type == 'ARMATURE'), None)
            sol_m = next((m for m in wo.modifiers if m.type == 'SOLIDIFY'), None)
            wardrobe_mods[wo.name] = {
                "armature": arm_m is not None and arm_m.object is not None,
                "solidify": sol_m is not None,
                "solidify_thickness": sol_m.thickness if sol_m else None
            }
        print("Wardrobe object modifiers:", wardrobe_mods)
        results["wardrobe_modifiers"] = wardrobe_mods
        results["all_wardrobe_have_armature"] = all(v["armature"] for v in wardrobe_mods.values())
        
    # 6. LIGHTING & CAMERA & RENDER SETTINGS
    scene = bpy.context.scene
    print(f"Render engine: {scene.render.engine}")
    results["render_engine"] = scene.render.engine
    if hasattr(scene, "cycles"):
        print(f"Cycles samples: {scene.cycles.samples}")
        results["cycles_samples"] = scene.cycles.samples
    if hasattr(scene, "view_settings"):
        print(f"View transform: {scene.view_settings.view_transform}")
        results["view_transform"] = scene.view_settings.view_transform
        
    cam = scene.camera
    results["camera_present"] = cam is not None
    if cam:
        print(f"Active camera: {cam.name}, lens: {cam.data.lens}mm")
        results["camera_lens"] = cam.data.lens
        
    print("\n=== SUMMARY VERIFICATION RESULTS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
        
    all_critical_pass = (
        results.get("root_col_exists") and
        results.get("exact_tiers_match") and
        results.get("all_10_materials_present") and
        results.get("has_163_def_bones") and
        results.get("has_52_arkit_keys") and
        results.get("all_shape_keys_have_deltas") and
        results.get("body_has_armature_mod") and
        results.get("all_wardrobe_have_armature")
    )
    print(f"\nOVERALL CRITICAL VERIFICATION PASS: {all_critical_pass}")
    if not all_critical_pass:
        sys.exit(1)
        
if bpy is not None:
    run_inspection()
