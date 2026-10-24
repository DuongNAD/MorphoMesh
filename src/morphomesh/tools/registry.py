"""
MorphoMesh Tools Subsystem: Central Tool Registry.

Registers all 19 authoritative tools across creature, human, inspection,
and animation subsystems onto the FastMCP server.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from morphomesh.tools.animation import (
    morphomesh_animate_asset,
    morphomesh_list_animations,
)
from morphomesh.tools.creature import (
    morphomesh_auto_rig,
    morphomesh_blender_execute,
    morphomesh_create_3d_asset,
    morphomesh_generate_concept,
    morphomesh_get_scene_status,
    morphomesh_optimize_topology,
    morphomesh_render_preview,
)
from morphomesh.tools.human import (
    morphomesh_assemble_master_character,
    morphomesh_auto_rig_human,
    morphomesh_create_human_asset,
    morphomesh_dress_human,
    morphomesh_export_production_character,
    morphomesh_groom_human,
    morphomesh_setup_human_materials,
)
from morphomesh.tools.inspection import (
    morphomesh_capture_viewport,
    morphomesh_critique_visual_quality,
    morphomesh_setup_inspector_camera_rig,
)


def register_all_tools(mcp: FastMCP) -> None:
    """Register all 19 MorphoMesh tools onto the FastMCP instance."""
    # 7 Canonical Creature Tools
    mcp.tool(name="morphomesh_generate_concept")(morphomesh_generate_concept)
    mcp.tool(name="morphomesh_create_3d_asset")(morphomesh_create_3d_asset)
    mcp.tool(name="morphomesh_optimize_topology")(morphomesh_optimize_topology)
    mcp.tool(name="morphomesh_auto_rig")(morphomesh_auto_rig)
    mcp.tool(name="morphomesh_blender_execute")(morphomesh_blender_execute)
    mcp.tool(name="morphomesh_get_scene_status")(morphomesh_get_scene_status)
    mcp.tool(name="morphomesh_render_preview")(morphomesh_render_preview)

    # 2 Animation Tools
    mcp.tool(name="morphomesh_animate_asset")(morphomesh_animate_asset)
    mcp.tool(name="morphomesh_list_animations")(morphomesh_list_animations)

    # 7 Human Tools
    mcp.tool(name="morphomesh_create_human_asset")(morphomesh_create_human_asset)
    mcp.tool(name="morphomesh_auto_rig_human")(morphomesh_auto_rig_human)
    mcp.tool(name="morphomesh_setup_human_materials")(morphomesh_setup_human_materials)
    mcp.tool(name="morphomesh_groom_human")(morphomesh_groom_human)
    mcp.tool(name="morphomesh_dress_human")(morphomesh_dress_human)
    mcp.tool(name="morphomesh_assemble_master_character")(morphomesh_assemble_master_character)
    mcp.tool(name="morphomesh_export_production_character")(morphomesh_export_production_character)

    # 3 Inspection Tools
    mcp.tool(name="morphomesh_setup_inspector_camera_rig")(morphomesh_setup_inspector_camera_rig)
    mcp.tool(name="morphomesh_capture_viewport")(morphomesh_capture_viewport)
    mcp.tool(name="morphomesh_critique_visual_quality")(morphomesh_critique_visual_quality)


__all__ = [
    "register_all_tools",
]
