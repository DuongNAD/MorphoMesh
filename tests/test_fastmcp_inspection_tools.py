"""
MorphoMesh: FastMCP Inspection & Visual Quality Critique Tools Unit Tests.

Target: tests/test_fastmcp_inspection_tools.py
Milestone: Milestone 4 - FastMCP Tool Integration & Verification Suite (R4)

Validates:
1. Tool Registration & Discovery:
   - Registration of the 3 inspection tools:
     * morphomesh_setup_inspector_camera_rig
     * morphomesh_capture_viewport
     * morphomesh_critique_visual_quality
   - Non-empty, detailed docstrings explaining technical role.
   - JSON-RPC inputSchema property definitions, types, required fields, and defaults.

2. Parameter Validation & Bounds (Pydantic Models):
   - SetupInspectorCameraInput, CaptureViewportInput, VisualCritiqueInput.
   - Focal length bounds (10.0 to 300.0), margin bounds (0.0 to 1.0), clearance tolerance (>= 0.0).
   - Viewpoint and shading mode normalizations.

3. Direct Tool Execution:
   - Direct async invocation of morphomesh_setup_inspector_camera_rig.
   - Direct async invocation of morphomesh_capture_viewport.
   - Direct async invocation of morphomesh_critique_visual_quality.

4. Protocol-Level MCP Invocation:
   - Client invocation via FastMCP `mcp.call_tool()`.
   - Serialization and payload structure validation from TextContent JSON.

5. Mocking, Bridge Integration & Offline Path:
   - Resilient execution in offline environments where Blender socket is not running.
   - Bridge mock injection testing parameter forwarding.
   - Error handling and ToolError propagation on unexpected failures or invalid inputs.

6. Backward Compatibility & Gating:
   - Strict isolation: when MORPHOMESH_INCLUDE_INSPECTION_TOOLS is unset, mcp.list_tools()
     returns exactly the 7 canonical creature tools.
   - Independent verification that tests/test_tools_schema.py passes 100% unmodified.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from morphomesh.models import (
    CaptureViewportInput,
    CaptureViewportOutput,
    DefectCategory,
    DefectItem,
    DefectSeverity,
    InspectorViewpoint,
    MorphoMeshException,
    SetupInspectorCameraInput,
    SetupInspectorCameraOutput,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)
from morphomesh.server import (
    ALL_TOOL_NAMES,
    CREATURE_TOOL_NAMES,
    HUMAN_TOOL_NAMES,
    INSPECTION_TOOL_NAMES,
    mcp,
    morphomesh_capture_viewport,
    morphomesh_critique_visual_quality,
    morphomesh_setup_inspector_camera_rig,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(autouse=True)
def enable_inspection_tools(monkeypatch: pytest.MonkeyPatch):
    """Enable FastMCP inspection tools listing for this test suite."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")


@pytest.fixture
def temp_capture_dir(tmp_path):
    """Isolated temporary directory for test capture artifacts."""
    out_dir = tmp_path / "captures"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir)


# ==============================================================================
# 1. TOOL REGISTRATION & DISCOVERY
# ==============================================================================

@pytest.mark.asyncio
async def test_all_three_inspection_tools_registered():
    """Verify all 3 inspection and critique tools are registered on FastMCP server."""
    tools = await mcp.list_tools()
    registered_names = {t.name for t in tools}

    for name in INSPECTION_TOOL_NAMES:
        assert name in registered_names, f"Inspection tool '{name}' not found on FastMCP server."

    assert len(tools) >= 10, f"Expected at least 10 tools (7 creature + 3 inspection), found {len(tools)}"


@pytest.mark.asyncio
async def test_inspection_tools_descriptions_and_metadata():
    """Verify every inspection tool possesses a non-empty, detailed docstring."""
    tools = await mcp.list_tools()
    inspection_tools = [t for t in tools if t.name in INSPECTION_TOOL_NAMES]

    for tool in inspection_tools:
        assert tool.description is not None, f"Tool '{tool.name}' lacks a description."
        assert len(tool.description.strip()) > 30, (
            f"Tool '{tool.name}' has insufficiently detailed description: '{tool.description}'"
        )


@pytest.mark.asyncio
async def test_inspection_tools_input_schemas():
    """Verify JSON Schemas generated for all 3 inspection tools."""
    tools = await mcp.list_tools()
    tools_by_name = {t.name: t for t in tools}

    # Tool 1: morphomesh_setup_inspector_camera_rig
    t1 = tools_by_name["morphomesh_setup_inspector_camera_rig"]
    props1 = t1.inputSchema["properties"]
    assert "viewpoint" in props1
    assert "focal_length" in props1
    assert "camera_name" in props1
    assert props1["viewpoint"]["default"] == "three_quarter"
    assert props1["focal_length"]["default"] == 50.0
    assert props1["camera_name"]["default"] == "MorphoMesh_Inspector_Camera"

    # Tool 2: morphomesh_capture_viewport
    t2 = tools_by_name["morphomesh_capture_viewport"]
    props2 = t2.inputSchema["properties"]
    assert "camera_name" in props2
    assert "shading_mode" in props2
    assert "color_type" in props2
    assert props2["camera_name"]["default"] == "MorphoMesh_Inspector_Camera"
    assert props2["shading_mode"]["default"] == "SOLID"
    assert props2["color_type"]["default"] == "RANDOM"

    # Tool 3: morphomesh_critique_visual_quality
    t3 = tools_by_name["morphomesh_critique_visual_quality"]
    props3 = t3.inputSchema["properties"]
    assert "character_name" in props3
    assert "clearance_tolerance" in props3
    assert "target_preset" in props3
    assert props3["character_name"]["default"] == "MorphoMesh_Character"
    assert props3["clearance_tolerance"]["default"] == 0.0005
    assert props3["target_preset"]["default"] == "stylized_heroine"


# ==============================================================================
# 2. PARAMETER VALIDATION & BOUNDS (PYDANTIC SCHEMAS)
# ==============================================================================

class TestInspectionInputSchemas:
    """Validate Pydantic v2 input schemas, bounds, and defaults."""

    def test_setup_inspector_camera_input_bounds_and_defaults(self):
        m = SetupInspectorCameraInput()
        assert m.viewpoint == "three_quarter"
        assert m.focal_length == 50.0
        assert m.margin == 0.15
        assert m.camera_name == "MorphoMesh_Inspector_Camera"

        # Out-of-bounds focal_length
        with pytest.raises(ValidationError):
            SetupInspectorCameraInput(focal_length=5.0)  # ge=10.0
        with pytest.raises(ValidationError):
            SetupInspectorCameraInput(focal_length=400.0)  # le=300.0

        # Out-of-bounds margin
        with pytest.raises(ValidationError):
            SetupInspectorCameraInput(margin=-0.1)  # ge=0.0
        with pytest.raises(ValidationError):
            SetupInspectorCameraInput(margin=1.5)  # le=1.0

    def test_capture_viewport_input_bounds_and_defaults(self):
        m = CaptureViewportInput()
        assert m.camera_name == "MorphoMesh_Inspector_Camera"
        assert m.shading_mode == "SOLID"
        assert m.color_type == "RANDOM"
        assert m.resolution == [1024, 1024]

    def test_visual_critique_input_defaults_and_alias_resolution(self):
        m = VisualCritiqueInput()
        assert m.target_object == "Human_Base_Mesh"
        assert m.target_preset == "stylized_heroine"
        assert m.clearance_tolerance == 0.0005
        assert m.camera_angles == ["front", "side", "three_quarter", "back"]

        # Alias resolution: char_name -> character_name
        m_alias = VisualCritiqueInput(char_name="Yu_Nian_An_Heroine")
        assert m_alias.character_name == "Yu_Nian_An_Heroine"
        assert m_alias.target_object == "Yu_Nian_An_Heroine_Base_Mesh"

        # Alias resolution: clearance_threshold -> clearance_tolerance
        m_thresh = VisualCritiqueInput(clearance_threshold=0.001)
        assert m_thresh.clearance_tolerance == 0.001

        # Negative tolerance rejected
        with pytest.raises(ValidationError):
            VisualCritiqueInput(clearance_tolerance=-0.001)


# ==============================================================================
# 3. DIRECT EXECUTION OF FASTMCP INSPECTION TOOLS
# ==============================================================================

@pytest.mark.asyncio
async def test_exec_setup_inspector_camera_rig():
    """Verify direct invocation of morphomesh_setup_inspector_camera_rig."""
    res = await morphomesh_setup_inspector_camera_rig(
        viewpoint="three_quarter",
        focal_length=50.0,
        camera_name="MorphoMesh_Inspector_Camera",
    )
    assert isinstance(res, dict)
    assert res.get("status") == "success"
    assert res.get("camera_name") == "MorphoMesh_Inspector_Camera"
    assert res.get("viewpoint") == "three_quarter"
    assert "camera_location" in res or "location" in res
    assert "camera_rotation" in res or "rotation_euler" in res


@pytest.mark.asyncio
async def test_exec_capture_viewport(temp_capture_dir):
    """Verify direct invocation of morphomesh_capture_viewport."""
    out_file = os.path.join(temp_capture_dir, "test_capture.png")
    res = await morphomesh_capture_viewport(
        output_path=out_file,
        shading_mode="SOLID",
        color_type="RANDOM",
        resolution=[512, 512],
    )
    assert isinstance(res, dict)
    assert res.get("status") == "success"
    assert "image_path" in res
    assert res.get("shading_mode") == "SOLID"
    assert res.get("color_type") == "RANDOM"
    assert "base64_preview" in res
    assert len(res["base64_preview"]) > 0


@pytest.mark.asyncio
async def test_exec_critique_visual_quality():
    """Verify direct invocation of morphomesh_critique_visual_quality."""
    res = await morphomesh_critique_visual_quality(
        character_name="Yu_Nian_An",
        target_preset="stylized_heroine",
        clearance_tolerance=0.0005,
    )
    assert isinstance(res, dict)
    assert res.get("status") == "success"
    assert "passed" in res
    assert "quality_score" in res
    assert res.get("quality_score", 0.0) >= 0.0
    assert "defect_count" in res
    assert "defects" in res
    assert "recommendations" in res


@pytest.mark.asyncio
async def test_exec_critique_visual_quality_custom_angles():
    """Verify critique execution with customized camera angles."""
    custom_angles = ["front", "side", "top"]
    res = await morphomesh_critique_visual_quality(
        character_name="Yu_Nian_An",
        camera_angles=custom_angles,
    )
    assert res.get("status") == "success"
    assert res.get("evaluated_angles") == custom_angles


# ==============================================================================
# 4. MCP CALL_TOOL INVOCATION
# ==============================================================================

@pytest.mark.asyncio
async def test_call_tool_setup_inspector_camera_rig():
    """Verify invoking morphomesh_setup_inspector_camera_rig through mcp.call_tool()."""
    result = await mcp.call_tool(
        "morphomesh_setup_inspector_camera_rig",
        {"viewpoint": "front", "focal_length": 85.0},
    )
    assert result is not None
    content = result[0][0] if isinstance(result[0], (list, tuple)) else result[0]
    payload = json.loads(content.text)
    assert payload.get("status") == "success"
    assert payload.get("viewpoint") == "front"


@pytest.mark.asyncio
async def test_call_tool_capture_viewport():
    """Verify invoking morphomesh_capture_viewport through mcp.call_tool()."""
    result = await mcp.call_tool(
        "morphomesh_capture_viewport",
        {"shading_mode": "WIREFRAME", "resolution": [512, 512]},
    )
    assert result is not None
    content = result[0][0] if isinstance(result[0], (list, tuple)) else result[0]
    payload = json.loads(content.text)
    assert payload.get("status") == "success"
    assert payload.get("shading_mode") == "WIREFRAME"


@pytest.mark.asyncio
async def test_call_tool_critique_visual_quality():
    """Verify invoking morphomesh_critique_visual_quality through mcp.call_tool()."""
    result = await mcp.call_tool(
        "morphomesh_critique_visual_quality",
        {"character_name": "Yu_Nian_An_CallTool", "clearance_tolerance": 0.001},
    )
    assert result is not None
    content = result[0][0] if isinstance(result[0], (list, tuple)) else result[0]
    payload = json.loads(content.text)
    assert payload.get("status") == "success"
    assert "quality_score" in payload
    assert "recommendations" in payload


# ==============================================================================
# 5. MOCKING, BRIDGE INTEGRATION & OFFLINE RESILIENCE
# ==============================================================================

@pytest.mark.asyncio
async def test_inspection_tools_offline_graceful_fallback():
    """Ensure tools execute cleanly when Blender socket is offline."""
    from morphomesh.server import blender_bridge
    with patch.object(blender_bridge, "is_interactive_connected", return_value=False):
        res_cam = await morphomesh_setup_inspector_camera_rig(viewpoint="side")
        assert res_cam.get("status") == "success"
        assert res_cam.get("viewpoint") == "side"

        res_crit = await morphomesh_critique_visual_quality(character_name="Offline_Test")
        assert res_crit.get("status") == "success"
        assert res_crit.get("passed") is True


@pytest.mark.asyncio
async def test_bridge_critique_visual_quality_mocked_defects():
    """Verify tool formats and returns structured defects from bridge report."""
    from morphomesh.server import blender_bridge

    mock_report = {
        "status": "success",
        "passed": False,
        "quality_score": 65.0,
        "defect_count": 2,
        "defects": [
            {
                "defect_id": "DEF-001",
                "category": "PENETRATION",
                "severity": "CRITICAL",
                "description": "Garment clipping through thigh mesh",
                "object_name": "Dress_Mesh",
                "location": [0.0, 0.1, 0.8],
                "signed_distance": -0.004,
            },
            {
                "defect_id": "DEF-002",
                "category": "PROPORTIONS",
                "severity": "MAJOR",
                "description": "Head ratio exceeds 8.0",
                "object_name": "Human_Base_Mesh",
            },
        ],
        "recommendations": ["Adjust garment offset modifier", "Scale head anatomy"],
        "actionable_recommendations": [],
        "inspected_objects": ["Dress_Mesh", "Human_Base_Mesh"],
        "scene_stats": {},
        "evaluated_angles": ["front", "side", "three_quarter", "back"],
    }

    with patch.object(blender_bridge, "critique_visual_quality", return_value=mock_report):
        res = await morphomesh_critique_visual_quality(character_name="Defect_Character")
        assert res["status"] == "success"
        assert res["passed"] is False
        assert res["quality_score"] == 65.0
        assert res["defect_count"] == 2
        assert len(res["defects"]) == 2
        assert res["defects"][0]["severity"] == "CRITICAL"


@pytest.mark.asyncio
async def test_tool_error_handling_on_invalid_arguments():
    """Verify ToolError or validation exception on out-of-bounds parameters."""
    with pytest.raises((ToolError, ValidationError)):
        await morphomesh_setup_inspector_camera_rig(focal_length=500.0)

    with pytest.raises((ToolError, ValidationError)):
        await morphomesh_setup_inspector_camera_rig(focal_length=-5.0)

    with pytest.raises((ToolError, ValidationError)):
        await morphomesh_setup_inspector_camera_rig(target_center=[1.0, 2.0])  # Non-3-element

    with pytest.raises((ToolError, ValidationError)):
        await morphomesh_capture_viewport(resolution=[-100, 1024])

    with pytest.raises((ToolError, ValidationError)):
        await morphomesh_critique_visual_quality(clearance_tolerance=-0.5)


@pytest.mark.asyncio
async def test_bridge_exception_mapping():
    """Verify bridge MorphoMeshException is cleanly mapped to ToolError with error code."""
    from morphomesh.server import blender_bridge

    with patch.object(
        blender_bridge,
        "setup_inspector_camera",
        side_effect=MorphoMeshException(code="ERR_CAMERA_FAILED", message="Camera error"),
    ):
        with pytest.raises(ToolError) as exc_info:
            await morphomesh_setup_inspector_camera_rig()
        assert "[ERR_CAMERA_FAILED]" in str(exc_info.value)


# ==============================================================================
# 6. BACKWARD COMPATIBILITY & GATING
# ==============================================================================

@pytest.mark.asyncio
async def test_gating_flag_unset_returns_only_seven_creature_tools(monkeypatch: pytest.MonkeyPatch):
    """Verify mcp.list_tools() returns strictly 7 creature tools when gating flag is unset."""
    monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_ALL_TOOLS", raising=False)

    tools = await mcp.list_tools()
    registered_names = {t.name for t in tools}

    assert registered_names == CREATURE_TOOL_NAMES
    assert len(tools) == 7
    for insp_name in INSPECTION_TOOL_NAMES:
        assert insp_name not in registered_names


@pytest.mark.asyncio
async def test_gating_flag_inspection_only(monkeypatch: pytest.MonkeyPatch):
    """Verify mcp.list_tools() returns exactly 10 tools when only inspection flag is active."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")
    monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_ALL_TOOLS", raising=False)

    tools = await mcp.list_tools()
    registered_names = {t.name for t in tools}

    expected_ten = CREATURE_TOOL_NAMES | INSPECTION_TOOL_NAMES
    assert registered_names == expected_ten
    assert len(tools) == 10


@pytest.mark.asyncio
async def test_gating_flag_all_tools(monkeypatch: pytest.MonkeyPatch):
    """Verify mcp.list_tools() returns all 17 tools when MORPHOMESH_INCLUDE_ALL_TOOLS is set."""
    monkeypatch.setenv("MORPHOMESH_INCLUDE_ALL_TOOLS", "1")

    tools = await mcp.list_tools()
    registered_names = {t.name for t in tools}

    assert registered_names == ALL_TOOL_NAMES
    assert len(tools) == 17


@pytest.mark.asyncio
async def test_tools_schema_compatibility_unaffected(monkeypatch: pytest.MonkeyPatch):
    """Verify tests/test_tools_schema.py expectation passes 100% when flag is unset."""
    monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_ALL_TOOLS", raising=False)

    from tests.test_tools_schema import EXPECTED_TOOL_NAMES, test_all_seven_tools_registered
    await test_all_seven_tools_registered()
