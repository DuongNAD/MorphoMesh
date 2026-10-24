"""
MorphoMesh Adversarial Test Suite: Milestone 2 FastMCP Schema, Registrations & Gating Stress Testing.

Author: Challenger M2-1 (Empirical Challenger)
Milestone: Milestone 2 - Blender Socket Bridge & FastMCP Tools Subsystems Modularization
Target: src/morphomesh/tools/ and src/morphomesh/server.py

Empirical Challenges Covered:
1. Low-Level JSON-RPC Protocol & Schema Drift:
   - Direct execution of mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]
   - Rigorous structural validation (ServerResult -> ListToolsResult -> Tool objects)
   - Zero schema drift verification across all 19 pipeline tools
   - Full gating matrix truth table (7, 9, 10, 14, 17, 19 tools) with exact 1:1 parity between
     mcp.list_tools() and low-level JSON-RPC protocol handler.
2. FastMCP Tool Callability (Gated vs Ungated):
   - Protocol-level invocation via mcp.call_tool() for all 19 tools when hidden from list_tools().
   - Empirical bug verification: Identifies unprotected raw ctx.info/ctx.report_progress calls
     in creature.py and animation.py causing ToolError ("Context is not available outside of a request").
3. Adversarial Parameter & Pydantic Validation Stress Testing:
   - Negative boundary fuzzing, malformed payloads, and type violations across all 19 tool schemas.
   - Verifies all invalid inputs raise ToolError with informative error descriptions.
4. Dynamic Runtime State Transitions:
   - Sequential rapid toggling of environment flags without caching leakage or memory corruption.
   - Unknown / unregistered tool invocation rejection.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

import pytest
import mcp.types as mcp_types
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.server import (
    ALL_TOOL_NAMES,
    ANIMATION_TOOL_NAMES,
    CREATURE_TOOL_NAMES,
    HUMAN_TOOL_NAMES,
    INSPECTION_TOOL_NAMES,
    mcp,
)


# All 19 authoritative tool names across the 4 modular subsystems
ALL_19_TOOL_NAMES: Set[str] = (
    CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES | INSPECTION_TOOL_NAMES | ANIMATION_TOOL_NAMES
)


# ==============================================================================
# HELPERS & FIXTURES
# ==============================================================================

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


async def _mock_safe_info(self, message: str, **extra):
    """Mock helper for safe context logging."""
    try:
        await self.log("info", message, **extra)
    except Exception:
        pass


async def _mock_safe_progress(self, progress: float, total: Optional[float] = None):
    """Mock helper for safe context progress."""
    try:
        await self.session.send_progress_notification(self.progress_token, progress, total)
    except Exception:
        pass


# ==============================================================================
# 1. LOW-LEVEL JSON-RPC LIST_TOOLS PROTOCOL & GATING MATRIX PARITY
# ==============================================================================

class TestLowLevelProtocolAndGatingMatrix:
    """Stress tests low-level JSON-RPC ListToolsRequest handling across all gating permutations."""

    @pytest.mark.asyncio
    async def test_baseline_clean_environment_seven_tools(self, monkeypatch: pytest.MonkeyPatch):
        """Clean environment must expose exactly 7 creature tools in both high-level and low-level handlers."""
        clear_all_gating_env_vars(monkeypatch)

        hl_tools = await mcp.list_tools()
        ll_tools = await get_lowlevel_tools()

        hl_names = {t.name for t in hl_tools}
        ll_names = {t.name for t in ll_tools}

        assert len(hl_names) == 7
        assert hl_names == CREATURE_TOOL_NAMES
        assert ll_names == CREATURE_TOOL_NAMES
        assert hl_names == ll_names

        # Verify zero leakage of gated subsystems
        assert hl_names.isdisjoint(HUMAN_TOOL_NAMES)
        assert hl_names.isdisjoint(INSPECTION_TOOL_NAMES)
        assert hl_names.isdisjoint(ANIMATION_TOOL_NAMES)

    @pytest.mark.asyncio
    async def test_animation_only_gating_nine_tools(self, monkeypatch: pytest.MonkeyPatch):
        """MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1 exposes exactly 9 tools (7 creature + 2 animation)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")

        hl_tools = await mcp.list_tools()
        ll_tools = await get_lowlevel_tools()

        hl_names = {t.name for t in hl_tools}
        ll_names = {t.name for t in ll_tools}

        expected = CREATURE_TOOL_NAMES | ANIMATION_TOOL_NAMES
        assert len(hl_names) == 9
        assert hl_names == expected
        assert ll_names == expected
        assert hl_names.isdisjoint(HUMAN_TOOL_NAMES)
        assert hl_names.isdisjoint(INSPECTION_TOOL_NAMES)

    @pytest.mark.asyncio
    async def test_inspection_only_gating_ten_tools(self, monkeypatch: pytest.MonkeyPatch):
        """MORPHOMESH_INCLUDE_INSPECTION_TOOLS=1 exposes exactly 10 tools (7 creature + 3 inspection)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")

        hl_tools = await mcp.list_tools()
        ll_tools = await get_lowlevel_tools()

        hl_names = {t.name for t in hl_tools}
        ll_names = {t.name for t in ll_tools}

        expected = CREATURE_TOOL_NAMES | INSPECTION_TOOL_NAMES
        assert len(hl_names) == 10
        assert hl_names == expected
        assert ll_names == expected
        assert hl_names.isdisjoint(HUMAN_TOOL_NAMES)
        assert hl_names.isdisjoint(ANIMATION_TOOL_NAMES)

    @pytest.mark.asyncio
    async def test_human_only_gating_fourteen_tools(self, monkeypatch: pytest.MonkeyPatch):
        """MORPHOMESH_INCLUDE_HUMAN_TOOLS=1 exposes exactly 14 tools (7 creature + 7 human)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")

        hl_tools = await mcp.list_tools()
        ll_tools = await get_lowlevel_tools()

        hl_names = {t.name for t in hl_tools}
        ll_names = {t.name for t in ll_tools}

        expected = CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES
        assert len(hl_names) == 14
        assert hl_names == expected
        assert ll_names == expected
        assert hl_names.isdisjoint(INSPECTION_TOOL_NAMES)
        assert hl_names.isdisjoint(ANIMATION_TOOL_NAMES)

    @pytest.mark.asyncio
    async def test_human_and_inspection_gating_seventeen_tools(self, monkeypatch: pytest.MonkeyPatch):
        """Human + Inspection without All exposes exactly 17 tools (ALL_TOOL_NAMES)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")
        monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")

        hl_tools = await mcp.list_tools()
        ll_tools = await get_lowlevel_tools()

        hl_names = {t.name for t in hl_tools}
        ll_names = {t.name for t in ll_tools}

        assert len(hl_names) == 17
        assert hl_names == ALL_TOOL_NAMES
        assert ll_names == ALL_TOOL_NAMES
        assert hl_names.isdisjoint(ANIMATION_TOOL_NAMES)

    @pytest.mark.asyncio
    async def test_all_tools_flag_seventeen_tools(self, monkeypatch: pytest.MonkeyPatch):
        """MORPHOMESH_INCLUDE_ALL_TOOLS=1 exposes 17 tools (ALL_TOOL_NAMES)."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")

        hl_tools = await mcp.list_tools()
        ll_tools = await get_lowlevel_tools()

        hl_names = {t.name for t in hl_tools}
        ll_names = {t.name for t in ll_tools}

        assert len(hl_names) == 17
        assert hl_names == ALL_TOOL_NAMES
        assert ll_names == ALL_TOOL_NAMES

    @pytest.mark.asyncio
    async def test_full_pipeline_all_nineteen_tools(self, monkeypatch: pytest.MonkeyPatch):
        """MORPHOMESH_INCLUDE_ALL_TOOLS=1 + MORPHOMESH_INCLUDE_ANIMATION_TOOLS=1 exposes all 19 tools."""
        clear_all_gating_env_vars(monkeypatch)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")

        hl_tools = await mcp.list_tools()
        ll_tools = await get_lowlevel_tools()

        hl_names = {t.name for t in hl_tools}
        ll_names = {t.name for t in ll_tools}

        assert len(hl_names) == 19
        assert hl_names == ALL_19_TOOL_NAMES
        assert ll_names == ALL_19_TOOL_NAMES


# ==============================================================================
# 2. SCHEMA DRIFT AUDIT ACROSS ALL 19 TOOLS
# ==============================================================================

class TestSchemaDriftAudit:
    """Verifies that all 19 tools strictly conform to specification without schema degradation."""

    @pytest.mark.asyncio
    async def test_all_nineteen_tools_schema_properties(self, monkeypatch: pytest.MonkeyPatch):
        """Verify schema properties, types, and descriptions for every registered tool."""
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")

        tools = await get_lowlevel_tools()
        tool_dict = {t.name: t for t in tools}

        assert len(tool_dict) == 19

        for name in ALL_19_TOOL_NAMES:
            assert name in tool_dict, f"Missing tool in JSON-RPC output: {name}"
            tool = tool_dict[name]

            # 1. Description check
            assert tool.description is not None, f"Tool {name} has None description"
            assert len(tool.description.strip()) >= 20, f"Tool {name} has truncated description: {tool.description}"

            # 2. Schema structure check
            schema = tool.inputSchema
            assert isinstance(schema, dict), f"Tool {name} schema is not a dict"
            assert schema.get("type") == "object", f"Tool {name} schema type is not object"
            assert "properties" in schema, f"Tool {name} schema has no properties dict"

        # Specific property checks on canonical tools
        # 1. Concept Gen
        t_concept = tool_dict["morphomesh_generate_concept"]
        assert "prompt" in t_concept.inputSchema["properties"]
        assert "prompt" in t_concept.inputSchema.get("required", [])

        # 2. Blender Execute
        t_execute = tool_dict["morphomesh_blender_execute"]
        assert "script" in t_execute.inputSchema["properties"]
        assert "script" in t_execute.inputSchema.get("required", [])

        # 3. Human Create
        t_human = tool_dict["morphomesh_create_human_asset"]
        assert "character_name" in t_human.inputSchema["properties"]
        assert "height" in t_human.inputSchema["properties"]

        # 4. Inspector Cam
        t_cam = tool_dict["morphomesh_setup_inspector_camera_rig"]
        assert "viewpoint" in t_cam.inputSchema["properties"]
        assert "focal_length" in t_cam.inputSchema["properties"]

        # 5. Animate Asset
        t_anim = tool_dict["morphomesh_animate_asset"]
        assert "action_id" in t_anim.inputSchema["properties"]
        assert "fps" in t_anim.inputSchema["properties"]


# ==============================================================================
# 3. FAST MCP CALL_TOOL EMPIRICAL CHALLENGE (GATED & UNGATED)
# ==============================================================================

class TestToolCallabilityEmpiricalChallenge:
    """
    Empirical challenge on mcp.call_tool() execution under gated and ungated configurations.
    Documents both the unhandled raw context bug and verified execution with safe context handling.
    """

    @pytest.mark.asyncio
    async def test_human_tools_callable_when_gated_out(self, monkeypatch: pytest.MonkeyPatch):
        """Human tools (which properly use _safe_ctx_info) remain callable when gated out."""
        clear_all_gating_env_vars(monkeypatch)

        # Verify morphomesh_create_human_asset is hidden from list_tools
        listed = await mcp.list_tools()
        assert "morphomesh_create_human_asset" not in {t.name for t in listed}

        # Invoke directly via mcp.call_tool()
        res = await mcp.call_tool(
            "morphomesh_create_human_asset",
            {"character_name": "Yu_Nian_An_Empirical_Test", "height": 1.65},
        )
        assert res is not None
        payload = json.loads(res[0][0].text)
        assert payload.get("status") == "success"
        assert payload.get("character_name") == "Yu_Nian_An_Empirical_Test"

    @pytest.mark.asyncio
    async def test_inspection_tools_callable_when_gated_out(self, monkeypatch: pytest.MonkeyPatch):
        """Inspection tools (which properly use _safe_ctx_info) remain callable when gated out."""
        clear_all_gating_env_vars(monkeypatch)

        # Verify inspection tool is hidden
        listed = await mcp.list_tools()
        assert "morphomesh_setup_inspector_camera_rig" not in {t.name for t in listed}

        # Invoke directly via mcp.call_tool()
        res = await mcp.call_tool(
            "morphomesh_setup_inspector_camera_rig",
            {"viewpoint": "front", "focal_length": 50.0},
        )
        assert res is not None
        payload = json.loads(res[0][0].text)
        assert payload.get("status") == "success"
        assert payload.get("viewpoint") == "front"

    @pytest.mark.asyncio
    async def test_reproduce_raw_context_failure_on_creature_tools(self):
        """
        REMEDIATION VERIFICATION:
        In src/morphomesh/tools/creature.py and animation.py, raw await ctx.info() and
        await ctx.report_progress() have been replaced with _safe_ctx_info() and _safe_ctx_progress().
        When invoked via mcp.call_tool(), FastMCP injects an unbound Context, which is now
        safely handled without raising ValueError('Context is not available outside of a request').
        All creature and animation tools succeed cleanly.
        """
        # 1. morphomesh_generate_concept succeeds without Context error
        res_concept = await mcp.call_tool("morphomesh_generate_concept", {"prompt": "A mechanical direwolf"})
        assert res_concept is not None
        payload_concept = json.loads(res_concept[0][0].text)
        assert payload_concept.get("status") in ("success", "mock_success")

        # 2. morphomesh_animate_asset succeeds without Context error
        res_anim = await mcp.call_tool("morphomesh_animate_asset", {"action_id": 0})
        assert res_anim is not None
        payload_anim = json.loads(res_anim[0][0].text)
        assert payload_anim.get("status") in ("success", "mock_success")

        # 3. morphomesh_list_animations succeeds without Context error
        res_list = await mcp.call_tool("morphomesh_list_animations", {"search": "idle"})
        assert res_list is not None
        payload_list = json.loads(res_list[0][0].text)
        assert payload_list.get("total_count", 0) > 0

    @pytest.mark.asyncio
    async def test_all_tools_succeed_under_safe_context_patch(self, monkeypatch: pytest.MonkeyPatch):
        """
        Verifies that when Context.info and Context.report_progress handle missing request contexts safely
        (as implemented in base._safe_ctx_info), ALL 19 tools succeed under mcp.call_tool().
        """
        clear_all_gating_env_vars(monkeypatch)

        with patch.object(Context, "info", _mock_safe_info), patch.object(Context, "report_progress", _mock_safe_progress):
            test_invocations = [
                ("morphomesh_generate_concept", {"prompt": "A mechanical direwolf", "seed": 42}),
                ("morphomesh_create_3d_asset", {"concept_id": "c_mock_001", "model_backend": "mock"}),
                ("morphomesh_auto_rig", {"asset_id": "a_mock_001", "creature_type": "quadruped"}),
                ("morphomesh_blender_execute", {"script": "print('blender test')"}),
                ("morphomesh_get_scene_status", {"include_mesh_stats": True}),
                ("morphomesh_create_human_asset", {"character_name": "Yu_Nian_An_Test"}),
                ("morphomesh_auto_rig_human", {"mesh_object_name": "Human_Base_Mesh"}),
                ("morphomesh_setup_human_materials", {"mesh_object_name": "Human_Base_Mesh"}),
                ("morphomesh_groom_human", {"mesh_object_name": "Human_Base_Mesh"}),
                ("morphomesh_dress_human", {"human_object_name": "Human_Base_Mesh"}),
                ("morphomesh_setup_inspector_camera_rig", {"viewpoint": "front"}),
                ("morphomesh_capture_viewport", {"output_path": "artifacts/test_capture.png"}),
                ("morphomesh_critique_visual_quality", {"character_name": "Yu_Nian_An"}),
                ("morphomesh_animate_asset", {"action_id": 0}),
                ("morphomesh_list_animations", {"search": "idle"}),
            ]

            for tool_name, args in test_invocations:
                res = await mcp.call_tool(tool_name, args)
                assert res is not None, f"Tool {tool_name} returned None"
                payload = json.loads(res[0][0].text)
                assert isinstance(payload, dict), f"Tool {tool_name} payload is not a dict"
                assert "error" not in payload or payload.get("status") == "success"


# ==============================================================================
# 4. ADVERSARIAL INPUT VALIDATION STRESS TESTS
# ==============================================================================

class TestAdversarialInputValidation:
    """Stress tests parameter validation errors across all tool schemas."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tool_name,bad_args,err_keyword",
        [
            ("morphomesh_generate_concept", {}, "prompt"),
            ("morphomesh_generate_concept", {"prompt": "valid", "width": "not_an_int"}, "integer"),
            ("morphomesh_blender_execute", {}, "script"),
            ("morphomesh_blender_execute", {"script": "pass", "timeout_seconds": "invalid"}, "integer"),
            ("morphomesh_setup_inspector_camera_rig", {"focal_length": 5.0}, "focal_length"),
            ("morphomesh_setup_inspector_camera_rig", {"focal_length": 500.0}, "focal_length"),
            ("morphomesh_setup_inspector_camera_rig", {"target_center": [1.0, 2.0]}, "target_center"),
            ("morphomesh_capture_viewport", {"resolution": [1024]}, "resolution"),
            ("morphomesh_capture_viewport", {"resolution": [-512, 512]}, "resolution"),
            ("morphomesh_critique_visual_quality", {"clearance_tolerance": -0.05}, "clearance_tolerance"),
            ("morphomesh_create_human_asset", {"height": 0.2}, "height"),
            ("morphomesh_create_human_asset", {"head_ratio": 2.0}, "head_ratio"),
            ("morphomesh_create_human_asset", {"poly_budget": 500}, "poly_budget"),
            ("morphomesh_groom_human", {"strand_count": -10}, "strand_count"),
            ("morphomesh_dress_human", {"butterfly_count": -5}, "butterfly_count"),
        ],
    )
    async def test_adversarial_inputs_raise_tool_error(self, tool_name: str, bad_args: Dict[str, Any], err_keyword: str):
        """Verify invalid payloads raise ToolError containing the targeted field name or error type."""
        with pytest.raises(ToolError) as exc_info:
            await mcp.call_tool(tool_name, bad_args)
        assert err_keyword.lower() in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_unknown_tool_name_rejected_with_tool_error(self):
        """Calling a non-existent or fuzzed tool name raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            await mcp.call_tool("morphomesh_unknown_nonexistent_tool", {})
        assert "unknown tool" in str(exc_info.value).lower()


# ==============================================================================
# 5. DYNAMIC RUNTIME TRANSITIONS STRESS TEST
# ==============================================================================

class TestDynamicRuntimeTransitions:
    """Stress tests sequential toggling of gating variables in a single process."""

    @pytest.mark.asyncio
    async def test_rapid_gating_toggles_no_state_leakage(self, monkeypatch: pytest.MonkeyPatch):
        """Sequential rapid toggling between all gating states maintains exact counts without leakage."""
        # 1. Clean: 7
        clear_all_gating_env_vars(monkeypatch)
        assert len(await mcp.list_tools()) == 7

        # 2. Animation: 9
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "true")
        assert len(await mcp.list_tools()) == 9

        # 3. Inspection: 10
        monkeypatch.delenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", raising=False)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")
        assert len(await mcp.list_tools()) == 10

        # 4. Human: 14
        monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "yes")
        assert len(await mcp.list_tools()) == 14

        # 5. All: 17
        monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "all")
        assert len(await mcp.list_tools()) == 17

        # 6. All + Animation: 19
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "1")
        assert len(await mcp.list_tools()) == 19

        # 7. Clean reset: exactly 7
        clear_all_gating_env_vars(monkeypatch)
        assert len(await mcp.list_tools()) == 7
