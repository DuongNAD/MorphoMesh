"""
Adversarial Offline Bridge Resilience & Protocol Stress Test Suite for Milestone 4 Iteration 2.

Target: tests/test_adversarial_offline_resilience_m4_iter2.py
Challenger: Challenger M4 Iter 2 - 2 (Offline Bridge & Protocol Resilience Challenger)
Milestone: Milestone 4 - FastMCP Tool Integration & Verification Suite (R4)

Empirically challenges:
1. Offline Viewport Capture Stress:
   - Forcing bridge offline (is_interactive_connected=False, blender_bin_path=None).
   - Invoking morphomesh_capture_viewport with custom path and default path.
   - Verifying output PNG file exists, starts with PNG magic header b"\\x89PNG\\r\\n\\x1a\\n".
   - Verifying base64_preview decodes to valid PNG bytes.
   - Verifying status == "success" and offline_fallback is True.
   - Testing across multiple shading modes, color types, and resolutions.
2. Offline Camera Setup Stress:
   - Forcing bridge offline.
   - Invoking morphomesh_setup_inspector_camera_rig with viewpoints ("front", "top", "bottom", "three_quarter", etc.).
   - Verifying status == "success", valid 3D coordinates [x, y, z], Euler rotation [rx, ry, rz], and offline_fallback is True.
   - Verifying coordinates are finite floats (not NaN, not Inf).
3. Protocol-Level Invocation via FastMCP:
   - Invoking via mcp.call_tool when offline.
4. Pre-Flight Rejection Priority:
   - Verifying invalid arguments still raise ToolError even when offline (pre-flight before fallback).
5. Operational Error Non-Masking:
   - Verifying ERR_CAMERA_FAILED is re-raised as ToolError and not masked as offline fallback.
"""

from __future__ import annotations

import base64
import json
import math
import os
import tempfile
from typing import Any, Dict
from unittest.mock import patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.camera_rig import FALLBACK_PNG_BYTES
from morphomesh.models import MorphoMeshException
from morphomesh.server import (
    blender_bridge,
    mcp,
    morphomesh_capture_viewport,
    morphomesh_setup_inspector_camera_rig,
)


@pytest.fixture(autouse=True)
def enable_inspection_tools(monkeypatch: pytest.MonkeyPatch):
    """Ensure inspection tools are active for testing."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


# ==============================================================================
# 1. OFFLINE VIEWPORT CAPTURE STRESS TESTS
# ==============================================================================

class TestOfflineViewportCaptureStress:
    """Empirical verification of morphomesh_capture_viewport in offline mode."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shading_mode", ["SOLID", "WIREFRAME", "MATERIAL", "RENDERED"])
    @pytest.mark.parametrize("color_type", ["RANDOM", "MATERIAL", "SINGLE", "OBJECT", "TEXTURE"])
    async def test_offline_viewport_capture_shading_and_color_variants(
        self, tmp_path, shading_mode: str, color_type: str
    ):
        """Test offline viewport capture across all valid shading modes and color types."""
        out_png = str(tmp_path / f"offline_{shading_mode}_{color_type}.png")

        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_capture_viewport(
                output_path=out_png,
                shading_mode=shading_mode,
                color_type=color_type,
                resolution=[512, 512],
            )

            assert isinstance(res, dict), f"Expected dict result, got {type(res)}"
            assert res.get("status") == "success", f"Expected status='success', got {res.get('status')}"
            assert res.get("offline_fallback") is True, "offline_fallback must be True"

            # Verify output file on disk
            assert os.path.isfile(out_png), f"File was not created on disk: {out_png}"
            with open(out_png, "rb") as f:
                disk_content = f.read()
            assert disk_content.startswith(PNG_HEADER), "Disk file does not start with PNG magic bytes"
            assert len(disk_content) > 0

            # Verify base64_preview
            assert "base64_preview" in res, "Missing base64_preview in result"
            b64_str = res["base64_preview"]
            decoded_bytes = base64.b64decode(b64_str)
            assert decoded_bytes.startswith(PNG_HEADER), "Decoded base64 does not start with PNG magic bytes"
            assert decoded_bytes == disk_content or decoded_bytes == FALLBACK_PNG_BYTES

    @pytest.mark.asyncio
    async def test_offline_viewport_capture_default_path(self):
        """Test offline viewport capture when output_path is None (auto-generated)."""
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_capture_viewport(output_path=None)

            assert res.get("status") == "success"
            assert res.get("offline_fallback") is True
            image_path = res.get("image_path") or res.get("output_path")
            assert image_path is not None
            assert os.path.isfile(image_path)
            with open(image_path, "rb") as f:
                content = f.read()
            assert content.startswith(PNG_HEADER)

            # Cleanup
            try:
                os.remove(image_path)
            except OSError:
                pass

    @pytest.mark.asyncio
    @pytest.mark.parametrize("resolution", [[256, 256], [1024, 1024], [1920, 1080]])
    async def test_offline_viewport_capture_resolutions(self, tmp_path, resolution):
        """Test offline viewport capture with different positive resolutions."""
        out_png = str(tmp_path / f"offline_res_{resolution[0]}_{resolution[1]}.png")

        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_capture_viewport(
                output_path=out_png,
                resolution=resolution,
            )
            assert res.get("status") == "success"
            assert res.get("offline_fallback") is True
            assert res.get("resolution") == resolution


# ==============================================================================
# 2. OFFLINE CAMERA SETUP STRESS TESTS
# ==============================================================================

class TestOfflineCameraSetupStress:
    """Empirical verification of morphomesh_setup_inspector_camera_rig in offline mode."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("viewpoint", [
        "front",
        "top",
        "bottom",
        "three_quarter",
        "side",
        "back",
        "head",
        "hands",
        "turntable",
        "turntable_4views",
    ])
    async def test_offline_camera_setup_viewpoints(self, viewpoint: str):
        """
        Verify offline setup_inspector_camera_rig across various viewpoints:
        - front, top, bottom, three_quarter, side, back, head, hands, turntable, turntable_4views
        - Must return status='success', valid 3D coordinates [x, y, z], Euler rotation [rx, ry, rz],
          and offline_fallback=True.
        """
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_setup_inspector_camera_rig(
                viewpoint=viewpoint,
                focal_length=50.0,
                camera_name="MorphoMesh_Inspector_Camera",
            )

            assert isinstance(res, dict), f"Expected dict, got {type(res)}"
            assert res.get("status") == "success", f"Expected status='success', got {res.get('status')}"
            assert res.get("offline_fallback") is True, f"Expected offline_fallback=True, got {res.get('offline_fallback')}"
            assert res.get("viewpoint") == viewpoint

            # Verify 3D coordinates: location or position
            coords = res.get("location") or res.get("position") or res.get("camera_location")
            assert coords is not None, f"Missing camera location in result: {res}"
            assert isinstance(coords, (list, tuple)), f"Coords must be list/tuple, got {type(coords)}"
            assert len(coords) == 3, f"Expected 3 coords [x, y, z], got {len(coords)}: {coords}"
            for i, c in enumerate(coords):
                assert isinstance(c, (int, float)), f"Coord {i} is not a number: {c}"
                assert not math.isnan(c) and not math.isinf(c), f"Coord {i} is non-finite: {c}"

            # Verify Euler rotation: rotation_euler or rotation
            rot = res.get("rotation_euler") or res.get("rotation") or res.get("camera_rotation")
            assert rot is not None, f"Missing camera rotation in result: {res}"
            assert isinstance(rot, (list, tuple)), f"Rotation must be list/tuple, got {type(rot)}"
            assert len(rot) == 3, f"Expected 3 Euler angles [rx, ry, rz], got {len(rot)}: {rot}"
            for i, r in enumerate(rot):
                assert isinstance(r, (int, float)), f"Rotation {i} is not a number: {r}"
                assert not math.isnan(r) and not math.isinf(r), f"Rotation {i} is non-finite: {r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target_center", [
        [0.0, 0.0, 0.0],
        [1.5, -2.0, 0.825],
        [0.0, 1.65, 0.0],
    ])
    async def test_offline_camera_setup_with_target_center(self, target_center):
        """Verify offline setup_inspector_camera_rig with specific target center."""
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await morphomesh_setup_inspector_camera_rig(
                viewpoint="three_quarter",
                target_center=target_center,
                focal_length=85.0,
            )

            assert res.get("status") == "success"
            assert res.get("offline_fallback") is True
            coords = res.get("location") or res.get("position")
            assert coords is not None and len(coords) == 3
            # Check focal length preserved
            assert res.get("focal_length") == 85.0


# ==============================================================================
# 3. FASTMCP PROTOCOL-LEVEL INVOCATION TESTS
# ==============================================================================

class TestFastMCPProtocolOfflineStress:
    """Empirical verification via mcp.call_tool in offline mode."""

    @pytest.mark.asyncio
    async def test_protocol_call_tool_capture_viewport_offline(self, tmp_path):
        """mcp.call_tool('morphomesh_capture_viewport') when bridge is offline."""
        out_file = str(tmp_path / "protocol_offline.png")

        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await mcp.call_tool(
                "morphomesh_capture_viewport",
                {"output_path": out_file, "shading_mode": "SOLID"},
            )

            content = res[0] if isinstance(res, tuple) else res
            text_content = content[0]
            data = json.loads(text_content.text)

            assert data.get("status") == "success"
            assert data.get("offline_fallback") is True
            assert "base64_preview" in data
            raw = base64.b64decode(data["base64_preview"])
            assert raw.startswith(PNG_HEADER)
            assert os.path.isfile(out_file)

    @pytest.mark.asyncio
    async def test_protocol_call_tool_setup_camera_offline(self):
        """mcp.call_tool('morphomesh_setup_inspector_camera_rig') when bridge is offline."""
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            res = await mcp.call_tool(
                "morphomesh_setup_inspector_camera_rig",
                {"viewpoint": "bottom", "focal_length": 50.0},
            )

            content = res[0] if isinstance(res, tuple) else res
            text_content = content[0]
            data = json.loads(text_content.text)

            assert data.get("status") == "success"
            assert data.get("offline_fallback") is True
            assert data.get("viewpoint") == "bottom"
            coords = data.get("location") or data.get("position")
            assert len(coords) == 3


# ==============================================================================
# 4. PRE-FLIGHT VALIDATION PRIORITY TESTS (EVEN WHEN OFFLINE)
# ==============================================================================

class TestPreflightValidationPriorityOffline:
    """Pre-flight parameter validation must take precedence over offline fallback."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_viewpoint", ["invalid_vp", "unknown", ""])
    async def test_invalid_viewpoint_rejected_when_offline(self, invalid_viewpoint: str):
        """Invalid viewpoints must raise ToolError even when bridge is offline."""
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            with pytest.raises(ToolError, match=r"(?i)(viewpoint|validation)"):
                await morphomesh_setup_inspector_camera_rig(viewpoint=invalid_viewpoint)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_shading", ["INVALID_SHADING", "RAYTRACING", ""])
    async def test_invalid_shading_rejected_when_offline(self, invalid_shading: str):
        """Invalid shading modes must raise ToolError even when bridge is offline."""
        with patch.object(blender_bridge, "is_interactive_connected", return_value=False), \
             patch.object(blender_bridge, "blender_bin_path", None):
            with pytest.raises(ToolError, match=r"(?i)(shading_mode|validation)"):
                await morphomesh_capture_viewport(shading_mode=invalid_shading)


# ==============================================================================
# 5. OPERATIONAL ERROR NON-MASKING TESTS
# ==============================================================================

class TestOperationalErrorNonMasking:
    """Operational exceptions (ERR_CAMERA_FAILED) must NOT be masked as offline fallbacks."""

    @pytest.mark.asyncio
    async def test_operational_camera_error_not_masked(self):
        """When bridge raises ERR_CAMERA_FAILED, it must raise ToolError, not return offline_fallback."""
        with patch.object(
            blender_bridge,
            "setup_inspector_camera",
            side_effect=MorphoMeshException("ERR_CAMERA_FAILED", "Camera framing failed internally"),
        ):
            with pytest.raises(ToolError, match=r"ERR_CAMERA_FAILED"):
                await morphomesh_setup_inspector_camera_rig(viewpoint="front")

    @pytest.mark.asyncio
    async def test_operational_capture_error_not_masked(self):
        """When bridge raises ERR_RENDER_FAILED, it must raise ToolError, not return offline_fallback."""
        with patch.object(
            blender_bridge,
            "capture_viewport",
            side_effect=MorphoMeshException("ERR_RENDER_FAILED", "Render pipeline crashed"),
        ):
            with pytest.raises(ToolError, match=r"ERR_RENDER_FAILED"):
                await morphomesh_capture_viewport()
