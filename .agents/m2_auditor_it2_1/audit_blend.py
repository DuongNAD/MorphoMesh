import sys
import json
import math
import bpy
import mathutils

def run_blend_audit():
    print("=== RUNNING FORENSIC BLENDER AUDIT ON ANIME_RIGGED.BLEND ===")
    arm_obj = bpy.data.objects.get("Anime_Armature")
    if not arm_obj:
        print("FAIL: Anime_Armature object not found!")
        sys.exit(1)
        
    print(f"Armature: {arm_obj.name}")
    print(f"Armature rotation_euler: {tuple(arm_obj.rotation_euler)}")
    print(f"Armature matrix_world:\n{arm_obj.matrix_world}")
    print(f"Armature total bones: {len(arm_obj.data.bones)}")
    
    expected_submeshes = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    
    submesh_results = {}
    all_aligned = True
    all_dqs_enabled = True
    all_parented = True
    
    for name in expected_submeshes:
        obj = bpy.data.objects.get(name)
        if not obj:
            print(f"FAIL: Submesh {name} not found in scene!")
            submesh_results[name] = {"found": False}
            all_aligned = False
            continue
            
        rot_e = tuple(obj.rotation_euler)
        rot_deg = tuple(math.degrees(r) for r in rot_e)
        mw = obj.matrix_world
        arm_mw = arm_obj.matrix_world
        
        # Check alignment: mw should match arm_mw
        diff = sum(sum(abs(mw[i][j] - arm_mw[i][j]) for j in range(4)) for i in range(4))
        is_aligned = (diff < 1e-4) and all(abs(r) < 1e-4 for r in rot_e)
        if not is_aligned:
            all_aligned = False
            
        # Check parent
        is_parented_to_arm = (obj.parent == arm_obj)
        if not is_parented_to_arm:
            all_parented = False
            
        # Check parent inverse
        mpi = obj.matrix_parent_inverse
        mpi_ident_diff = sum(sum(abs(mpi[i][j] - (1.0 if i==j else 0.0)) for j in range(4)) for i in range(4))
        
        # Check modifiers
        arm_mods = [m for m in obj.modifiers if m.type == 'ARMATURE']
        has_arm_mod = len(arm_mods) > 0
        dqs_on = has_arm_mod and arm_mods[0].use_deform_preserve_volume and (arm_mods[0].object == arm_obj)
        if not dqs_on:
            all_dqs_enabled = False
            
        submesh_results[name] = {
            "found": True,
            "vertex_count": len(obj.data.vertices),
            "rotation_euler_rad": [round(r, 6) for r in rot_e],
            "rotation_euler_deg": [round(d, 4) for d in rot_deg],
            "matrix_world_diff_from_armature": diff,
            "is_aligned": is_aligned,
            "parent": obj.parent.name if obj.parent else None,
            "is_parented_to_armature": is_parented_to_arm,
            "matrix_parent_inverse_is_identity": (mpi_ident_diff < 1e-4),
            "armature_modifier_present": has_arm_mod,
            "dqs_preserve_volume": dqs_on,
            "vertex_groups_count": len(obj.vertex_groups),
        }
        
    print("\n--- Submesh Audit Summary ---")
    for name, res in submesh_results.items():
        print(f"{name}: verts={res['vertex_count']}, rot_euler={res['rotation_euler_deg']}, aligned={res['is_aligned']}, parent={res['parent']}, DQS={res['dqs_preserve_volume']}")

    # Check live deformation
    print("\n--- Live Deformation & Volume Retention Test ---")
    # Twist left wrist by 90 and 180 degrees
    arms_obj = bpy.data.objects.get("Anime_Arms")
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    pose_bones = arm_obj.pose.bones
    hand_l = pose_bones.get("Hand.L")
    if hand_l:
        # Measure rest coordinates of a wrist vertex
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_arms = arms_obj.evaluated_get(depsgraph)
        eval_mesh = eval_arms.to_mesh()
        
        # Calculate volume at rest
        def calc_mesh_volume(me):
            vol = 0.0
            for poly in me.polygons:
                v0 = me.vertices[poly.vertices[0]].co
                for i in range(1, len(poly.vertices) - 1):
                    v1 = me.vertices[poly.vertices[i]].co
                    v2 = me.vertices[poly.vertices[i+1]].co
                    vol += v0.dot(v1.cross(v2)) / 6.0
            return abs(vol)
            
        rest_vol = calc_mesh_volume(eval_mesh)
        eval_arms.to_mesh_clear()
        
        # Rotate Hand.L around local Y by 90 deg (pi/2)
        hand_l.rotation_mode = 'XYZ'
        hand_l.rotation_euler = (0, math.pi / 2, 0)
        depsgraph.update()
        eval_arms = arms_obj.evaluated_get(depsgraph)
        eval_mesh = eval_arms.to_mesh()
        vol_90 = calc_mesh_volume(eval_mesh)
        eval_arms.to_mesh_clear()
        
        # Rotate Hand.L around local Y by 180 deg (pi)
        hand_l.rotation_euler = (0, math.pi, 0)
        depsgraph.update()
        eval_arms = arms_obj.evaluated_get(depsgraph)
        eval_mesh = eval_arms.to_mesh()
        vol_180 = calc_mesh_volume(eval_mesh)
        eval_arms.to_mesh_clear()
        
        # Reset Hand.L
        hand_l.rotation_euler = (0, 0, 0)
        depsgraph.update()
        
        rv_90 = vol_90 / rest_vol if rest_vol > 0 else 0
        rv_180 = vol_180 / rest_vol if rest_vol > 0 else 0
        print(f"Rest Volume: {rest_vol:.8f}")
        print(f"Vol at 90 deg: {vol_90:.8f}, Retention Rv={rv_90*100:.2f}%")
        print(f"Vol at 180 deg: {vol_180:.8f}, Retention Rv={rv_180*100:.2f}%")
    else:
        print("FAIL: Hand.L pose bone not found!")
        
    bpy.ops.object.mode_set(mode='OBJECT')
    
    audit_data = {
        "all_aligned": all_aligned,
        "all_dqs_enabled": all_dqs_enabled,
        "all_parented": all_parented,
        "submeshes": submesh_results,
        "volume_retention": {
            "rest_vol": rest_vol,
            "vol_90": vol_90,
            "rv_90": rv_90,
            "vol_180": vol_180,
            "rv_180": rv_180,
        }
    }
    with open("E:/tool/mcp/MorphoMesh/.agents/m2_auditor_it2_1/blend_audit_result.json", "w") as f:
        json.dump(audit_data, f, indent=2)
    print("\nBlend audit complete. Saved to blend_audit_result.json")

if __name__ == "__main__":
    run_blend_audit()
