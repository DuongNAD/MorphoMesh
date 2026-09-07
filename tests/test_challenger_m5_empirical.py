"""
Empirical Challenger Test Suite for Milestone 5 Production Exports.
Author: challenger_human_m5_1

Can be run via:
1. pytest tests/test_challenger_m5_empirical.py -v
2. & 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --python tests/test_challenger_m5_empirical.py
"""

import os
import sys
import json
import struct

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytest
except ImportError:
    pytest = None

try:
    import bpy
    import bmesh
    import mathutils
except ImportError:
    bpy = None
    bmesh = None
    mathutils = None

OUTPUT_DIR = "output/yu_nian_an"
GLB_PATH = os.path.join(OUTPUT_DIR, "Yu_Nian_An.glb")
FBX_PATH = os.path.join(OUTPUT_DIR, "Yu_Nian_An.fbx")
BLEND_PATH = os.path.join(OUTPUT_DIR, "Yu_Nian_An_Master.blend")
TEX_DIR = os.path.join(OUTPUT_DIR, "textures")

EXPECTED_TEXTURES = [
    "Yu_Nian_An_BaseColor_4K.png",
    "Yu_Nian_An_Normal_4K.png",
    "Yu_Nian_An_Roughness_4K.png",
    "Yu_Nian_An_Metallic_4K.png",
    "Yu_Nian_An_SSS_4K.png",
    "Yu_Nian_An_Alpha_4K.png",
    "Yu_Nian_An_Height_4K.png",
]

ARKIT_52 = [
    "eyeBlinkLeft", "eyeLookDownLeft", "eyeLookInLeft", "eyeLookOutLeft", "eyeLookUpLeft",
    "eyeSquintLeft", "eyeWideLeft", "eyeBlinkRight", "eyeLookDownRight", "eyeLookInRight",
    "eyeLookOutRight", "eyeLookUpRight", "eyeSquintRight", "eyeWideRight", "jawForward",
    "jawLeft", "jawRight", "jawOpen", "mouthClose", "mouthFunnel",
    "mouthPucker", "mouthLeft", "mouthRight", "mouthSmileLeft", "mouthSmileRight",
    "mouthFrownLeft", "mouthFrownRight", "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft",
    "mouthStretchRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthPressLeft", "mouthPressRight", "mouthLowerDownLeft", "mouthLowerDownRight", "mouthUpperUpLeft",
    "mouthUpperUpRight", "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft",
    "browOuterUpRight", "cheekPuff", "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft",
    "noseSneerRight", "tongueOut"
]


class TestEmpiricalContainersAndTextures:
    """Empirical tests for container structures and texture signal mathematics."""

    def test_glb_container_and_morphs(self):
        assert os.path.isfile(GLB_PATH)
        file_size = os.path.getsize(GLB_PATH)
        assert file_size > 2_000_000

        with open(GLB_PATH, "rb") as f:
            header = f.read(12)
            magic, version, length = struct.unpack("<4sII", header)
            assert magic == b"glTF"
            assert version == 2
            assert length == file_size

            chunk0_header = f.read(8)
            chunk0_len, chunk0_type = struct.unpack("<I4s", chunk0_header)
            assert chunk0_type == b"JSON"
            json_data = json.loads(f.read(chunk0_len).decode("utf-8"))

        nodes = json_data.get("nodes", [])
        meshes = json_data.get("meshes", [])
        skins = json_data.get("skins", [])
        assert len(nodes) >= 190, f"Expected >= 190 nodes, got {len(nodes)}"
        assert len(meshes) >= 30, f"Expected >= 30 meshes, got {len(meshes)}"
        assert len(skins) >= 1, "Missing skin container in GLB"

        joints = skins[0].get("joints", [])
        assert len(joints) == 164, f"Expected 164 skin joints, got {len(joints)}"

        body_mesh = next(m for m in meshes if "Body" in m.get("name", ""))
        target_names = body_mesh.get("extras", {}).get("targetNames", [])
        assert len(target_names) == 52, f"Expected 52 morph targets, got {len(target_names)}"
        assert sorted(target_names) == sorted(ARKIT_52)

    def test_fbx_binary_header_and_bones(self):
        assert os.path.isfile(FBX_PATH)
        file_size = os.path.getsize(FBX_PATH)
        assert file_size > 5_000_000

        with open(FBX_PATH, "rb") as f:
            header = f.read(27)
            assert header[:23] == b"Kaydara FBX Binary  \x00\x1a\x00"
            version = struct.unpack("<I", header[23:27])[0]
            assert version == 7400

            f.seek(0)
            fbx_bytes = f.read()

        for bone_name in [b"DEF-spine", b"DEF-head", b"DEF-upper_arm.L", b"DEF-hand.L", b"DEF-thigh.L", b"DEF-foot.L"]:
            assert bone_name in fbx_bytes, f"Missing {bone_name} in FBX"

        for shape_name in [b"eyeBlinkLeft", b"jawOpen", b"mouthSmileLeft", b"cheekPuff"]:
            assert shape_name in fbx_bytes, f"Missing shape {shape_name} in FBX"

    def test_all_texture_dimensions_and_channels(self):
        for tex_name in EXPECTED_TEXTURES:
            fpath = os.path.join(TEX_DIR, tex_name)
            assert os.path.isfile(fpath), f"Missing {tex_name}"
            with Image.open(fpath) as img:
                assert img.size == (4096, 4096), f"{tex_name} not 4096x4096"
                arr = np.array(img)
                assert arr.shape[:2] == (4096, 4096)

    def test_normal_map_unit_vectors(self):
        norm_path = os.path.join(TEX_DIR, "Yu_Nian_An_Normal_4K.png")
        with Image.open(norm_path) as img:
            arr = np.array(img)[:, :, :3]
        norm_vec = (arr.astype(np.float32) / 127.5) - 1.0
        mag = np.sqrt(np.sum(norm_vec ** 2, axis=-1))
        mean_deviation = float(np.mean(np.abs(mag - 1.0)))
        max_deviation = float(np.max(np.abs(mag - 1.0)))
        assert mean_deviation < 0.01, f"Mean normal vector deviation too high: {mean_deviation}"
        assert max_deviation < 0.02, f"Max normal vector deviation too high: {max_deviation}"
        assert float(np.min(norm_vec[..., 2])) > 0.0, "Tangent normal Z not facing forward"

    def test_roughness_dual_variation(self):
        rough_path = os.path.join(TEX_DIR, "Yu_Nian_An_Roughness_4K.png")
        with Image.open(rough_path) as img:
            arr = np.array(img)
        unique_vals = np.unique(arr)
        assert len(unique_vals) >= 10, f"Expected >= 10 regional roughness levels, got {len(unique_vals)}"
        assert arr.std() > 20.0, "Roughness map lacks standard deviation"

    def test_metallic_hardware_masks(self):
        met_path = os.path.join(TEX_DIR, "Yu_Nian_An_Metallic_4K.png")
        with Image.open(met_path) as img:
            arr = np.array(img)
        unique_vals = np.unique(arr)
        assert 0 in unique_vals and 255 in unique_vals
        zero_ratio = float(np.sum(arr == 0)) / arr.size
        high_ratio = float(np.sum(arr == 255)) / arr.size
        assert zero_ratio > 0.95, f"Dielectric ratio too low: {zero_ratio}"
        assert 0.01 < high_ratio < 0.05, f"Hardware metallic ratio unexpected: {high_ratio}"

    def test_height_and_sss_signals(self):
        height_path = os.path.join(TEX_DIR, "Yu_Nian_An_Height_4K.png")
        sss_path = os.path.join(TEX_DIR, "Yu_Nian_An_SSS_4K.png")
        with Image.open(height_path) as img:
            h_arr = np.array(img)
        with Image.open(sss_path) as img:
            s_arr = np.array(img)

        assert h_arr.var() > 50.0, "Height map variance too low"
        assert s_arr.max() > 200, "SSS map peak too low"
        assert s_arr.min() == 0, "SSS map minimum not zero"


def run_blender_live_test():
    """Executed directly inside Blender to verify mesh import and depsgraph deformation."""
    if bpy is None:
        print("Not running inside Blender, skipping live Blender test.")
        return

    print("\n=======================================================")
    print("=== CHALLENGER LIVE BLENDER RE-IMPORT DEPSGRAPH AUDIT ===")
    print("=======================================================")

    # 1. TEST GLB RE-IMPORT
    print("\n--- 1. TESTING GLB RE-IMPORT ---")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    res = bpy.ops.import_scene.gltf(filepath=os.path.abspath(GLB_PATH))
    assert 'FINISHED' in res, f"GLB import failed: {res}"

    scene_objs = bpy.context.scene.objects
    mesh_objs = [o for o in scene_objs if o.type == 'MESH']
    arm_objs = [o for o in scene_objs if o.type == 'ARMATURE']
    print(f"GLB imported: {len(scene_objs)} objects, {len(mesh_objs)} meshes, {len(arm_objs)} armatures")
    assert len(mesh_objs) >= 20, f"Expected >= 20 meshes, got {len(mesh_objs)}"
    assert len(arm_objs) >= 1, "Expected at least 1 armature in GLB"

    body_obj = next((o for o in mesh_objs if "Body" in o.name), None)
    assert body_obj is not None, "Yu_Nian_An_Body not found in GLB"

    # Non-manifold and degenerate face check
    bm = bmesh.new()
    bm.from_mesh(body_obj.data)
    zero_area = [f for f in bm.faces if f.calc_area() <= 1e-8]
    non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
    bm.free()
    print(f"GLB Body Mesh: {len(body_obj.data.vertices)} verts, {len(body_obj.data.polygons)} polys")
    print(f"  Zero-area faces: {len(zero_area)}")
    print(f"  Non-manifold edges: {len(non_manifold_edges)}")
    assert len(zero_area) == 0, f"Degenerate zero area faces in GLB: {len(zero_area)}"

    # Shape key check and depsgraph evaluation
    sk = body_obj.data.shape_keys
    assert sk is not None, "Shape keys missing on GLB Body"
    assert len(sk.key_blocks) >= 53, f"Expected >= 53 shape keys, got {len(sk.key_blocks)}"
    v_orig = [v.co.copy() for v in body_obj.data.vertices]

    sk.key_blocks["jawOpen"].value = 1.0
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = body_obj.evaluated_get(dg)
    eval_mesh = eval_obj.to_mesh()
    jaw_disp = max((v2 - v1).length for v1, v2 in zip(v_orig, [v.co for v in eval_mesh.vertices]))
    eval_obj.to_mesh_clear()
    sk.key_blocks["jawOpen"].value = 0.0
    print(f"  GLB jawOpen vertex displacement: {jaw_disp:.6f}m")
    assert jaw_disp > 0.01, f"GLB jawOpen displacement too low: {jaw_disp}"

    # 2. TEST FBX RE-IMPORT
    print("\n--- 2. TESTING FBX RE-IMPORT ---")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    res = bpy.ops.import_scene.fbx(filepath=os.path.abspath(FBX_PATH))
    assert 'FINISHED' in res, f"FBX import failed: {res}"

    scene_objs = bpy.context.scene.objects
    mesh_objs = [o for o in scene_objs if o.type == 'MESH']
    arm_objs = [o for o in scene_objs if o.type == 'ARMATURE']
    print(f"FBX imported: {len(scene_objs)} objects, {len(mesh_objs)} meshes, {len(arm_objs)} armatures")
    assert len(mesh_objs) >= 20, f"Expected >= 20 meshes, got {len(mesh_objs)}"
    assert len(arm_objs) >= 1, "Expected at least 1 armature in FBX"

    body_obj = next((o for o in mesh_objs if "Body" in o.name), None)
    assert body_obj is not None, "Yu_Nian_An_Body not found in FBX"

    # Non-manifold and degenerate face check
    bm = bmesh.new()
    bm.from_mesh(body_obj.data)
    zero_area = [f for f in bm.faces if f.calc_area() <= 1e-8]
    bm.free()
    print(f"FBX Body Mesh: {len(body_obj.data.vertices)} verts, {len(body_obj.data.polygons)} polys")
    print(f"  Zero-area faces: {len(zero_area)}")
    assert len(zero_area) == 0, f"Degenerate zero area faces in FBX: {len(zero_area)}"

    # Shape key check and depsgraph evaluation
    sk = body_obj.data.shape_keys
    assert sk is not None, "Shape keys missing on FBX Body"
    assert len(sk.key_blocks) >= 53, f"Expected >= 53 shape keys, got {len(sk.key_blocks)}"
    v_orig = [v.co.copy() for v in body_obj.data.vertices]

    sk.key_blocks["jawOpen"].value = 1.0
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = body_obj.evaluated_get(dg)
    eval_mesh = eval_obj.to_mesh()
    jaw_disp = max((v2 - v1).length for v1, v2 in zip(v_orig, [v.co for v in eval_mesh.vertices]))
    eval_obj.to_mesh_clear()
    sk.key_blocks["jawOpen"].value = 0.0
    print(f"  FBX jawOpen vertex displacement: {jaw_disp:.6f}m")
    assert jaw_disp > 0.01, f"FBX jawOpen displacement too low: {jaw_disp}"

    # Skeletal deformation check
    arm = arm_objs[0]
    def_bones = [b for b in arm.data.bones if b.name.startswith("DEF-")]
    print(f"  FBX Armature: {len(arm.data.bones)} bones, {len(def_bones)} DEF bones")
    assert len(def_bones) == 163, f"Expected 163 DEF bones, got {len(def_bones)}"

    # Pose mode bone rotation
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    arm_bone = arm.pose.bones.get("DEF-upper_arm.L")
    assert arm_bone is not None, "DEF-upper_arm.L not found in FBX armature"
    arm_bone.rotation_mode = 'XYZ'
    arm_bone.rotation_euler = (0, 0, 1.2) # ~70 deg
    bpy.context.view_layer.update()

    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = body_obj.evaluated_get(dg)
    eval_mesh = eval_obj.to_mesh()
    bone_disp = max((v2 - v1).length for v1, v2 in zip(v_orig, [v.co for v in eval_mesh.vertices]))
    eval_obj.to_mesh_clear()
    print(f"  FBX upper_arm rotation skinning displacement: {bone_disp:.6f}m")
    assert bone_disp > 0.1, f"FBX skin deform displacement too low: {bone_disp}"

    print("\n>>> ALL LIVE BLENDER RE-IMPORT AUDITS PASSED WITH ZERO ERRORS! <<<")


if __name__ == '__main__':
    run_blender_live_test()
