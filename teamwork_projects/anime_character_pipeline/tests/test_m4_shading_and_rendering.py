"""
Unit & Integration Tests for Milestone 4 (Shading, Outline, Camera & Video Pipeline).
Features F14-F19:
- F14: Stepped Cel-Shading Toon Materials
- F15: Procedural Hair Angel Ring
- F16: Inverted Hull Solidify Outline
- F17: Cinematic Camera Rig & 3-Point Studio Lighting
- F18: Headless Full HD Video Exporter & ISO BMFF Container Validation
- F19: Master Unified CLI Entrypoint
"""

from __future__ import annotations

import math
import struct
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from anime_pipeline.shading.toon_materials import (
    CLOTHES_PRESETS,
    EYE_HIGHLIGHT_COLOR,
    EYE_IRIS_COLOR,
    EYE_PUPIL_COLOR,
    OUTLINE_COLOR,
    SKIN_BASE_COLOR,
    SKIN_SHADOW_COLOR,
    build_anime_clothes_material,
    build_anime_eye_material,
    build_anime_outline_material,
    build_anime_skin_material,
    hex_to_rgba,
)
from anime_pipeline.shading.angel_ring import (
    ANGEL_RING_COLOR,
    DEFAULT_CROWN_Z_MAX,
    DEFAULT_CROWN_Z_MIN,
    HAIR_BASE_COLOR,
    HAIR_SHADOW_COLOR,
    build_procedural_angel_ring_material,
    compute_hair_crown_z_bounds,
)
from anime_pipeline.shading.inverted_hull import (
    CANONICAL_MESH_NAMES,
    DEFAULT_OUTLINE_OFFSET,
    DEFAULT_OUTLINE_THICKNESS,
    OUTLINE_MATERIAL_NAME,
    OUTLINE_MODIFIER_NAME,
    OutlineConfig,
    apply_inverted_hull_outline,
    validate_solidify_outline_dict,
)
from anime_pipeline.rendering.camera_rig import (
    DEFAULT_CAMERA_FOCAL_LENGTH,
    DEFAULT_CAMERA_NAME,
    DEFAULT_CAMERA_POSITION,
    DEFAULT_TRACK_TARGET_BONE,
    FILL_LIGHT_NAME,
    KEY_LIGHT_NAME,
    RIM_LIGHT_NAME,
    CameraConfig,
    LightingRigConfig,
    calculate_optical_framing_distance,
    hex_to_linear_rgb,
)
from anime_pipeline.rendering.video_exporter import (
    DEFAULT_CODEC,
    DEFAULT_ENGINE,
    DEFAULT_FPS,
    DEFAULT_RESOLUTION_X,
    DEFAULT_RESOLUTION_Y,
    MIN_DURATION_SECONDS,
    MIN_FILE_SIZE_BYTES,
    RESOLUTION_PRESETS,
    VideoExportConfig,
    parse_iso_bmff_mp4_header,
)
from pipeline import build_cli_parser


class TestM4ShadingAndMaterials:
    """Validates F14 & F15 Stepped Cel-Shading and Angel Ring."""

    def test_skin_material_palette_warm_peach(self):
        """Verifies fair porcelain skin and warm peach shadow invariants."""
        assert SKIN_BASE_COLOR[0] >= 0.95 and SKIN_BASE_COLOR[1] >= 0.85
        # Invariant from Tier 1 contract: R > 0.90, G > 0.70, B < 0.75
        assert SKIN_SHADOW_COLOR[0] > 0.90
        assert SKIN_SHADOW_COLOR[1] > 0.70
        assert SKIN_SHADOW_COLOR[2] < 0.75

    def test_hex_to_rgba_converter(self):
        """Verifies hex string to RGBA conversion."""
        rgba = hex_to_rgba("#FFE2D4")
        assert len(rgba) == 4
        assert rgba[3] == 1.0
        assert abs(rgba[0] - (0xFF / 255.0)) < 1e-3
        assert abs(rgba[1] - (0xE2 / 255.0)) < 1e-3
        assert abs(rgba[2] - (0xD4 / 255.0)) < 1e-3

    def test_clothes_and_eye_presets(self):
        """Verifies garment presets for SHIRT, SKIRT, and SHOES, plus Eye colors."""
        for garment in ("SHIRT", "SKIRT", "SHOES"):
            assert garment in CLOTHES_PRESETS
            assert "base" in CLOTHES_PRESETS[garment]
            assert "shadow" in CLOTHES_PRESETS[garment]

        assert len(EYE_IRIS_COLOR) == 4
        assert len(EYE_PUPIL_COLOR) == 4
        assert len(EYE_HIGHLIGHT_COLOR) == 4

    def test_angel_ring_parameters(self):
        """Verifies procedural angel ring highlight crown coordinates and gating."""
        assert DEFAULT_CROWN_Z_MIN == 1.45
        assert DEFAULT_CROWN_Z_MAX == 1.55
        assert ANGEL_RING_COLOR == (1.0, 1.0, 0.95, 1.0)
        assert compute_hair_crown_z_bounds("nonexistent_obj") == (1.45, 1.55)


class TestM4OutlineAndCamera:
    """Validates F16 Inverted Hull Outline & F17 Camera / Lighting Rig."""

    def test_outline_config_validation(self):
        """Verifies OutlineConfig boundaries and validation checks."""
        cfg = OutlineConfig()
        assert cfg.validate() is True
        assert cfg.thickness < 0.0
        assert cfg.offset == 1.0
        assert cfg.use_flip_normals is True
        assert cfg.use_rim is False

        # Adversarial thickness check
        with pytest.raises(AssertionError):
            invalid_cfg = OutlineConfig(thickness=0.01)
            invalid_cfg.validate()

    def test_validate_solidify_outline_dict(self):
        """Verifies dictionary validator for Solidify outline modifier."""
        valid_dict = {
            "type": "SOLIDIFY",
            "thickness": -0.0035,
            "use_flip_normals": True,
            "material_offset": 1,
        }
        assert validate_solidify_outline_dict(valid_dict) is True

    def test_camera_rig_optical_specifications(self):
        """Verifies Anime_Camera focal length, sensor, and positioning."""
        cam_cfg = CameraConfig()
        assert cam_cfg.validate() is True
        assert cam_cfg.name == "Anime_Camera"
        assert cam_cfg.focal_length_mm == 65.0
        assert cam_cfg.position == (0.0, -2.6, 1.25)
        assert cam_cfg.target_bone == "Spine2"

    def test_lighting_rig_3point_balance(self):
        """Verifies 3-point lighting setup, Key-to-Fill ratio, and Rim intensity."""
        light_cfg = LightingRigConfig()
        assert light_cfg.validate() is True
        lights = light_cfg.get_lights()
        assert len(lights) == 3

        key = light_cfg.key_light
        fill = light_cfg.fill_light
        rim = light_cfg.rim_light

        assert key.energy_watts == 650.0
        assert fill.energy_watts == 200.0
        assert rim.energy_watts == 800.0
        assert key.energy_watts > fill.energy_watts
        assert rim.energy_watts >= key.energy_watts

    def test_optical_framing_distance_calculation(self):
        """Verifies portrait framing distance math for 1.58m anime character."""
        dist = calculate_optical_framing_distance(character_height=1.58, focal_length_mm=65.0)
        assert 2.5 <= dist <= 6.5


class TestM4RenderingAndPipelineCLI:
    """Validates F18 Video Exporter & F19 Master CLI."""

    def test_video_export_config_defaults_and_presets(self):
        """Verifies VideoExportConfig defaults and preset resolution parsing."""
        cfg = VideoExportConfig()
        assert cfg.resolution_x == 1920
        assert cfg.resolution_y == 1080
        assert cfg.fps == 30
        assert cfg.engine == "BLENDER_EEVEE_NEXT"
        assert cfg.video_codec == "H264"
        assert cfg.min_size_bytes == 1024 * 1024
        assert cfg.min_duration_s == 3.0

        p1080 = VideoExportConfig.from_resolution_string("1080p")
        assert (p1080.resolution_x, p1080.resolution_y) == (1920, 1080)

        p720 = VideoExportConfig.from_resolution_string("720p")
        assert (p720.resolution_x, p720.resolution_y) == (1280, 720)

    def test_iso_bmff_mp4_box_parser(self):
        """Verifies pure-Python ISO BMFF header decoder on synthetic bytes."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            tmp_path = Path(tf.name)
            # Construct synthetic ftyp box (24 bytes)
            ftyp_bytes = (
                (24).to_bytes(4, "big")
                + b"ftyp"
                + b"isom"
                + (0x00000200).to_bytes(4, "big")
                + b"iso2"
                + b"mp41"
            )
            # mvhd box: 4 size, 4 'mvhd', 1 ver(0), 3 flags, 4 creation, 4 mod, 4 timescale(1000), 4 duration(4500)
            mvhd_payload = (
                (0).to_bytes(1, "big")
                + (0).to_bytes(3, "big")
                + (0).to_bytes(4, "big")
                + (0).to_bytes(4, "big")
                + (1000).to_bytes(4, "big")
                + (4500).to_bytes(4, "big")
            )
            mvhd_box = (len(mvhd_payload) + 8).to_bytes(4, "big") + b"mvhd" + mvhd_payload
            moov_box = (len(mvhd_box) + 8).to_bytes(4, "big") + b"moov" + mvhd_box
            tf.write(ftyp_bytes + moov_box)

        try:
            res = parse_iso_bmff_mp4_header(tmp_path)
            assert res["valid_container"] is True
            assert res["major_brand"] == "isom"
            assert res["duration_s"] == 4.5
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_cli_parser_flags(self):
        """Verifies master CLI parser accepts all stage flags and parameter arguments."""
        parser = build_cli_parser()
        args = parser.parse_args([
            "--all",
            "--action", "action_anime_jump_cheer",
            "--resolution", "1080p",
            "--fps", "30",
            "--output-dir", "custom_output",
        ])
        assert args.all is True
        assert args.action == "action_anime_jump_cheer"
        assert args.resolution == "1080p"
        assert args.fps == 30
        assert args.output_dir == "custom_output"
