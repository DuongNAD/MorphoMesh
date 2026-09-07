"""
Adversarial Stress Test Suite for FastMCP Server and Blender Bridge Integration
Targets:
  - src/morphomesh/server.py
  - src/morphomesh/blender_bridge.py
  - src/morphomesh/models.py
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import socket
import tempfile
import threading
import time
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from morphomesh.blender_bridge import BlenderBridge, BlenderExecutionError, BpyCodeValidator
from morphomesh.models import (
    AutoRigHumanInput,
    CreateHumanAssetInput,
    DressHumanInput,
    GroomHumanInput,
    HumanAnatomyConfig,
    SetupHumanMaterialsInput,
)
from morphomesh.server import (
    HUMAN_TOOL_NAMES,
    mcp,
    morphomesh_auto_rig_human,
    morphomesh_create_human_asset,
    morphomesh_dress_human,
    morphomesh_groom_human,
    morphomesh_setup_human_materials,
)


@pytest.fixture(autouse=True)
def enable_human_tools(monkeypatch: pytest.MonkeyPatch):
    """Ensure FastMCP exposes all 12 tools."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")


# ==============================================================================
# 1. BOUNDARY AND INVALID INPUT STRESS TESTS
# ==============================================================================

class TestBoundaryAndInvalidInputs:
    """Stress tests parameter validation boundaries across all 5 human tools."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_height", [-1.0, 0.0, 0.5, 0.99, 2.51, 5.0, 100.0, float("nan"), float("inf")])
    async def test_create_human_asset_invalid_height(self, invalid_height):
        with pytest.raises(ToolError):
            await morphomesh_create_human_asset(height=invalid_height)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_head_ratio", [-5.0, 0.0, 3.0, 4.99, 10.01, 15.0, float("nan"), float("inf")])
    async def test_create_human_asset_invalid_head_ratio(self, invalid_head_ratio):
        with pytest.raises(ToolError):
            await morphomesh_create_human_asset(head_ratio=invalid_head_ratio)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_chest", [0.2, 0.49, 1.51, 3.0, -0.5])
    async def test_create_human_asset_invalid_chest_girth(self, invalid_chest):
        with pytest.raises(ToolError):
            await morphomesh_create_human_asset(chest_girth=invalid_chest)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_waist", [0.1, 0.39, 1.21, 2.0, -0.2])
    async def test_create_human_asset_invalid_waist_girth(self, invalid_waist):
        with pytest.raises(ToolError):
            await morphomesh_create_human_asset(waist_girth=invalid_waist)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_hip", [0.2, 0.49, 1.51, 3.0, -0.5])
    async def test_create_human_asset_invalid_hip_girth(self, invalid_hip):
        with pytest.raises(ToolError):
            await morphomesh_create_human_asset(hip_girth=invalid_hip)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_poly", [-100, 0, 500, 999, 200001, 1000000])
    async def test_create_human_asset_invalid_poly_budget(self, invalid_poly):
        with pytest.raises(ToolError):
            await morphomesh_create_human_asset(poly_budget=invalid_poly)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_strands", [-50, 0, 500, 999, 200001, 500000])
    async def test_groom_human_invalid_strand_count(self, invalid_strands):
        with pytest.raises(ToolError):
            await morphomesh_groom_human(strand_count=invalid_strands)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_butterflies", [-10, 0, 51, 100])
    async def test_dress_human_invalid_butterfly_count(self, invalid_butterflies):
        with pytest.raises(ToolError):
            await morphomesh_dress_human(butterfly_count=invalid_butterflies)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_offset", [-0.01, 0.0, 0.001, 0.0049, 0.051, 0.5])
    async def test_dress_human_invalid_clearance_offset(self, invalid_offset):
        with pytest.raises(ToolError):
            await morphomesh_dress_human(clearance_offset=invalid_offset)

    @pytest.mark.asyncio
    async def test_unicode_and_special_character_names(self):
        """Verify non-ASCII names and characters do not crash the engine."""
        res = await morphomesh_create_human_asset(character_name="余念安_Yu_Nian_An_测试")
        assert res.get("status") == "success"
        assert res.get("character_name") == "余念安_Yu_Nian_An_测试"


# ==============================================================================
# 2. FASTMCP EXCEPTION CONTAINMENT & SERVER CRASH RESILIENCE
# ==============================================================================

class TestFastMCPExceptionContainment:
    """Verifies that no uncaught exceptions escape or crash the FastMCP server."""

    @pytest.mark.asyncio
    async def test_call_tool_with_invalid_arguments_raises_tool_error(self):
        """FastMCP client invocation gracefully raises ToolError instead of unhandled crash."""
        with pytest.raises(ToolError):
            await mcp.call_tool("morphomesh_create_human_asset", {"height": "invalid_string"})

        with pytest.raises(ToolError):
            await mcp.call_tool("morphomesh_groom_human", {"strand_count": -999})

        with pytest.raises(ToolError):
            await mcp.call_tool("morphomesh_dress_human", {"butterfly_count": 999})

    @pytest.mark.asyncio
    async def test_context_reporting_resilience_when_ctx_throws(self):
        """Verify tool execution succeeds even when Context logging raises exceptions."""
        broken_ctx = MagicMock()
        broken_ctx.info = AsyncMock(side_effect=RuntimeError("Logging stream corrupted"))
        broken_ctx.report_progress = AsyncMock(side_effect=RuntimeError("Progress stream closed"))

        res = await morphomesh_create_human_asset(
            character_name="Ctx_Resilience_Test",
            ctx=broken_ctx,
        )
        assert res.get("status") == "success"
        assert res.get("character_name") == "Ctx_Resilience_Test"

        res_rig = await morphomesh_auto_rig_human(ctx=broken_ctx)
        assert res_rig.get("status") == "success"

        res_mat = await morphomesh_setup_human_materials(ctx=broken_ctx)
        assert res_mat.get("status") == "success"

        res_groom = await morphomesh_groom_human(ctx=broken_ctx)
        assert res_groom.get("status") == "success"

        res_dress = await morphomesh_dress_human(ctx=broken_ctx)
        assert res_dress.get("status") == "success"


# ==============================================================================
# 3. BRIDGE FALLBACK & CONNECTIVITY STRESS TESTS
# ==============================================================================

class TestBridgeConnectivityAndFallbackMatrix:
    """Stress tests BlenderBridge under various socket and headless conditions."""

    def test_offline_local_procedural_fallback(self):
        """When socket is unreachable and headless runner is unavailable, local fallback must succeed."""
        bridge = BlenderBridge(port=19999, socket_timeout=0.2)
        bridge.blender_bin_path = None  # Disable headless runner

        # 1. create_human_asset
        res1 = bridge.create_human_asset(character_name="Offline_Test")
        assert res1.get("status") == "success"
        assert res1.get("character_name") == "Offline_Test"
        assert os.path.exists(res1.get("mesh_path"))

        # 2. auto_rig_human
        res2 = bridge.auto_rig_human()
        assert res2.get("status") == "success"
        assert res2.get("def_bone_count") == 163

        # 3. setup_human_materials
        res3 = bridge.setup_human_materials()
        assert res3.get("status") == "success"
        assert len(res3.get("materials_created", [])) >= 5

        # 4. groom_human
        res4 = bridge.groom_human()
        assert res4.get("status") == "success"
        assert res4.get("strand_count") == 15000

        # 5. dress_human
        res5 = bridge.dress_human()
        assert res5.get("status") == "success"
        assert res5.get("prop_count") >= 20

    def test_hanging_socket_times_out_cleanly(self):
        """When socket server hangs, send_socket_request enforces timeout and raises TimeoutError."""
        port = 19890
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        s.listen(5)
        running = True

        def hang():
            while running:
                try:
                    conn, _ = s.accept()
                    time.sleep(3)
                    conn.close()
                except Exception:
                    break

        th = threading.Thread(target=hang, daemon=True)
        th.start()
        time.sleep(0.1)

        try:
            bridge = BlenderBridge(port=port, socket_timeout=0.2)
            t0 = time.time()
            with pytest.raises(TimeoutError):
                bridge.send_socket_request("ping", {}, timeout=0.5)
            elapsed = time.time() - t0
            assert elapsed < 2.0, f"Hanging socket took too long: {elapsed:.2f}s"
        finally:
            running = False
            s.close()

    def test_corrupted_socket_data_handled_gracefully(self):
        """When socket sends garbage/corrupted bytes, bridge must catch error and fall back."""
        port = 19891
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        s.listen(5)
        running = True

        def garbage():
            while running:
                try:
                    conn, _ = s.accept()
                    conn.sendall(b"HTTP/1.1 500 Internal Server Error\r\n\r\nCorrupted binary payload \x00\xff")
                    conn.close()
                except Exception:
                    break

        th = threading.Thread(target=garbage, daemon=True)
        th.start()
        time.sleep(0.1)

        try:
            bridge = BlenderBridge(port=port, socket_timeout=0.2)
            bridge.blender_bin_path = None
            res = bridge.create_human_asset(character_name="Garbage_Test")
            assert res.get("status") == "success"
        finally:
            running = False
            s.close()

    def test_socket_error_response_handled_gracefully(self):
        """When socket returns JSON with status error, bridge must fall back."""
        port = 19892
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        s.listen(5)
        running = True

        def err_resp():
            while running:
                try:
                    conn, _ = s.accept()
                    conn.recv(1024)
                    conn.sendall(json.dumps({"jsonrpc": "2.0", "status": "error", "message": "Simulated Blender Failure"}).encode("utf-8") + b"\n")
                    conn.close()
                except Exception:
                    break

        th = threading.Thread(target=err_resp, daemon=True)
        th.start()
        time.sleep(0.1)

        try:
            bridge = BlenderBridge(port=port, socket_timeout=0.2)
            bridge.blender_bin_path = None
            res = bridge.create_human_asset(character_name="Err_Test")
            assert res.get("status") == "success"
        finally:
            running = False
            s.close()


# ==============================================================================
# 4. EMPIRICAL DISCREPANCY & ADVERSARIAL BUG PROBES
# ==============================================================================

class TestEmpiricalDiscrepanciesAndBugs:
    """
    Empirical tests probing specific implementation discrepancies and parameter
    dropping bugs identified during adversarial review.
    """

    @pytest.mark.asyncio
    async def test_challenge_head_ratio_dropped(self):
        """
        RESOLVED:
        Verify that `head_ratio` parameter is preserved by blender_bridge.py
        when generating human mesh (both in params serialization and procedural fallback).
        """
        res = await morphomesh_create_human_asset(head_ratio=8.5)
        returned_head_ratio = res.get("head_ratio")
        assert abs(returned_head_ratio - 8.5) < 0.1, (
            f"Returned head_ratio was {returned_head_ratio}, expected requested ~8.5"
        )

    @pytest.mark.asyncio
    async def test_challenge_config_object_ignored(self):
        """
        RESOLVED:
        Verify that passing a `config: HumanAnatomyConfig` object to
        `morphomesh_create_human_asset` is unpacked and applied rather than ignored.
        """
        custom_cfg = HumanAnatomyConfig(height=1.85, head_ratio=8.2, chest_girth=0.90)
        res = await morphomesh_create_human_asset(config=custom_cfg)
        assert res.get("height") == 1.85, (
            f"Expected config height 1.85, returned {res.get('height')}"
        )
        assert abs(res.get("head_ratio", 0.0) - 8.2) < 0.1

    @pytest.mark.asyncio
    async def test_challenge_clearance_offset_hardcoded_in_headless_script(self):
        """
        RESOLVED:
        Verify that `clearance_offset` in `morphomesh_dress_human` uses the requested
        parameter value rather than hardcoding 0.015.
        """
        res = await morphomesh_dress_human(clearance_offset=0.035)
        returned_offset = res.get("clearance_offset")
        assert abs(returned_offset - 0.035) < 1e-4, (
            f"Expected clearance_offset=0.035, got {returned_offset}"
        )

    @pytest.mark.asyncio
    async def test_challenge_export_format_fbx_phantom_file(self):
        """
        RESOLVED:
        Verify that requesting `export_format='fbx'` in `create_human_asset`
        actually exports the FBX file to disk.
        """
        res = await morphomesh_create_human_asset(export_format="fbx")
        mesh_path = res.get("mesh_path")
        assert mesh_path.endswith(".fbx")
        assert os.path.exists(mesh_path), (
            f"Expected FBX file to exist at {mesh_path}"
        )

    @pytest.mark.asyncio
    async def test_challenge_auto_rig_exported_mesh_path_phantom_file(self):
        """
        RESOLVED:
        Verify that `morphomesh_auto_rig_human` actually exports the rigged mesh
        file to disk.
        """
        res = await morphomesh_auto_rig_human()
        rig_path = res.get("exported_mesh_path")
        assert rig_path is not None
        assert os.path.exists(rig_path), (
            f"Expected rigged FBX file to exist at {rig_path}"
        )

    def test_challenge_dress_human_fallback_outfit_preset_mismatch(self):
        """
        RESOLVED:
        Verify that `BlenderBridge.dress_human` procedural fallback returns
        `outfit_preset` when specified.
        """
        bridge = BlenderBridge(port=19998, socket_timeout=0.1)
        bridge.blender_bin_path = None
        res = bridge.dress_human(outfit_preset="court_dress")
        assert res.get("outfit_preset") == "court_dress", (
            f"Expected outfit_preset='court_dress', got {res.get('outfit_preset')}"
        )

    def test_challenge_generated_headless_script_fails_code_validator(self):
        """
        CHALLENGE ISSUE:
        Verify that `BpyCodeValidator` rejects `_generate_headless_script` outputs,
        proving that the interactive socket `execute_code` bridge fallback can never succeed.
        """
        bridge = BlenderBridge()
        validator = BpyCodeValidator()
        script = bridge._generate_headless_script("morphomesh.create_human_asset", {"character_name": "test"})

        # Script length exceeds 10,000 characters limit (actual ~67,000 chars)
        with pytest.raises(Exception) as exc_info:
            validator.validate(script)
        assert "exceeds maximum length" in str(exc_info.value)
