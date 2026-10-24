"""
Empirical Challenger Test Suite for Milestone M1 Container Deliverables.
Target: Yu Nian An (余念安) GLB & FBX Containers
Author: challenger_m1_1 (GLB & FBX Container Empirical Stress Test)

Verification scope:
1. GLB container binary header, chunk parsing, and structural integrity.
2. Every GLB mesh primitive has a valid TEXCOORD_0 attribute with UV values strictly in [0, 1].
3. GLB Yu_Nian_An_Body has all 52 Apple ARKit FACS morph targets in extras.targetNames.
4. glTF POSITION accessors for all 52 morph targets reconstructed and verified for non-zero displacement deltas.
5. FBX binary header, version 7400, file size > 5,000,000 bytes.
6. FBX binary contains all 163 DEF bones from Rigify deformation armature.
7. Live Blender re-import audit: vertex deformation under shape keys and skeletal pose rotation.
"""

import os
import sys
import json
import struct
import re
import subprocess
import numpy as np
import pytest

GLB_PATH = "output/yu_nian_an/Yu_Nian_An.glb"
FBX_PATH = "output/yu_nian_an/Yu_Nian_An.fbx"
BLEND_PATH = "output/yu_nian_an/Yu_Nian_An_Master.blend"
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

ARKIT_52_SPEC = [
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

REQUIRED_DEF_BONE_SAMPLES = [
    "DEF-spine", "DEF-spine.001", "DEF-spine.002", "DEF-spine.003", "DEF-spine.004", "DEF-spine.005", "DEF-spine.006",
    "DEF-head", "DEF-jaw.center", "DEF-eye.L", "DEF-eye.R",
    "DEF-shoulder.L", "DEF-upper_arm.L", "DEF-upper_arm.L.001", "DEF-forearm.L", "DEF-forearm.L.001", "DEF-hand.L",
    "DEF-shoulder.R", "DEF-upper_arm.R", "DEF-upper_arm.R.001", "DEF-forearm.R", "DEF-forearm.R.001", "DEF-hand.R",
    "DEF-thumb.01.L", "DEF-thumb.02.L", "DEF-thumb.03.L",
    "DEF-f_index.01.L", "DEF-f_index.02.L", "DEF-f_index.03.L",
    "DEF-f_middle.01.L", "DEF-f_middle.02.L", "DEF-f_middle.03.L",
    "DEF-f_ring.01.L", "DEF-f_ring.02.L", "DEF-f_ring.03.L",
    "DEF-f_pinky.01.L", "DEF-f_pinky.02.L", "DEF-f_pinky.03.L",
    "DEF-thigh.L", "DEF-thigh.L.001", "DEF-shin.L", "DEF-shin.L.001", "DEF-foot.L", "DEF-toe.L",
    "DEF-thigh.R", "DEF-thigh.R.001", "DEF-shin.R", "DEF-shin.R.001", "DEF-foot.R", "DEF-toe.R",
    "DEF-brow.B.L.000", "DEF-cheek.T.L.000", "DEF-lip.B.L.000", "DEF-nose.L.000", "DEF-tongue.L.000"
]


class TestEmpiricalGLBContainer:
    """Empirical adversarial stress testing of the production GLB asset."""

    def test_glb_file_header_and_magic(self):
        assert os.path.isfile(GLB_PATH), f"GLB file missing at {GLB_PATH}"
        file_size = os.path.getsize(GLB_PATH)
        assert file_size > 2_000_000, f"GLB file size too small: {file_size} bytes"

        with open(GLB_PATH, "rb") as f:
            header = f.read(12)
            magic, version, length = struct.unpack("<4sII", header)
            assert magic == b"glTF", f"Invalid glTF magic: {magic}"
            assert version == 2, f"Invalid glTF version: {version}"
            assert length == file_size, f"Header length {length} does not match file size {file_size}"

    def test_glb_chunks_and_mesh_primitive_count(self):
        with open(GLB_PATH, "rb") as f:
            f.seek(12)
            c0_len, c0_type = struct.unpack("<II", f.read(8))
            assert c0_type == 0x4E4F534A, f"Chunk 0 must be JSON (0x4E4F534A), got {hex(c0_type)}"
            json_data = json.loads(f.read(c0_len).decode("utf-8"))

            c1_len, c1_type = struct.unpack("<II", f.read(8))
            assert c1_type == 0x004E4942, f"Chunk 1 must be BIN (0x004E4942), got {hex(c1_type)}"

        meshes = json_data.get("meshes", [])
        assert len(meshes) >= 30, f"Expected >= 30 meshes in GLB, found {len(meshes)}"

        total_primitives = sum(len(m.get("primitives", [])) for m in meshes)
        assert total_primitives >= 30, f"Expected >= 30 primitives in GLB, found {total_primitives}"

    def test_glb_texcoord_0_on_all_primitives(self):
        """Every mesh primitive must feature a valid TEXCOORD_0 with UVs strictly in [0.0, 1.0]."""
        with open(GLB_PATH, "rb") as f:
            f.seek(12)
            c0_len, _ = struct.unpack("<II", f.read(8))
            json_data = json.loads(f.read(c0_len).decode("utf-8"))
            c1_len, _ = struct.unpack("<II", f.read(8))
            bin_data = f.read(c1_len)

        meshes = json_data.get("meshes", [])
        assert len(meshes) > 0

        missing_uv_prims = []
        tested_prims = 0

        for mi, m in enumerate(meshes):
            m_name = m.get("name", f"mesh_{mi}")
            for pi, prim in enumerate(m.get("primitives", [])):
                tested_prims += 1
                attrs = prim.get("attributes", {})
                if "TEXCOORD_0" not in attrs:
                    missing_uv_prims.append(f"{m_name}_prim_{pi}")
                    continue

                acc_idx = attrs["TEXCOORD_0"]
                acc = json_data["accessors"][acc_idx]
                bv = json_data["bufferViews"][acc["bufferView"]]
                off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                cnt = acc["count"]
                assert acc["componentType"] == 5126, f"TEXCOORD_0 must be FLOAT (5126), got {acc['componentType']}"
                assert acc["type"] == "VEC2", f"TEXCOORD_0 must be VEC2, got {acc['type']}"

                uvs = np.frombuffer(bin_data, dtype=np.float32, count=cnt * 2, offset=off).reshape((cnt, 2))

                # Numerical assertions
                assert not np.isnan(uvs).any(), f"NaN found in UVs of {m_name}_prim_{pi}"
                assert not np.isinf(uvs).any(), f"Inf found in UVs of {m_name}_prim_{pi}"

                # Float32 precision tolerance: allow machine epsilon 1e-5
                min_u, max_u = float(np.min(uvs[:, 0])), float(np.max(uvs[:, 0]))
                min_v, max_v = float(np.min(uvs[:, 1])), float(np.max(uvs[:, 1]))
                assert min_u >= -1e-5, f"{m_name}_prim_{pi} min U={min_u} < 0.0"
                assert max_u <= 1.0 + 1e-5, f"{m_name}_prim_{pi} max U={max_u} > 1.0"
                assert min_v >= -1e-5, f"{m_name}_prim_{pi} min V={min_v} < 0.0"
                assert max_v <= 1.0 + 1e-5, f"{m_name}_prim_{pi} max V={max_v} > 1.0"

        assert len(missing_uv_prims) == 0, f"Primitives missing TEXCOORD_0: {missing_uv_prims}"
        assert tested_prims >= 30, f"Expected >= 30 primitives, tested {tested_prims}"

    def test_glb_52_arkit_morph_target_names(self):
        """Yu_Nian_An_Body must declare exactly 52 ARKit targetNames in extras."""
        with open(GLB_PATH, "rb") as f:
            f.seek(12)
            c0_len, _ = struct.unpack("<II", f.read(8))
            json_data = json.loads(f.read(c0_len).decode("utf-8"))

        body_mesh = next((m for m in json_data.get("meshes", []) if "Body" in m.get("name", "")), None)
        assert body_mesh is not None, "Body mesh not found in GLB"

        target_names = body_mesh.get("extras", {}).get("targetNames", [])
        assert len(target_names) == 52, f"Expected exactly 52 morph targets, got {len(target_names)}"
        assert sorted(target_names) == sorted(ARKIT_52_SPEC), "targetNames do not match ARKit 52 specification"

    def test_glb_all_52_morph_targets_have_nonzero_deltas(self):
        """Every one of the 52 ARKit morph targets must possess non-zero displacement deltas."""
        with open(GLB_PATH, "rb") as f:
            f.seek(12)
            c0_len, _ = struct.unpack("<II", f.read(8))
            json_data = json.loads(f.read(c0_len).decode("utf-8"))
            c1_len, _ = struct.unpack("<II", f.read(8))
            bin_data = f.read(c1_len)

        body_mesh = next((m for m in json_data.get("meshes", []) if "Body" in m.get("name", "")), None)
        assert body_mesh is not None
        target_names = body_mesh.get("extras", {}).get("targetNames", [])
        targets = body_mesh["primitives"][0].get("targets", [])
        assert len(targets) == 52, f"Expected 52 target primitives, got {len(targets)}"

        def read_accessor_vec3(acc_idx):
            acc = json_data["accessors"][acc_idx]
            cnt = acc["count"]
            assert acc["type"] == "VEC3"
            assert acc["componentType"] == 5126

            if "bufferView" in acc:
                bv = json_data["bufferViews"][acc["bufferView"]]
                off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                arr = np.frombuffer(bin_data, dtype=np.float32, count=cnt * 3, offset=off).reshape((cnt, 3)).copy()
            else:
                arr = np.zeros((cnt, 3), dtype=np.float32)

            if "sparse" in acc:
                sp = acc["sparse"]
                sp_cnt = sp["count"]
                idx_bv = json_data["bufferViews"][sp["indices"]["bufferView"]]
                idx_off = idx_bv.get("byteOffset", 0) + sp["indices"].get("byteOffset", 0)
                idx_type = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32}[sp["indices"]["componentType"]]
                indices = np.frombuffer(bin_data, dtype=idx_type, count=sp_cnt, offset=idx_off)

                val_bv = json_data["bufferViews"][sp["values"]["bufferView"]]
                val_off = val_bv.get("byteOffset", 0) + sp["values"].get("byteOffset", 0)
                values = np.frombuffer(bin_data, dtype=np.float32, count=sp_cnt * 3, offset=val_off).reshape((sp_cnt, 3))
                arr[indices] = values

            return arr

        zero_delta_targets = []
        for ti, target in enumerate(targets):
            tname = target_names[ti]
            assert "POSITION" in target, f"Target {tname} missing POSITION accessor"
            deltas = read_accessor_vec3(target["POSITION"])

            assert not np.isnan(deltas).any(), f"NaN in deltas of {tname}"
            assert not np.isinf(deltas).any(), f"Inf in deltas of {tname}"

            norms = np.linalg.norm(deltas, axis=1)
            max_disp = float(np.max(norms))
            moved_verts = int(np.sum(norms > 1e-6))

            if max_disp <= 0.0005 or moved_verts == 0:
                zero_delta_targets.append((tname, max_disp, moved_verts))

            # Plausibility check: facial FACS deltas should not exceed 100mm (0.1m)
            assert max_disp < 0.10, f"Target {tname} has absurd displacement delta: {max_disp}m"

        assert len(zero_delta_targets) == 0, f"Targets with zero or sub-threshold displacement: {zero_delta_targets}"


class TestEmpiricalFBXContainer:
    """Empirical adversarial stress testing of the production FBX asset."""

    def test_fbx_file_size_and_binary_header(self):
        assert os.path.isfile(FBX_PATH), f"FBX file missing at {FBX_PATH}"
        file_size = os.path.getsize(FBX_PATH)
        assert file_size > 5_000_000, f"FBX file size must be > 5MB, got {file_size} bytes"

        with open(FBX_PATH, "rb") as f:
            header = f.read(27)
            magic = header[:23]
            version = struct.unpack("<I", header[23:27])[0]
            assert magic == b"Kaydara FBX Binary  \x00\x1a\x00", f"Invalid FBX binary header: {magic}"
            assert version in (7400, 7500), f"Unexpected FBX version: {version}"

    def test_fbx_contains_all_163_def_bones(self):
        """FBX binary stream must contain all 163 DEF bones from Rigify deformation armature."""
        with open(FBX_PATH, "rb") as f:
            fbx_bytes = f.read()

        matches = re.findall(rb"DEF-[a-zA-Z0-9_\.]+", fbx_bytes)
        unique_def_bones = sorted(list(set(m.decode("ascii", errors="ignore") for m in matches)))

        assert len(unique_def_bones) == 163, f"Expected 163 unique DEF bones in FBX, found {len(unique_def_bones)}"

        missing_samples = [b for b in REQUIRED_DEF_BONE_SAMPLES if b not in unique_def_bones]
        assert len(missing_samples) == 0, f"Missing critical DEF bones in FBX: {missing_samples}"

    def test_fbx_shape_keys_and_uv_layers(self):
        """FBX binary stream must contain ARKit shape keys and UV layer definitions."""
        with open(FBX_PATH, "rb") as f:
            fbx_bytes = f.read()

        # ARKit blendshapes in FBX
        for shape in [b"eyeBlinkLeft", b"eyeBlinkRight", b"jawOpen", b"mouthSmileLeft", b"tongueOut", b"cheekPuff"]:
            assert shape in fbx_bytes, f"Missing shape key {shape} in FBX binary"

        # UV layer tokens
        assert b"LayerElementUV" in fbx_bytes or b"UVMap" in fbx_bytes, "Missing UV layer definitions in FBX"


class TestLiveBlenderReimportAudit:
    """Executes live re-import inside Blender to verify depsgraph deformation."""

    def test_live_blender_reimport_depsgraph(self):
        if not os.path.isfile(BLENDER_EXE):
            pytest.skip("Blender executable not found at specified path")

        cmd = [
            BLENDER_EXE,
            "--background",
            "--python",
            "tests/test_challenger_m5_empirical.py"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, f"Blender live re-import failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert "ALL LIVE BLENDER RE-IMPORT AUDITS PASSED WITH ZERO ERRORS" in result.stdout
