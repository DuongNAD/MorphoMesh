"""
MorphoMesh: FastMCP Digital Human Tools Unit Tests.

Validates:
1. Tool registration, discovery, and JSON-RPC schema generation for the 5 human tools.
2. Parameter validation, bounds checking, and Pydantic v2 schemas.
3. Direct execution of the 5 FastMCP human tools.
4. Client invocation via FastMCP `mcp.call_tool()`.
5. Error handling and ToolError raising on out-of-bounds parameters.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

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
    """Ensure FastMCP lists all 12 tools for human tool tests."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")


# ==============================================================================
# 1. REGISTRATION & DISCOVERY
# ==============================================================================

@pytest.mark.asyncio
async def test_all_five_human_tools_registered():
    """Verify all 5 digital human tools are registered on FastMCP."""
    tools = await mcp.list_tools()
    registered_names = {t.name for t in tools}

    for name in HUMAN_TOOL_NAMES:
        assert name in registered_names, f"Tool '{name}' not found on FastMCP server."

    assert len(tools) >= 12, f"Expected at least 12 tools, found {len(tools)}"


@pytest.mark.asyncio
async def test_human_tools_descriptions_and_metadata():
    """Verify every human tool possesses a non-empty, detailed docstring."""
    tools = await mcp.list_tools()
    human_tools = [t for t in tools if t.name in HUMAN_TOOL_NAMES]

    for tool in human_tools:
        assert tool.description is not None, f"Tool '{tool.name}' lacks a description."
        assert len(tool.description.strip()) > 30, (
            f"Tool '{tool.name}' has insufficiently detailed description: '{tool.description}'"
        )


@pytest.mark.asyncio
async def test_human_tools_input_schemas():
    """Verify JSON Schemas generated for all 5 human tools."""
    tools = await mcp.list_tools()
    tools_by_name = {t.name: t for t in tools}

    # Tool 8: morphomesh_create_human_asset
    t8 = tools_by_name["morphomesh_create_human_asset"]
    props8 = t8.inputSchema["properties"]
    assert "character_name" in props8
    assert "height" in props8
    assert "head_ratio" in props8
    assert props8["height"]["default"] == 1.65
    assert props8["head_ratio"]["default"] == 7.41

    # Tool 9: morphomesh_auto_rig_human
    t9 = tools_by_name["morphomesh_auto_rig_human"]
    props9 = t9.inputSchema["properties"]
    assert "rig_type" in props9
    assert props9["rig_type"]["default"] == "rigify_human"
    assert "pose" in props9

    # Tool 10: morphomesh_setup_human_materials
    t10 = tools_by_name["morphomesh_setup_human_materials"]
    props10 = t10.inputSchema["properties"]
    assert "material_preset" in props10
    assert props10["material_preset"]["default"] == "yu_nian_an"
    assert "subsurface_scattering" in props10
    assert props10["subsurface_scattering"]["default"] is True

    # Tool 11: morphomesh_groom_human
    t11 = tools_by_name["morphomesh_groom_human"]
    props11 = t11.inputSchema["properties"]
    assert "hair_style" in props11
    assert props11["hair_style"]["default"] == "hime_cut_long"
    assert "strand_count" in props11
    assert props11["strand_count"]["default"] == 15000

    # Tool 12: morphomesh_dress_human
    t12 = tools_by_name["morphomesh_dress_human"]
    props12 = t12.inputSchema["properties"]
    assert "outfit" in props12
    assert props12["outfit"]["default"] == "yu_nian_an_dress"
    assert "butterfly_count" in props12
    assert props12["butterfly_count"]["default"] == 10


# ==============================================================================
# 2. PARAMETER VALIDATION & BOUNDS
# ==============================================================================

class TestHumanInputSchemas:
    """Validate Pydantic v2 input schemas, bounds, and defaults."""

    def test_create_human_asset_input_bounds(self):
        m = CreateHumanAssetInput()
        assert m.height == 1.65
        assert m.head_ratio == 7.41

        # Out of bounds height
        with pytest.raises(ValidationError):
            CreateHumanAssetInput(height=0.5)  # ge=1.0
        with pytest.raises(ValidationError):
            CreateHumanAssetInput(height=3.0)  # le=2.5

        # Out of bounds head_ratio
        with pytest.raises(ValidationError):
            CreateHumanAssetInput(head_ratio=3.0)  # ge=5.0
        with pytest.raises(ValidationError):
            CreateHumanAssetInput(head_ratio=15.0)  # le=10.0

    def test_auto_rig_human_input_defaults(self):
        m = AutoRigHumanInput()
        assert m.rig_type == "rigify_human"
        assert m.skinning_method == "automatic_weights"
        assert m.include_face_rig is True
        assert m.include_finger_rig is True
        assert m.pose == "puppeteer_pose"

    def test_setup_human_materials_input_defaults(self):
        m = SetupHumanMaterialsInput()
        assert m.material_preset == "yu_nian_an"
        assert m.skin_tone == "porcelain_fair"
        assert m.subsurface_scattering is True
        assert m.refractive_eyes is True
        assert m.render_engine == "CYCLES"

    def test_groom_human_input_bounds(self):
        m = GroomHumanInput()
        assert m.hair_style == "hime_cut_long"
        assert m.strand_count == 15000

        with pytest.raises(ValidationError):
            GroomHumanInput(strand_count=100)  # ge=1000
        with pytest.raises(ValidationError):
            GroomHumanInput(strand_count=500000)  # le=200000

    def test_dress_human_input_bounds(self):
        m = DressHumanInput()
        assert m.outfit == "yu_nian_an_dress"
        assert m.butterfly_count == 10
        assert m.clearance_offset == 0.015

        with pytest.raises(ValidationError):
            DressHumanInput(butterfly_count=0)  # ge=1
        with pytest.raises(ValidationError):
            DressHumanInput(butterfly_count=100)  # le=50


# ==============================================================================
# 3. DIRECT EXECUTION OF FAST-MCP HUMAN TOOLS
# ==============================================================================

@pytest.mark.asyncio
async def test_exec_create_human_asset():
    """Verify direct invocation of morphomesh_create_human_asset."""
    res = await morphomesh_create_human_asset(
        character_name="Yu_Nian_An_Test",
        height=1.65,
        head_ratio=7.41,
        style="stylized_photorealism",
    )
    assert res.get("status") == "success"
    assert "asset_id" in res
    assert res.get("character_name") == "Yu_Nian_An_Test"
    assert abs(res.get("height", 0) - 1.65) < 0.05
    assert len(res.get("vertex_groups", [])) >= 24
    assert len(res.get("landmarks", {})) >= 20
    assert len(res.get("shape_keys", [])) == 52


@pytest.mark.asyncio
async def test_exec_auto_rig_human():
    """Verify direct invocation of morphomesh_auto_rig_human."""
    res = await morphomesh_auto_rig_human(
        mesh_object_name="Human_Base_Mesh",
        rig_type="rigify_human",
        pose="puppeteer_pose",
    )
    assert res.get("status") == "success"
    assert "armature_name" in res
    assert res.get("def_bone_count") == 163
    assert res.get("bone_count") == 163
    assert len(res.get("bone_hierarchy", [])) >= 20
    assert res.get("pose") == "puppeteer_pose"


@pytest.mark.asyncio
async def test_exec_setup_human_materials():
    """Verify direct invocation of morphomesh_setup_human_materials."""
    res = await morphomesh_setup_human_materials(
        mesh_object_name="Human_Base_Mesh",
        material_preset="yu_nian_an",
        subsurface_scattering=True,
        refractive_eyes=True,
    )
    assert res.get("status") == "success"
    assert res.get("material_preset") == "yu_nian_an"
    assert res.get("subsurface_scattering") is True
    assert res.get("refractive_eyes") is True
    assert len(res.get("materials_created", [])) >= 5


@pytest.mark.asyncio
async def test_exec_groom_human():
    """Verify direct invocation of morphomesh_groom_human."""
    res = await morphomesh_groom_human(
        mesh_object_name="Human_Base_Mesh",
        hair_style="hime_cut_long",
        strand_count=15000,
    )
    assert res.get("status") == "success"
    assert res.get("hair_style") == "hime_cut_long"
    assert len(res.get("layers", [])) >= 5
    assert res.get("strand_count") == 15000


@pytest.mark.asyncio
async def test_exec_dress_human():
    """Verify direct invocation of morphomesh_dress_human."""
    res = await morphomesh_dress_human(
        human_object_name="Human_Base_Mesh",
        outfit="yu_nian_an_dress",
        butterfly_count=10,
    )
    assert res.get("status") == "success"
    assert res.get("outfit_preset") == "yu_nian_an_dress"
    assert len(res.get("garments", [])) >= 3
    assert len(res.get("accessories", [])) >= 2
    assert res.get("prop_count") == 20  # 10 strings + 10 butterflies


# ==============================================================================
# 4. MCP CALL_TOOL INVOCATION
# ==============================================================================

@pytest.mark.asyncio
async def test_call_tool_create_human_asset():
    """Verify invoking morphomesh_create_human_asset through mcp.call_tool()."""
    result = await mcp.call_tool(
        "morphomesh_create_human_asset",
        {"character_name": "Yu_Nian_An_CallTool", "height": 1.65},
    )
    assert result is not None
    # Result contains TextContent with serialized JSON
    text_content = result[0][0]
    payload = json.loads(text_content.text)
    assert payload.get("status") == "success"
    assert payload.get("character_name") == "Yu_Nian_An_CallTool"
    assert len(payload.get("shape_keys", [])) == 52


@pytest.mark.asyncio
async def test_call_tool_auto_rig_human():
    """Verify invoking morphomesh_auto_rig_human through mcp.call_tool()."""
    result = await mcp.call_tool(
        "morphomesh_auto_rig_human",
        {"mesh_object_name": "Yu_Nian_An_Mesh", "pose": "puppeteer_pose"},
    )
    assert result is not None
    text_content = result[0][0]
    payload = json.loads(text_content.text)
    assert payload.get("status") == "success"
    assert payload.get("def_bone_count") == 163


# ==============================================================================
# 5. ERROR HANDLING ON INVALID ARGUMENTS
# ==============================================================================

@pytest.mark.asyncio
async def test_tool_create_human_asset_invalid_height():
    """Verify ToolError is raised when height is outside acceptable range."""
    with pytest.raises(ToolError) as exc_info:
        await morphomesh_create_human_asset(height=0.4)
    assert "error" in str(exc_info.value).lower()


def test_blender_bridge_create_human_asset_non_fallback():
    """Verify BlenderBridge.create_human_asset executes headless Blender without triggering fallback."""
    from morphomesh.blender_bridge import BlenderBridge
    bridge = BlenderBridge()
    if not bridge.blender_bin_path:
        pytest.skip("Blender binary not available on host system.")
    res = bridge.create_human_asset(character_name="TestBlenderDirect")
    assert res.get("status") == "success"
    assert res.get("vertex_count") == 2144
    assert res.get("face_count") == 2036
    assert res.get("quad_ratio") == 1.0
    assert len(res.get("landmarks", {})) == 24
    assert len(res.get("vertex_groups", [])) == 29

