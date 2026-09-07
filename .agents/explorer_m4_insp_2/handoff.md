# Handoff Report: FastMCP Inspection Test Suite Blueprint (`tests/test_fastmcp_inspection_tools.py`)

**Agent**: Explorer M4_2 (`.agents/explorer_m4_insp_2`)  
**Milestone**: Milestone 4 — FastMCP Tool Integration & Verification Suite  
**Target File**: `tests/test_fastmcp_inspection_tools.py`  
**Reference Implementations**: `tests/test_fastmcp_human_tools.py`, `tests/test_tools_schema.py`

---

## 1. Observation

Direct code inspections and empirical commands yielded the following ground-truth observations across the repository:

### A. Existing Test Suite Baseline & Legacy Gating
1. **`tests/test_tools_schema.py`** (Lines 42–66):
   ```python
   EXPECTED_TOOL_NAMES = {
       "morphomesh_generate_concept",
       "morphomesh_create_3d_asset",
       "morphomesh_optimize_topology",
       "morphomesh_auto_rig",
       "morphomesh_blender_execute",
       "morphomesh_get_scene_status",
       "morphomesh_render_preview",
   }
   ...
   @pytest.mark.asyncio
   async def test_all_seven_tools_registered():
       tools = await mcp.list_tools()
       registered_names = {t.name for t in tools}
       assert registered_names == EXPECTED_TOOL_NAMES
       assert len(tools) == 7
   ```
   *Verification*: `test_all_seven_tools_registered` runs without setting any environment variables and strictly asserts `len(tools) == 7`.

2. **`tests/test_fastmcp_human_tools.py`** (Lines 41–45):
   ```python
   @pytest.fixture(autouse=True)
   def enable_human_tools(monkeypatch: pytest.MonkeyPatch):
       """Ensure FastMCP lists all 12 tools for human tool tests."""
       monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")
   ```
   *Verification*: Human tools test uses an autouse fixture setting `MORPHOMESH_INCLUDE_HUMAN_TOOLS="1"` so discovery tests see human tools while legacy tests in `test_tools_schema.py` remain unaffected.

3. **`src/morphomesh/server.py`** (Lines 1114–1143):
   ```python
   async def _filtered_list_tools(*args, **kwargs):
       tools = await _orig_fastmcp_list_tools(*args, **kwargs)
       flag = os.environ.get("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "").strip().lower()
       if flag in ("1", "true", "yes", "all"):
           return tools
       return [t for t in tools if t.name in CREATURE_TOOL_NAMES]
   ```
   *Observation*: `mcp.list_tools` and `mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]` filter registered tools against `CREATURE_TOOL_NAMES` unless the gating flag is active.

### B. Existing Inspection Engine & Pydantic Models
1. **`src/morphomesh/models.py`**:
   - Lines 680–692: `SetupInspectorCameraInput` (`viewpoint: str = "three_quarter"`, `target_object: Optional[str]`, `target_center: Optional[List[float]]`, `framing_radius: Optional[float]`, `focal_length: float = 50.0` [ge=10.0, le=300.0], `camera_name: str = "MorphoMesh_Inspector_Camera"`, `margin: float = 0.15` [ge=0.0, le=1.0], `resolution: List[int] = [1024, 1024]`).
   - Lines 694–708: `SetupInspectorCameraOutput` (`status`, `camera_name`, `viewpoint`, `focal_length`, `camera_location`, `camera_rotation`, `target_center`, `framing_distance`, `bounding_radius`, `bounding_box`).
   - Lines 710–722: `CaptureViewportInput` (`output_path: Optional[str]`, `camera_name: str = "MorphoMesh_Inspector_Camera"`, `resolution: List[int] = [1024, 1024]`, `shading_mode: str = "SOLID"`, `color_type: str = "RANDOM"`).
   - Lines 724–735: `CaptureViewportOutput` (`status`, `image_path`, `image_format`, `resolution`, `shading_mode`, `color_type`, `camera_name`, `base64_preview: Optional[str]`).
   - Lines 998–1043: `VisualCritiqueInput` (`target_object: Optional[str] = "Human_Base_Mesh"`, `character_name: Optional[str]`, `camera_angles: Optional[List[str]] = ["front", "side", "three_quarter", "back"]`, `clearance_tolerance: float = 0.0005` [ge=0.0], `target_preset: str = "stylized_heroine"`, `evaluate_penetration: bool = True`, `evaluate_proportions: bool = True`, `evaluate_skinning: bool = True`, `evaluate_grooming: bool = True`, `capture_images: bool = False`). Aliases: `char_name` -> `character_name`, `clearance_threshold` -> `clearance_tolerance`, `viewpoints` -> `camera_angles`.
   - Lines 1046–1060: `VisualCritiqueOutput` (`status`, `passed: bool`, `quality_score: float` [0.0..100.0], `defect_count: int`, `defects: List[DefectItem]`, `recommendations: List[str]`, `actionable_recommendations: List[ActionableRecommendation]`, `inspected_objects: List[str]`, `scene_stats: Dict[str, Any]`, `evaluated_angles: List[str]`).

2. **`src/morphomesh/camera_rig.py`**:
   - Lines 815–918: `setup_inspector_camera` functions completely in pure Python when `HAS_BPY` is False or `scene is None`. Calculates optical distance $d = \frac{R}{\sin(\alpha_{\min})} \cdot (1 + \mu)$ and spherical coordinates, returning a complete metadata dictionary.
   - Lines 921–955: `capture_viewport_image` creates a valid PNG on disk using PIL or writes `FALLBACK_PNG_BYTES` when running outside Blender.
   - Lines 34–46: `encode_image_to_base64` encodes saved images to base64 strings.

3. **`src/morphomesh/visual_critic.py`**:
   - Lines 2093–2170: `run_visual_critique(input_data: VisualCritiqueInput) -> VisualCritiqueOutput` executes pure-Python BVH evaluations, proportion metrics, skinning crease evaluations, and returns a structured Pydantic `VisualCritiqueOutput` report.

4. **`src/morphomesh/blender_bridge.py`**:
   - Lines 2463–2498: `capture_viewport` client method dispatches to `self.execute("morphomesh.capture_viewport", ...)`.
   - Lines 2500–2538: `setup_inspector_camera` client method dispatches to `self.execute("morphomesh.setup_inspector_camera", ...)`.
   - Lines 2585–2638: `critique_visual_quality` client method dispatches to `self.execute("morphomesh.critique_visual_quality", ...)`.
   - Lines 589–630: `_generate_interactive_script` maps all 3 inspection RPC methods.
   - Lines 2120–2285: `_generate_headless_script` maps all 3 inspection RPC methods.

5. **Empirical Verification Baseline**:
   - Running `pytest tests/test_tools_schema.py tests/test_fastmcp_human_tools.py tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_visual_critic.py tests/test_bridge_socket_parity.py` returned:
   - **`161 passed in 18.93s`** with zero warnings and zero failures.

---

## 2. Logic Chain

From these observations, we establish the following step-by-step engineering logic:

1. **Architectural Parity with Human Tools**:
   - `test_fastmcp_human_tools.py` successfully isolates human tools from breaking legacy `test_tools_schema.py` via `monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")`.
   - By creating `tests/test_fastmcp_inspection_tools.py` with an autouse fixture setting `monkeypatch.setenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "1")`, the inspection test suite can thoroughly validate all 3 inspection tools without mutating global server state or breaking `test_tools_schema.py`.

2. **Tool Discovery & Schema Validation**:
   - FastMCP compiles Pydantic models and function signatures into standard MCP tool descriptors (`name`, `description`, `inputSchema`).
   - The test suite must assert that `mcp.list_tools()` discovers:
     * `morphomesh_setup_inspector_camera_rig`
     * `morphomesh_capture_viewport`
     * `morphomesh_critique_visual_quality`
   - Schema validation must verify property types, required parameters, and defaults (e.g. `focal_length=50.0`, `shading_mode="SOLID"`, `color_type="RANDOM"`, `clearance_tolerance=0.0005`, `target_preset="stylized_heroine"`).

3. **Execution Modes: Direct vs Protocol**:
   - Direct execution calls the async tool functions (`morphomesh_setup_inspector_camera_rig(...)`, `morphomesh_capture_viewport(...)`, `morphomesh_critique_visual_quality(...)`) directly.
   - Protocol-level execution calls `mcp.call_tool(tool_name, args)`. FastMCP wraps results in `TextContent` containing serialized JSON. The test must parse `result[0][0].text` and validate the payload schema.

4. **Mocking & Bridge Resilience in Offline Environments**:
   - Standard CI and test environments lack a running Blender GUI window.
   - The tests must verify both:
     a) Graceful fallback execution when bridge is offline (utilizing `camera_rig.py` and `visual_critic.py` pure-Python engines).
     b) Mock injection patching `blender_bridge` methods (`setup_inspector_camera`, `capture_viewport`, `critique_visual_quality`) to assert correct RPC parameter formatting and defect reporting.
     c) Error containment: verifying `ToolError` is raised on invalid inputs or bridge failures.

5. **Gating & Backward Compatibility Guarantee**:
   - Test cases with `monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)` and `monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)` must assert that `len(tools) == 7` and matches `EXPECTED_TOOL_NAMES` identically.
   - Combined gating tests verify selective inclusion: inspection-only (10 tools), human-only (14 tools), or both (17 tools).

---

## 3. Caveats

- **No live Blender requirement**: All unit tests in `tests/test_fastmcp_inspection_tools.py` are engineered to run completely offline without Blender installed or running. If Blender is running, the bridge will connect dynamically without test failure.
- **FastMCP TextContent Structure**: In FastMCP, `call_tool` returns a tuple `(content_list, meta_dict)` or list of content blocks. The blueprint accesses `result[0][0]` if nested, or `result[0]` with fallback `getattr(content, "text", str(content))`, matching the established pattern in `test_fastmcp_human_tools.py`.
- **Read-Only Explorer Scope**: In accordance with the explorer archetype, no source files were modified during this investigation.

---

## 4. Conclusion & Complete Implementation Blueprint

Below is the complete, self-contained blueprint for `tests/test_fastmcp_inspection_tools.py`.

```python
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
    SetupInspectorCameraInput,
    SetupInspectorCameraOutput,
    VisualCritiqueInput,
    VisualCritiqueOutput,
)
from morphomesh.server import (
    CREATURE_TOOL_NAMES,
    mcp,
    morphomesh_capture_viewport,
    morphomesh_critique_visual_quality,
    morphomesh_setup_inspector_camera_rig,
)

INSPECTION_TOOL_NAMES = {
    "morphomesh_setup_inspector_camera_rig",
    "morphomesh_capture_viewport",
    "morphomesh_critique_visual_quality",
}


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
    # TextContent payload extraction
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
    # Ensure bridge is offline
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
async def test_tools_schema_compatibility_unaffected(monkeypatch: pytest.MonkeyPatch):
    """Verify tests/test_tools_schema.py expectation passes 100% when flag is unset."""
    monkeypatch.delenv("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", raising=False)
    monkeypatch.delenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", raising=False)

    from tests.test_tools_schema import EXPECTED_TOOL_NAMES, test_all_seven_tools_registered
    await test_all_seven_tools_registered()
```

---

## 5. Verification Method

To independently verify this blueprint:

1. **Verify Existing Suites Pass Unmodified**:
   ```bash
   pytest tests/test_tools_schema.py tests/test_fastmcp_human_tools.py tests/test_inspector_camera.py tests/test_multiview_rendering.py tests/test_visual_critic.py tests/test_bridge_socket_parity.py -v
   ```
   *Expected Result*: Exit code 0, 161 tests passed.

2. **Verify New Test Suite Execution (Once Implemented)**:
   ```bash
   pytest tests/test_fastmcp_inspection_tools.py -v
   ```
   *Expected Result*: Exit code 0, all discovery, schema, execution, mock, and gating tests pass.

3. **Verify Zero Regression Across Entire Repository**:
   ```bash
   pytest -q
   ```
   *Expected Result*: Exit code 0, 0 failures.

4. **Invalidation Conditions**:
   - If `mcp.list_tools()` returns inspection tools when `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` is unset (breaking `test_tools_schema.py`).
   - If `morphomesh_setup_inspector_camera_rig` or `morphomesh_capture_viewport` fails in offline environments due to missing Blender binary.
   - If `morphomesh_critique_visual_quality` returns invalid defect schema or fails to map aliases.
