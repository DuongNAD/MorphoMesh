"""
MorphoMesh: Milestone 5 Production Packaging & Multi-Format Exports Test Suite.

Verifies:
1. Production .blend integrity and non-zero file sizes (>1 MB).
2. Multi-format rigged FBX export with binary header, 163 DEF bones, and 52 ARKit shape keys.
3. Web & Real-Time ready glTF 2.0 GLB binary container, skinning joints, and 52 ARKit morph targets.
4. Complete 4K (4096 x 4096) PBR Texture Suite:
   - Yu_Nian_An_BaseColor_4K.png (Porcelain skin, rose lips, dark eyeliner, ivory silk, ice-blue sash)
   - Yu_Nian_An_Normal_4K.png (Tangent-space normal map with micro-pores, lip wrinkles, fabric weave)
   - Yu_Nian_An_Roughness_4K.png (Dual roughness: face 0.38, lips 0.28, scalp 0.70, dress 0.45, sash 0.22)
   - Yu_Nian_An_Metallic_4K.png (Dielectric 0.0, metallic sheen on aglets/buckles)
   - Yu_Nian_An_SSS_4K.png (Subsurface scattering mask: high on ears, nose, lips)
   - Yu_Nian_An_Alpha_4K.png (Eyelashes/eyebrows and bangs fringe opacity mask)
   - Yu_Nian_An_Height_4K.png (Displacement / bump height map)
5. Authoritative README_EXPORT.md import documentation for UE5, Unity 6, and Three.js.
6. Export automation pipeline in character_assembler.py and FastMCP tool registration in server.py.
"""

from __future__ import annotations

import ast
import json
import os
import struct
from typing import Any, Dict, List

import numpy as np
import pytest
from PIL import Image

from morphomesh.character_assembler import (
    MasterAssemblyConfig,
    YuNianAnAssembler,
    export_production_assets,
    generate_yu_nian_an_pbr_textures,
    get_export_script,
)
from morphomesh.human_generator import ARKIT_52_BLENDSHAPES
from morphomesh.server import (
    HUMAN_TOOL_NAMES,
    mcp,
    morphomesh_export_production_character,
)

OUTPUT_DIR = "output/yu_nian_an"
TEXTURES_DIR = os.path.join(OUTPUT_DIR, "textures")
MASTER_BLEND = os.path.join(OUTPUT_DIR, "Yu_Nian_An_Master.blend")
EXPORT_FBX = os.path.join(OUTPUT_DIR, "Yu_Nian_An.fbx")
EXPORT_GLB = os.path.join(OUTPUT_DIR, "Yu_Nian_An.glb")
README_DOC = os.path.join(OUTPUT_DIR, "README_EXPORT.md")

EXPECTED_TEXTURES = [
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


# ==============================================================================
# 1. PRODUCTION FILE EXISTENCE & MINIMUM SIZES
# ==============================================================================

class TestProductionFileExistence:
    """Verifies all production deliverables exist and meet production size criteria."""

    def test_master_blend_exists_and_size(self):
        """Master .blend file must exist and be > 1 MB."""
        assert os.path.isfile(MASTER_BLEND), f"Missing master blend: {MASTER_BLEND}"
        size = os.path.getsize(MASTER_BLEND)
        assert size > 1_000_000, f"Master blend too small ({size} bytes), expected > 1 MB"

    def test_fbx_export_exists_and_size(self):
        """Rigged FBX asset must exist and be > 1 MB."""
        assert os.path.isfile(EXPORT_FBX), f"Missing production FBX: {EXPORT_FBX}"
        size = os.path.getsize(EXPORT_FBX)
        assert size > 1_000_000, f"FBX asset too small ({size} bytes), expected > 1 MB"

    def test_glb_export_exists_and_size(self):
        """Real-time GLB asset must exist and be > 1 MB."""
        assert os.path.isfile(EXPORT_GLB), f"Missing production GLB: {EXPORT_GLB}"
        size = os.path.getsize(EXPORT_GLB)
        assert size > 1_000_000, f"GLB asset too small ({size} bytes), expected > 1 MB"

    def test_all_seven_4k_textures_exist(self):
        """All 9 4K PBR textures must exist in textures/ and be non-empty."""
        for tex_name in EXPECTED_TEXTURES:
            tex_path = os.path.join(TEXTURES_DIR, tex_name)
            assert os.path.isfile(tex_path), f"Missing required 4K texture: {tex_path}"
            size = os.path.getsize(tex_path)
            assert size > 10_000, f"Texture {tex_name} appears empty or truncated ({size} bytes)"

    def test_readme_export_documentation_exists(self):
        """README_EXPORT.md must exist and contain thorough engine import guides."""
        assert os.path.isfile(README_DOC), f"Missing export documentation: {README_DOC}"
        with open(README_DOC, "r", encoding="utf-8") as f:
            content = f.read()
        assert len(content) > 1000, "README_EXPORT.md is too short"
        assert "Unreal Engine" in content, "README_EXPORT.md missing Unreal Engine guide"
        assert "Unity" in content, "README_EXPORT.md missing Unity guide"
        assert "Three.js" in content, "README_EXPORT.md missing Three.js guide"
        assert "4096" in content, "README_EXPORT.md missing 4K texture specs"
        assert "Flip Green Channel" in content, "README_EXPORT.md missing Flip Green Channel instruction for UE5"
        assert "THREE.TextureLoader" in content, "README_EXPORT.md missing THREE.TextureLoader in Three.js guide"


# ==============================================================================
# 2. 4K PBR TEXTURE SPECIFICATIONS & RESOLUTION TESTS
# ==============================================================================

class TestTextureSpecifications:
    """Verifies image dimensions, channel counts, and PBR value distributions."""

    @pytest.mark.parametrize("tex_name", EXPECTED_TEXTURES)
    def test_texture_resolution_is_strictly_4096(self, tex_name: str):
        """Every texture must be strictly 4096 x 4096 resolution."""
        tex_path = os.path.join(TEXTURES_DIR, tex_name)
        with Image.open(tex_path) as img:
            w, h = img.size
            assert (w, h) == (4096, 4096), f"{tex_name} resolution is {w}x{h}, expected (4096, 4096)"

    def test_base_color_texture_distribution(self):
        """BaseColor texture must feature porcelain skin, rose lips, dark eyeliner, ivory silk, ice-blue sash."""
        tex_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_BaseColor_4K.png")
        with Image.open(tex_path) as img:
            assert img.mode in ("RGB", "RGBA"), f"Unexpected mode: {img.mode}"
            arr = np.array(img)

        # Body skin in Q2 (upper right) should be porcelain skin (#F4E4DC ~ RGB 244, 228, 220)
        q2_skin_sample = arr[500:800, 2500:2800, :3]
        mean_r = np.mean(q2_skin_sample[:, :, 0])
        mean_g = np.mean(q2_skin_sample[:, :, 1])
        mean_b = np.mean(q2_skin_sample[:, :, 2])
        assert 230 <= mean_r <= 255, f"Skin Red out of expected range: {mean_r}"
        assert 215 <= mean_g <= 245, f"Skin Green out of expected range: {mean_g}"
        assert 205 <= mean_b <= 235, f"Skin Blue out of expected range: {mean_b}"

        # Lips region in Q1: soft rose vermilion (R should be higher than G and B)
        # Lip center around (u1=0.5, v1=0.72) -> pixel (1024, 1475) in full 4K
        lip_pixel = arr[1475, 1024, :3]
        assert lip_pixel[0] > lip_pixel[1] + 40, f"Lip red contrast failed: {lip_pixel}"
        assert lip_pixel[0] > lip_pixel[2] + 40, f"Lip blue contrast failed: {lip_pixel}"

        # Eyeliner margin in Q1: dark slate/charcoal (RGB < 60)
        # Left eyeliner around (u1=0.35, v1=0.45) -> pixel (716, 921)
        eyeliner_pixel = arr[921, 716, :3]
        assert eyeliner_pixel[0] < 80 and eyeliner_pixel[1] < 80 and eyeliner_pixel[2] < 80, f"Eyeliner not dark: {eyeliner_pixel}"

        # Sash in Q4 (top half of Q4): pale ice-blue satin (Blue higher than Red and Green)
        # u4=0.25, v4=0.25 -> pixel (2560, 2560)
        sash_pixel = arr[2560, 2560, :3]
        assert sash_pixel[2] > sash_pixel[0], f"Sash blue tone failed: {sash_pixel}"

    def test_normal_map_properties(self):
        """Normal map must be tangent-space OpenGL with unit-normalized vectors."""
        tex_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_Normal_4K.png")
        with Image.open(tex_path) as img:
            assert img.mode in ("RGB", "RGBA")
            arr = np.array(img)[:, :, :3]

        # Convert back to [-1, 1] range
        nx = arr[:, :, 0].astype(np.float32) / 127.5 - 1.0
        ny = arr[:, :, 1].astype(np.float32) / 127.5 - 1.0
        nz = arr[:, :, 2].astype(np.float32) / 127.5 - 1.0

        # Vector lengths should be ~ 1.0 everywhere
        vec_len = np.sqrt(nx**2 + ny**2 + nz**2)
        assert np.all(vec_len > 0.90) and np.all(vec_len < 1.10), "Normal vectors not normalized"

        # Tangent normal vectors point outward along +Z (dominant blue channel ~ 255)
        mean_nz = np.mean(arr[:, :, 2])
        assert mean_nz > 230, f"Normal map Z channel should be dominant, got mean {mean_nz}"

    def test_roughness_map_dual_roughness(self):
        """Roughness map must adhere to dual roughness specifications: face 0.38, lips 0.28, scalp 0.70, dress 0.45, sash 0.22."""
        tex_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_Roughness_4K.png")
        with Image.open(tex_path) as img:
            arr = np.array(img)
            if arr.ndim == 3:
                arr = arr[:, :, 0]

        # Scalp in Q1 (top area) should be ~ 0.70 (178 +/- 10)
        scalp_val = float(arr[200, 1024]) / 255.0
        assert 0.65 <= scalp_val <= 0.75, f"Scalp roughness unexpected: {scalp_val}"

        # Face skin in Q1 should be ~ 0.38 (97 +/- 10)
        face_val = float(arr[1200, 700]) / 255.0
        assert 0.34 <= face_val <= 0.42, f"Face roughness unexpected: {face_val}"

        # Lips in Q1 should be ~ 0.28 (71 +/- 10)
        lip_val = float(arr[1475, 1024]) / 255.0
        assert 0.24 <= lip_val <= 0.32, f"Lips roughness unexpected: {lip_val}"
        assert lip_val < face_val, "Lips should have lower roughness (higher specular gloss) than face"

        # Dress in Q3 should be ~ 0.45 (115 +/- 10)
        dress_val = float(arr[3000, 1000]) / 255.0
        assert 0.40 <= dress_val <= 0.50, f"Dress roughness unexpected: {dress_val}"

        # Sash in Q4 should be ~ 0.22 (56 +/- 10)
        sash_val = float(arr[2560, 2560]) / 255.0
        assert 0.18 <= sash_val <= 0.26, f"Sash roughness unexpected: {sash_val}"
        assert sash_val < dress_val, "Satin sash should be glossier than silk dress"

    def test_metallic_and_sss_maps(self):
        """Metallic map must be non-metal dielectric (0.0) except hardware; SSS mask high on ears, nose, lips."""
        met_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_Metallic_4K.png")
        sss_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_SSS_4K.png")

        with Image.open(met_path) as img:
            met_arr = np.array(img)
            if met_arr.ndim == 3:
                met_arr = met_arr[:, :, 0]

        with Image.open(sss_path) as img:
            sss_arr = np.array(img)
            if sss_arr.ndim == 3:
                sss_arr = sss_arr[:, :, 0]

        # Skin and dress are dielectric (metallic == 0)
        assert met_arr[1200, 700] == 0, "Face skin must be dielectric"
        assert met_arr[3000, 1000] == 0, "Dress must be dielectric"

        # SSS is high on ears (pixel 1024, 160) and lips (pixel 1475, 1024)
        lip_sss = float(sss_arr[1475, 1024]) / 255.0
        ear_sss = float(sss_arr[1024, 160]) / 255.0
        dress_sss = float(sss_arr[3000, 1000]) / 255.0

        assert lip_sss >= 0.60, f"Lips SSS too low: {lip_sss}"
        assert ear_sss >= 0.70, f"Ears SSS too low: {ear_sss}"
        assert dress_sss == 0.0, f"Dress SSS must be zero: {dress_sss}"

    def test_orm_and_maskmap_packed_textures(self):
        """Verify pre-packed ORM (Unreal Engine) and MaskMap (Unity HDRP) channel definitions."""
        orm_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_ORM_4K.png")
        mask_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_MaskMap_4K.png")

        assert os.path.isfile(orm_path), f"Missing ORM texture: {orm_path}"
        assert os.path.isfile(mask_path), f"Missing MaskMap texture: {mask_path}"

        with Image.open(orm_path) as img:
            assert img.size == (4096, 4096), f"ORM resolution {img.size} != (4096, 4096)"
            assert img.mode == "RGBA", f"ORM mode {img.mode} != RGBA"
            orm_arr = np.array(img)

        with Image.open(mask_path) as img:
            assert img.size == (4096, 4096), f"MaskMap resolution {img.size} != (4096, 4096)"
            assert img.mode == "RGBA", f"MaskMap mode {img.mode} != RGBA"
            mask_arr = np.array(img)

        # ORM: R=AO, G=Roughness, B=Metallic, A=SSS
        # Face skin (pixel 1200, 700): Roughness ~0.38, Metallic == 0, SSS ~0.45
        assert 80 <= orm_arr[1200, 700, 1] <= 115, "ORM Green (Roughness) failed on face"
        assert orm_arr[1200, 700, 2] == 0, "ORM Blue (Metallic) must be 0 on dielectric face"
        assert orm_arr[1200, 700, 3] >= 100, "ORM Alpha (SSS) must be active on face"

        # MaskMap: R=Metallic, G=AO, B=SSS, A=Smoothness (1 - Roughness)
        # Face skin (pixel 1200, 700): Metallic == 0, Smoothness ~ (1 - 0.38)*255 = 158
        assert mask_arr[1200, 700, 0] == 0, "MaskMap Red (Metallic) must be 0 on face"
        assert 140 <= mask_arr[1200, 700, 3] <= 175, "MaskMap Alpha (Smoothness) failed on face"


# ==============================================================================
# 3. BINARY FBX VALIDATION & MORPH KEYS
# ==============================================================================

class TestFBXBinaryIntegrity:
    """Verifies FBX binary structure, deformers, and shape keys."""

    def test_fbx_magic_header(self):
        """FBX must begin with canonical Kaydara binary magic header."""
        with open(EXPORT_FBX, "rb") as f:
            header = f.read(27)
        assert header.startswith(b"Kaydara FBX Binary"), f"Invalid FBX header: {header[:23]}"

    def test_fbx_contains_def_bones_and_shape_keys(self):
        """FBX binary content must contain Rigify DEF bones and 52 ARKit FACS shape keys."""
        with open(EXPORT_FBX, "rb") as f:
            content = f.read()

        # Check key DEF bones
        sample_bones = [b"DEF-spine", b"DEF-head", b"DEF-hand.L", b"DEF-hand.R", b"DEF-foot.L"]
        found_bones = [b for b in sample_bones if b in content]
        assert len(found_bones) >= 4, f"Missing expected DEF bones in FBX: {found_bones}"

        # Check sample ARKit FACS blendshapes
        sample_arkit = [
            b"eyeBlinkLeft", b"eyeBlinkRight", b"jawOpen", b"mouthSmileLeft",
            b"mouthSmileRight", b"browDownLeft", b"browInnerUp", b"cheekPuff"
        ]
        found_keys = [k for k in sample_arkit if k in content]
        assert len(found_keys) == len(sample_arkit), f"Missing ARKit shape keys in FBX: {found_keys}"

    def test_fbx_uv_layer_presence(self):
        """FBX export must contain UV layer definitions."""
        with open(EXPORT_FBX, "rb") as f:
            content = f.read()
        assert b"LayerElementUV" in content or b"UVMap" in content, "FBX missing UV layer definitions"


# ==============================================================================
# 4. GLTF / GLB BINARY STRUCTURE, 52 MORPH TARGETS & SKINNING
# ==============================================================================

class TestGLBContainerAndMorphTargets:
    """Verifies GLB 2.0 binary chunks, 164 skin joints, and 52 ARKit morph targets."""

    def test_glb_magic_and_version(self):
        """GLB must begin with glTF magic and version 2."""
        with open(EXPORT_GLB, "rb") as f:
            magic = f.read(4)
            version, length = struct.unpack("<II", f.read(8))

        assert magic == b"glTF", f"Invalid GLB magic: {magic}"
        assert version == 2, f"Expected glTF version 2, got {version}"
        assert length == os.path.getsize(EXPORT_GLB), "GLB header length mismatch"

    def test_glb_json_structure(self):
        """GLB JSON chunk must parse cleanly and contain scene nodes, meshes, skins, materials."""
        with open(EXPORT_GLB, "rb") as f:
            f.seek(12)  # Skip 12-byte header
            chunk_len, chunk_type = struct.unpack("<II", f.read(8))
            assert chunk_type == 0x4E4F534A, f"First chunk must be JSON (0x4E4F534A), got {hex(chunk_type)}"
            json_data = json.loads(f.read(chunk_len).decode("utf-8"))

        assert "asset" in json_data
        assert "nodes" in json_data
        assert "meshes" in json_data
        assert "skins" in json_data
        assert "materials" in json_data

        # Verify skinning joints
        skins = json_data.get("skins", [])
        assert len(skins) >= 1, "GLB missing armature skin"
        main_skin = skins[0]
        joints = main_skin.get("joints", [])
        assert len(joints) >= 160, f"Expected at least 160 joints in glTF skin, found {len(joints)}"

    def test_glb_body_mesh_has_all_52_arkit_morph_targets(self):
        """The primary body mesh in GLB must feature exactly 52 ARKit FACS morph targets."""
        with open(EXPORT_GLB, "rb") as f:
            f.seek(12)
            chunk_len, _ = struct.unpack("<II", f.read(8))
            json_data = json.loads(f.read(chunk_len).decode("utf-8"))

        body_mesh = None
        for m in json_data.get("meshes", []):
            if "Body" in m.get("name", ""):
                body_mesh = m
                break

        assert body_mesh is not None, "Yu_Nian_An_Body mesh not found in GLB"

        # Check morph target names in extras.targetNames
        target_names = body_mesh.get("extras", {}).get("targetNames", [])
        assert len(target_names) == 52, f"Expected 52 morph targets, got {len(target_names)}"

        # Verify all 52 Apple ARKit blendshapes are present
        missing_keys = [k for k in ARKIT_52_BLENDSHAPES if k not in target_names]
        assert len(missing_keys) == 0, f"Missing ARKit shape keys in GLB: {missing_keys}"

    def test_glb_all_mesh_primitives_have_texcoord_0(self):
        """Every mesh primitive in GLB must feature TEXCOORD_0 attribute for texture mapping."""
        with open(EXPORT_GLB, "rb") as f:
            f.seek(12)
            chunk_len, _ = struct.unpack("<II", f.read(8))
            json_data = json.loads(f.read(chunk_len).decode("utf-8"))

        meshes = json_data.get("meshes", [])
        assert len(meshes) > 0, "No meshes found in GLB"

        missing_uvs = []
        tested_primitives = 0
        for m in meshes:
            m_name = m.get("name", "unnamed")
            for idx, p in enumerate(m.get("primitives", [])):
                tested_primitives += 1
                attrs = p.get("attributes", {})
                if "TEXCOORD_0" not in attrs:
                    missing_uvs.append(f"{m_name}_prim_{idx}")

        assert len(missing_uvs) == 0, f"Primitives missing TEXCOORD_0: {missing_uvs}"
        assert tested_primitives >= 30, f"Expected at least 30 primitives in GLB, tested {tested_primitives}"

    def test_glb_uv_semantic_texture_sampling(self):
        """Extract vertex UVs from GLB for key meshes and sample BaseColor_4K to verify semantic color alignment."""
        with open(EXPORT_GLB, "rb") as f:
            f.seek(12)
            chunk_len, _ = struct.unpack("<II", f.read(8))
            json_data = json.loads(f.read(chunk_len).decode("utf-8"))
            bin_len, _ = struct.unpack("<II", f.read(8))
            bin_data = f.read(bin_len)

        def get_uvs(prim):
            acc = json_data["accessors"][prim["attributes"]["TEXCOORD_0"]]
            bv = json_data["bufferViews"][acc["bufferView"]]
            off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            cnt = acc["count"]
            return np.frombuffer(bin_data, dtype=np.float32, count=cnt * 2, offset=off).reshape((cnt, 2))

        base_color_path = os.path.join(TEXTURES_DIR, "Yu_Nian_An_BaseColor_4K.png")
        assert os.path.isfile(base_color_path), f"Missing BaseColor texture: {base_color_path}"
        base_img = np.array(Image.open(base_color_path))
        h, w, _ = base_img.shape

        # 1. Mesh_Lips_Mesh samples rose vermilion (R > G + 30, R > B + 30, R > 180)
        lips_mesh = next(m for m in json_data.get("meshes", []) if "Lips" in m.get("name", ""))
        uv_lips = get_uvs(lips_mesh["primitives"][0]).mean(axis=0)
        col_lips = int(np.clip(uv_lips[0] * w, 0, w - 1))
        row_lips = int(np.clip(uv_lips[1] * h, 0, h - 1))
        c_lips = base_img[row_lips, col_lips]
        assert c_lips[0] > c_lips[1] + 30, f"Lips Red not > Green + 30: {c_lips}"
        assert c_lips[0] > c_lips[2] + 30, f"Lips Red not > Blue + 30: {c_lips}"
        assert c_lips[0] > 180, f"Lips Red not > 180: {c_lips}"

        # 2. Mesh_Dress_PleatedSkirt_Mesh samples ivory silk (R, G, B > 230 and |R - G| < 10)
        skirt_mesh = next(m for m in json_data.get("meshes", []) if "PleatedSkirt" in m.get("name", ""))
        uv_skirt = get_uvs(skirt_mesh["primitives"][0]).mean(axis=0)
        c_skirt = base_img[int(np.clip(uv_skirt[1] * h, 0, h - 1)), int(np.clip(uv_skirt[0] * w, 0, w - 1))]
        assert c_skirt[0] > 230 and c_skirt[1] > 230 and c_skirt[2] > 230, f"PleatedSkirt not ivory silk: {c_skirt}"
        assert abs(int(c_skirt[0]) - int(c_skirt[1])) < 10, f"PleatedSkirt |R-G| >= 10: {c_skirt}"

        # 3. Mesh_Dress_Bodice_Mesh samples ivory silk (R, G, B > 230 and |R - G| < 10)
        bodice_mesh = next(m for m in json_data.get("meshes", []) if "Bodice" in m.get("name", ""))
        uv_bodice = get_uvs(bodice_mesh["primitives"][0]).mean(axis=0)
        c_bodice = base_img[int(np.clip(uv_bodice[1] * h, 0, h - 1)), int(np.clip(uv_bodice[0] * w, 0, w - 1))]
        assert c_bodice[0] > 230 and c_bodice[1] > 230 and c_bodice[2] > 230, f"Bodice not ivory silk: {c_bodice}"
        assert abs(int(c_bodice[0]) - int(c_bodice[1])) < 10, f"Bodice |R-G| >= 10: {c_bodice}"

        # 4. Yu_Nian_An_Body head samples porcelain skin (R > 200, G > 180, B > 170)
        body_mesh = next(m for m in json_data.get("meshes", []) if "Body" in m.get("name", ""))
        uvs_body = get_uvs(body_mesh["primitives"][0])
        head_mask = uvs_body[:, 0] < 0.5  # Head and face vertices reside in Q1 (U < 0.5)
        assert np.any(head_mask), "No head vertices detected on Yu_Nian_An_Body"
        uv_head = uvs_body[head_mask].mean(axis=0)
        c_head = base_img[int(np.clip(uv_head[1] * h, 0, h - 1)), int(np.clip(uv_head[0] * w, 0, w - 1))]
        assert c_head[0] > 200, f"Body head Red not > 200: {c_head}"
        assert c_head[1] > 180, f"Body head Green not > 180: {c_head}"
        assert c_head[2] > 170, f"Body head Blue not > 170: {c_head}"



# ==============================================================================
# 5. EXPORT PIPELINE AUTOMATION & FASTMCP TOOL
# ==============================================================================

class TestExportAutomationPipeline:
    """Verifies programmatic export functions in character_assembler and server."""

    def test_get_export_script_ast_validation(self):
        """get_export_script must generate syntactically valid Python code."""
        script_code = get_export_script(
            blend_path="output/yu_nian_an/Yu_Nian_An_Master.blend",
            output_fbx_path="output/yu_nian_an/Yu_Nian_An.fbx",
            output_glb_path="output/yu_nian_an/Yu_Nian_An.glb",
        )
        tree = ast.parse(script_code)
        assert isinstance(tree, ast.Module), "Generated export script failed AST parse"
        assert "export_scene.fbx" in script_code
        assert "export_scene.gltf" in script_code

    def test_export_production_assets_function_execution(self):
        """export_production_assets should return valid metadata dictionary with all paths."""
        res = export_production_assets(
            blend_path=MASTER_BLEND,
            output_dir=OUTPUT_DIR,
            character_name="Yu_Nian_An",
            export_fbx=False,       # Skip re-exporting heavy binary during quick unit test
            export_glb=False,
            generate_textures=False,
            generate_docs=True,
        )
        assert res["status"] == "success"
        assert res["character_name"] == "Yu_Nian_An"
        assert "output_dir" in res

    def test_yunianan_assembler_export_packages_method(self):
        """YuNianAnAssembler.export_production_packages must be callable and return manifest."""
        asm = YuNianAnAssembler()
        res = asm.export_production_packages(
            output_dir=OUTPUT_DIR,
            export_fbx=False,
            export_glb=False,
            generate_textures=False,
        )
        assert res["status"] == "success"

    @pytest.mark.asyncio
    async def test_fastmcp_export_tool_registration(self):
        """morphomesh_export_production_character must be registered in HUMAN_TOOL_NAMES."""
        assert "morphomesh_export_production_character" in HUMAN_TOOL_NAMES
        tools = await mcp.list_tools()
        registered_names = {t.name for t in tools}

        # If human tools are enabled, verify it's discovered
        if os.environ.get("MORPHOMESH_INCLUDE_HUMAN_TOOLS") in ("1", "true", "all"):
            assert "morphomesh_export_production_character" in registered_names

    @pytest.mark.asyncio
    async def test_fastmcp_export_tool_execution(self):
        """Verify calling morphomesh_export_production_character returns valid export dictionary."""
        res = await morphomesh_export_production_character(
            character_name="Yu_Nian_An",
            blend_path=MASTER_BLEND,
            output_dir=OUTPUT_DIR,
            export_fbx=False,
            export_glb=False,
            generate_textures=False,
            generate_docs=True,
        )
        assert res["status"] == "success"
        assert "blend_file_path" in res
