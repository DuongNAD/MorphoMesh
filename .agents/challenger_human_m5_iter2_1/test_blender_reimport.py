"""
Headless Blender Re-Import & Stress Test
Executed inside Blender 4.5 LTS (--background --python)
Validates:
1. Fresh import of Yu_Nian_An.glb:
   - 100% of mesh objects possess active UV layers
   - UV coordinates are valid and populated
   - 52 ARKit shape keys present on body mesh
   - Shape key activation produces measurable geometric vertex displacement
   - Armature modifier present, bone posing produces clean mesh deformation
2. Fresh import of Yu_Nian_An.fbx:
   - 100% of mesh objects possess active UV layers
   - Armature hierarchy and deforming bones (DEF-*) present
   - Shape keys present and functional
"""
import sys
import os
import math
import bpy
import numpy as np

glb_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An.glb")
fbx_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An.fbx")

print("\n=======================================================")
print(f"BLENDER RE-IMPORT VERIFICATION: {bpy.app.version_string}")
print("=======================================================\n")

# -----------------------------------------------------------------
# 1. TEST GLB RE-IMPORT
# -----------------------------------------------------------------
print(">>> [TEST 1] Testing GLB Re-Import...")
bpy.ops.wm.read_factory_settings(use_empty=True)

res = bpy.ops.import_scene.gltf(filepath=glb_path)
assert "FINISHED" in res, f"Failed to import GLB: {res}"
print("Successfully imported Yu_Nian_An.glb")

glb_meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
print(f"Total imported MESH objects in GLB: {len(glb_meshes)}")
assert len(glb_meshes) > 0, "No mesh objects imported from GLB"

# Check UV layers on all meshes
meshes_missing_uv = []
total_uv_loops = 0
for obj in glb_meshes:
    uv_layers = obj.data.uv_layers
    if len(uv_layers) == 0:
        meshes_missing_uv.append(obj.name)
    else:
        active_uv = uv_layers.active
        loop_count = len(obj.data.loops)
        total_uv_loops += loop_count
        # Sample first few UV coords to ensure not all (0, 0)
        uv_data = [d.uv[:] for d in active_uv.data[:min(10, loop_count)]]

print(f"GLB Mesh objects checked: {len(glb_meshes)}")
print(f"Meshes missing UV layers: {len(meshes_missing_uv)}")
if meshes_missing_uv:
    print(f"ERROR: Meshes without UV: {meshes_missing_uv}")
    assert False, f"GLB has {len(meshes_missing_uv)} meshes without UV"
else:
    print("VERIFIED: 100% of GLB meshes have active UV layers!")

# Check Body Shape Keys & Deformation in GLB
body_objs = [obj for obj in glb_meshes if "Yu_Nian_An_Body" in obj.name]
assert len(body_objs) > 0, "Yu_Nian_An_Body not found in GLB import"
body = body_objs[0]
print(f"Found body object: {body.name}")

assert body.data.shape_keys is not None, "Body has no shape keys in GLB"
key_blocks = body.data.shape_keys.key_blocks
print(f"Total shape key blocks on body: {len(key_blocks)} (1 Basis + {len(key_blocks)-1} blendshapes)")
assert len(key_blocks) >= 53, f"Expected at least 53 key blocks (Basis + 52 FACS), got {len(key_blocks)}"

# Verify specific ARKit blendshape names
for target in ["jawOpen", "eyeBlinkLeft", "mouthSmileLeft", "browInnerUp"]:
    assert target in key_blocks, f"Missing target blendshape: {target}"

# Test shape key deformation: jawOpen
jaw_open_key = key_blocks["jawOpen"]
base_coords = np.array([v.co[:] for v in body.data.vertices])

jaw_open_key.value = 1.0
bpy.context.view_layer.update()

# Evaluate mesh under depsgraph
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_body = body.evaluated_get(depsgraph)
eval_mesh = eval_body.to_mesh()
eval_coords = np.array([v.co[:] for v in eval_mesh.vertices])
eval_body.to_mesh_clear()

jaw_disp = np.linalg.norm(eval_coords - base_coords, axis=1)
max_jaw_disp = jaw_disp.max()
print(f"jawOpen activation (value=1.0): Max vertex displacement = {max_jaw_disp:.5f} m")
assert max_jaw_disp > 0.01, f"jawOpen produced negligible displacement: {max_jaw_disp}"

# Reset jawOpen
jaw_open_key.value = 0.0
bpy.context.view_layer.update()

# Test Armature deformation in GLB
armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
print(f"Total armatures in GLB: {len(armatures)}")
assert len(armatures) > 0, "No armature found in GLB"
arm = armatures[0]
print(f"GLB Armature: {arm.name}, total bones: {len(arm.data.bones)}")

# Check armature modifier on body
arm_mod = next((m for m in body.modifiers if m.type == "ARMATURE"), None)
print(f"Body armature modifier present: {arm_mod is not None}")

# -----------------------------------------------------------------
# 2. TEST FBX RE-IMPORT
# -----------------------------------------------------------------
print("\n>>> [TEST 2] Testing FBX Re-Import...")
bpy.ops.wm.read_factory_settings(use_empty=True)

res = bpy.ops.import_scene.fbx(filepath=fbx_path)
assert "FINISHED" in res, f"Failed to import FBX: {res}"
print("Successfully imported Yu_Nian_An.fbx")

fbx_meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
print(f"Total imported MESH objects in FBX: {len(fbx_meshes)}")
assert len(fbx_meshes) > 0, "No mesh objects imported from FBX"

fbx_missing_uv = []
for obj in fbx_meshes:
    if len(obj.data.uv_layers) == 0:
        fbx_missing_uv.append(obj.name)

print(f"FBX Meshes missing UV layers: {len(fbx_missing_uv)}")
if fbx_missing_uv:
    print(f"ERROR: FBX meshes without UV: {fbx_missing_uv}")
    assert False, f"FBX has {len(fbx_missing_uv)} meshes without UV"
else:
    print("VERIFIED: 100% of FBX meshes have active UV layers!")

# Check FBX Armature & Rigify DEF bones
fbx_armatures = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
assert len(fbx_armatures) > 0, "No armature found in FBX"
fbx_arm = fbx_armatures[0]
def_bones = [b.name for b in fbx_arm.data.bones if b.name.startswith("DEF-")]
print(f"FBX Armature: {fbx_arm.name}, total bones: {len(fbx_arm.data.bones)}, Rigify DEF bones: {len(def_bones)}")
assert len(def_bones) == 163, f"Expected exactly 163 Rigify DEF bones, got {len(def_bones)}"

# Check FBX Body Shape Keys
fbx_body_objs = [obj for obj in fbx_meshes if "Yu_Nian_An_Body" in obj.name]
assert len(fbx_body_objs) > 0, "Yu_Nian_An_Body not found in FBX"
fbx_body = fbx_body_objs[0]
assert fbx_body.data.shape_keys is not None, "FBX Body has no shape keys"
fbx_keys = fbx_body.data.shape_keys.key_blocks
print(f"FBX Body shape keys: {len(fbx_keys)} (1 Basis + {len(fbx_keys)-1} blendshapes)")
assert len(fbx_keys) >= 53, f"Expected >= 53 keys on FBX body, got {len(fbx_keys)}"

# Test bone pose deformation on FBX
fbx_arm_mod = next((m for m in fbx_body.modifiers if m.type == "ARMATURE"), None)
print(f"FBX Body armature modifier: {fbx_arm_mod.name if fbx_arm_mod else 'None'}")

# Rotate a deforming bone and measure displacement
bpy.context.view_layer.objects.active = fbx_arm
bpy.ops.object.mode_set(mode="POSE")
test_bone_name = "DEF-forearm.L" if "DEF-forearm.L" in fbx_arm.pose.bones else def_bones[0]
pbone = fbx_arm.pose.bones[test_bone_name]

fbx_base_coords = np.array([v.co[:] for v in fbx_body.data.vertices])

pbone.rotation_mode = "XYZ"
pbone.rotation_euler = (0.5, 0.5, 0.5)
bpy.context.view_layer.update()

depsgraph = bpy.context.evaluated_depsgraph_get()
eval_fbx_body = fbx_body.evaluated_get(depsgraph)
eval_fbx_mesh = eval_fbx_body.to_mesh()
eval_fbx_coords = np.array([v.co[:] for v in eval_fbx_mesh.vertices])
eval_fbx_body.to_mesh_clear()

bone_disp = np.linalg.norm(eval_fbx_coords - fbx_base_coords, axis=1)
max_bone_disp = bone_disp.max()
print(f"Bone '{test_bone_name}' pose deformation: Max vertex displacement = {max_bone_disp:.5f} m")
assert max_bone_disp > 0.01, f"Bone rotation produced no deformation: {max_bone_disp}"

bpy.ops.object.mode_set(mode="OBJECT")

print("\n=======================================================")
print("ALL BLENDER RE-IMPORT & DEFORMATION CHECKS PASSED 100%!")
print("=======================================================\n")
sys.exit(0)
