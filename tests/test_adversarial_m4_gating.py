"""
MorphoMesh Adversarial Test Suite: Milestone 4 Environment Gating Matrix & JSON-RPC Protocol Fuzzer.

Target: tests/test_adversarial_m4_gating.py
Author: Challenger M4_1 (Empirical Challenger)
Milestone: Milestone 4 - FastMCP Tool Integration & Verification Suite (R4)

Empirical challenges covered:
1. Gating Matrix Permutations:
   - (INSPECTION=0, HUMAN=0, ALL=0) -> exactly 7 tools (CREATURE_TOOL_NAMES)
   - (INSPECTION=1, HUMAN=0, ALL=0) -> exactly 10 tools (CREATURE_TOOL_NAMES | INSPECTION_TOOL_NAMES)
   - (INSPECTION=0, HUMAN=1, ALL=0) -> exactly 14 tools (CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES)
   - (INSPECTION=1, HUMAN=1, ALL=0) -> exactly 17 tools (ALL_TOOL_NAMES)
   - (ALL=1) -> exactly 17 tools (ALL_TOOL_NAMES), independent of other flags.
2. Comprehensive Environment Value Fuzzing:
   - Truthy tokens: 'true', 'TRUE', 'True', 'yes', 'YES', 'all', 'ALL', '1', ' 1 ', ' true ', ' YeS '
   - Falsy/Inactive tokens: 'false', 'FALSE', '0', '', 'none', 'NONE', 'random', 'no', 'off', '2', '   '
   - Fuzzed across MORPHOMESH_INCLUDE_INSPECTION_TOOLS, MORPHOMESH_INCLUDE_HUMAN_TOOLS, and MORPHOMESH_INCLUDE_ALL_TOOLS.
3. Low-Level JSON-RPC Protocol Testing:
   - Direct invocation of mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]
   - Structure validation (ServerResult -> ListToolsResult -> Tool objects)
   - Strict 1:1 parity between mcp.list_tools() and low-level JSON-RPC handler across all states.
4. Protocol-Level Invocation via mcp.call_tool:
   - Valid executions for all 3 inspection tools returning structured TextContent.
   - Verification that inspection tools remain callable via mcp.call_tool() even when gated out of list_tools().
   - Negative boundary / invalid argument injections triggering ToolError:
     * setup_inspector_camera_rig: focal_length < 10, focal_length > 300, non-3 target_center, empty camera_name.
     * capture_viewport: negative/zero resolution, non-2 resolution, empty camera_name.
     * critique_visual_quality: negative clearance_tolerance, empty character and target object.
     * Unknown / non-existent tool invocation.
5. Dynamic Runtime State Transitions:
   - Sequential rapid toggling of environment flags without caching leakage or memory corruption.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from typing import Any, Dict, List, Set

import pytest
import mcp.types as mcp_types
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.server import (
    ALL_TOOL_NAMES,
    CREATURE_TOOL_NAMES,
    HUMAN_TOOL_NAMES,
    INSPECTION_TOOL_NAMES,
    mcp,
)


# ==============================================================================
# HELPERS
# ==============================================================================

def clear_all_gating_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all tool gating environment variables."""
    monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_ALL_TOOLS", raising=False)


async def get_lowlevel_tools() -> List[mcp_types.Tool]:
    """Execute low-level JSON-RPC ListToolsRequest handler directly."""
    handler = mcp._mcp_server.request_handlers.get(mcp_types.ListToolsRequest)
    assert handler is not None, "ListToolsRequest handler not registered in mcp._mcp_server"
    result = await handler(mcp_types.ListToolsRequest())
    assert isinstance(result, mcp_types.ServerResult), f"Expected ServerResult, got {type(result)}"
    assert isinstance(result.root, mcp_types.ListToolsResult), f"Expected ListToolsResult, got {type(result.root)}"
    return result.root.tools


# ==============================================================================
# 1. GATING MATRIX PERMUTATIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_matrix_perm_0_0_0(monkeypatch: pytest.MonkeyPatch):
    """(INSPECTION=0, HUMAN=0, ALL=0) -> exactly 7 tools (CREATURE_TOOL_NAMES)."""
    clear_all_gating_env_vars(monkeypatch)

    high_level_tools = await mcp.list_tools()
    low_level_tools = await get_lowlevel_tools()

    hl_names = {t.name for t in high_level_tools}
    ll_names = {t.name for t in low_level_tools}

    assert len(hl_names) == 7, f"Expected 7 tools, got {len(hl_names)}: {hl_names}"
    assert hl_names == CREATURE_TOOL_NAMES
    assert ll_names == CREATURE_TOOL_NAMES
    assert hl_names == ll_names

    # Ensure zero leakage of human or inspection tools
    assert hl_names.isdisjoint(HUMAN_TOOL_NAMES)
    assert hl_names.isdisjoint(INSPECTION_TOOL_NAMES)


@pytest.mark.asyncio
async def test_matrix_perm_1_0_0(monkeypatch: pytest.MonkeyPatch):
    """(INSPECTION=1, HUMAN=0, ALL=0) -> exactly 10 tools (CREATURE + INSPECTION)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")

    high_level_tools = await mcp.list_tools()
    low_level_tools = await get_lowlevel_tools()

    hl_names = {t.name for t in high_level_tools}
    ll_names = {t.name for t in low_level_tools}

    expected = CREATURE_TOOL_NAMES | INSPECTION_TOOL_NAMES
    assert len(hl_names) == 10, f"Expected 10 tools, got {len(hl_names)}: {hl_names}"
    assert hl_names == expected
    assert ll_names == expected
    assert hl_names == ll_names

    # Ensure zero leakage of human tools
    assert hl_names.isdisjoint(HUMAN_TOOL_NAMES)


@pytest.mark.asyncio
async def test_matrix_perm_0_1_0(monkeypatch: pytest.MonkeyPatch):
    """(INSPECTION=0, HUMAN=1, ALL=0) -> exactly 14 tools (CREATURE + HUMAN)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")

    high_level_tools = await mcp.list_tools()
    low_level_tools = await get_lowlevel_tools()

    hl_names = {t.name for t in high_level_tools}
    ll_names = {t.name for t in low_level_tools}

    expected = CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES
    assert len(hl_names) == 14, f"Expected 14 tools, got {len(hl_names)}: {hl_names}"
    assert hl_names == expected
    assert ll_names == expected
    assert hl_names == ll_names

    # Ensure zero leakage of inspection tools
    assert hl_names.isdisjoint(INSPECTION_TOOL_NAMES)


@pytest.mark.asyncio
async def test_matrix_perm_1_1_0(monkeypatch: pytest.MonkeyPatch):
    """(INSPECTION=1, HUMAN=1, ALL=0) -> exactly 17 tools (ALL_TOOL_NAMES)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")

    high_level_tools = await mcp.list_tools()
    low_level_tools = await get_lowlevel_tools()

    hl_names = {t.name for t in high_level_tools}
    ll_names = {t.name for t in low_level_tools}

    assert len(hl_names) == 17, f"Expected 17 tools, got {len(hl_names)}: {hl_names}"
    assert hl_names == ALL_TOOL_NAMES
    assert ll_names == ALL_TOOL_NAMES
    assert hl_names == ll_names


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "insp_val,human_val",
    [
        ("0", "0"),
        ("1", "0"),
        ("0", "1"),
        ("1", "1"),
        ("false", "false"),
        ("", ""),
    ],
)
async def test_matrix_perm_all_override(monkeypatch: pytest.MonkeyPatch, insp_val: str, human_val: str):
    """(ALL=1) -> exactly 17 tools, overriding any other combinations."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", insp_val)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", human_val)

    high_level_tools = await mcp.list_tools()
    low_level_tools = await get_lowlevel_tools()

    hl_names = {t.name for t in high_level_tools}
    ll_names = {t.name for t in low_level_tools}

    assert len(hl_names) == 17
    assert hl_names == ALL_TOOL_NAMES
    assert ll_names == ALL_TOOL_NAMES


# ==============================================================================
# 2. COMPREHENSIVE ENVIRONMENT VALUE FUZZING
# ==============================================================================

TRUTHY_FUZZ_VALUES = [
    "true",
    "TRUE",
    "True",
    "yes",
    "YES",
    "YeS",
    "all",
    "ALL",
    "1",
    " 1 ",
    " true ",
    "  yes  ",
    " ALL ",
]

FALSY_FUZZ_VALUES = [
    "false",
    "FALSE",
    "0",
    "",
    "none",
    "NONE",
    "None",
    "random",
    "no",
    "off",
    "2",
    "-1",
    "   ",
    "undefined",
    "null",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fuzz_val", TRUTHY_FUZZ_VALUES)
async def test_fuzz_inspection_truthy(monkeypatch: pytest.MonkeyPatch, fuzz_val: str):
    """Truthy fuzzed values must activate inspection tools (7 + 3 = 10)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", fuzz_val)

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) == 10, f"Failed on truthy value '{fuzz_val}'"
    assert names == (CREATURE_TOOL_NAMES | INSPECTION_TOOL_NAMES)


@pytest.mark.asyncio
@pytest.mark.parametrize("fuzz_val", FALSY_FUZZ_VALUES)
async def test_fuzz_inspection_falsy(monkeypatch: pytest.MonkeyPatch, fuzz_val: str):
    """Falsy fuzzed values must NOT activate inspection tools (7 tools only)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", fuzz_val)

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) == 7, f"Failed on falsy value '{fuzz_val}'"
    assert names == CREATURE_TOOL_NAMES
    assert names.isdisjoint(INSPECTION_TOOL_NAMES)


@pytest.mark.asyncio
@pytest.mark.parametrize("fuzz_val", TRUTHY_FUZZ_VALUES)
async def test_fuzz_human_truthy(monkeypatch: pytest.MonkeyPatch, fuzz_val: str):
    """Truthy fuzzed values must activate human tools (7 + 7 = 14)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", fuzz_val)

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) == 14, f"Failed on truthy human value '{fuzz_val}'"
    assert names == (CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES)


@pytest.mark.asyncio
@pytest.mark.parametrize("fuzz_val", FALSY_FUZZ_VALUES)
async def test_fuzz_human_falsy(monkeypatch: pytest.MonkeyPatch, fuzz_val: str):
    """Falsy fuzzed values must NOT activate human tools (7 tools only)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", fuzz_val)

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) == 7, f"Failed on falsy human value '{fuzz_val}'"
    assert names == CREATURE_TOOL_NAMES
    assert names.isdisjoint(HUMAN_TOOL_NAMES)


@pytest.mark.asyncio
@pytest.mark.parametrize("fuzz_val", TRUTHY_FUZZ_VALUES)
async def test_fuzz_all_tools_truthy(monkeypatch: pytest.MonkeyPatch, fuzz_val: str):
    """Truthy fuzzed values for ALL_TOOLS must activate all 17 tools."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", fuzz_val)

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) == 17, f"Failed on truthy ALL_TOOLS value '{fuzz_val}'"
    assert names == ALL_TOOL_NAMES


@pytest.mark.asyncio
@pytest.mark.parametrize("fuzz_val", FALSY_FUZZ_VALUES)
async def test_fuzz_all_tools_falsy(monkeypatch: pytest.MonkeyPatch, fuzz_val: str):
    """Falsy fuzzed values for ALL_TOOLS must NOT activate extra tools (7 tools only)."""
    clear_all_gating_env_vars(monkeypatch)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", fuzz_val)

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) == 7, f"Failed on falsy ALL_TOOLS value '{fuzz_val}'"
    assert names == CREATURE_TOOL_NAMES


# ==============================================================================
# 3. LOW-LEVEL JSON-RPC PROTOCOL HANDLER RIGOROUS PARITY
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "insp,human,all_tools,expected_count",
    [
        (False, False, False, 7),
        (True, False, False, 10),
        (False, True, False, 14),
        (True, True, False, 17),
        (False, False, True, 17),
    ],
)
async def test_json_rpc_list_tools_request_handler(
    monkeypatch: pytest.MonkeyPatch,
    insp: bool,
    human: bool,
    all_tools: bool,
    expected_count: int,
):
    """Direct invocation of mcp._mcp_server.request_handlers[ListToolsRequest] matches mcp.list_tools."""
    clear_all_gating_env_vars(monkeypatch)
    if insp:
        monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")
    if human:
        monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")
    if all_tools:
        monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")

    # High-level
    hl_tools = await mcp.list_tools()
    hl_tool_names = [t.name for t in hl_tools]

    # Low-level JSON-RPC protocol
    ll_tools = await get_lowlevel_tools()
    ll_tool_names = [t.name for t in ll_tools]

    assert len(ll_tool_names) == expected_count
    assert ll_tool_names == hl_tool_names

    # Check structural compliance of each Tool object
    for tool in ll_tools:
        assert isinstance(tool, mcp_types.Tool)
        assert tool.name in ALL_TOOL_NAMES
        assert tool.description is not None
        assert isinstance(tool.inputSchema, dict)
        assert tool.inputSchema.get("type") == "object"


# ==============================================================================
# 4. PROTOCOL-LEVEL TOOL INVOCATION VIA mcp.call_tool
# ==============================================================================

@pytest.mark.asyncio
async def test_call_tool_valid_setup_inspector_camera_rig():
    """Verify valid invocation of morphomesh_setup_inspector_camera_rig via mcp.call_tool."""
    res = await mcp.call_tool(
        "morphomesh_setup_inspector_camera_rig",
        {
            "viewpoint": "front",
            "focal_length": 85.0,
            "camera_name": "Adversarial_Test_Cam",
        },
    )
    assert isinstance(res, tuple)
    content, meta = res
    assert len(content) >= 1
    assert content[0].type == "text"
    payload = json.loads(content[0].text)
    assert payload["status"] == "success"
    assert payload["camera_name"] == "Adversarial_Test_Cam"
    assert payload["viewpoint"] == "front"
    assert payload["focal_length"] == 85.0
    assert "camera_location" in payload


@pytest.mark.asyncio
async def test_call_tool_valid_capture_viewport(tmp_path):
    """Verify valid invocation of morphomesh_capture_viewport via mcp.call_tool."""
    out_file = str(tmp_path / "test_cap.png")
    res = await mcp.call_tool(
        "morphomesh_capture_viewport",
        {
            "output_path": out_file,
            "camera_name": "Adversarial_Test_Cam",
            "resolution": [512, 512],
            "shading_mode": "SOLID",
            "color_type": "RANDOM",
        },
    )
    assert isinstance(res, tuple)
    content, meta = res
    payload = json.loads(content[0].text)
    assert payload["status"] == "success"
    assert payload["resolution"] == [512, 512]
    assert payload["shading_mode"] == "SOLID"
    assert payload["color_type"] == "RANDOM"
    assert "base64_preview" in payload
    assert len(payload["base64_preview"]) > 50


@pytest.mark.asyncio
async def test_call_tool_valid_critique_visual_quality():
    """Verify valid invocation of morphomesh_critique_visual_quality via mcp.call_tool."""
    res = await mcp.call_tool(
        "morphomesh_critique_visual_quality",
        {
            "character_name": "Yu_Nian_An",
            "camera_angles": ["front", "side", "three_quarter"],
            "clearance_tolerance": 0.001,
            "target_preset": "stylized_heroine",
        },
    )
    assert isinstance(res, tuple)
    content, meta = res
    payload = json.loads(content[0].text)
    assert "passed" in payload
    assert "quality_score" in payload
    assert "defects" in payload
    assert "recommendations" in payload
    assert payload["character_name"] == "Yu_Nian_An"


@pytest.mark.asyncio
async def test_call_tool_when_inspection_tools_gated_out(monkeypatch: pytest.MonkeyPatch):
    """
    Critical Architecture Test:
    When MORPHOMESH_INCLUDE_INSPECTION_TOOLS is unset (legacy 7-tool mode),
    the tool is filtered from list_tools(), but mcp.call_tool() directly invokes it.
    """
    clear_all_gating_env_vars(monkeypatch)

    # Confirm it is NOT listed
    listed = await mcp.list_tools()
    assert "morphomesh_setup_inspector_camera_rig" not in {t.name for t in listed}

    # Execute directly via protocol
    res = await mcp.call_tool(
        "morphomesh_setup_inspector_camera_rig",
        {"viewpoint": "side", "focal_length": 50.0},
    )
    content, meta = res
    payload = json.loads(content[0].text)
    assert payload["status"] == "success"
    assert payload["viewpoint"] == "side"


# ==============================================================================
# 5. ADVERSARIAL NEGATIVE INVOCATIONS VIA mcp.call_tool
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_args,expected_err_substring",
    [
        ({"focal_length": 5.0}, "focal_length"),       # < 10.0
        ({"focal_length": 450.0}, "focal_length"),     # > 300.0
        ({"focal_length": -50.0}, "focal_length"),     # negative
        ({"target_center": [1.0, 2.0]}, "target_center"),  # only 2 elements
        ({"target_center": [1.0, 2.0, 3.0, 4.0]}, "target_center"),  # 4 elements
        ({"camera_name": ""}, "camera_name"),          # empty
        ({"camera_name": "   "}, "camera_name"),       # whitespace
    ],
)
async def test_call_tool_setup_camera_adversarial_inputs(bad_args: Dict[str, Any], expected_err_substring: str):
    """Adversarial parameter boundary violations for setup_inspector_camera_rig must raise ToolError."""
    with pytest.raises(ToolError) as exc_info:
        await mcp.call_tool("morphomesh_setup_inspector_camera_rig", bad_args)
    assert expected_err_substring in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_args,expected_err_substring",
    [
        ({"resolution": [1024]}, "resolution"),          # only 1 dim
        ({"resolution": [-1024, 1024]}, "resolution"),    # negative width
        ({"resolution": [1024, 0]}, "resolution"),        # zero height
        ({"resolution": "1024x1024"}, "resolution"),      # string instead of list
        ({"camera_name": ""}, "camera_name"),             # empty
        ({"camera_name": "  \t "}, "camera_name"),        # whitespace
    ],
)
async def test_call_tool_capture_viewport_adversarial_inputs(bad_args: Dict[str, Any], expected_err_substring: str):
    """Adversarial parameter boundary violations for capture_viewport must raise ToolError."""
    with pytest.raises(ToolError) as exc_info:
        await mcp.call_tool("morphomesh_capture_viewport", bad_args)
    assert expected_err_substring in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_args,expected_err_substring",
    [
        ({"clearance_tolerance": -0.01}, "clearance_tolerance"),  # negative tolerance
        ({"character_name": "", "target_object": ""}, "character_name"),  # both empty
        ({"character_name": None, "target_object": None}, "character_name"),
    ],
)
async def test_call_tool_critique_adversarial_inputs(bad_args: Dict[str, Any], expected_err_substring: str):
    """Adversarial parameter boundary violations for critique_visual_quality must raise ToolError."""
    with pytest.raises(ToolError) as exc_info:
        await mcp.call_tool("morphomesh_critique_visual_quality", bad_args)
    assert expected_err_substring in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_tool_unknown_tool_raises_tool_error():
    """Calling an unregistered or fuzzed tool name must raise ToolError with 'Unknown tool'."""
    with pytest.raises(ToolError) as exc_info:
        await mcp.call_tool("morphomesh_non_existent_hack_tool", {})
    assert "Unknown tool" in str(exc_info.value)


# ==============================================================================
# 6. DYNAMIC RUNTIME STATE TRANSITIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_dynamic_runtime_state_transitions(monkeypatch: pytest.MonkeyPatch):
    """
    Stress-test sequential dynamic flipping of environment variables in a single lifecycle.
    Confirms there is no static caching or state contamination between queries.
    """
    # 1. Start clean: 7 tools
    clear_all_gating_env_vars(monkeypatch)
    t1 = await mcp.list_tools()
    assert len(t1) == 7

    # 2. Flip to inspection only: 10 tools
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "true")
    t2 = await mcp.list_tools()
    assert len(t2) == 10

    # 3. Flip to human only: 14 tools
    monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "yes")
    t3 = await mcp.list_tools()
    assert len(t3) == 14

    # 4. Flip to all tools: 17 tools
    monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")
    t4 = await mcp.list_tools()
    assert len(t4) == 17

    # 5. Flip back to clean: exactly 7 tools
    clear_all_gating_env_vars(monkeypatch)
    t5 = await mcp.list_tools()
    assert len(t5) == 7
    assert {t.name for t in t5} == CREATURE_TOOL_NAMES
