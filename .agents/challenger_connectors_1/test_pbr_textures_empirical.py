"""
MorphoMesh Phase 2: Empirical Challenge Suite 4
PBR Texture Map Verification for TrellisConnector and HunyuanConnector:
4 Distinct Channels (Albedo, Normal, Roughness, Metallic), Valid PNG Headers, & Pixel Dimensions.
"""

from __future__ import annotations

import os
import struct
import numpy as np
import pytest
from PIL import Image
from typing import Dict, Tuple

from morphomesh.connectors.hunyuan_connector import (
    HunyuanConnector,
    HunyuanInput,
    HunyuanOutput,
)
from morphomesh.connectors.trellis_connector import (
    TrellisConnector,
    TrellisInput,
    TrellisOutput,
)
from morphomesh.models import ERR_IMAGE_NOT_FOUND, MorphoMeshException

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def inspect_raw_png_header(file_path: str) -> Tuple[int, int, int, int]:
    """
    Parse raw bytes of a PNG file to extract dimensions, bit depth, and color type.
    
    Returns:
        Tuple[width, height, bit_depth, color_type]
    """
    assert os.path.exists(file_path), f"PNG file not found: {file_path}"
    with open(file_path, "rb") as f:
        sig = f.read(8)
        assert sig == PNG_SIGNATURE, f"Invalid PNG signature in {file_path}: {sig}"

        # Next 4 bytes: IHDR length (13)
        ihdr_len, = struct.unpack(">I", f.read(4))
        assert ihdr_len == 13, f"Unexpected IHDR chunk length {ihdr_len}"

        # Next 4 bytes: IHDR chunk type
        chunk_type = f.read(4)
        assert chunk_type == b"IHDR", f"Expected IHDR chunk, got {chunk_type}"

        # IHDR data: Width (4), Height (4), BitDepth (1), ColorType (1)
        width, height, bit_depth, color_type = struct.unpack(">IIBB", f.read(10))
        return width, height, bit_depth, color_type


@pytest.fixture
def sample_image_path(tmp_path) -> str:
    """Create a temporary concept image."""
    img = Image.new("RGBA", (256, 256), (120, 100, 90, 255))
    path = str(tmp_path / "test_concept.png")
    img.save(path)
    return path


class TestTrellisPBRTextures:
    """Empirically test TRELLIS 4-channel PBR texture generation, PNG headers, and dimensions."""

    @pytest.mark.parametrize("res", [512, 1024, 2048])
    def test_trellis_all_four_channels_headers_and_dimensions(self, sample_image_path, tmp_path, res):
        """
        Verify TrellisConnector produces 4 distinct channels:
        - Albedo (sRGB)
        - Normal (Tangent OpenGL Non-Color)
        - Roughness (Non-Color)
        - Metallic (Non-Color)
        With valid PNG magic bytes, correct width & height, and channel distinctness.
        """
        out_dir = str(tmp_path / f"trellis_pbr_{res}")
        conn = TrellisConnector()
        inp = TrellisInput(
            image_path=sample_image_path,
            generate_pbr=True,
            texture_resolution=res,
            output_dir=out_dir,
        )
        out = conn.execute(inp)

        assert isinstance(out, TrellisOutput)
        pbr = out.pbr_textures
        channels = {
            "albedo": pbr.albedo_path,
            "normal": pbr.normal_path,
            "roughness": pbr.roughness_path,
            "metallic": pbr.metallic_path,
        }

        # 1. Verify all 4 paths exist and are unique files
        paths_set = set()
        for cname, cpath in channels.items():
            assert cpath is not None, f"Missing path for channel {cname}"
            assert os.path.exists(cpath), f"File does not exist for channel {cname}: {cpath}"
            assert cpath not in paths_set, f"Channel {cname} has duplicate file path: {cpath}"
            paths_set.add(cpath)

        # 2. Raw byte header inspection for all 4 channels
        for cname, cpath in channels.items():
            w, h, depth, ctype = inspect_raw_png_header(cpath)
            assert w == res, f"{cname} width {w} != requested {res}"
            assert h == res, f"{cname} height {h} != requested {res}"
            assert depth == 8, f"{cname} bit depth {depth} != 8"
            if cname in ("albedo", "normal"):
                assert ctype == 2, f"{cname} color type {ctype} != 2 (RGB)"
            else:
                assert ctype in (0, 2), f"{cname} color type {ctype} must be Grayscale (0) or RGB (2)"

        # 3. Verify distinct image content (no two channels are byte-identical)
        file_hashes = {}
        for cname, cpath in channels.items():
            with open(cpath, "rb") as f:
                content = f.read()
                file_hashes[cname] = hash(content)

        assert len(set(file_hashes.values())) == 4, "Not all 4 PBR texture files have distinct contents!"

        # 4. Tangent-space Normal vector mathematical properties
        with Image.open(pbr.normal_path) as n_img:
            narr = np.array(n_img)
            # Tangent space normal pointing primarily outward (+Z): Blue channel (Z) must dominate
            mean_r = np.mean(narr[:, :, 0])
            mean_g = np.mean(narr[:, :, 1])
            mean_b = np.mean(narr[:, :, 2])
            assert 120 <= mean_r <= 136, f"Normal X not centered near 128: {mean_r}"
            assert 120 <= mean_g <= 136, f"Normal Y not centered near 128: {mean_g}"
            assert mean_b >= 240, f"Normal Z not strongly positive: {mean_b}"

        # 5. Color space metadata
        assert pbr.color_space_map["albedo"] == "sRGB"
        assert pbr.color_space_map["normal"] == "Non-Color"
        assert pbr.color_space_map["roughness"] == "Non-Color"
        assert pbr.color_space_map["metallic"] == "Non-Color"


class TestHunyuanPBRTextures:
    """Empirically test Hunyuan 4-channel PBR texture generation, PNG headers, and dimensions."""

    @pytest.mark.parametrize("res", [1024, 2048])
    def test_hunyuan_all_four_channels_headers_and_dimensions(self, sample_image_path, tmp_path, res):
        """
        Verify HunyuanConnector produces all 4 distinct PBR channels:
        Albedo, Normal, Roughness, Metallic.
        """
        out_dir = str(tmp_path / f"hunyuan_pbr_{res}")
        conn = HunyuanConnector(config={"texture_resolution": res})
        inp = HunyuanInput(image_path=sample_image_path, generate_pbr=True)
        out = conn.execute(inp, output_dir=out_dir)

        assert isinstance(out, HunyuanOutput)
        channels = {
            "albedo": out.albedo_map_path,
            "normal": out.normal_map_path,
            "roughness": out.roughness_map_path,
            "metallic": out.metallic_map_path,
        }

        # Verify all 4 exist in pbr_textures dict as well
        assert len(out.pbr_textures) == 4

        paths_set = set()
        for cname, cpath in channels.items():
            assert cpath is not None, f"Missing path for channel {cname}"
            assert os.path.exists(cpath), f"Channel file does not exist: {cpath}"
            assert cpath not in paths_set, f"Duplicate file path for {cname}"
            paths_set.add(cpath)

            # Raw byte header inspection
            w, h, depth, ctype = inspect_raw_png_header(cpath)
            assert w == res, f"{cname} width {w} != {res}"
            assert h == res, f"{cname} height {h} != {res}"
            assert depth == 8

        # Verify contents are distinct
        file_hashes = {}
        for cname, cpath in channels.items():
            with open(cpath, "rb") as f:
                file_hashes[cname] = hash(f.read())
        assert len(set(file_hashes.values())) == 4

        # Verify Normal map tangent space characteristics
        with Image.open(out.normal_map_path) as n_img:
            narr = np.array(n_img)
            assert np.mean(narr[:, :, 2]) > 200, "Normal Z component must dominate"

        # Verify Metallic is dielectric (low values for biological material)
        with Image.open(out.metallic_map_path) as m_img:
            marr = np.array(m_img)
            assert np.mean(marr) < 50, "Organic creature metallic map should be dielectric (~0.0)"
