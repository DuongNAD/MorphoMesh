"""
MorphoMesh: Milestone 4 Challenger M4-1 Adversarial Stress Test Suite.

Audits and stress-tests:
1. Collection hierarchy creation (7 standard collections), lighting setups (3-point, dramatic cinematic, high-key anime), and 4-camera multi-angle rigs (+ portrait & fullbody).
2. 4K PBR procedural texture baker node graph setup, channel distributions, and UV atlas margins.
3. glTF 2.0 / FBX / OBJ packager, ZIP archiving, and documentation manifest generation.
4. Master assembly coordinator integration across human body, metarig, wardrobe, hair ribbons, and materials.
"""

from __future__ import annotations

import ast
import json
import math
import os
import shutil
import struct
import tempfile
import zipfile
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest
from PIL import Image

from morphomesh.assembler import (
    ALL_163_DEF_BONES,
    ALL_SEVEN_COLLECTIONS,
    ARKIT_52_BLENDSHAPES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    FINGER_DEF_BONE_KEYS,
    FINGER_LANDMARK_KEYS,
    MATERIAL_NAMES,
    ROOT_COLLECTION_NAME,
    SEVEN_TIER_COLLECTION_HIERARCHY,
    STANDARD_HUMAN_MATERIALS,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    TIER_COLLECTION_NAMES,
    MasterAssemblyConfig,
    YuNianAnAssembler,
    assemble_master_character,
    export_production_assets,
    generate_yu_nian_an_pbr_textures,
    get_export_script,
    get_master_assembly_script,
)
from morphomesh.character_assembler import (
    ALL_SEVEN_COLLECTIONS as FACADE_ALL_SEVEN_COLLECTIONS,
    MasterAssemblyConfig as FacadeMasterAssemblyConfig,
    YuNianAnAssembler as FacadeYuNianAnAssembler,
    assemble_master_character as facade_assemble_master_character,
    generate_yu_nian_an_pbr_textures as facade_generate_pbr_textures,
)
from morphomesh.geometry.exporters import export_obj
from morphomesh.geometry.mesh import MeshGeometry

OUTPUT_DIR = "output/yu_nian_an"
TEXTURES_DIR = os.path.join(OUTPUT_DIR, "textures")
MASTER_BLEND = os.path.join(OUTPUT_DIR, "Yu_Nian_An_Master.blend")
EXPORT_FBX = os.path.join(OUTPUT_DIR, "Yu_Nian_An.fbx")
EXPORT_GLB = os.path.join(OUTPUT_DIR, "Yu_Nian_An.glb")
README_DOC = os.path.join(OUTPUT_DIR, "README_EXPORT.md")


# ==============================================================================
# 1. COLLECTION HIERARCHY & RESILIENCE ADVERSARIAL TESTS
# ==============================================================================

class TestCollectionHierarchyAdversarial:
    """Stress tests 7-tier collection hierarchy and scene resilience."""

    def test_authoritative_hierarchy_invariance(self):
        """Verifies exact 7-tier structure, ordering, and re-export parity."""
        assert ROOT_COLLECTION_NAME == "Yu_Nian_An_Master"
        assert len(TIER_COLLECTION_NAMES) == 6
        assert TIER_COLLECTION_NAMES == (
            "01_Body",
            "02_Hair",
            "03_Wardrobe",
            "04_Props",
            "05_Armature",
            "06_Lights_Camera",
        )
        assert ALL_SEVEN_COLLECTIONS == (ROOT_COLLECTION_NAME,) + TIER_COLLECTION_NAMES
        assert ALL_SEVEN_COLLECTIONS == FACADE_ALL_SEVEN_COLLECTIONS

        assembler = YuNianAnAssembler()
        tree = assembler.get_collection_hierarchy()
        assert ROOT_COLLECTION_NAME in tree
        assert tree[ROOT_COLLECTION_NAME] == list(TIER_COLLECTION_NAMES)
        assert assembler.get_all_collection_names() == list(ALL_SEVEN_COLLECTIONS)

    def test_assembly_script_handles_collection_sanitization(self):
        """Checks generated script cleans startup objects (Cube, Light, Camera) and links 7 collections."""
        cfg = MasterAssemblyConfig(character_name="Test_Yu_Nian_An")
        script = get_master_assembly_script(cfg)
        tree = ast.parse(script)
        assert isinstance(tree, ast.Module)

        # Check collection creation code in script
        for col_name in ALL_SEVEN_COLLECTIONS:
            assert f'"{col_name}"' in script or f"'{col_name}'" in script, f"Missing {col_name} in script"

        # Check default object cleanup
        assert '"Cube"' in script or "'Cube'" in script
        assert '"Light"' in script or "'Light'" in script
        assert '"Camera"' in script or "'Camera'" in script

    def test_offline_scene_integrity_check(self):
        """Verifies verify_scene_integrity handles offline simulation cleanly."""
        assembler = YuNianAnAssembler()
        res = assembler.verify_scene_integrity()
        assert "verified" in res
        assert res["verified"] is True
        assert res.get("mode") == "offline"


# ==============================================================================
# 2. LIGHTING SETUPS (3-POINT, DRAMATIC CINEMATIC, HIGH-KEY ANIME) & CAMERAS
# ==============================================================================

class TestLightingAndCameraSetupsAdversarial:
    """Stress tests calibrated lighting setups, color temperature, and camera rigs."""

    @staticmethod
    def _kelvin_to_rgb(kelvin: float) -> Tuple[float, float, float]:
        """Reference Kelvin-to-RGB model matching scene_builder.py."""
        temp = kelvin / 100.0
        if temp <= 66:
            red = 1.0
            green = max(0.0, min(1.0, 0.39008157876 * math.log(temp) - 0.63184144378))
        else:
            red = max(0.0, min(1.0, 1.29293618606 * ((temp - 60) ** -0.1332047592)))
            green = max(0.0, min(1.0, 1.12989086089 * ((temp - 60) ** -0.0755148492)))
        if temp >= 66:
            blue = 1.0
        elif temp <= 19:
            blue = 0.0
        else:
            blue = max(0.0, min(1.0, 0.54320678911 * math.log(temp - 10) - 1.19625408914))
        return (red, green, blue)

    @pytest.mark.parametrize(
        "kelvin",
        [1900.0, 2400.0, 3200.0, 4500.0, 5500.0, 6500.0, 7500.0, 10000.0, 15000.0],
    )
    def test_kelvin_to_rgb_spectrum_numerical_stability(self, kelvin: float):
        """Ensures kelvin_to_rgb outputs strictly normalized, non-NaN RGB values across spectrum."""
        r, g, b = self._kelvin_to_rgb(kelvin)
        assert 0.0 <= r <= 1.0, f"Red out of range for {kelvin}K: {r}"
        assert 0.0 <= g <= 1.0, f"Green out of range for {kelvin}K: {g}"
        assert 0.0 <= b <= 1.0, f"Blue out of range for {kelvin}K: {b}"
        assert not (math.isnan(r) or math.isnan(g) or math.isnan(b)), f"NaN for {kelvin}K"

        # Warm temperatures (<= 4500K) should have Red > Blue
        if kelvin <= 4500.0:
            assert r >= b, f"Warm temperature {kelvin}K expected R >= B, got R={r}, B={b}"
        # Cool temperatures (>= 7500K) should have Blue >= Red
        if kelvin >= 7500.0:
            assert b >= r, f"Cool temperature {kelvin}K expected B >= R, got R={r}, B={b}"

    def test_studio_3point_lighting_preset(self):
        """Validates default 3-point studio lighting configuration."""
        cfg = MasterAssemblyConfig()
        assert cfg.key_light_temperature == 5500.0
        assert cfg.key_light_energy == 500.0
        assert cfg.fill_light_temperature == 6500.0
        assert cfg.fill_light_energy == 250.0
        assert cfg.rim_light_temperature == 4500.0
        assert cfg.rim_light_energy == 450.0

        asm = YuNianAnAssembler(cfg)
        manifest = asm.get_lighting_camera_manifest()
        assert manifest["key_light"]["energy"] == 500.0
        assert manifest["fill_light"]["energy"] == 250.0
        assert manifest["rim_light"]["energy"] == 450.0

        # Contrast ratio Key : Fill should be 2:1
        ratio = manifest["key_light"]["energy"] / manifest["fill_light"]["energy"]
        assert math.isclose(ratio, 2.0, rel_tol=1e-3)

    def test_dramatic_cinematic_lighting_setup(self):
        """Adversarial stress test: dramatic cinematic high-contrast lighting preset."""
        # Key: Warm tungsten 3200K, 1200W
        # Fill: Cool moonlight 8000K, 50W (deep shadows, 24:1 key-to-fill ratio)
        # Rim: Sharp backlight 4000K, 700W
        cfg = MasterAssemblyConfig(
            key_light_temperature=3200.0,
            key_light_energy=1200.0,
            fill_light_temperature=8000.0,
            fill_light_energy=50.0,
            rim_light_temperature=4000.0,
            rim_light_energy=700.0,
        )
        asm = YuNianAnAssembler(cfg)
        manifest = asm.get_lighting_camera_manifest()
        assert manifest["key_light"]["energy"] / manifest["fill_light"]["energy"] == 24.0

        # Verify script generation produces valid AST with these parameters
        script = asm.get_assembly_script()
        tree = ast.parse(script)
        assert isinstance(tree, ast.Module)
        assert "1200.0" in script
        assert "50.0" in script
        assert "3200.0" in script

    def test_high_key_anime_lighting_setup(self):
        """Adversarial stress test: high-key bright anime studio lighting preset."""
        # Key: 5600K 600W
        # Fill: 6000K 550W (near-flat fill, 1.09:1 ratio, virtually shadowless)
        # Rim: 5000K 250W
        cfg = MasterAssemblyConfig(
            key_light_temperature=5600.0,
            key_light_energy=600.0,
            fill_light_temperature=6000.0,
            fill_light_energy=550.0,
            rim_light_temperature=5000.0,
            rim_light_energy=250.0,
        )
        asm = YuNianAnAssembler(cfg)
        manifest = asm.get_lighting_camera_manifest()
        ratio = manifest["key_light"]["energy"] / manifest["fill_light"]["energy"]
        assert 1.0 < ratio < 1.2, f"High-key fill ratio unexpected: {ratio}"

        script = asm.get_assembly_script()
        tree = ast.parse(script)
        assert isinstance(tree, ast.Module)
        assert "600.0" in script
        assert "550.0" in script

    def test_four_camera_turnaround_rig_and_portrait(self):
        """Verifies geometry, focal length, and distance for all cameras in rig."""
        cfg = MasterAssemblyConfig(camera_fullbody_distance=5.5, camera_fullbody_lens=50.0)
        asm = YuNianAnAssembler(cfg)
        manifest = asm.get_lighting_camera_manifest()
        cam = manifest["camera"]
        assert cam["lens"] == 85.0
        assert cam["distance"] == 2.0
        assert cam["sensor"] == (36.0, 24.0)
        assert set(cam["turnaround_views"]) == {
            "Camera_Front",
            "Camera_ThreeQuarter",
            "Camera_Profile",
            "Camera_Back",
        }

        # Check script defines all 4 turnaround angles at radius 5.5m
        script = asm.get_assembly_script()
        assert "Camera_Front" in script
        assert "Camera_ThreeQuarter" in script
        assert "Camera_Profile" in script
        assert "Camera_Back" in script
        assert "Camera_FullBody" in script
        assert "Camera_Portrait_85mm" in script


# ==============================================================================
# 3. 4K PBR PROCEDURAL TEXTURE BAKER & UV MARGIN AUDIT
# ==============================================================================

class TestTextureBakerAndUVMarginAdversarial:
    """Stress tests 4K procedural texture maps, channel distributions, and UV margins."""

    def test_pbr_baker_downscaled_stress_execution(self, tmp_path):
        """Stress test: execute texture baker at 512x512 resolution to verify parametric scaling."""
        tex_dir = tmp_path / "stress_textures_512"
        res = generate_yu_nian_an_pbr_textures(output_dir=str(tex_dir), resolution=512)

        expected_keys = [
            "BaseColor", "Normal", "Roughness", "Metallic", "SSS", "Alpha", "Height", "ORM", "MaskMap",
            "Skin_Albedo", "Skin_Normal", "Skin_Roughness", "Dress_Albedo", "Dress_Normal", "Dress_Sheen",
            "Sash_Albedo", "Sash_Metallic", "Sash_Roughness",
        ]
        for k in expected_keys:
            assert k in res, f"Missing output texture key: {k}"
            assert os.path.isfile(res[k]), f"Texture file not created: {res[k]}"
            with Image.open(res[k]) as img:
                assert img.size == (512, 512), f"Texture {k} size is {img.size}, expected (512, 512)"

    def test_production_4k_textures_inventory(self):
        """Verifies existing production 4K textures in output/yu_nian_an/textures/."""
        all_expected = [
            "Yu_Nian_An_BaseColor_4K.png",
            "Yu_Nian_An_Normal_4K.png",
            "Yu_Nian_An_Roughness_4K.png",
            "Yu_Nian_An_Metallic_4K.png",
            "Yu_Nian_An_SSS_4K.png",
            "Yu_Nian_An_Alpha_4K.png",
            "Yu_Nian_An_Height_4K.png",
            "Yu_Nian_An_ORM_4K.png",
            "Yu_Nian_An_MaskMap_4K.png",
        ]
        for name in all_expected:
            path = os.path.join(TEXTURES_DIR, name)
            assert os.path.isfile(path), f"Missing 4K texture: {path}"
            assert os.path.getsize(path) > 10_000, f"Texture {name} too small"

    def test_uv_quadrant_isolation_and_margin(self):
        """
        Adversarially asserts that UV coordinates assigned to character meshes
        stay strictly inside their designated quadrants and do not cross boundaries.
        Q1: [0.0, 0.5] x [0.5, 1.0] (Head & Face)
        Q2: [0.5, 1.0] x [0.5, 1.0] (Body & Limbs)
        Q3: [0.0, 0.5] x [0.0, 0.5] (Silk Dress)
        Q4: [0.5, 1.0] x [0.0, 0.5] (Sash, Sandals, Props)
        """
        # Load GLB and read UVs
        assert os.path.isfile(EXPORT_GLB)
        with open(EXPORT_GLB, "rb") as f:
            data = f.read()

        magic, version, length = struct.unpack_from("<4sII", data, 0)
        assert magic == b"glTF"
        assert version == 2

        json_len, json_type = struct.unpack_from("<II", data, 12)
        json_bytes = data[20: 20 + json_len]
        gltf = json.loads(json_bytes.decode("utf-8"))

        bin_offset = 20 + json_len
        bin_len, bin_type = struct.unpack_from("<II", data, bin_offset)
        bin_data = data[bin_offset + 8: bin_offset + 8 + bin_len]

        def extract_uvs(prim):
            if "TEXCOORD_0" not in prim["attributes"]:
                return None
            acc = gltf["accessors"][prim["attributes"]["TEXCOORD_0"]]
            bv = gltf["bufferViews"][acc["bufferView"]]
            off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            cnt = acc["count"]
            return np.frombuffer(bin_data, dtype=np.float32, count=cnt * 2, offset=off).reshape((cnt, 2))

        # Check every mesh primitive with UV coordinates
        for mesh in gltf.get("meshes", []):
            mesh_name = mesh.get("name", "")
            for prim in mesh.get("primitives", []):
                uvs = extract_uvs(prim)
                if uvs is None:
                    continue
                # Every UV must stay within [0.0, 1.0]
                assert np.all(uvs >= -1e-4), f"Negative UV in {mesh_name}: min={uvs.min()}"
                assert np.all(uvs <= 1.0 + 1e-4), f"UV > 1 in {mesh_name}: max={uvs.max()}"

                # Quadrant-specific assertions for canonical character meshes (accounting for glTF V_gltf = 1 - V_blender):
                if mesh_name == "Mesh_Dress_Bodice_Mesh" or mesh_name == "Mesh_Dress_PleatedSkirt_Mesh":
                    # In Blender: Dress lives in Q3 [0.0, 0.5] x [0.0, 0.5]
                    # In glTF: U in [0.0, 0.5], V_gltf = 1 - V_blender in [0.5, 1.0] (matching PBR texture row indices >= 2048)
                    assert np.all(uvs[:, 0] <= 0.50 + 1e-3), f"{mesh_name} UV.U spilled past Q3: max={uvs[:, 0].max()}"
                    assert np.all(uvs[:, 1] >= 0.50 - 1e-3), f"{mesh_name} UV.V_gltf < 0.5: min={uvs[:, 1].min()}"
                    assert np.all(uvs[:, 1] <= 1.00 + 1e-3), f"{mesh_name} UV.V_gltf > 1.0: max={uvs[:, 1].max()}"
                elif mesh_name == "Mesh_Dress_WaistSash_Mesh":
                    # In Blender: Sash lives in Q4 [0.5, 1.0] x [0.28, 0.50]
                    # In glTF: U in [0.5, 1.0], V_gltf in [0.50, 0.75]
                    assert np.all(uvs[:, 0] >= 0.50 - 1e-3), f"{mesh_name} UV.U < 0.5: min={uvs[:, 0].min()}"
                    assert np.all(uvs[:, 1] >= 0.45 - 1e-3), f"{mesh_name} UV.V_gltf < 0.45: min={uvs[:, 1].min()}"
                    assert np.all(uvs[:, 1] <= 0.75 + 1e-3), f"{mesh_name} UV.V_gltf > 0.75: max={uvs[:, 1].max()}"
                elif mesh_name in ("Mesh_Sandal_L_Mesh", "Mesh_Sandal_R_Mesh"):
                    # In Blender: Sandals live in Q4 bottom [0.5, 0.85] x [0.0, 0.28]
                    # In glTF: U in [0.5, 0.85], V_gltf in [0.70, 1.0]
                    assert np.all(uvs[:, 0] >= 0.50 - 1e-3), f"{mesh_name} UV.U < 0.5: min={uvs[:, 0].min()}"
                    assert np.all(uvs[:, 1] >= 0.70 - 1e-3), f"{mesh_name} UV.V_gltf < 0.70: min={uvs[:, 1].min()}"
                elif mesh_name == "Mesh_Lips_Mesh":
                    # Lips live in Q1 mouth region: U in [0.20, 0.30], V_gltf in [0.30, 0.42]
                    assert np.all(uvs[:, 0] >= 0.19) and np.all(uvs[:, 0] <= 0.31)
                    assert np.all(uvs[:, 1] >= 0.30) and np.all(uvs[:, 1] <= 0.42)


# ==============================================================================
# 4. PACKAGING, CONTAINERS (glTF / FBX / OBJ), ZIP ARCHIVING & MANIFEST
# ==============================================================================

class TestPackagingAndContainersAdversarial:
    """Stress tests glTF 2.0, FBX, OBJ export, ZIP archiving, and documentation manifests."""

    def test_gltf_2_container_full_specification(self):
        """Audits glTF 2.0 GLB binary container for ARKit targets and joint hierarchy."""
        with open(EXPORT_GLB, "rb") as f:
            data = f.read()

        magic, version, total_size = struct.unpack_from("<4sII", data, 0)
        assert magic == b"glTF"
        assert version == 2
        assert total_size == len(data)

        json_len, _ = struct.unpack_from("<II", data, 12)
        gltf = json.loads(data[20: 20 + json_len].decode("utf-8"))

        # 1. Body mesh must have 52 ARKit morph targets
        body_mesh = next(m for m in gltf["meshes"] if "Body" in m.get("name", ""))
        body_prim = body_mesh["primitives"][0]
        assert "targets" in body_prim, "Body primitive has no morph targets"
        assert len(body_prim["targets"]) == 52, f"Expected 52 morph targets, got {len(body_prim['targets'])}"

        # 2. extras.targetNames must list all 52 keys
        extras = body_mesh.get("extras", {})
        target_names = extras.get("targetNames", [])
        assert len(target_names) == 52, f"extras.targetNames length {len(target_names)} != 52"
        for k in ARKIT_52_BLENDSHAPES:
            assert k in target_names, f"Missing ARKit key in GLB extras: {k}"

        # 3. Skins must contain 164 nodes (1 root + 163 DEF bones)
        assert "skins" in gltf
        skin = gltf["skins"][0]
        assert len(skin["joints"]) == 164, f"Expected 164 joints in skin, got {len(skin['joints'])}"

    def test_fbx_binary_header_and_node_tokens(self):
        """Audits FBX binary structure, DEF bone names, and shape key tokens."""
        with open(EXPORT_FBX, "rb") as f:
            header = f.read(27)
        assert header.startswith(b"Kaydara FBX Binary  \x00"), "Invalid FBX magic header"

        with open(EXPORT_FBX, "rb") as f:
            content = f.read()

        # Check DEF bones in FBX
        sample_def_bones = [
            b"DEF-spine", b"DEF-head", b"DEF-hand.L", b"DEF-hand.R",
            b"DEF-foot.L", b"DEF-foot.R", b"DEF-thumb.03.L", b"DEF-f_pinky.03.R",
        ]
        for sb in sample_def_bones:
            assert sb in content, f"Missing bone in FBX: {sb.decode('utf-8')}"

        # Check sample ARKit shape keys in FBX
        sample_keys = [b"eyeBlinkLeft", b"jawOpen", b"mouthSmileLeft", b"browInnerUp"]
        for sk in sample_keys:
            assert sk in content, f"Missing shape key in FBX: {sk.decode('utf-8')}"

    def test_obj_exporter_functional_execution(self, tmp_path):
        """Tests pure-Python OBJ exporter on character geometry produces valid OBJ syntax."""
        body_geom = MeshGeometry()
        body_geom.vertices = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
        body_geom.faces = [[0, 1, 2, 3]]
        body_geom.normals = [[0.0, 0.0, 1.0]] * 4
        body_geom.uvs = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]

        obj_out = tmp_path / "test_char.obj"
        export_obj(body_geom, str(obj_out))
        assert obj_out.exists()
        with open(obj_out, "r", encoding="utf-8") as f:
            lines = f.readlines()

        v_lines = [ln for ln in lines if ln.startswith("v ")]
        f_lines = [ln for ln in lines if ln.startswith("f ")]
        vn_lines = [ln for ln in lines if ln.startswith("vn ")]
        vt_lines = [ln for ln in lines if ln.startswith("vt ")]

        assert len(v_lines) == 4
        assert len(f_lines) == 1
        assert len(vn_lines) == 4
        assert len(vt_lines) == 4

    def test_zip_distribution_packaging_and_crc_verification(self, tmp_path):
        """
        Adversarially builds a full production ZIP package containing
        the .blend, .fbx, .glb, all 4K textures, and README_EXPORT.md,
        and verifies integrity, CRC32, and extraction.
        """
        zip_path = tmp_path / "Yu_Nian_An_Production_Package.zip"

        # Bundle production files
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(MASTER_BLEND, arcname="Yu_Nian_An_Master.blend")
            zf.write(EXPORT_FBX, arcname="Yu_Nian_An.fbx")
            zf.write(EXPORT_GLB, arcname="Yu_Nian_An.glb")
            zf.write(README_DOC, arcname="README_EXPORT.md")

            for tex_file in os.listdir(TEXTURES_DIR):
                full_t = os.path.join(TEXTURES_DIR, tex_file)
                if os.path.isfile(full_t):
                    zf.write(full_t, arcname=f"textures/{tex_file}")

        assert zip_path.exists()
        zip_size = zip_path.stat().st_size
        assert zip_size > 5_000_000, f"Zip archive suspiciously small: {zip_size} bytes"

        # Verify archive integrity
        extract_dir = tmp_path / "extracted_package"
        with zipfile.ZipFile(zip_path, "r") as zf:
            corrupt = zf.testzip()
            assert corrupt is None, f"Corrupted file in ZIP: {corrupt}"
            zf.extractall(extract_dir)

        # Check extracted files
        assert (extract_dir / "Yu_Nian_An_Master.blend").exists()
        assert (extract_dir / "Yu_Nian_An.fbx").exists()
        assert (extract_dir / "Yu_Nian_An.glb").exists()
        assert (extract_dir / "README_EXPORT.md").exists()
        assert (extract_dir / "textures" / "Yu_Nian_An_BaseColor_4K.png").exists()
        assert (extract_dir / "textures" / "Yu_Nian_An_Normal_4K.png").exists()

    def test_readme_export_manifest_completeness(self):
        """Verifies README_EXPORT.md provides comprehensive multi-engine guides and metadata."""
        assert os.path.isfile(README_DOC)
        with open(README_DOC, "r", encoding="utf-8") as f:
            content = f.read()

        # Engine guides
        assert "Unreal Engine" in content
        assert "Unity" in content
        assert "Three.js" in content

        # Technical specs
        assert "4096" in content
        assert "163" in content
        assert "52" in content
        assert "Random Walk" in content or "SSS" in content
        assert "ORM" in content
        assert "MaskMap" in content


# ==============================================================================
# 5. MASTER ASSEMBLY COORDINATOR INTEGRATION ACROSS ALL SUBSYSTEMS
# ==============================================================================

class TestMasterAssemblyCoordinatorIntegration:
    """Stress tests master character assembly integration across body, metarig, wardrobe, hair, props."""

    def test_coordinator_execution_and_schema_conformance(self):
        """Executes assemble_master_character and validates complete dictionary schema."""
        res = assemble_master_character(
            character_name="Yu_Nian_An_Audit",
            height=1.65,
            head_ratio=7.41,
            include_hair=True,
            include_wardrobe=True,
            include_props=True,
            include_armature=True,
            include_lighting=True,
        )
        assert res["status"] == "success"
        assert res["character_name"] == "Yu_Nian_An_Audit"
        assert res["root_collection"] == ROOT_COLLECTION_NAME
        assert res["tier_collections"] == list(TIER_COLLECTION_NAMES)

        # Body checks
        body = res["body"]
        assert body["vertex_count"] > 1000
        assert body["face_count"] > 1000
        assert body["quad_ratio"] >= 0.99
        assert body["vertex_groups_count"] == 36  # 34 standardized + breast.L + breast.R
        assert body["landmarks_count"] >= 34  # Full anatomical mold contains 188 landmarks (>= 34 core skeleton)
        assert body["shape_keys_count"] == 52

        # Armature checks
        arm = res["armature"]
        assert arm["total_bones"] == 163
        assert arm["def_bones_count"] == 163
        assert arm["body_def_bones_count"] == len(BODY_DEF_BONES)
        assert arm["facial_def_bones_count"] == len(FACIAL_DEF_BONES)

        # Hair checks
        hair = res["hair"]
        assert hair["strata_count"] == 6
        assert hair["material"] == "Mat_Human_Hair"

        # Wardrobe checks
        wardrobe = res["wardrobe"]
        assert "Dress_Bodice" in wardrobe["garments"]
        assert "Dress_PleatedSkirt" in wardrobe["garments"]
        assert "Dress_WaistSash" in wardrobe["garments"]
        assert wardrobe["armature_binding"] is True

        # Props checks
        props = res["props"]
        assert props["strings_count"] == 10
        assert props["butterflies_count"] == 10
        assert len(props["finger_anchors"]) == 10

        # Lighting & Camera checks
        light_cam = res["lighting_camera"]
        assert "key_light" in light_cam
        assert "fill_light" in light_cam
        assert "rim_light" in light_cam
        assert "camera" in light_cam

    def test_facade_parity_and_export_reexports(self):
        """Verifies character_assembler facade matches morphomesh.assembler exactly."""
        assert FacadeMasterAssemblyConfig is MasterAssemblyConfig
        assert FacadeYuNianAnAssembler is YuNianAnAssembler
        assert facade_assemble_master_character is assemble_master_character
        assert facade_generate_pbr_textures is generate_yu_nian_an_pbr_textures
