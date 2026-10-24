"""
MorphoMesh Tools Subsystem: Environment Tool Gating & Matrix Filtering.

Controls tool visibility and discovery across FastMCP list_tools and low-level JSON-RPC
request handlers based on environment flags (MORPHOMESH_INCLUDE_ALL_TOOLS,
MORPHOMESH_INCLUDE_HUMAN_TOOLS, MORPHOMESH_INCLUDE_INSPECTION_TOOLS,
MORPHOMESH_INCLUDE_ANIMATION_TOOLS).
"""

from __future__ import annotations

import os
from typing import Set

import mcp.types as mcp_types
from mcp.server.fastmcp import FastMCP

CREATURE_TOOL_NAMES: Set[str] = {
    "morphomesh_generate_concept",
    "morphomesh_create_3d_asset",
    "morphomesh_optimize_topology",
    "morphomesh_auto_rig",
    "morphomesh_blender_execute",
    "morphomesh_get_scene_status",
    "morphomesh_render_preview",
}

HUMAN_TOOL_NAMES: Set[str] = {
    "morphomesh_create_human_asset",
    "morphomesh_auto_rig_human",
    "morphomesh_setup_human_materials",
    "morphomesh_groom_human",
    "morphomesh_dress_human",
    "morphomesh_assemble_master_character",
    "morphomesh_export_production_character",
}

INSPECTION_TOOL_NAMES: Set[str] = {
    "morphomesh_setup_inspector_camera_rig",
    "morphomesh_capture_viewport",
    "morphomesh_critique_visual_quality",
}

ANIMATION_TOOL_NAMES: Set[str] = {
    "morphomesh_animate_asset",
    "morphomesh_list_animations",
}

ALL_TOOL_NAMES: Set[str] = CREATURE_TOOL_NAMES | HUMAN_TOOL_NAMES | INSPECTION_TOOL_NAMES


def _get_active_allowed_tool_names() -> Set[str]:
    """Resolve allowed tool names based on environment flags."""
    all_flag = os.environ.get("MORPHOMESH_INCLUDE_ALL_TOOLS", "").strip().lower()
    if all_flag in ("1", "true", "yes", "all"):
        allowed = set(ALL_TOOL_NAMES)
    else:
        allowed = set(CREATURE_TOOL_NAMES)
        human_flag = os.environ.get("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "").strip().lower()
        if human_flag in ("1", "true", "yes", "all"):
            allowed |= HUMAN_TOOL_NAMES

        insp_flag = os.environ.get("MORPHOMESH_INCLUDE_INSPECTION_TOOLS", "").strip().lower()
        if insp_flag in ("1", "true", "yes", "all"):
            allowed |= INSPECTION_TOOL_NAMES

    anim_flag = os.environ.get("MORPHOMESH_INCLUDE_ANIMATION_TOOLS", "").strip().lower()
    if anim_flag in ("1", "true", "yes", "all"):
        allowed |= ANIMATION_TOOL_NAMES

    return allowed


def apply_tool_gating(mcp: FastMCP) -> None:
    """
    Wrap FastMCP list_tools and low-level JSON-RPC handler with environment gating.
    Preserves direct invocability via mcp.call_tool().
    """
    _orig_fastmcp_list_tools = mcp.list_tools

    async def _filtered_list_tools(*args, **kwargs):
        tools = await _orig_fastmcp_list_tools(*args, **kwargs)
        allowed = _get_active_allowed_tool_names()
        return [t for t in tools if t.name in allowed]

    mcp.list_tools = _filtered_list_tools

    if mcp_types.ListToolsRequest in mcp._mcp_server.request_handlers:
        _orig_lowlevel_handler = mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest]

        async def _wrapped_lowlevel_list_tools(req: mcp_types.ListToolsRequest):
            res = await _orig_lowlevel_handler(req)
            allowed = _get_active_allowed_tool_names()
            filtered = [t for t in res.root.tools if t.name in allowed]
            return mcp_types.ServerResult(mcp_types.ListToolsResult(tools=filtered))

        mcp._mcp_server.request_handlers[mcp_types.ListToolsRequest] = _wrapped_lowlevel_list_tools


__all__ = [
    "CREATURE_TOOL_NAMES",
    "HUMAN_TOOL_NAMES",
    "INSPECTION_TOOL_NAMES",
    "ANIMATION_TOOL_NAMES",
    "ALL_TOOL_NAMES",
    "_get_active_allowed_tool_names",
    "apply_tool_gating",
]
