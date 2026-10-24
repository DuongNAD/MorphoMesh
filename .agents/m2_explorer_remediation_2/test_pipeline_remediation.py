"""
E:\tool\mcp\MorphoMesh\.agents\m2_explorer_remediation_2\test_pipeline_remediation.py

Verifies end-to-end pipeline remediation by building a patched rig into our folder
and running test_m2_adversarial_stress directly on it in 'as-delivered' state.
"""

import math
import sys
from pathlib import Path

# Add project root to sys.path
proj_root = Path("E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline")
sys.path.insert(0, str(proj_root))

import bpy
from anime_pipeline.rigging.armature_builder import ArmatureBuilder
from anime_pipeline.rigging.secondary_bones import SecondaryBonesRig
from anime_pipeline.rigging.skinning_dqs import (
    SkinningDQS,
    apply_vertex_weights_to_blender_mesh,
    verify_skin_weights_normalization,
)

clean_blend = proj_root / "output" / "anime_mesh_clean.blend"
test_blend = Path("E:/tool/mcp/MorphoMesh/.agents/m2_explorer_remediation_2/anime_rigged_test.blend")
test_glb = Path("E:/tool/mcp/MorphoMesh/.agents/m2_explorer_remediation_2/anime_rigged_test.glb")

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

print("Applying transform synchronization fix...")
for obj in submesh_objs.values():
    obj.rotation_euler = (0.0, 0.0, 0.0)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

print("Building Armature...")
builder = ArmatureBuilder(submeshes=submesh_objs)
arm_obj = builder.build_in_blender()

print("Setting up Secondary Rig...")
sec_rig = SecondaryBonesRig(scale=builder.scale_factor)
sec_results = sec_rig.setup_secondary_rig_and_skinning(
    armature_obj=arm_obj,
    submesh_objs=submesh_objs,
    landmarks=builder.resolved_landmarks,
)

print("Setting up DQS and skinning...")
dqs = SkinningDQS(armature_obj=arm_obj)
twist_res = dqs.setup_twist_bone_constraints(arm_obj)
dqs_count = dqs.configure_all_submeshes_dqs(list(submesh_objs.values()), arm_obj)

for obj in submesh_objs.values():
    obj.parent = arm_obj
    obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()

for name, obj in submesh_objs.items():
    if name in ("Anime_Skirt", "Anime_Hair"):
        continue
    verts = [(v.co.x, v.co.y, v.co.z) for v in obj.data.vertices]
    vgroups = dqs.calculate_skin_weights(name, verts, builder.resolved_landmarks)
    apply_vertex_weights_to_blender_mesh(obj, vgroups, clear_existing=True)

print(f"Saving to {test_blend}...")
bpy.ops.wm.save_as_mainfile(filepath=str(test_blend))

print("\n--- Running Adversarial Stress Suite on Patched Asset ---")
from tests.test_m2_adversarial_stress import run_live_adversarial_suite
import pprint

report = run_live_adversarial_suite(test_blend)
print("=" * 80)
print("REMEDIATION AUDIT REPORT")
print("=" * 80)
pprint.pprint(report)

assert report["transform_audit"]["is_aligned"], f"Transform audit failed: {report['transform_audit']}"
assert report["weight_audit"]["passed"], f"Weight audit failed: {report['weight_audit']}"
assert report["finger_audit"]["passed"], f"Finger audit failed: {report['finger_audit']}"
assert report["wrist_twist_audit"]["as_delivered"]["passed_85_pct"], f"As-delivered twist audit failed: {report['wrist_twist_audit']['as_delivered']}"
assert report["elbow_flexion_audit"]["passed"], f"Elbow audit failed: {report['elbow_flexion_audit']}"
print("\n>>> ALL ADVERSARIAL STRESS INVARIANTS PASSED 100% <<<")
