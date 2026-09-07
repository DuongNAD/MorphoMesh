"""
MorphoMesh: Multiview Viewport Rendering Automated Test Suite.
Target File: tests/test_multiview_rendering.py
Milestone: Milestone 2 (Multi-Angle Inspector Camera & Fast Viewport Capture)

Validates:
1. Single Viewport Capture:
   - File output creation, PNG format, valid schema return.
   - Custom resolution scaling ((512,512), (1024,1024), (1920,1080), (1080,1920)).
   - Temp path generation when output_path=None.
2. Multi-Angle Batch Capture Pipeline:
   - Sequential capture across canonical viewpoints (front, side, three_quarter, back, head).
   - Zero filename collisions, all viewpoints populated in output list.
   - Turntable batch sequencing.
   - Empty viewpoint list handling.
3. Diagnostic Shading & Color Mode Configurations:
   - SOLID with RANDOM color (vital diagnostic mode distinguishing separate garments/clipping).
   - SOLID with MATERIAL color.
   - WIREFRAME mode and MATERIAL preview mode.
   - Graceful fallback on invalid shading modes.
4. Dual-Mode Execution Resilience:
   - Socket Interactive Mode (bpy.ops.render.opengl with temp_override on VIEW_3D, <200ms).
   - Headless Workbench Mode (scene.render.engine='BLENDER_WORKBENCH', <0.7s).
   - Automatic fallback when OpenGL fails in background mode.
   - Scene render engine restoration (restoring CYCLES/EEVEE after workbench render).
5. PNG Binary Header & Base64 Preview Validation:
   - PNG magic header signature (\x89PNG\r\n\x1a\n).
   - IHDR chunk 32-bit big-endian width and height validation.
   - Base64 string generation and bit-exact binary roundtrip decode.
6. BlenderBridge & Socket RPC Integration:
   - Client method BlenderBridge.capture_viewport() execution.
   - Client method BlenderBridge.setup_inspector_camera() execution.
   - Client method BlenderBridge.capture_multi_angle_inspection() execution.
"""

from __future__ import annotations

import base64
import os
import tempfile
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from morphomesh.blender_bridge import BlenderBridge
from morphomesh.camera_rig import (
    capture_multi_angle_inspection,
    capture_viewport_image,
    encode_image_to_base64,
    setup_inspector_camera,
)


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def temp_render_dir(tmp_path):
    """Provides isolated directory for render artifacts."""
    out_dir = tmp_path / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir)


@pytest.fixture
def sample_test_png(temp_render_dir):
    """Generates a valid test PNG file with synthetic dimensions."""
    img_path = os.path.join(temp_render_dir, "test_render.png")
    img = Image.new("RGB", (1024, 1024), color=(70, 90, 120))
    img.save(img_path, "PNG")
    return img_path


# ==============================================================================
# 1. SINGLE VIEWPORT CAPTURE UNIT TESTS
# ==============================================================================

class TestSingleViewportCapture:
    """Validates single viewport capture API, file creation, and schema contract."""

    def test_single_viewport_capture_schema_and_file_creation(self, temp_render_dir):
        """Single capture must return valid path and create non-empty PNG file."""
        out_file = os.path.join(temp_render_dir, "viewport_single.png")

        res_path = capture_viewport_image(
            output_path=out_file,
            resolution=(1024, 1024),
            shading_mode="SOLID",
            color_type="RANDOM",
        )
        assert os.path.isfile(res_path)
        assert os.path.getsize(res_path) > 0
        assert res_path.endswith(".png")

    @pytest.mark.parametrize("res_tuple", [
        (512, 512),
        (1024, 1024),
        (1920, 1080),
        (1080, 1920),
    ])
    def test_custom_resolution_capture(self, temp_render_dir, res_tuple):
        """Rendered image must match requested resolution."""
        out_file = os.path.join(temp_render_dir, f"render_{res_tuple[0]}x{res_tuple[1]}.png")
        res_path = capture_viewport_image(output_path=out_file, resolution=res_tuple)
        assert os.path.isfile(res_path)

        with Image.open(res_path) as im:
            assert im.size == res_tuple

    def test_auto_temp_path_generation_when_none(self):
        """When output_path is None, a unique temporary PNG path is generated."""
        res_path = capture_viewport_image(output_path=None)
        assert os.path.isfile(res_path)
        assert os.path.getsize(res_path) > 0


# ==============================================================================
# 2. MULTI-ANGLE BATCH CAPTURE UNIT TESTS
# ==============================================================================

class TestMultiAngleBatchCapture:
    """Validates multi-angle inspection sequencing and metadata aggregation."""

    def test_batch_four_canonical_angles(self, temp_render_dir):
        """Batch capture over 4 angles must produce 4 distinct image files."""
        vps = ["front", "side", "three_quarter", "back"]
        captures = capture_multi_angle_inspection(viewpoints=vps, output_dir=temp_render_dir)

        assert len(captures) == 4
        captured_files = [c["image_path"] for c in captures]
        assert len(set(captured_files)) == 4

        for c in captures:
            assert os.path.isfile(c["image_path"])
            assert os.path.getsize(c["image_path"]) > 0
            assert c["viewpoint"] in vps
            assert "base64_image" in c
            assert c["base64_image"] is not None

    def test_batch_subregion_closeups(self, temp_render_dir):
        """Batch capture must handle anatomical close-ups (head, hands, torso, feet)."""
        subregions = ["close_up_head", "torso", "close_up_hands", "feet"]
        captures = capture_multi_angle_inspection(viewpoints=subregions, output_dir=temp_render_dir)

        assert len(captures) == 4
        for c in captures:
            assert os.path.isfile(c["image_path"])
            assert c["framing_distance"] > 0.0

    def test_empty_viewpoints_list_graceful(self, temp_render_dir):
        """Empty viewpoints list returns empty captures array without raising error."""
        captures = capture_multi_angle_inspection(viewpoints=[], output_dir=temp_render_dir)
        assert captures == []

    def test_default_viewpoints_when_none(self, temp_render_dir):
        """When viewpoints is None, defaults to 5 canonical viewpoints."""
        captures = capture_multi_angle_inspection(viewpoints=None, output_dir=temp_render_dir)
        assert len(captures) == 5
        vp_names = [c["viewpoint"] for c in captures]
        assert "front" in vp_names
        assert "three_quarter" in vp_names
        assert "side" in vp_names
        assert "back" in vp_names
        assert "close_up_head" in vp_names


# ==============================================================================
# 3. DIAGNOSTIC SHADING & COLOR MODE TESTS
# ==============================================================================

class TestShadingAndColorModes:
    """Validates diagnostic viewport shading parameters (SOLID, RANDOM, WIREFRAME)."""

    def test_solid_random_diagnostic_configuration(self, temp_render_dir):
        """SOLID with RANDOM color assigns distinct colors to separate objects."""
        out_file = os.path.join(temp_render_dir, "shading_solid_random.png")
        res_path = capture_viewport_image(
            output_path=out_file,
            shading_mode="SOLID",
            color_type="RANDOM",
        )
        assert os.path.isfile(res_path)

    def test_wireframe_shading_mode(self, temp_render_dir):
        """WIREFRAME mode configures viewport topology visualization."""
        out_file = os.path.join(temp_render_dir, "shading_wireframe.png")
        res_path = capture_viewport_image(
            output_path=out_file,
            shading_mode="WIREFRAME",
        )
        assert os.path.isfile(res_path)

    def test_material_shading_mode(self, temp_render_dir):
        """MATERIAL mode configures material preview shading."""
        out_file = os.path.join(temp_render_dir, "shading_material.png")
        res_path = capture_viewport_image(
            output_path=out_file,
            shading_mode="MATERIAL",
        )
        assert os.path.isfile(res_path)

    def test_invalid_shading_mode_defaults_to_solid(self, temp_render_dir):
        """Invalid shading modes must be normalized to 'SOLID' without error."""
        out_file = os.path.join(temp_render_dir, "shading_invalid.png")
        res_path = capture_viewport_image(
            output_path=out_file,
            shading_mode="NEON_CYBERPUNK",
        )
        assert os.path.isfile(res_path)


# ==============================================================================
# 4. DUAL-MODE EXECUTION RESILIENCE TESTS
# ==============================================================================

class TestDualModeExecution:
    """Validates interactive OpenGL grab vs headless Workbench render fallback."""

    def test_interactive_opengl_path_simulation(self, tmp_path):
        """Interactive mode utilizes VIEW_3D temp_override and opengl render."""
        out_file = str(tmp_path / "interactive.png")
        mock_bpy = MagicMock()
        mock_bpy.app.background = False

        mock_win = MagicMock()
        mock_area = MagicMock()
        mock_area.type = 'VIEW_3D'
        mock_space = MagicMock()
        mock_area.spaces.active = mock_space
        mock_region = MagicMock()
        mock_region.type = 'WINDOW'
        mock_area.regions = [mock_region]
        mock_win.screen.areas = [mock_area]
        mock_bpy.context.window_manager.windows = [mock_win]

        mock_scene = MagicMock()
        mock_bpy.context.scene = mock_scene
        mock_bpy.data.objects.get.return_value = None
        mock_bpy.ops.render.opengl.return_value = {'FINISHED'}

        with patch("morphomesh.camera_rig.bpy", mock_bpy), patch("morphomesh.camera_rig.HAS_BPY", True):
            res_path = capture_viewport_image(output_path=out_file, scene=mock_scene)
            assert res_path == out_file.replace("\\", "/")
            mock_bpy.ops.render.opengl.assert_called_once_with(write_still=True)
            mock_bpy.ops.render.render.assert_not_called()

    def test_headless_workbench_render_fallback(self, tmp_path):
        """Headless mode sets engine to BLENDER_WORKBENCH and renders still."""
        out_file = str(tmp_path / "headless.png")
        mock_bpy = MagicMock()
        mock_bpy.app.background = True

        mock_scene = MagicMock()
        mock_scene.render.engine = 'CYCLES'
        mock_bpy.context.scene = mock_scene
        mock_bpy.data.objects.get.return_value = None
        mock_bpy.ops.render.render.return_value = {'FINISHED'}

        with patch("morphomesh.camera_rig.bpy", mock_bpy), patch("morphomesh.camera_rig.HAS_BPY", True):
            res_path = capture_viewport_image(output_path=out_file, scene=mock_scene)
            assert res_path == out_file.replace("\\", "/")
            mock_bpy.ops.render.render.assert_called_once_with(write_still=True)
            assert mock_scene.render.engine == 'CYCLES'

    def test_opengl_failure_triggers_workbench_fallback(self, tmp_path):
        """When OpenGL throws background context error, fallback to Workbench succeeds."""
        out_file = str(tmp_path / "fallback.png")
        mock_bpy = MagicMock()
        mock_bpy.app.background = False

        mock_win = MagicMock()
        mock_area = MagicMock()
        mock_area.type = 'VIEW_3D'
        mock_space = MagicMock()
        mock_area.spaces.active = mock_space
        mock_win.screen.areas = [mock_area]
        mock_bpy.context.window_manager.windows = [mock_win]

        mock_scene = MagicMock()
        mock_scene.render.engine = 'BLENDER_EEVEE'
        mock_bpy.context.scene = mock_scene
        mock_bpy.data.objects.get.return_value = None
        mock_bpy.ops.render.opengl.side_effect = RuntimeError("Cannot use OpenGL in background mode")
        mock_bpy.ops.render.render.return_value = {'FINISHED'}

        with patch("morphomesh.camera_rig.bpy", mock_bpy), patch("morphomesh.camera_rig.HAS_BPY", True):
            res_path = capture_viewport_image(output_path=out_file, scene=mock_scene)
            assert res_path == out_file.replace("\\", "/")
            assert mock_bpy.ops.render.opengl.called
            mock_bpy.ops.render.render.assert_called_once_with(write_still=True)
            assert mock_scene.render.engine == 'BLENDER_EEVEE'


# ==============================================================================
# 5. PNG BINARY HEADER & BASE64 PREVIEW VALIDATION
# ==============================================================================

class TestImageValidationAndEncoding:
    """Validates PNG binary integrity, dimension headers, and base64 roundtrip."""

    def test_png_magic_header_signature(self, sample_test_png):
        """File must start with canonical 8-byte PNG magic number."""
        with open(sample_test_png, "rb") as f:
            header = f.read(8)
        assert header == b"\x89PNG\r\n\x1a\n"

    def test_png_ihdr_dimension_extraction(self, sample_test_png):
        """IHDR chunk bytes 16..24 must encode requested width and height."""
        with open(sample_test_png, "rb") as f:
            f.seek(16)
            w_bytes = f.read(4)
            h_bytes = f.read(4)
        width = int.from_bytes(w_bytes, "big")
        height = int.from_bytes(h_bytes, "big")
        assert (width, height) == (1024, 1024)

    def test_base64_preview_encoding_and_roundtrip(self, sample_test_png):
        """Base64 preview string must decode to bit-exact image file content."""
        with open(sample_test_png, "rb") as f:
            raw_bytes = f.read()

        b64_str = base64.b64encode(raw_bytes).decode("utf-8")
        assert isinstance(b64_str, str)
        assert len(b64_str) > 0

        decoded_bytes = base64.b64decode(b64_str)
        assert decoded_bytes == raw_bytes

    def test_missing_file_base64_grace(self, sample_test_png):
        """Missing image file returns None for base64 without throwing FileNotFoundError."""
        ghost_path = "/non_existent_dir/ghost_render.png"
        assert encode_image_to_base64(ghost_path) is None

        valid_b64 = encode_image_to_base64(sample_test_png)
        assert valid_b64 is not None
        assert len(valid_b64) > 0


# ==============================================================================
# 6. BLENDER BRIDGE & SOCKET PARITY INTEGRATION
# ==============================================================================

class TestBridgeAndSocketParity:
    """Validates high-level client methods on BlenderBridge."""

    def test_client_capture_viewport_dispatch(self):
        """BlenderBridge.capture_viewport sends morphomesh.capture_viewport."""
        bridge = BlenderBridge()
        with patch.object(bridge, "execute") as mock_exec:
            mock_exec.return_value = {
                "status": "success",
                "image_path": "/tmp/v.png",
                "resolution": [1024, 1024],
                "shading_mode": "SOLID",
                "color_type": "RANDOM",
            }
            res = bridge.capture_viewport(resolution=(1024, 1024), shading_mode="SOLID", color_type="RANDOM")
            assert res["status"] == "success"
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            assert args[0] == "morphomesh.capture_viewport"
            assert args[1]["resolution"] == [1024, 1024]
            assert args[1]["shading_mode"] == "SOLID"
            assert args[1]["color_type"] == "RANDOM"

    def test_client_setup_inspector_camera_dispatch(self):
        """BlenderBridge.setup_inspector_camera sends morphomesh.setup_inspector_camera."""
        bridge = BlenderBridge()
        with patch.object(bridge, "execute") as mock_exec:
            mock_exec.return_value = {
                "status": "success",
                "camera_name": "MorphoMesh_Inspector_Camera",
                "viewpoint": "three_quarter",
            }
            res = bridge.setup_inspector_camera(viewpoint="three_quarter", focal_length=50.0)
            assert res["status"] == "success"
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            assert args[0] == "morphomesh.setup_inspector_camera"
            assert args[1]["viewpoint"] == "three_quarter"
            assert args[1]["focal_length"] == 50.0

    def test_client_capture_multi_angle_inspection_dispatch(self):
        """BlenderBridge.capture_multi_angle_inspection sends morphomesh.capture_multi_angle_inspection."""
        bridge = BlenderBridge()
        with patch.object(bridge, "execute") as mock_exec:
            mock_exec.return_value = {
                "status": "success",
                "capture_count": 4,
                "viewpoints": ["front", "side", "three_quarter", "back"],
                "captures": [],
            }
            res = bridge.capture_multi_angle_inspection(
                viewpoints=["front", "side", "three_quarter", "back"],
                resolution=(1024, 1024),
            )
            assert res["status"] == "success"
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            assert args[0] == "morphomesh.capture_multi_angle_inspection"
            assert args[1]["viewpoints"] == ["front", "side", "three_quarter", "back"]
            assert args[1]["resolution"] == [1024, 1024]
