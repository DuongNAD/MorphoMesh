import sys
import os
import bpy
import bmesh
import mathutils

def main():
    print("=================================================================")
    print("=== INDEPENDENT ADVERSARIAL AUDIT OF Yu_Nian_An_Master.blend ===")
    print("=================================================================")

    errors = []
    warnings = []

    # -------------------------------------------------------------
    # 1. HAIR GEOMETRY NODES MODIFIER COMPILATION & EVALUATED VERTS
    # -------------------------------------------------------------
    print("\n--- 1. AUDITING HAIR GEOMETRY NODES ---")
    hair_col = bpy.data.collections.get("02_Hair")
    if not hair_col:
        errors.append("Collection '02_Hair' missing!")
    else:
        print(f"Objects in 02_Hair: {[o.name for o in hair_col.objects]}")
        depsgraph = bpy.context.evaluated_depsgraph_get()
        
        expected_hair_layers = [
            "Hair_Hime_Bangs",
            "Hair_Hime_Sidelocks",
            "Hair_Scalp_Crown",
            "Hair_Back_Cascade",
            "Hair_Eyebrows",
            "Hair_Eyelashes"
        ]
        
        total_eval_hair_verts = 0
        for h_name in expected_hair_layers:
            h_obj = bpy.data.objects.get(h_name)
            if not h_obj:
                errors.append(f"Hair object '{h_name}' missing!")
                continue
            
            raw_verts = len(h_obj.data.vertices)
            
            # Check modifiers
            gn_mods = [m for m in h_obj.modifiers if m.type == 'NODES']
            if not gn_mods:
                warnings.append(f"Hair object '{h_name}' has no Geometry Nodes modifier!")
            else:
                for mod in gn_mods:
                    tree = mod.node_group
                    if not tree:
                        errors.append(f"{h_name} GN modifier has no node_group!")
                    else:
                        print(f"  {h_name}: GN tree '{tree.name}', is_modifier={getattr(tree, 'is_modifier', False)}")
                        if hasattr(tree, "interface"):
                            in_sockets = [item.name for item in tree.interface.items_tree if getattr(item, "in_out", None) == 'INPUT']
                            out_sockets = [item.name for item in tree.interface.items_tree if getattr(item, "in_out", None) == 'OUTPUT']
                            print(f"    tree.interface sockets: in={in_sockets}, out={out_sockets}")
                            if "Geometry" not in in_sockets or "Geometry" not in out_sockets:
                                errors.append(f"{h_name}: tree.interface missing Geometry in/out sockets!")
            
            # Evaluated mesh
            eval_obj = h_obj.evaluated_get(depsgraph)
            eval_mesh = eval_obj.to_mesh()
            eval_verts = len(eval_mesh.vertices)
            eval_polys = len(eval_mesh.polygons)
            total_eval_hair_verts += eval_verts
            print(f"  {h_name}: raw_verts={raw_verts}, evaluated_verts={eval_verts}, evaluated_polys={eval_polys}")
            
            if eval_verts == 0:
                errors.append(f"CRITICAL: {h_name} evaluated to 0 vertices! Hair is completely invisible!")
            eval_obj.to_mesh_clear()

        print(f"Total evaluated hair vertices across all layers: {total_eval_hair_verts}")
        if total_eval_hair_verts < 1000:
            errors.append(f"Total evaluated hair vertices ({total_eval_hair_verts}) is less than 1,000 threshold!")

        # Check bangs and back cascade specifically
        bangs = bpy.data.objects.get("Hair_Hime_Bangs")
        cascade = bpy.data.objects.get("Hair_Back_Cascade")
        if bangs:
            bangs_eval = bangs.evaluated_get(depsgraph).to_mesh()
            print(f"Hair_Hime_Bangs eval verts: {len(bangs_eval.vertices)}")
            if len(bangs_eval.vertices) < 1000:
                errors.append(f"Hair_Hime_Bangs has only {len(bangs_eval.vertices)} evaluated vertices (expected >1000)!")
            bangs.evaluated_get(depsgraph).to_mesh_clear()
        if cascade:
            cascade_eval = cascade.evaluated_get(depsgraph).to_mesh()
            print(f"Hair_Back_Cascade eval verts: {len(cascade_eval.vertices)}")
            if len(cascade_eval.vertices) < 1000:
                errors.append(f"Hair_Back_Cascade has only {len(cascade_eval.vertices)} evaluated vertices (expected >1000)!")
            cascade.evaluated_get(depsgraph).to_mesh_clear()

    # -------------------------------------------------------------
    # 2. 7-TIER COLLECTION HIERARCHY & OBJECT MANIFEST
    # -------------------------------------------------------------
    print("\n--- 2. AUDITING 7-TIER COLLECTION HIERARCHY ---")
    all_col_names = [c.name for c in bpy.data.collections]
    print(f"Collections present in bpy.data ({len(all_col_names)}): {all_col_names}")
    
    expected_7_collections = [
        "Yu_Nian_An_Master",
        "01_Body",
        "02_Hair",
        "03_Wardrobe",
        "04_Props",
        "05_Armature",
        "06_Lights_Camera"
    ]
    
    for c_name in expected_7_collections:
        if c_name not in all_col_names:
            errors.append(f"Collection '{c_name}' missing from scene!")
            
    root_col = bpy.data.collections.get("Yu_Nian_An_Master")
    if root_col:
        child_names = [c.name for c in root_col.children]
        expected_subtiers = ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"]
        print(f"Root child collections: {child_names}")
        if sorted(child_names) != sorted(expected_subtiers):
            errors.append(f"Root child collections {child_names} do not exactly match expected 6 subtiers {expected_subtiers}!")

    # Check Material Fake Users
    print("\n--- AUDITING PBR MATERIALS & FAKE USERS ---")
    print(f"Total materials in bpy.data: {len(bpy.data.materials)}")
    for mat in bpy.data.materials:
        print(f"  Material '{mat.name}': use_fake_user={mat.use_fake_user}, users={mat.users}, use_nodes={mat.use_nodes}")
        if not mat.use_fake_user:
            errors.append(f"Material '{mat.name}' does NOT have use_fake_user=True (use_fake_user={mat.use_fake_user})!")

    # -------------------------------------------------------------
    # 3. MASTER BLEND INTEGRITY (PURE QUADS, DEF BONES, BLENDSHAPES)
    # -------------------------------------------------------------
    print("\n--- 3. AUDITING BODY MESH INTEGRITY (PURE QUADS) ---")
    body = bpy.data.objects.get("Yu_Nian_An_Body")
    if not body:
        errors.append("Yu_Nian_An_Body object not found!")
    else:
        mesh = body.data
        poly_count = len(mesh.polygons)
        vert_count = len(mesh.vertices)
        
        tris = [p for p in mesh.polygons if len(p.vertices) == 3]
        quads = [p for p in mesh.polygons if len(p.vertices) == 4]
        ngons = [p for p in mesh.polygons if len(p.vertices) > 4]
        
        print(f"Body Mesh: total_polys={poly_count}, verts={vert_count}")
        print(f"  Quads: {len(quads)} ({len(quads)/poly_count*100:.2f}%)")
        print(f"  Tris: {len(tris)}")
        print(f"  N-gons: {len(ngons)}")
        
        if len(quads) != 2036 or poly_count != 2036:
            errors.append(f"Body mesh quads ({len(quads)}) != 2036 or total polys ({poly_count}) != 2036!")
        if len(tris) != 0:
            errors.append(f"Body mesh has {len(tris)} tris! Must be 0 tris!")
        if len(ngons) != 0:
            errors.append(f"Body mesh has {len(ngons)} n-gons! Must be 0 n-gons!")
            
        # BMESH checks
        bm = bmesh.new()
        bm.from_mesh(mesh)
        non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
        zero_area_faces = [f for f in bm.faces if f.calc_area() < 1e-8]
        boundary_edges = [e for e in bm.edges if e.is_boundary]
        print(f"  Non-manifold edges: {len(non_manifold_edges)}")
        print(f"  Zero-area faces: {len(zero_area_faces)}")
        print(f"  Boundary edges: {len(boundary_edges)}")
        if len(non_manifold_edges) > 0:
            errors.append(f"Body mesh has {len(non_manifold_edges)} non-manifold edges!")
        if len(zero_area_faces) > 0:
            errors.append(f"Body mesh has {len(zero_area_faces)} zero-area faces!")
        bm.free()

    print("\n--- AUDITING ARMATURE & 163 DEF BONES ---")
    arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")
    if not arm_obj:
        errors.append("Armature_Yu_Nian_An_Rigify object not found!")
    else:
        def_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("DEF-")]
        print(f"Total bones: {len(arm_obj.data.bones)}, DEF bones: {len(def_bones)}")
        if len(def_bones) != 163:
            errors.append(f"Armature has {len(def_bones)} DEF bones, expected exactly 163!")

    print("\n--- AUDITING 52 ARKit FACS BLENDSHAPES ---")
    if body and body.data.shape_keys:
        sk = body.data.shape_keys
        key_blocks = sk.key_blocks
        basis = key_blocks.get("Basis")
        if not basis:
            errors.append("Shape key 'Basis' not found!")
        else:
            arkit_keys = [k for k in key_blocks if k.name != "Basis"]
            print(f"Total shape key blocks: {len(key_blocks)}, Non-basis keys: {len(arkit_keys)}")
            if len(arkit_keys) != 52:
                errors.append(f"Found {len(arkit_keys)} ARKit shape keys, expected exactly 52!")
                
            zero_delta_keys = []
            basis_cos = [v.co.copy() for v in basis.data]
            for kb in arkit_keys:
                max_d = max((v.co - basis_cos[i]).length for i, v in enumerate(kb.data))
                if max_d < 1e-6:
                    zero_delta_keys.append((kb.name, max_d))
            if zero_delta_keys:
                errors.append(f"Found shape keys with ZERO vertex delta: {zero_delta_keys}")
            else:
                print("All 52 ARKit shape keys have verified NON-ZERO vertex deltas!")

    # -------------------------------------------------------------
    # 4. PROPS, CAMERAS, LIGHTS, AND EYE AUDIT
    # -------------------------------------------------------------
    print("\n--- 4. ADVERSARIAL INSPECTION: PROPS, CAMERAS, LIGHTS, EYES ---")
    # Eye positions
    eye_l = bpy.data.objects.get("Mesh_Eye_Left_CorneaSclera")
    if eye_l:
        world_y = (eye_l.matrix_world.translation).y
        print(f"Left Eye Y translation: {world_y:.4f}m")
        if world_y > -0.10:
            errors.append(f"Left Eye buried at Y={world_y:.4f}m (expected <= -0.11m)!")
            
    # Lighting constraints
    key_light = bpy.data.objects.get("Light_Key_Softbox")
    if key_light:
        track = next((c for c in key_light.constraints if c.type == 'TRACK_TO'), None)
        print(f"Light_Key_Softbox TRACK_TO constraint: {track is not None}")
        if not track:
            warnings.append("Light_Key_Softbox has no TRACK_TO constraint!")

    # Cameras
    portrait_cam = bpy.data.objects.get("Camera_Portrait_85mm")
    fullbody_cam = bpy.data.objects.get("Camera_FullBody")
    print(f"Portrait cam: {portrait_cam is not None}, FullBody cam: {fullbody_cam is not None}")
    if not portrait_cam or not fullbody_cam:
        warnings.append("Portrait or FullBody camera missing!")

    # -------------------------------------------------------------
    # FINAL REPORT
    # -------------------------------------------------------------
    print("\n=================================================================")
    print(f"AUDIT SUMMARY: {len(errors)} ERRORS, {len(warnings)} WARNINGS")
    for w in warnings:
        print(f"  [WARN] {w}")
    for e in errors:
        print(f"  [FAIL] {e}")
    print("=================================================================")
    
    if errors:
        sys.exit(1)
    else:
        print("ALL INDEPENDENT ADVERSARIAL AUDIT CHECKS PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    main()
