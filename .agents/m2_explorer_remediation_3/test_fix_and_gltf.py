import os
import sys
import math
from pathlib import Path

# Add project root to sys.path
proj_root = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
sys.path.insert(0, str(proj_root))

import bpy
from anime_pipeline.rigging.armature_builder import ArmatureBuilder
from anime_pipeline.rigging.secondary_bones import SecondaryBonesRig
from anime_pipeline.rigging.skinning_dqs import (
    SkinningDQS,
    apply_vertex_weights_to_blender_mesh,
    verify_skin_weights_normalization,
)

def run_investigation():
    clean_blend = proj_root / "output" / "anime_mesh_clean.blend"
    test_glb = Path(r"E:\tool\mcp\MorphoMesh\.agents\m2_explorer_remediation_3\test_rigged.glb")
    test_blend = Path(r"E:\tool\mcp\MorphoMesh\.agents\m2_explorer_remediation_3\test_rigged.blend")

    print(f"Loading {clean_blend}...")
    bpy.ops.wm.open_mainfile(filepath=str(clean_blend))

    expected_submeshes = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    submesh_objs = {}
    for name in expected_submeshes:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH':
            submesh_objs[name] = obj

    print(f"Found {len(submesh_objs)} submeshes.")

    # APPLY TRANSFORM FIX:
    # Submeshes had rotation_euler.x = 1.5708, but raw v.co were already Z-up.
    # We must reset rotation_euler to (0, 0, 0) so object space matches bone world space!
    for name, obj in submesh_objs.items():
        print(f"Submesh {name} original rot: {tuple(round(x, 4) for x in obj.rotation_euler)}")
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.location = (0.0, 0.0, 0.0)
        obj.scale = (1.0, 1.0, 1.0)
        # Apply transform cleanly
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # 2. Build Armature
    builder = ArmatureBuilder(submeshes=submesh_objs)
    arm_obj = builder.build_in_blender()
    print(f"Armature built: {arm_obj.name} with {len(arm_obj.data.bones)} bones.")

    # 3. Secondary rig
    sec_rig = SecondaryBonesRig(scale=builder.scale_factor)
    sec_results = sec_rig.setup_secondary_rig_and_skinning(
        armature_obj=arm_obj,
        submesh_objs=submesh_objs,
        landmarks=builder.resolved_landmarks,
    )
    print("Secondary rig setup completed.")

    # 4. DQS & Parenting
    dqs = SkinningDQS(armature_obj=arm_obj)
    dqs.setup_twist_bone_constraints(arm_obj)
    dqs.configure_all_submeshes_dqs(list(submesh_objs.values()), arm_obj)

    for obj in submesh_objs.values():
        obj.parent = arm_obj
        obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    # Calculate and assign skin weights
    for name, obj in submesh_objs.items():
        if name in ("Anime_Skirt", "Anime_Hair"):
            continue
        verts = [(v.co.x, v.co.y, v.co.z) for v in obj.data.vertices]
        vgroups = dqs.calculate_skin_weights(name, verts, builder.resolved_landmarks)
        apply_vertex_weights_to_blender_mesh(obj, vgroups, clear_existing=True)

    # Verify normalization
    for name, obj in submesh_objs.items():
        num_v = len(obj.data.vertices)
        vgroups_data = {vg.name: [] for vg in obj.vertex_groups}
        for v in obj.data.vertices:
            for g in v.groups:
                vg_name = obj.vertex_groups[g.group].name
                vgroups_data[vg_name].append((v.index, g.weight))
        valid, msg = verify_skin_weights_normalization(name, vgroups_data, num_v)
        if not valid:
            raise RuntimeError(f"Audit failed for {name}: {msg}")

    print("Skinning verified and valid.")

    # Save test blend
    bpy.ops.wm.save_as_mainfile(filepath=str(test_blend))
    print(f"Saved test blend to {test_blend}")

    # Export test GLB
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True)
    for obj in submesh_objs.values():
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.export_scene.gltf(
        filepath=str(test_glb),
        export_format='GLB',
        use_selection=True,
        export_skins=True,
        export_yup=True,
        export_apply=False,
    )
    print(f"Exported test GLB to {test_glb}")

if __name__ == "__main__":
    run_investigation()
