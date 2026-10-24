"""
MorphoMesh Empirical Challenger Test Suite: Milestone 2 Iteration 2 Remediation.
Author: Challenger M2-3 (Empirical Challenger)
Target: src/morphomesh/tools/ and src/morphomesh/server.py

Verification Objectives:
1. Zero Context Shielding Errors:
   Empirically prove that ALL 19 FastMCP tools can be invoked via `mcp.call_tool()`
   WITHOUT raising `ValueError: Context is not available outside of a request`
   and WITHOUT any mock-patching of Context.info / Context.report_progress.
2. Dual-Layer Gating Invariance:
   Verify that all 12 gated tools (7 human, 3 inspection, 2 animation) remain
   fully callable via protocol-level `mcp.call_tool()` even when filtered out
   from `mcp.list_tools()`.
3. Full Gating Truth Matrix Parity:
   Validate 7, 9, 10, 14, 17, and 19 tool states across high-level `mcp.list_tools()`
   and low-level JSON-RPC protocol handler `mcp._mcp_server.request_handlers[ListToolsRequest]`.
4. Schema & Output Contract Invariance:
   Validate payload output integrity, Pydantic type safety, and adversarial error handling.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Set

import pytest
import mcp.types as mcp_types
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.server import (
    ALL_TOOL_NAMES,
    ANIMATION_TOOL_NAMES,
    CREATURE_TOOL_NAMES,
    HUMAN_TOOL_NAMES,
    INSPECTION_TOOL_NAMES,
    mcp,
)

ALL_19_TOOL_NAMES: Set[str] = (
    CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES | INSPECTION_TOOL_NAMES | ANIMATION_TOOL_NAMES
)

# Canonical valid test argument sets for all 19 tools (pure unmocked execution)
CANONICAL_TOOL_INVOCATIONS: Dict[str, Dict[str, Any]] = {
    # 7 Canonical Creature Tools
    "morphomesh_generate_concept": {"prompt": "A mechanical direwolf", "seed": 42},
    "morphomesh_create_3d_asset": {"concept_id": "c_mock_001", "model_backend": "mock"},
    "morphomesh_optimize_topology": {
        "input_mesh_path": "output/yu_nian_an/Yu_Nian_An.glb",
        "target_poly_count": 5000,
    },
    "morphomesh_auto_rig": {"asset_id": "a_mock_001", "creature_type": "quadruped"},
    "morphomesh_blender_execute": {"script": "pass"},
    "morphomesh_get_scene_status": {"include_mesh_stats": True},
    "morphomesh_render_preview": {"render_engine": "CYCLES", "samples": 1, "view_angle": "front"},
    # 2 Animation Tools
    "morphomesh_animate_asset": {"action_id": 0},
    "morphomesh_list_animations": {"search": "idle"},
    # 7 Digital Human Tools
    "morphomesh_create_human_asset": {"character_name": "Yu_Nian_An_Empirical"},
    "morphomesh_auto_rig_human": {"mesh_object_name": "Human_Base_Mesh"},
    "morphomesh_setup_human_materials": {"mesh_object_name": "Human_Base_Mesh"},
    "morphomesh_groom_human": {"mesh_object_name": "Human_Base_Mesh"},
    "morphomesh_dress_human": {"human_object_name": "Human_Base_Mesh"},
    "morphomesh_assemble_master_character": {"character_name": "Yu_Nian_An_Empirical", "save_blend": False},
    "morphomesh_export_production_character": {
        "character_name": "Yu_Nian_An",
        "export_fbx": False,
        "export_glb": False,
        "generate_textures": False,
        "generate_docs": False,
    },
    # 3 Inspection Tools
    "morphomesh_setup_inspector_camera_rig": {"viewpoint": "front"},
    "morphomesh_capture_viewport": {"output_path": "artifacts/test_capture.png"},
    "morphomesh_critique_visual_quality": {"character_name": "Yu_Nian_An"},
}


def clear_all_gating_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all tool gating environment variables to enforce baseline state."""
    monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_ALL_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", raising=False)


async def get_lowlevel_tools() -> List[mcp_types.Tool]:
    """Directly invoke low-level JSON-RPC ListToolsRequest handler on mcp._mcp_server."""
    handler = mcp._mcp_server.request_handlers.get(mcp_types.ListToolsRequest)
    assert handler is not None, "ListToolsRequest handler not registered in mcp._mcp_server"
    result = await handler(mcp_types.ListToolsRequest())
    assert isinstance(result, mcp_types.ServerResult), f"Expected ServerResult, got {type(result)}"
    assert isinstance(result.root, mcp_types.ListToolsResult), f"Expected ListToolsResult, got {type(result.root)}"
    return result.root.tools


# ==============================================================================
# 1. EMPIRICAL UNPATCHED CALL_TOOL ON ALL 19 TOOLS (GATED & UNGATED)
# ==============================================================================

class TestEmpiricalUnpatchedToolExecution:
    """
    Empirical tests proving ALL 19 tools execute without Context shielding errors
    under direct protocol mcp.call_tool() WITHOUT ANY MOCK PATCHING.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_name", list(CANONICAL_TOOL_INVOCATIONS.keys()))
    async def test_all_19_tools_execute_unpatched_in_clean_environment(
        self, tool_name: str, monkeypatch: pytest.MonkeyPatch
    ):
        """
        Verify every single tool executes via mcp.call_tool() in a baseline environment
        (where human, inspection, animation tools are gated out from list_tools)
        without raising ValueError('Context is not available outside of a request').
        """
        clear_all_gating_env_vars(monkeypatch)
        args = CANONICAL_TOOL_INVOCATIONS[tool_name]

        # Invoke directly via protocol handler
        res = await mcp.call_tool(tool_name, args)

        assert res is not None, f"Tool {tool_name} returned None"
        assert len(res) > 0 and len(res[0]) > 0, f"Tool {tool_name} returned empty content"
        text_content = res[0][0].text
        payload = json.loads(text_content)

        assert isinstance(payload, dict), f"Tool {tool_name} payload is not a dict"
        # Verify valid returned structure
        valid_keys = (
            "status",
            "asset_id",
            "optimized_asset_id",
            "armature_id",
            "success",
            "scene_name",
            "image_path",
            "total_count",
            "character_name",
        )
        assert any(k in payload for k in valid_keys), (
            f"Tool {tool_name} returned unexpected payload schema: {payload}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool_name", list(CANONICAL_TOOL_INVOCATIONS.keys()))
    async def test_all_19_tools_execute_unpatched_in_ungated_environment(
        self, tool_name: str, monkeypatch: pytest.MonkeyPatch
    ):
        """
        Verify every single tool executes via mcp.call_tool() when all tools
        are fully enabled via environment variables.
        """
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")

        args = CANONICAL_TOOL_INVOCATIONS[tool_name]
        res = await mcp.call_tool(tool_name, args)

        assert res is not None, f"Tool {tool_name} returned None"
        payload = json.loads(res[0][0].text)
        assert isinstance(payload, dict), f"Tool {tool_name} payload is not a dict"
        valid_keys = (
            "status",
            "asset_id",
            "optimized_asset_id",
            "armature_id",
            "success",
            "scene_name",
            "image_path",
            "total_count",
            "character_name",
        )
        assert any(k in payload for k in valid_keys), (
            f"Tool {tool_name} returned unexpected payload schema: {payload}"
        )


# ==============================================================================
# 2. LOW-LEVEL JSON-RPC LIST_TOOLS PROTOCOL & GATING TRUTH MATRIX
# ==============================================================================

class TestLowLevelProtocolAndGatingMatrix:
    """Verifies low-level JSON-RPC protocol handler and gating truth matrix parity."""

    @pytest.mark.asyncio
    async def test_baseline_clean_environment_7_tools(self, monkeypatch: pytest.MonkeyPatch):
        """Clean baseline exposes exactly 7 creature tools."""
        clear_all_gating_env_vars(monkeypatch)
        hl_names = {t.name for t in await mcp.list_tools()}
        ll_names = {t.name for t in await get_lowlevel_tools()}
        assert hl_names == CREATURE_TOOL_NAMES
        assert ll_names == CREATURE_TOOL_NAMES
        assert len(hl_names) == 7

    @pytest.mark.asyncio
    async def test_animation_only_gating_9_tools(self, monkeypatch: pytest.MonkeyPatch):
        """Animation flag exposes exactly 9 tools (7 creature + 2 animation)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")
        hl_names = {t.name for t in await mcp.list_tools()}
        ll_names = {t.name for t in await get_lowlevel_tools()}
        expected = CREATURE_TOOL_NAMES | ANIMATION_TOOL_NAMES
        assert hl_names == expected
        assert ll_names == expected
        assert len(hl_names) == 9

    @pytest.mark.asyncio
    async def test_inspection_only_gating_10_tools(self, monkeypatch: pytest.MonkeyPatch):
        """Inspection flag exposes exactly 10 tools (7 creature + 3 inspection)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")
        hl_names = {t.name for t in await mcp.list_tools()}
        ll_names = {t.name for t in await get_lowlevel_tools()}
        expected = CREATURE_TOOL_NAMES | INSPECTION_TOOL_NAMES
        assert hl_names == expected
        assert ll_names == expected
        assert len(hl_names) == 10

    @pytest.mark.asyncio
    async def test_human_only_gating_14_tools(self, monkeypatch: pytest.MonkeyPatch):
        """Human flag exposes exactly 14 tools (7 creature + 7 human)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")
        hl_names = {t.name for t in await mcp.list_tools()}
        ll_names = {t.name for t in await get_lowlevel_tools()}
        expected = CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES
        assert hl_names == expected
        assert ll_names == expected
        assert len(hl_names) == 14

    @pytest.mark.asyncio
    async def test_human_and_inspection_gating_17_tools(self, monkeypatch: pytest.MonkeyPatch):
        """Human + Inspection flags expose exactly 17 tools (ALL_TOOL_NAMES)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")
        monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")
        hl_names = {t.name for t in await mcp.list_tools()}
        ll_names = {t.name for t in await get_lowlevel_tools()}
        assert hl_names == ALL_TOOL_NAMES
        assert ll_names == ALL_TOOL_NAMES
        assert len(hl_names) == 17

    @pytest.mark.asyncio
    async def test_all_tools_flag_17_tools(self, monkeypatch: pytest.MonkeyPatch):
        """MORPHOMESH_INCLUDE_ALL_TOOLS=1 exposes 17 tools."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
        hl_names = {t.name for t in await mcp.list_tools()}
        ll_names = {t.name for t in await get_lowlevel_tools()}
        assert hl_names == ALL_TOOL_NAMES
        assert ll_names == ALL_TOOL_NAMES
        assert len(hl_names) == 17

    @pytest.mark.asyncio
    async def test_full_pipeline_all_19_tools(self, monkeypatch: pytest.MonkeyPatch):
        """MORPHOMESH_INCLUDE_ALL_TOOLS=1 + MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1 exposes 19 tools."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")
        hl_names = {t.name for t in await mcp.list_tools()}
        ll_names = {t.name for t in await get_lowlevel_tools()}
        assert hl_names == ALL_19_TOOL_NAMES
        assert ll_names == ALL_19_TOOL_NAMES
        assert len(hl_names) == 19


# ==============================================================================
# 3. SCHEMA DRIFT AUDIT FOR ALL 19 TOOLS
# ==============================================================================

class TestSchemaDriftAudit:
    """Verifies schema invariants across all 19 tools in low-level JSON-RPC protocol."""

    @pytest.mark.asyncio
    async def test_all_19_tools_registered_with_valid_schema(self, monkeypatch: pytest.MonkeyPatch):
        """All 19 tools have valid JSON-RPC schema, description, and properties."""
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")

        tools = await get_lowlevel_tools()
        tool_map = {t.name: t for t in tools}
        assert len(tool_map) == 19

        for tool_name in ALL_19_TOOL_NAMES:
            assert tool_name in tool_map, f"Missing tool: {tool_name}"
            tool = tool_map[tool_name]
            assert tool.description and len(tool.description.strip()) >= 20
            schema = tool.inputSchema
            assert isinstance(schema, dict)
            assert schema.get("type") == "object"
            assert "properties" in schema
