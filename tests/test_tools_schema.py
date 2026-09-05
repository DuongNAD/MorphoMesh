"""
MorphoMesh: MCP Tool Schema and Parameter Validation Tests.

Validates tool definitions, JSON-RPC schemas, parameter constraints, bounds,
type coercion, and error handling for all 7 authoritative MCP tools according to
MCP Specification MM-R3-SPEC-001.
"""

from __future__ import annotations

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from morphomesh.models import (
    AutoRigInput,
    BlenderExecuteInput,
    Create3DAssetInput,
    CreatureType,
    GenerateConceptInput,
    LightingPreset,
    OptimizeTopologyInput,
    Pose,
    RenderEngine,
    RenderPreviewInput,
    RetopoMethod,
    RigType,
    SceneStatusInput,
    SkinningMethod,
    Style,
    TopologyType,
    ViewMode,
)
from morphomesh.server import (
    mcp,
    morphomesh_blender_execute,
    morphomesh_create_3d_asset,
    morphomesh_generate_concept,
    morphomesh_optimize_topology,
)

EXPECTED_TOOL_NAMES = {
    "morphomesh_generate_concept",
    "morphomesh_create_3d_asset",
    "morphomesh_optimize_topology",
    "morphomesh_auto_rig",
    "morphomesh_blender_execute",
    "morphomesh_get_scene_status",
    "morphomesh_render_preview",
}


# ==============================================================================
# 1. TOOL REGISTRATION & SCHEMA DISCOVERY
# ==============================================================================

@pytest.mark.asyncio
async def test_all_seven_tools_registered():
    """Verify that exactly 7 tools are registered on the FastMCP server."""
    tools = await mcp.list_tools()
    registered_names = {t.name for t in tools}
    assert registered_names == EXPECTED_TOOL_NAMES, (
        f"Mismatch in registered tool names. Expected {EXPECTED_TOOL_NAMES}, got {registered_names}"
    )
    assert len(tools) == 7, f"Expected 7 tools, found {len(tools)}"


@pytest.mark.asyncio
async def test_tools_have_non_empty_descriptions():
    """Verify each registered tool possesses a descriptive docstring explaining its role."""
    tools = await mcp.list_tools()
    for tool in tools:
        assert tool.description is not None, f"Tool {tool.name} lacks a description."
        assert len(tool.description.strip()) > 20, (
            f"Tool {tool.name} has an insufficiently detailed description: '{tool.description}'"
        )


@pytest.mark.asyncio
async def test_tools_input_schema_structure():
    """Verify top-level JSON Schema parameters on each tool."""
    tools = await mcp.list_tools()
    tools_by_name = {t.name: t for t in tools}

    # Tool 1: morphomesh_generate_concept
    t1 = tools_by_name["morphomesh_generate_concept"]
    assert "prompt" in t1.inputSchema["properties"]
    assert "required" in t1.inputSchema
    assert "prompt" in t1.inputSchema["required"]
    assert t1.inputSchema["properties"]["prompt"]["type"] == "string"
    assert t1.inputSchema["properties"]["width"]["default"] == 1024
    assert t1.inputSchema["properties"]["height"]["default"] == 1024

    # Tool 2: morphomesh_create_3d_asset
    t2 = tools_by_name["morphomesh_create_3d_asset"]
    assert "image_path" in t2.inputSchema["properties"]
    assert "concept_id" in t2.inputSchema["properties"]
    assert t2.inputSchema["properties"]["model_backend"]["default"] == "mock"
    assert t2.inputSchema["properties"]["generate_pbr"]["default"] is True

    # Tool 3: morphomesh_optimize_topology
    t3 = tools_by_name["morphomesh_optimize_topology"]
    assert "target_poly_count" in t3.inputSchema["properties"]
    assert t3.inputSchema["properties"]["target_poly_count"]["default"] == 10000
    assert t3.inputSchema["properties"]["topology_type"]["default"] == "quad_dominant"

    # Tool 4: morphomesh_auto_rig
    t4 = tools_by_name["morphomesh_auto_rig"]
    assert "creature_type" in t4.inputSchema["properties"]
    assert t4.inputSchema["properties"]["creature_type"]["default"] == "quadruped"
    assert t4.inputSchema["properties"]["rig_type"]["default"] == "rigify_creature"

    # Tool 5: morphomesh_blender_execute
    t5 = tools_by_name["morphomesh_blender_execute"]
    assert "script" in t5.inputSchema["properties"]
    assert "script" in t5.inputSchema["required"]
    assert t5.inputSchema["properties"]["timeout_seconds"]["default"] == 30

    # Tool 6: morphomesh_get_scene_status
    t6 = tools_by_name["morphomesh_get_scene_status"]
    assert "include_mesh_stats" in t6.inputSchema["properties"]
    assert t6.inputSchema["properties"]["include_mesh_stats"]["default"] is True

    # Tool 7: morphomesh_render_preview
    t7 = tools_by_name["morphomesh_render_preview"]
    assert "render_engine" in t7.inputSchema["properties"]
    assert t7.inputSchema["properties"]["render_engine"]["default"] == "BLENDER_EEVEE"
    assert t7.inputSchema["properties"]["samples"]["default"] == 64


# ==============================================================================
# 2. PARAMETER VALIDATION & BOUNDS (PYDANTIC SCHEMAS)
# ==============================================================================

class TestGenerateConceptInputSchema:
    """Validate GenerateConceptInput schema bounds, types, and step validators."""

    def test_valid_defaults(self):
        m = GenerateConceptInput(prompt="A ferocious direwolf")
        assert m.prompt == "A ferocious direwolf"
        assert m.creature_type == CreatureType.CUSTOM
        assert m.width == 1024
        assert m.height == 1024
        assert m.seed == -1

    def test_prompt_min_length(self):
        with pytest.raises(ValidationError):
            GenerateConceptInput(prompt="ab")  # min 3 chars

    def test_prompt_max_length(self):
        with pytest.raises(ValidationError):
            GenerateConceptInput(prompt="x" * 2001)  # max 2000 chars

    def test_width_height_bounds(self):
        with pytest.raises(ValidationError):
            GenerateConceptInput(prompt="Valid prompt", width=256)  # ge=512
        with pytest.raises(ValidationError):
            GenerateConceptInput(prompt="Valid prompt", height=4096)  # le=2048

    def test_dimension_step_rounding(self):
        # 1000 is not a multiple of 64; should round to 1024
        m = GenerateConceptInput(prompt="Valid prompt", width=1000, height=700)
        assert m.width == 1024
        assert m.height == 704  # round(700/64)*64 = 11*64 = 704

    def test_seed_bounds(self):
        with pytest.raises(ValidationError):
            GenerateConceptInput(prompt="Valid prompt", seed=-2)  # ge=-1
        m = GenerateConceptInput(prompt="Valid prompt", seed=42)
        assert m.seed == 42

    def test_enums(self):
        m = GenerateConceptInput(
            prompt="Valid prompt",
            creature_type=CreatureType.QUADRUPED,
            view_mode=ViewMode.FRONT,
            pose=Pose.STANDING_NEUTRAL,
            style=Style.DARK_FANTASY,
        )
        assert m.creature_type == "quadruped"
        assert m.view_mode == "front"


class TestCreate3DAssetInputSchema:
    """Validate Create3DAssetInput schema bounds and options."""

    def test_valid_input(self):
        m = Create3DAssetInput(concept_id="c-123", guidance_scale=8.0)
        assert m.concept_id == "c-123"
        assert m.guidance_scale == 8.0
        assert m.export_format == "glb"
        assert m.generate_pbr is True

    def test_guidance_scale_bounds(self):
        with pytest.raises(ValidationError):
            Create3DAssetInput(concept_id="c-123", guidance_scale=0.5)  # ge=1.0
        with pytest.raises(ValidationError):
            Create3DAssetInput(concept_id="c-123", guidance_scale=25.0)  # le=20.0

    def test_seed_bounds(self):
        with pytest.raises(ValidationError):
            Create3DAssetInput(concept_id="c-123", seed=-5)  # ge=-1


class TestOptimizeTopologyInputSchema:
    """Validate OptimizeTopologyInput bounds and defaults."""

    def test_valid_defaults(self):
        m = OptimizeTopologyInput(asset_id="a-123")
        assert m.target_poly_count == 10000
        assert m.topology_type == TopologyType.QUAD_DOMINANT
        assert m.method == RetopoMethod.QUADRIFLOW

    def test_target_poly_count_bounds(self):
        with pytest.raises(ValidationError):
            OptimizeTopologyInput(asset_id="a-123", target_poly_count=100)  # ge=500
        with pytest.raises(ValidationError):
            OptimizeTopologyInput(asset_id="a-123", target_poly_count=600000)  # le=500000

    def test_retopo_methods(self):
        for method in [RetopoMethod.QUADRIFLOW, RetopoMethod.DECIMATE, RetopoMethod.VOXEL_REMESH, RetopoMethod.MOCK]:
            m = OptimizeTopologyInput(asset_id="a-123", method=method)
            assert m.method == method


class TestAutoRigInputSchema:
    """Validate AutoRigInput enums and defaults."""

    def test_valid_defaults(self):
        m = AutoRigInput(asset_id="a-123")
        assert m.creature_type == CreatureType.QUADRUPED
        assert m.rig_type == RigType.RIGIFY_CREATURE
        assert m.skinning_method == SkinningMethod.AUTOMATIC_WEIGHTS
        assert m.symmetry is True
        assert m.generate_test_animation is True
        assert m.load_into_scene is True

    def test_creature_type_variants(self):
        types = [CreatureType.QUADRUPED, CreatureType.BIPED, CreatureType.WINGED_QUADRUPED, CreatureType.SERPENTINE]
        for ct in types:
            m = AutoRigInput(asset_id="a-123", creature_type=ct)
            assert m.creature_type == ct


class TestBlenderExecuteInputSchema:
    """Validate BlenderExecuteInput constraints."""

    def test_valid_script(self):
        m = BlenderExecuteInput(script="import bpy\nprint('hello')", timeout_seconds=15)
        assert m.script.startswith("import bpy")
        assert m.timeout_seconds == 15
        assert m.save_after is False

    def test_empty_script_rejected(self):
        with pytest.raises(ValidationError):
            BlenderExecuteInput(script="")  # min_length=1

    def test_script_length_limit(self):
        with pytest.raises(ValidationError):
            BlenderExecuteInput(script="x" * 10001)  # max_length=10000

    def test_timeout_bounds(self):
        with pytest.raises(ValidationError):
            BlenderExecuteInput(script="pass", timeout_seconds=0)  # ge=1
        with pytest.raises(ValidationError):
            BlenderExecuteInput(script="pass", timeout_seconds=400)  # le=300


class TestSceneStatusInputSchema:
    """Validate SceneStatusInput defaults."""

    def test_defaults(self):
        m = SceneStatusInput()
        assert m.scene_name is None
        assert m.include_mesh_stats is True
        assert m.include_hierarchy is True
        assert m.include_materials is True
        assert m.include_armatures is True
        assert m.include_cameras_lights is True


class TestRenderPreviewInputSchema:
    """Validate RenderPreviewInput constraints and engine normalization."""

    def test_valid_defaults(self):
        m = RenderPreviewInput()
        assert m.resolution_width == 1024
        assert m.resolution_height == 1024
        assert m.render_engine == RenderEngine.BLENDER_EEVEE
        assert m.samples == 64
        assert m.lighting_preset == LightingPreset.STUDIO_THREE_POINT

    def test_engine_normalization_eevee_next(self):
        """Blender 5.2.1 LTS strictly identifies EEVEE Next as 'BLENDER_EEVEE'."""
        m = RenderPreviewInput(render_engine="BLENDER_EEVEE_NEXT")
        assert m.render_engine == "BLENDER_EEVEE"

    def test_resolution_bounds(self):
        with pytest.raises(ValidationError):
            RenderPreviewInput(resolution_width=128)  # ge=256
        with pytest.raises(ValidationError):
            RenderPreviewInput(resolution_height=5000)  # le=4096

    def test_samples_bounds(self):
        with pytest.raises(ValidationError):
            RenderPreviewInput(samples=0)  # ge=1
        with pytest.raises(ValidationError):
            RenderPreviewInput(samples=2048)  # le=1024


# ==============================================================================
# 3. TOOL ERROR RESPONSES ON INVALID ARGUMENTS
# ==============================================================================

@pytest.mark.asyncio
async def test_tool_concept_invalid_prompt():
    """Verify tool raises ToolError when prompt is empty or whitespace-only."""
    with pytest.raises(ToolError) as exc_info:
        await morphomesh_generate_concept(prompt="a", ctx=None)
    assert "validation error" in str(exc_info.value).lower()
    assert "at least 3 characters" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tool_create_3d_asset_missing_image_and_concept():
    """Verify tool raises ToolError when neither image_path nor concept_id is provided."""
    with pytest.raises(ToolError) as exc_info:
        await morphomesh_create_3d_asset(image_path=None, concept_id=None, ctx=None)
    err_msg = str(exc_info.value)
    assert "ERR_IMAGE_NOT_FOUND" in err_msg


@pytest.mark.asyncio
async def test_tool_optimize_topology_missing_input():
    """Verify tool raises ToolError when input mesh file does not exist."""
    with pytest.raises(ToolError) as exc_info:
        await morphomesh_optimize_topology(input_mesh_path="/nonexistent/missing_file.glb", ctx=None)
    err_msg = str(exc_info.value)
    assert "ERR_INPUT_MESH_NOT_FOUND" in err_msg


@pytest.mark.asyncio
async def test_tool_blender_execute_empty_script():
    """Verify tool raises ToolError when script parameter is empty."""
    with pytest.raises(ToolError) as exc_info:
        await morphomesh_blender_execute(script="", ctx=None)
    err_msg = str(exc_info.value)
    assert "ERR_INVALID_ARGUMENT" in err_msg

    with pytest.raises(ToolError) as exc_info2:
        await morphomesh_blender_execute(script="   \n\t  ", ctx=None)
    assert "ERR_INVALID_ARGUMENT" in str(exc_info2.value)
