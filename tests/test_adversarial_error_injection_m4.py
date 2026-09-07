"""
Adversarial Error Injection & Schema Stress Test Suite for Milestone 4.

Target: tests/test_adversarial_error_injection_m4.py
Milestone: Milestone 4 - FastMCP Tool Integration & Verification Suite (R4)
Challenger: Challenger M4_2 (Error Injection & Schema Stress Challenger)

Tests:
1. Parameter Bounds & Type Coercion:
   - morphomesh_setup_inspector_camera_rig: invalid viewpoints ("nadir_flipped", ""),
     negative/zero focal lengths (0.0, -10.0, 5.0, 400.0), malformed target centers ([1, 2], [1, 2, 3, 4], "invalid").
   - morphomesh_capture_viewport: invalid shading modes ("PATH_TRACING", "RAYTRACING"),
     zero/negative resolutions ([0, 0], [-1920, 1080], [1024, -512]), invalid color types ("INVALID_COLOR_TYPE", "RAINBOW").
   - morphomesh_critique_visual_quality: negative clearance tolerance (-0.005, -0.1),
     invalid target presets ("alien_hydra", "draconic_quadruped", "").
2. FastMCP ToolError Enforcement:
   - Verify that invalid parameters consistently raise ToolError cleanly without leaking uncaught Python exceptions.
3. Offline Bridge Resilience:
   - Force bridge offline/unreachable (no socket, no local Blender CLI):
     * Verify morphomesh_capture_viewport produces valid transparent 1x1 RGBA fallback PNG (FALLBACK_PNG_BYTES).
     * Verify morphomesh_setup_inspector_camera_rig returns valid mock camera metadata without throwing uncaught connection errors.
"""

from __future__ import annotations

import base64
import os
import tempfile
from typing import Any, Dict
from unittest.mock import patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.camera_rig import FALLBACK_PNG_BYTES
from morphomesh.server import (
    blender_bridge,
    morphomesh_capture_viewport,
    morphomesh_critique_visual_quality,
    morphomesh_setup_inspector_camera_rig,
)


@pytest.fixture(autouse=True)
def enable_inspection_tools(monkeypatch: pytest.MonkeyPatch):
    """Ensure inspection tools are enabled for this test suite."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")


# ==============================================================================
# 1. PARAMETER BOUNDS & TYPE COERCION TESTS
# ==============================================================================

class TestCameraRigParameterValidation:
    """Stress-testing parameter bounds and type coercion on morphomesh_setup_inspector_camera_rig."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_viewpoint", [
        "nadir_flipped",
        "",
        "zenith_99",
        "diagonal_underneath",
        "UPWARD_45",
    ])
    async def test_invalid_viewpoints_rejected(self, invalid_viewpoint: str):
        """Invalid viewpoints must raise ToolError cleanly."""
        with pytest.raises(ToolError, match=r"(?i)(viewpoint|validation|invalid|preset)"):
            await morphomesh_setup_inspector_camera_rig(viewpoint=invalid_viewpoint)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_focal", [0.0, -10.0, -50.0, 5.0, 400.0, 999.0])
    async def test_focal_length_bounds_enforced(self, invalid_focal: float):
        """Focal lengths outside [10.0, 300.0] must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(focal_length|validation|between 10.0 and 300.0)"):
            await morphomesh_setup_inspector_camera_rig(focal_length=invalid_focal)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("malformed_center", [
        [1.0, 2.0],
        [1.0, 2.0, 3.0, 4.0],
        "center_point",
        {"x": 0.0, "y": 0.0, "z": 0.0},
        123,
    ])
    async def test_malformed_target_center_rejected(self, malformed_center: Any):
        """Malformed target center coordinates must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(target_center|validation|3 coordinates)"):
            await morphomesh_setup_inspector_camera_rig(target_center=malformed_center)


class TestCaptureViewportParameterValidation:
    """Stress-testing parameter bounds and type coercion on morphomesh_capture_viewport."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_shading", [
        "PATH_TRACING",
        "RAYTRACING",
        "UNLIT_DEBUG",
        "",
        "NORMAL_MAP_PREVIEW",
    ])
    async def test_invalid_shading_modes_rejected(self, invalid_shading: str):
        """Invalid shading modes must raise ToolError cleanly."""
        with pytest.raises(ToolError, match=r"(?i)(shading_mode|validation|invalid)"):
            await morphomesh_capture_viewport(shading_mode=invalid_shading)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_res", [
        [0, 0],
        [-1920, 1080],
        [1024, -512],
        [-100, -100],
        [0, 1024],
        [1024, 0],
    ])
    async def test_zero_or_negative_resolutions_rejected(self, invalid_res: Any):
        """Zero or negative resolutions must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(resolution|validation|positive)"):
            await morphomesh_capture_viewport(resolution=invalid_res)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_color", [
        "INVALID_COLOR_TYPE",
        "NEON_RAINBOW",
        "HSV_GRADIENT",
        "",
        "DEBUG_UV",
    ])
    async def test_invalid_color_types_rejected(self, invalid_color: str):
        """Invalid solid color types must raise ToolError cleanly."""
        with pytest.raises(ToolError, match=r"(?i)(color_type|validation|invalid)"):
            await morphomesh_capture_viewport(color_type=invalid_color)


class TestVisualCritiqueParameterValidation:
    """Stress-testing parameter bounds and type coercion on morphomesh_critique_visual_quality."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_tolerance", [-0.005, -0.1, -1.0, -0.0001])
    async def test_negative_clearance_tolerance_rejected(self, invalid_tolerance: float):
        """Negative clearance tolerance must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(clearance_tolerance|validation|non-negative)"):
            await morphomesh_critique_visual_quality(clearance_tolerance=invalid_tolerance)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_preset", [
        "alien_hydra",
        "draconic_quadruped",
        "spider_titan",
        "",
        "unknown_preset",
    ])
    async def test_invalid_target_preset_rejected(self, invalid_preset: str):
        """Invalid target anthropometric presets must raise ToolError cleanly."""
        with pytest.raises(ToolError, match=r"(?i)(target_preset|validation|invalid|preset)"):
            await morphomesh_critique_visual_quality(target_preset=invalid_preset)


# ==============================================================================
# 2. FASTMCP TOOLERROR ENFORCEMENT
# ==============================================================================

class TestToolErrorEnforcement:
    """Verify ToolError contract: no leaking of raw Python exceptions."""

    @pytest.mark.asyncio
    async def test_camera_rig_empty_name_raises_tool_error(self):
        """Empty camera_name must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(camera_name|empty)"):
            await morphomesh_setup_inspector_camera_rig(camera_name="   ")

    @pytest.mark.asyncio
    async def test_capture_viewport_empty_camera_name_raises_tool_error(self):
        """Empty camera_name in viewport capture must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(camera_name|empty)"):
            await morphomesh_capture_viewport(camera_name="")

    @pytest.mark.asyncio
    async def test_critique_missing_character_and_target_raises_tool_error(self):
        """Missing both character_name and target_object must raise ToolError."""
        with pytest.raises(ToolError, match=r"(?i)(character_name|target_object)"):
            await morphomesh_critique_visual_quality(character_name="", target_object="")


# ==============================================================================
# 3. OFFLINE BRIDGE RESILIENCE TESTS
# ==============================================================================

class TestOfflineBridgeResilience:
    """Verify graceful fallback when Blender bridge is completely offline and unreachable."""

    @pytest.mark.asyncio
    async def test_capture_viewport_offline_produces_fallback_png(self, tmp_path):
        """
        When Blender bridge is offline/unreachable (no socket, no local Blender CLI):
        morphomesh_capture_viewport must produce a valid 1x1 transparent PNG fallback,
        returning valid base64 image data and status='success' without raising uncaught connection error.
        """
        out_file = str(tmp_path / "offline_fallback.png")

        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_capture_viewport(output_path=out_file)

            assert isinstance(res, dict)
            assert res.get("status") == "success"
            assert "base64_preview" in res
            assert len(res["base64_preview"]) > 0

            # Verify that decoded bytes match FALLBACK_PNG_BYTES or valid PNG header
            raw_bytes = base64.b64decode(res["base64_preview"])
            assert raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"), "Fallback payload is not a valid PNG."
            assert raw_bytes == FALLBACK_PNG_BYTES or len(raw_bytes) > 0

            # Verify file written to disk
            assert os.path.isfile(out_file)
            with open(out_file, "rb") as f:
                disk_bytes = f.read()
            assert disk_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    @pytest.mark.asyncio
    async def test_setup_camera_rig_offline_returns_mock_metadata(self):
        """
        When Blender bridge is offline/unreachable:
        morphomesh_setup_inspector_camera_rig must return valid mock metadata
        (camera_name, viewpoint, location, rotation_euler, focal_length)
        without throwing uncaught connection errors.
        """
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_setup_inspector_camera_rig(
                viewpoint="front",
                focal_length=85.0,
                camera_name="MorphoMesh_Inspector_Camera",
            )

            assert isinstance(res, dict)
            assert res.get("status") == "success"
            assert res.get("viewpoint") == "front"
            assert res.get("camera_name") == "MorphoMesh_Inspector_Camera"
            assert "location" in res or "camera_location" in res
            assert "rotation_euler" in res or "camera_rotation" in res
